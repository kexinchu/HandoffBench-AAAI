import importlib.util
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from handoffbench.dataset import load_tasks
from handoffbench.providers import DeterministicFakeProvider
from handoffbench.runner import RunConfig
from handoffbench.transfer import FACTORIAL_CELLS, STATE_FIELDS, TransferKind


def _cli_module():
    path = Path(__file__).parents[1] / "scripts/run_pilot.py"
    spec = importlib.util.spec_from_file_location("pilot_cli", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_independent_jobs_write_unique_atomic_artifacts(tmp_path):
    cli = _cli_module()
    record = load_tasks()[0]
    raw = json.dumps({"receiver_state": {field: [] for field in STATE_FIELDS},
                      "action": {"name": "ask_user", "arguments": {"slot": "change_fee_consent"},
                                 "rationale": "need consent"}})
    jobs = []
    for seed in (3, 4):
        config = RunConfig("fake", TransferKind.FULL_HISTORY, seed=seed, max_turns=1)
        path = tmp_path / f"seed-{seed}.json"
        jobs.append((record, "full_history", config, path,
                     lambda raw=raw: DeterministicFakeProvider([raw])))
    with ThreadPoolExecutor(max_workers=2) as pool:
        paths = list(pool.map(lambda args: cli.execute_job(*args), jobs))
    assert len(set(paths)) == 2
    values = [json.loads(path.read_text()) for path in paths]
    assert {value["seed"] for value in values} == {3, 4}
    assert all(value["status"] == "ok" for value in values)
    assert not list(tmp_path.rglob("*.tmp"))


def test_factorial_block_reuses_one_source_across_eight_cells_with_workers(tmp_path):
    cli = _cli_module()
    record = load_tasks()[0]
    state = {field: [] for field in STATE_FIELDS}
    source = json.dumps({"state": state, "provenance": []})
    receiver = json.dumps({
        "receiver_state": state,
        "action": {"name": "ask_user", "arguments": {"slot": "change_fee_consent"},
                   "rationale": "need consent"},
    })
    source_calls = []

    class SchemaProvider:
        last_usage = None

        def complete(self, messages, **kwargs):
            if kwargs.get("schema_name") == "factorial_source_artifact":
                source_calls.append(1)
                self.last_usage = {"prompt_tokens": 101, "completion_tokens": 23}
                return source
            self.last_usage = {"prompt_tokens": 41, "completion_tokens": 17}
            return receiver

    jobs = []
    for cell_id, cell in FACTORIAL_CELLS.items():
        config = RunConfig("fake", TransferKind.FACTORIAL, seed=77, max_turns=1,
                           factorial_cell=cell)
        jobs.append((record, cell_id, config, tmp_path / f"{cell_id}.json"))
    factory = SchemaProvider
    shared = cli.prepare_factorial_sources(jobs, factory, workers=4)
    assert len(shared) == 1
    assert len(source_calls) == 1, "the block must make one physical source call"
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(cli.execute_job, *job, factory,
                               shared[cli.factorial_block_key(job[0], job[2])]) for job in jobs]
        paths = [future.result() for future in futures]
    runs = [json.loads(path.read_text()) for path in paths]
    assert len({run["source_hash"] for run in runs}) == 1
    assert len({run["source_raw"] for run in runs}) == 1
    assert len({run["calls"][0]["prompt_hash"] for run in runs}) == 1
    assert len({run["calls"][0]["response_schema_hash"] for run in runs}) == 1
    assert all(run["calls"][0]["usage"] == {
        "prompt_tokens": 101, "completion_tokens": 23
    } for run in runs)
    assert all(run["source_reused_within_factorial_block"] is True for run in runs)
    assert all(run["metrics"]["input_tokens"] == 142 for run in runs)
    assert all(run["metrics"]["output_tokens"] == 40 for run in runs)
    assert all(run["metrics"]["validator_cost"] == 0.0 for run in runs)


