import importlib.util
from pathlib import Path


PATH = Path(__file__).parents[1] / "scripts/analyze_counterfactual.py"
SPEC = importlib.util.spec_from_file_location("analyze_counterfactual", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def _run(task, method, success, f1=1.0):
    return {"task_id": task, "method": method, "model": "m", "seed": 1,
            "status": "ok", "success": success,
            "metrics": {"macro_state_f1": f1, "critical_errors": 0, "input_tokens": 10}}


def test_summary_stratifies_variants_and_reports_wilson_interval():
    rows = MODULE.summarize([
        _run("cf_01_unknown", "ehc", True),
        _run("cf_01_denied", "ehc", False),
    ])
    overall = next(row for row in rows if row["method"] == "ehc" and row["variant"] == "all")
    assert overall["n_ok"] == 2
    assert overall["success_rate"] == 0.5
    assert 0 < overall["success_ci_low"] < overall["success_ci_high"] < 1


def test_paired_comparison_aligns_task_model_seed():
    runs = [
        _run("cf_01_unknown", "ehc", True),
        _run("cf_01_unknown", "structured_payload", False),
        _run("cf_02_unknown", "ehc", False),
        _run("cf_02_unknown", "structured_payload", False),
    ]
    result = MODULE.paired_ehc_vs_structured(runs, draws=1000)
    assert result["n_pairs"] == 2
    assert result["ehc_minus_structured_success"] == 0.5
    assert result["ehc_only_success"] == 1


def test_executable_capsule_alias_pairs_with_structured():
    result = MODULE.paired_ehc_vs_structured([
        _run("cf_01_unknown", "executable_capsule", True),
        _run("cf_01_unknown", "structured_payload", False),
    ], draws=100)
    assert result["n_pairs"] == 1
    assert result["ehc_only_success"] == 1


def test_gold_state_oracle_alias_summarizes_with_gold_oracle():
    rows = MODULE.summarize([
        _run("cf_01_unknown", "gold_state_oracle", True),
        _run("cf_02_unknown", "gold_oracle", False),
    ])
    overall = next(row for row in rows if row["variant"] == "all")
    assert overall["method"] == "gold_oracle"
    assert overall["n_expected"] == 2


def test_error_run_remains_in_intent_to_treat_denominator():
    error = _run("cf_02_denied", "ehc", False)
    error["status"] = "error"
    error["metrics"]["macro_state_f1"] = 0
    rows = MODULE.summarize([_run("cf_01_unknown", "ehc", True), error])
    overall = next(row for row in rows if row["variant"] == "all")
    assert overall["n_expected"] == 2 and overall["n_ok"] == 1
    assert overall["success_rate"] == 0.5


def test_paired_error_without_success_key_counts_as_failure():
    ehc_error = _run("cf_01_unknown", "ehc", False)
    ehc_error["status"] = "error"
    ehc_error.pop("success")
    result = MODULE.paired_ehc_vs_structured([
        ehc_error, _run("cf_01_unknown", "structured_payload", True)
    ], draws=100)
    assert result["n_pairs"] == 1
    assert result["structured_only_success"] == 1
