"""Scoring and aggregation for resumable pilot runs."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import canonical_json, canonicalize
from .dataset import TaskRecord, primary_gold_claims
from .matching import maximum_weight_pairs
from .transfer import _CATEGORY_FIELD


def _atom(item: Any) -> tuple[str, str, Any] | None:
    if not isinstance(item, Mapping) or not {"key", "status", "value"} <= set(item):
        return None
    return str(item["key"]), str(item["status"]), item["value"]


def _overlap(reference: tuple[str, str, Any], candidate: tuple[str, str, Any]) -> float:
    if reference[:2] != candidate[:2]:
        return 0.0
    ref_value, candidate_value = reference[2], candidate[2]
    if isinstance(ref_value, list) and isinstance(candidate_value, list):
        ref_items = {canonical_json(value) for value in ref_value}
        candidate_items = {canonical_json(value) for value in candidate_value}
        if not ref_items:
            return float(not candidate_items)
        return len(ref_items & candidate_items) / len(ref_items)
    return float(canonical_json(ref_value) == canonical_json(candidate_value))


def score_receiver_state(record: TaskRecord, state: Mapping[str, Any] | None) -> dict[str, Any]:
    """Exact field-local claim matching against evaluator gold.

    Values use the gold value type normalizer. Invalid/duplicate predictions are
    retained as false positives rather than silently discarded.
    """
    state = state or {}
    field_scores: dict[str, dict[str, float | int]] = {}
    critical_errors = 0
    total_tp = total_fp = total_fn = 0
    critical_keys = set(record.episode.scoring.critical_keys)
    primary_claims = primary_gold_claims(record)
    for field in _CATEGORY_FIELD.values():
        gold_claims = [c for c in primary_claims if _CATEGORY_FIELD[c.category.value] == field]
        gold = [(c.key, c.status.value, canonicalize(c.value, c.value_type)) for c in gold_claims]
        predicted: list[tuple[str, str, Any] | None] = []
        for item in state.get(field, []) if isinstance(state.get(field, []), list) else [None]:
            atom = _atom(item)
            if atom is not None:
                matching = next((c for c in gold_claims if c.key == atom[0]), None)
                if matching is not None:
                    try:
                        atom = (atom[0], atom[1], canonicalize(item["value"], matching.value_type))
                    except (KeyError, TypeError, ValueError):
                        atom = None
            predicted.append(atom)
        pred = [p for p in predicted if p is not None]
        pairs = maximum_weight_pairs(gold, pred, lambda g, p: _overlap(g, p) + _overlap(p, g))
        matched_gold = sum(_overlap(gold[i], pred[j]) for i, j in pairs)
        matched_pred = sum(_overlap(pred[j], gold[i]) for i, j in pairs)
        precision_den, recall_den = len(predicted), len(gold)
        precision = matched_pred / precision_den if precision_den else (1.0 if not gold else 0.0)
        recall = matched_gold / recall_den if recall_den else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        tp, fp, fn = matched_gold, precision_den - matched_pred, recall_den - matched_gold
        total_tp += tp; total_fp += fp; total_fn += fn
        field_scores[field] = {"precision": precision, "recall": recall, "f1": f1,
                               "tp": tp, "fp": fp, "fn": fn}
        for claim in gold_claims:
            gold_atom = (claim.key, claim.status.value, canonicalize(claim.value, claim.value_type))
            if claim.key in critical_keys and max((_overlap(gold_atom, p) for p in pred), default=0) < 1:
                critical_errors += 1
    scored_fields = [field_scores[_CATEGORY_FIELD[category]]["f1"] for category in _CATEGORY_FIELD
                     if any(claim.category.value == category for claim in primary_claims)]
    macro = sum(scored_fields) / len(scored_fields) if scored_fields else 1.0
    return {"macro_state_f1": macro, "critical_errors": critical_errors,
            "field_scores": field_scores, "state_tp": total_tp,
            "state_fp": total_fp, "state_fn": total_fn}


def score_boundary_transfer(record: TaskRecord, receiver_states: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Score the pre-action, first receiver probe against boundary state G_b."""
    states = list(receiver_states)
    return score_receiver_state(record, states[0] if states else None)


def aggregate_runs(runs: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    for run in runs:
        metrics = run.get("metrics", {})
        rows.append({"task_id": run.get("task_id"), "method": run.get("method"),
                     "seed": run.get("seed"), "model": run.get("model"),
                     "status": run.get("status"), "strict_success": metrics.get("strict_success", 0),
                     "macro_state_f1": metrics.get("macro_state_f1", 0),
                     "critical_errors": metrics.get("critical_errors", 0),
                     "input_tokens": metrics.get("input_tokens")})
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["task_id"]), str(row["model"]), int(row["seed"]))].append(row)
    table = []
    for (task_id, model, seed), items in sorted(groups.items()):
        paired: dict[str, Any] = {"task_id": task_id, "model": model, "seed": seed}
        for item in sorted(items, key=lambda x: str(x["method"])):
            prefix = str(item["method"])
            for metric in ("strict_success", "macro_state_f1", "critical_errors", "input_tokens"):
                paired[f"{prefix}.{metric}"] = item[metric]
        table.append(paired)
    return rows, table


def write_summary(output_dir: Path, runs: Iterable[Mapping[str, Any]]) -> None:
    rows, table = aggregate_runs(runs)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps({"runs": rows, "paired_method_table": table}, indent=2))
    for name, values in (("summary.csv", rows), ("paired_methods.csv", table)):
        if values:
            with (output_dir / name).open("w", newline="", encoding="utf-8") as stream:
                fields = list(dict.fromkeys(key for row in values for key in row))
                writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(values)