def test_cli_persists_temperature_and_protocol_version(tmp_path, monkeypatch):
    cli = _cli_module()
    record = load_tasks()[0]
    raw = json.dumps({
        "receiver_state": {field: [] for field in STATE_FIELDS},
        "action": {"name": "ask_user", "arguments": {"slot": "change_fee_consent"},
                   "rationale": "need consent"},
    })

    class Provider:
        last_usage = {"prompt_tokens": 5, "completion_tokens": 3}

        def __init__(self, *_args, **_kwargs):
            pass

        def complete(self, *_args, **_kwargs):
            return raw

    monkeypatch.setattr(cli, "OpenAICompatibleProvider", Provider)
    monkeypatch.setattr(sys, "argv", [
        "run_pilot.py", "--data", str(Path(__file__).parents[1] / "data/tasks/dev/pilot.json"),
        "--base-url", "http://unused/v1", "--model", "fake",
        "--tasks", record.episode.task_id, "--methods", "full_history",
        "--seeds", "19", "--max-turns", "1", "--temperature", "0.7",
        "--protocol-version", "handoffbench-confirmatory-v3",
        "--output-dir", str(tmp_path),
    ])
    assert cli.main() == 0
    run = json.loads(next((tmp_path / "runs").rglob("*.json")).read_text())
    assert run["config"]["temperature"] == 0.7
    assert run["config"]["protocol_version"] == "handoffbench-confirmatory-v3"
    assert run["metrics"]["output_tokens"] == 3
    assert run["metrics"]["validator_cost"] == 0.0


def test_factorial_source_provider_failure_fans_out_as_complete_itt_records(tmp_path):
    cli = _cli_module()
    record = load_tasks()[0]
    source_calls = []

    class FailingProvider:
        last_usage = None

        def complete(self, _messages, **kwargs):
            source_calls.append(kwargs["schema_name"])
            raise RuntimeError("source endpoint unavailable")

    jobs = []
    for cell_id, cell in FACTORIAL_CELLS.items():
        config = RunConfig("fake", TransferKind.FACTORIAL, seed=31, max_turns=1,
                           factorial_cell=cell)
        jobs.append((record, config.transfer_config.cell_id, config,
                     tmp_path / f"{cell_id}.json"))
    shared = cli.prepare_factorial_sources(jobs, FailingProvider, workers=2)
    assert len(source_calls) == 1
    source = next(iter(shared.values()))
    assert source["error"]["stage"] == "source_provider"
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = [future.result() for future in [
            pool.submit(cli.execute_job, *job, FailingProvider,
                        source) for job in jobs
        ]]
    runs = [json.loads(path.read_text()) for path in paths]
    assert len({run["source_hash"] for run in runs}) == 1
    assert all(run["status"] == "error" and run["source_stage_failure"] is True
               for run in runs)
    assert all(len(run["calls"]) == 1 for run in runs)
    assert all(run["calls"][0]["source_output_hash"] == run["source_hash"] for run in runs)
    assert all(run["metrics"] == {
        "strict_success": 0, "macro_state_f1": 0,
        "critical_errors": len(record.episode.scoring.critical_keys),
        "input_tokens": 0, "output_tokens": 0, "validator_cost": 0.0,
    } for run in runs)
    recovered = cli.shared_source_from_run(runs[0])
    assert recovered is not None and cli.source_signature(recovered) == cli.source_signature(source)


def test_factorial_source_parse_failure_preserves_raw_usage_and_hash(tmp_path):
    cli = _cli_module()
    record = load_tasks()[0]

    class InvalidJsonProvider:
        last_usage = None

        def complete(self, _messages, **_kwargs):
            self.last_usage = {"prompt_tokens": 13, "completion_tokens": 7}
            return "not-json"

    cell = next(iter(FACTORIAL_CELLS.values()))
    config = RunConfig("fake", TransferKind.FACTORIAL, seed=41, max_turns=1,
                       factorial_cell=cell)
    job = (record, config.transfer_config.cell_id, config, tmp_path / "parse.json")
    shared = cli.prepare_factorial_sources([job], InvalidJsonProvider, workers=1)
    source = next(iter(shared.values()))
    assert source["error"]["stage"] == "source_parse"
    path = cli.execute_job(*job, InvalidJsonProvider, source)
    run = json.loads(path.read_text())
    assert run["source_raw"] == "not-json"
    assert run["source_hash"] == hashlib.sha256(b"not-json").hexdigest()
    assert run["metrics"]["input_tokens"] == 13
    assert run["metrics"]["output_tokens"] == 7
    assert run["metrics"]["validator_cost"] == 0.0
