"""Offline extraction → transport → utilization decomposition for saved runs."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable, Mapping

from .canonical import canonical_json
from .dataset import TaskRecord
from .transfer import STATE_FIELDS, checked_ehc, oracle_state


DIRECT_SOURCE_METHODS = {"structured_payload", "ehc"}


def _parse_json(raw: Any) -> Mapping[str, Any] | None:
    if not isinstance(raw, str):
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, Mapping) else None


def parse_source_artifact(run: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, str | None]:
    """Return directly atomized source state, or an explicit NA reason."""

    method = run.get("method")
    if method not in DIRECT_SOURCE_METHODS:
        return None, "source_state_not_directly_atomized"
    payload = _parse_json(run.get("source_raw"))
    if payload is None:
        return None, "source_raw_unparseable"
    state = payload.get("state") if method == "ehc" else payload
    if not isinstance(state, Mapping) or set(state) != set(STATE_FIELDS):
        return None, "source_state_schema_mismatch"
    return state, None


def _atoms(state: Mapping[str, Any] | None) -> tuple[list[str], int]:
    atoms: list[str] = []
    invalid = 0
    if state is None:
        return atoms, invalid
    for field in STATE_FIELDS:
        values = state.get(field)
        if not isinstance(values, list):
            invalid += 1
            continue
        for value in values:
            if not isinstance(value, Mapping) or not {"key", "status", "value"} <= set(value):
                invalid += 1
                continue
            atoms.append(canonical_json([field, value["key"], value["status"], value["value"]]))
    return atoms, invalid


def exact_fidelity(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    """One-to-one exact micro fidelity; duplicate candidates are false positives."""

    ref, ref_invalid = _atoms(reference)
    pred, pred_invalid = _atoms(candidate)
    ref_counts, pred_counts = Counter(ref), Counter(pred)
    tp = sum((ref_counts & pred_counts).values())
    fp = len(pred) + pred_invalid - tp
    fn = len(ref) + ref_invalid - tp
    precision = tp / (tp + fp) if tp + fp else (1.0 if not ref else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "retention": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn}


def analyze_run(
    record: TaskRecord,
    run: Mapping[str, Any],
    *,
    reconstruct_checked_ehc: bool = False,
) -> dict[str, Any]:
    source, na_reason = parse_source_artifact(run)
    receiver = run.get("boundary_receiver_state")
    receiver = receiver if isinstance(receiver, Mapping) else None
    row: dict[str, Any] = {
        "task_id": run.get("task_id"), "method": run.get("method"),
        "model": run.get("model"), "seed": run.get("seed"),
        "success": bool(run.get("success")), "source_state_na_reason": na_reason,
        "extraction": None, "transport": None, "checked_transport": None,
        "validation": None,
    }
    if source is not None:
        row["extraction"] = exact_fidelity(oracle_state(record), source)
        if receiver is not None:
            row["transport"] = exact_fidelity(source, receiver)
    if reconstruct_checked_ehc and run.get("method") == "ehc" and source is not None:
        payload = _parse_json(run.get("source_raw"))
        try:
            checked = checked_ehc(
                record, source, list(payload.get("provenance", [])), list(payload.get("checks", []))
            )
        except (KeyError, TypeError, ValueError) as error:
            row["validation"] = {"reconstructed": False, "error": str(error)}
        else:
            raw_atoms, raw_invalid = _atoms(source)
            clean_atoms, clean_invalid = _atoms(checked["state"])
            raw_n, clean_n = len(raw_atoms) + raw_invalid, len(clean_atoms) + clean_invalid
            row["validation"] = {
                "reconstructed": True,
                "retained": clean_n,
                "quarantined": checked["audit"]["quarantined_claim_count"],
                "retention_rate": clean_n / raw_n if raw_n else 1.0,
                "strict_validation_pass": checked["audit"]["strict_validation_pass"],
            }
            if receiver is not None:
                row["checked_transport"] = exact_fidelity(checked["state"], receiver)
    return row


def analyze_paired_runs(
    records: Iterable[TaskRecord],
    runs: Iterable[Mapping[str, Any]],
    *,
    reconstruct_checked_ehc: bool = False,
) -> list[dict[str, Any]]:
    """Analyze runs and attach same-task/model/seed gold-oracle outcomes."""

    by_task = {record.episode.task_id: record for record in records}
    runs = list(runs)
    oracles = {
        (run.get("task_id"), run.get("model"), run.get("seed")): bool(run.get("success"))
        for run in runs if run.get("method") == "gold_oracle" and run.get("status") == "ok"
    }
    rows = []
    for run in runs:
        record = by_task.get(str(run.get("task_id")))
        if record is None:
            continue
        row = analyze_run(record, run, reconstruct_checked_ehc=reconstruct_checked_ehc)
        oracle = oracles.get((run.get("task_id"), run.get("model"), run.get("seed")))
        row["utilization_ceiling"] = oracle
        row["handoff_regret"] = None if oracle is None else bool(oracle and not run.get("success"))
        rows.append(row)
    return rows
