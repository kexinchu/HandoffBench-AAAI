import importlib.util
import json
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
