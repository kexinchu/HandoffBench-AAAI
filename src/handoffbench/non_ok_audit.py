"""Post-confirmatory descriptive accounting for non-OK scheduled runs.

This module is intentionally separate from the sealed confirmatory analyzer.
It only describes validated raw rows and never recomputes or changes a
confirmatory estimand, inference result, or execution seal.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable


ANALYSIS_CONTRACT = "post_confirmatory_non_ok_audit_v1"
ANALYSIS_STATUS = "exploratory_descriptive"
FACTOR_LEVELS = {
    "typing": ("free_form", "typed", "not_applicable"),
    "provenance": ("absent", "trace_linked", "not_applicable"),
    "checks": ("absent", "executable", "not_applicable"),
    "enforcement": ("advisory", "enforced", "not_applicable"),
}


def _rate(non_ok_rows: int, total_rows: int) -> dict[str, float | int]:
    return {
        "non_ok_rows": non_ok_rows,
        "total_rows": total_rows,
        "non_ok_rate": non_ok_rows / total_rows if total_rows else 0.0,
        "non_ok_percent": 100 * non_ok_rows / total_rows if total_rows else 0.0,
    }


def _categorical_breakdown(
    rows: Iterable[dict[str, Any]],
    key: Callable[[dict[str, Any]], str],
    categories: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    totals = Counter(key(row) for row in rows)
    non_ok = Counter(key(row) for row in rows if row.get("status") != "ok")
    labels = sorted(set(categories or ()) | set(totals) | set(non_ok))
    return [{"group": label, **_rate(non_ok[label], totals[label])} for label in labels]


def _factor_level(run: dict[str, Any], factor: str) -> str:
    config = run.get("config")
    cell = config.get("factorial_cell") if isinstance(config, dict) else None
    if not isinstance(cell, dict):
        return "not_applicable"
    if factor == "enforcement":
        return "enforced" if config.get("enforce_action_gates") else "advisory"
    value = cell.get(factor)
    return str(value) if value in FACTOR_LEVELS[factor] else "not_applicable"


def classify_error_stage(run: dict[str, Any]) -> str:
    """Classify only the validator's recorded error prefix, without inference."""
    error = run.get("error") if isinstance(run.get("error"), dict) else {}
    error_type = str(error.get("type", ""))
    message = str(error.get("message", ""))
    if message.startswith("source transfer is not valid JSON"):
        return "source_transfer_parse"
    if error_type == "JSONDecodeError":
        return "receiver_output_parse"
    if message.startswith("receiver_state "):
        return "receiver_state_validation"
    if message.startswith("receiver selected action outside visible catalog"):
        return "receiver_action_validation"
    return "other_model_output_or_validation"


def _error_type(run: dict[str, Any]) -> str:
    error = run.get("error") if isinstance(run.get("error"), dict) else {}
    return str(error.get("type", "missing_error_type"))


def _error_message(run: dict[str, Any]) -> str:
    error = run.get("error") if isinstance(run.get("error"), dict) else {}
    return str(error.get("message", "missing_error_message"))


def analyze_non_ok_rows(manifest: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a deterministic, descriptive audit of validated scheduled rows."""
    design = manifest["confirmatory_design"]
    models = [str(model) for model in design["models"]]
    conditions = [str(condition) for condition in design["conditions"]]
    non_ok = [run for run in runs if run.get("status") != "ok"]
    status_categories = sorted({str(run.get("status", "missing_status")) for run in runs})

    condition_model_categories = [
        f"{model}|{condition}" for model in models for condition in conditions
    ]
    reported_strict = [
        (run.get("metrics") or {}).get("strict_success")
        for run in non_ok
        if isinstance(run.get("metrics"), dict)
    ]
    reported_macro_f1 = [
        (run.get("metrics") or {}).get("macro_state_f1")
        for run in non_ok
        if isinstance(run.get("metrics"), dict)
    ]

    return {
        "analysis_contract": ANALYSIS_CONTRACT,
        "analysis_status": ANALYSIS_STATUS,
        "confirmatory_inference": False,
        "scope": (
            "Post-confirmatory descriptive audit of non-OK rows in the two raw "
            "roots validated by the v3.4.1 execution seal. It does not alter "
            "sealed analysis, results, raw runs, or the execution seal."
        ),
        "denominator": "all 8,800 validated scheduled ITT rows",
        "error_stage_rule": {
            "source_transfer_parse": "message starts with 'source transfer is not valid JSON'",
            "receiver_output_parse": "error type is JSONDecodeError after source-transfer parsing",
            "receiver_state_validation": "message starts with 'receiver_state '",
            "receiver_action_validation": (
                "message starts with 'receiver selected action outside visible catalog'"
            ),
            "other_model_output_or_validation": "all remaining non-OK validator records",
        },
        "overall": {
            **_rate(len(non_ok), len(runs)),
            "ok_rows": len(runs) - len(non_ok),
        },
        "breakdowns": {
            "by_status": _categorical_breakdown(runs, lambda row: str(row.get("status")), status_categories),
            "by_model": _categorical_breakdown(runs, lambda row: str(row["model"]), models),
            "by_condition": _categorical_breakdown(runs, lambda row: str(row["method"]), conditions),
            "by_model_condition": _categorical_breakdown(
                runs,
                lambda row: f"{row['model']}|{row['method']}",
                condition_model_categories,
            ),
            "by_factor_level": {
                factor: _categorical_breakdown(
                    runs,
                    lambda row, factor=factor: _factor_level(row, factor),
                    FACTOR_LEVELS[factor],
                )
                for factor in sorted(FACTOR_LEVELS)
            },
            "by_error_stage": _categorical_breakdown(
                non_ok, classify_error_stage
            ),
            "by_error_type": _categorical_breakdown(non_ok, _error_type),
            "by_error_message": _categorical_breakdown(non_ok, _error_message),
        },
        "success_treatment": {
            "formal_strict_success_rule": (
                "the sealed analyzer assigns strict_success=1 only when status is ok "
                "and success is truthy; every non-OK row therefore receives zero"
            ),
            "formal_macro_state_f1_rule": (
                "the sealed analyzer assigns macro_state_f1=0 to every non-OK row"
            ),
            "non_ok_rows_with_formal_strict_success_zero": len(non_ok),
            "non_ok_rows_with_formal_macro_state_f1_zero": len(non_ok),
            "reported_strict_success_metric_all_zero": all(value == 0 for value in reported_strict),
            "reported_macro_state_f1_metric_all_zero": all(value == 0 for value in reported_macro_f1),
            "reported_metric_rows_checked": len(reported_strict),
        },
    }
