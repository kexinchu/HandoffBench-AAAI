from handoffbench.non_ok_audit import analyze_non_ok_rows, classify_error_stage


def _run(model: str, method: str, status: str, error: dict | None = None) -> dict:
    cell = None
    enforced = False
    if method.startswith("typed__"):
        cell = {"typing": "typed", "provenance": "absent", "checks": "executable"}
        enforced = method.endswith("__enforced")
    elif method.startswith("free_form__"):
        cell = {"typing": "free_form", "provenance": "trace_linked", "checks": "absent"}
    return {
        "model": model,
        "method": method,
        "status": status,
        "error": error,
        "config": {"factorial_cell": cell, "enforce_action_gates": enforced},
        "metrics": {"strict_success": 0, "macro_state_f1": 0},
    }


def test_non_ok_audit_reports_denominators_stages_and_itt_zero_credit() -> None:
    manifest = {
        "confirmatory_design": {
            "models": ["model-a", "model-b"],
            "conditions": ["gold_oracle", "free_form__trace_linked__absent__advisory", "typed__absent__executable__enforced"],
        }
    }
    runs = [
        _run("model-a", "gold_oracle", "ok"),
        _run("model-a", "free_form__trace_linked__absent__advisory", "error", {"type": "ValueError", "message": "receiver_state x"}),
        _run("model-b", "gold_oracle", "error", {"type": "JSONDecodeError", "message": "bad json"}),
        _run("model-b", "typed__absent__executable__enforced", "error", {"type": "ValueError", "message": "receiver selected action outside visible catalog: x"}),
    ]
    report = analyze_non_ok_rows(manifest, runs)

    assert report["analysis_status"] == "exploratory_descriptive"
    assert report["overall"] == {"non_ok_rows": 3, "total_rows": 4, "non_ok_rate": 0.75, "non_ok_percent": 75.0, "ok_rows": 1}
    assert report["breakdowns"]["by_model"][0]["group"] == "model-a"
    assert report["breakdowns"]["by_model"][0]["non_ok_rows"] == 1
    stages = {row["group"]: row["non_ok_rows"] for row in report["breakdowns"]["by_error_stage"]}
    assert stages == {"receiver_action_validation": 1, "receiver_output_parse": 1, "receiver_state_validation": 1}
    factors = {row["group"]: row["total_rows"] for row in report["breakdowns"]["by_factor_level"]["typing"]}
    assert factors == {"free_form": 1, "not_applicable": 2, "typed": 1}
    assert report["success_treatment"]["reported_strict_success_metric_all_zero"] is True
    assert report["success_treatment"]["non_ok_rows_with_formal_strict_success_zero"] == 3


def test_error_stage_rules_cover_source_parse_and_other() -> None:
    assert classify_error_stage({"error": {"type": "ValueError", "message": "source transfer is not valid JSON"}}) == "source_transfer_parse"
    assert classify_error_stage({"error": {"type": "RuntimeError", "message": "unclassified"}}) == "other_model_output_or_validation"
