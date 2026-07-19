import importlib.util
import json
from pathlib import Path

import pytest


PATH = Path(__file__).parents[1] / "scripts/analyze_factorial.py"
SPEC = importlib.util.spec_from_file_location("analyze_factorial", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def _cube():
    runs = []
    for typing in ("free_form", "typed"):
        for provenance in ("absent", "trace_linked"):
            for checks in ("absent", "executable"):
                success = typing == "typed"
                runs.append({"task_id": "cf_01_unknown", "model": "m", "seed": 1,
                             "method": f"{typing}__{provenance}__{checks}__advisory",
                             "status": "ok", "success": success,
                             "metrics": {"macro_state_f1": float(success), "critical_errors": 0},
                             "source_raw": "same", "calls": [{"prompt_hash": "p",
                             "response_schema_hash": "s", "usage": {"input_tokens": 10}}]})
    return runs


def test_effect_coding_recovers_high_minus_low_typing_effect():
    result = MODULE.estimate(_cube(), draws=100)
    assert result["effects"]["strict_success"]["typing"]["effect"] == 1
    assert result["effects"]["strict_success"]["provenance"]["effect"] == 0


def test_fairness_audit_requires_identical_source_artifact_prompt_and_schema():
    runs = _cube()
    assert MODULE.fairness_audit(runs)["pass"]
    runs[0]["source_raw"] = "different"
    assert not MODULE.fairness_audit(runs)["pass"]


def test_fairness_audit_checks_shared_source_usage_metadata():
    runs = _cube()
    runs[0]["calls"][0]["usage"] = {"input_tokens": 99}
    result = MODULE.fairness_audit(runs)
    assert not result["pass"]
    assert result["failures"][0]["source_usage_variants"] == 2


def test_load_runs_combines_model_directories(tmp_path):
    directories = []
    for model in ("m1", "m2"):
        directory = tmp_path / model
        run_dir = directory / "runs"
        run_dir.mkdir(parents=True)
        run = _cube()[0]
        run["model"] = model
        (run_dir / "run.json").write_text(json.dumps(run))
        directories.append(str(directory))
    assert {run["model"] for run in MODULE.load_runs(directories)} == {"m1", "m2"}


def test_load_runs_rejects_duplicate_scheduled_cell(tmp_path):
    directories = []
    for name in ("a", "b"):
        directory = tmp_path / name
        run_dir = directory / "runs"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(json.dumps(_cube()[0]))
        directories.append(str(directory))
    with pytest.raises(ValueError, match="duplicate scheduled cell"):
        MODULE.load_runs(directories)
