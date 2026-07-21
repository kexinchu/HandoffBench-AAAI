import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from handoffbench.dataset import public_action_contract
from handoffbench.transfer import STATE_FIELDS


ROOT = Path(__file__).parents[1]


def _module():
    path = ROOT / "scripts/run_confirmatory.py"
    spec = importlib.util.spec_from_file_location("confirmatory_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _plan_fixture(tmp_path):
    runner = _module()
    config = yaml.safe_load((ROOT / "configs/confirmatory_v3.yaml").read_text())
    config["project_root"] = str(ROOT)
    manifest = json.loads((ROOT / "data/splits/confirmatory_v3.1.sealed.json").read_text())
    design = runner.preflight_cli.confirmatory_design(config, ROOT)
    manifest["confirmatory_design"] = design
    manifest_path = tmp_path / "sealed.json"
    manifest_path.write_text(json.dumps(manifest))
    config["sealed_manifest"] = str(manifest_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    plan = runner.validated_plan(config_path, verify_preflight=False)
    return runner, plan


def test_plan_has_exactly_8800_unique_rows_and_44_bound_config_hashes(tmp_path):
    runner, plan = _plan_fixture(tmp_path)
    rows = plan["rows"]
    keys = {(row["task_id"], row["model"], row["seed"], row["condition"])
            for row in rows}
    assert len(rows) == len(keys) == 8800
    assert len(plan["design"]["config_hashes"]) == 44
    assert {row["config_hash"] for row in rows} == set(
        plan["design"]["config_hashes"].values()
    )
    for row in rows:
        assert row["config_hash"] == plan["design"]["config_hashes"][
            f"{row['model']}|{row['seed']}|{row['condition']}"
        ]

    selected = runner.dry_run_payload(plan, [plan["design"]["models"][0]])
    assert selected["counts"]["all_scheduled_rows"] == 8800
    assert selected["counts"]["selected_scheduled_rows"] == 4400
    assert selected["counts"]["unique_selected_rows"] == 4400


def test_dry_run_builds_schedule_without_constructing_or_calling_provider(tmp_path, monkeypatch):
    runner, plan = _plan_fixture(tmp_path)

    class ForbiddenProvider:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("dry-run must not construct a provider")

    monkeypatch.setattr(runner, "OpenAICompatibleProvider", ForbiddenProvider)
    payload = runner.dry_run_payload(plan)
    assert payload["status"] == "validated_no_provider_calls"
    assert payload["counts"]["selected_scheduled_rows"] == 8800
    assert len(payload["schedule"]) == 8800


def test_health_failure_aborts_before_any_candidate_provider_call(tmp_path, monkeypatch):
    runner, plan = _plan_fixture(tmp_path)
    model = plan["design"]["models"][0]
    plan = copy.copy(plan)
    plan["rows"] = [row for row in plan["rows"] if row["model"] == model][:1]
    calls = []

    def fail_health(*_args, **_kwargs):
        raise ValueError("served model absent")

    class ForbiddenProvider:
        def __init__(self, *_args, **_kwargs):
            calls.append("constructed")

        def complete(self, *_args, **_kwargs):
            calls.append("called")
            raise AssertionError("candidate call must not occur")

    monkeypatch.setattr(runner, "health_check", fail_health)
    monkeypatch.setattr(runner, "OpenAICompatibleProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="served model absent"):
        runner.execute(plan, [model], tmp_path / "out", {}, "EMPTY", 1, 1)
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_model_scoped_execution_is_resumable_and_reuses_one_factorial_source(
        tmp_path, monkeypatch):
    runner, full_plan = _plan_fixture(tmp_path)
    model = full_plan["design"]["models"][0]
    seed = full_plan["design"]["seeds"][0]
    task_id = full_plan["rows"][0]["task_id"]
    plan = copy.copy(full_plan)
    plan["rows"] = [row for row in full_plan["rows"]
                    if row["model"] == model and row["seed"] == seed
                    and row["task_id"] == task_id]
    plan["records"] = [record for record in full_plan["records"]
                       if record.episode.task_id == task_id]
    record = plan["records"][0]
    contract = public_action_contract(record)[0]
    arguments = {}
    for key, schema in contract["arguments"].items():
        if "enum" in schema:
            arguments[key] = schema["enum"][0]
        elif schema.get("type") == "boolean":
            arguments[key] = False
        else:
            arguments[key] = "unknown"
    state = {field: [] for field in STATE_FIELDS}
    source = json.dumps({"state": state, "provenance": []})
    receiver = json.dumps({
        "receiver_state": state,
        "action": {"name": contract["action"], "arguments": arguments,
                   "rationale": "test"},
    })
    physical_calls = []

    class Provider:
        last_usage = None

        def __init__(self, *_args, **_kwargs):
            pass

        def complete(self, _messages, **kwargs):
            physical_calls.append(kwargs.get("schema_name"))
            self.last_usage = {"prompt_tokens": 5, "completion_tokens": 2}
            return source if kwargs.get("schema_name") == "factorial_source_artifact" else receiver

    monkeypatch.setattr(runner, "health_check", lambda url, name, key, timeout: {
        "endpoint": url + "/models", "http_status": 200,
        "served_model_ids": [name], "response_sha256": "a" * 64,
        "server_header": "test-runtime",
    })
    monkeypatch.setattr(runner, "OpenAICompatibleProvider", Provider)
    output = tmp_path / "out"
    first = runner.execute(plan, [model], output, {model: "http://test/v1"},
                           "EMPTY", 1, 3)
    assert first == {"scheduled": 11, "resumed": 0, "written": 11}
    assert physical_calls.count("factorial_source_artifact") == 1
    assert len(list((output / model / "runs").rglob("*.json"))) == 11
    before = list(physical_calls)
    second = runner.execute(plan, [model], output, {model: "http://test/v1"},
                            "EMPTY", 1, 3)
    assert second == {"scheduled": 11, "resumed": 11, "written": 0}
    assert physical_calls == before
    ledger = json.loads((output / model / "execution_ledger.json").read_text())
    assert ledger["provider_health"]["server_header"] == "test-runtime"
    assert ledger["persisted_rows_for_model"] == 11
