"""Deterministic double-annotation agreement and adjudication-queue analysis."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .canonical import canonical_json, canonicalize
from .matching import maximum_weight_pairs


@dataclass(frozen=True)
class AnnotationSet:
    annotator_id: str
    tasks: tuple[dict[str, Any], ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _no_nulls(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return all(_no_nulls(item) for item in value.values())
    if isinstance(value, list):
        return bool(value) and all(_no_nulls(item) for item in value)
    return value != ""


def _json_tasks(path: Path) -> AnnotationSet:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) < {"annotator_id", "annotations"}:
        raise ValueError(f"{path}: JSON requires annotator_id and annotations")
    if "assignments" in payload or any("response" in item and item.get("response") is None
                                        for item in payload.get("annotations", [])
                                        if isinstance(item, dict)):
        raise ValueError(f"{path}: assignment/null-response files are not completed annotations")
    return AnnotationSet(str(payload["annotator_id"]), tuple(payload["annotations"]))


def _csv_tasks(path: Path) -> AnnotationSet:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    annotators = {row.get("annotator_id") for row in rows}
    if len(annotators) != 1 or None in annotators or "" in annotators:
        raise ValueError(f"{path}: CSV must contain one annotator_id")
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_id = row.get("task_id", "")
        task = grouped.setdefault(task_id, {
            "task_id": task_id, "template_family": row.get("template_family") or task_id,
            "claims": [], "action_sequence": None,
        })
        if row.get("record_type") == "claim":
            try:
                value = json.loads(row["value_json"])
            except (KeyError, json.JSONDecodeError) as error:
                raise ValueError(f"{path}: invalid value_json for {task_id}") from error
            task["claims"].append({
                "key": row.get("claim_key"), "category": row.get("category"),
                "status": row.get("status"), "value": value,
                "criticality": row.get("criticality"),
                "provenance": [{"trace_id": row.get("trace_id"),
                                "source_type": row.get("source_type"),
                                "field_path": row.get("field_path")}],
            })
        if row.get("action_sequence_json"):
            sequence = json.loads(row["action_sequence_json"])
            if task["action_sequence"] is not None and task["action_sequence"] != sequence:
                raise ValueError(f"{path}: conflicting action sequences for {task_id}")
            task["action_sequence"] = sequence
    return AnnotationSet(str(next(iter(annotators))), tuple(grouped.values()))


def load_locked_annotations(
    first: str | Path, second: str | Path, lock_manifest: str | Path
) -> tuple[AnnotationSet, AnnotationSet]:
    paths = [Path(first).resolve(), Path(second).resolve()]
    if paths[0] == paths[1]:
        raise ValueError("two distinct annotation files are required")
    manifest_path = Path(lock_manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("locked") is not True or not isinstance(manifest.get("inputs"), list):
        raise ValueError("lock manifest must have locked=true and inputs")
    locked = {
        (Path(item["path"]) if Path(item["path"]).is_absolute()
         else manifest_path.parent / item["path"]).resolve(): item
        for item in manifest["inputs"]
    }
    if set(paths) != set(locked):
        raise ValueError("lock manifest paths do not exactly cover both inputs")
    for path in paths:
        if locked[path].get("sha256") != _sha256(path):
            raise ValueError(f"locked input hash mismatch: {path}")
    loaded = [(_csv_tasks(path) if path.suffix.lower() == ".csv" else _json_tasks(path))
              for path in paths]
    if loaded[0].annotator_id == loaded[1].annotator_id:
        raise ValueError("independent annotation files need distinct annotator IDs")
    for data, path in zip(loaded, paths):
        _validate_complete(data, path)
        expected_id = locked[path].get("annotator_id")
        if expected_id and expected_id != data.annotator_id:
            raise ValueError(f"annotator ID does not match lock manifest: {path}")
    expected_tasks = manifest.get("expected_task_ids")
    task_sets = [{task["task_id"] for task in data.tasks} for data in loaded]
    if task_sets[0] != task_sets[1]:
        raise ValueError("annotations do not provide complete double coverage")
    families = [{task["task_id"]: task.get("template_family") or task["task_id"]
                 for task in data.tasks} for data in loaded]
    if families[0] != families[1]:
        raise ValueError("annotators disagree on locked task-family identities")
    if expected_tasks is not None and task_sets[0] != set(expected_tasks):
        raise ValueError("annotations do not cover locked expected_task_ids")
    return loaded[0], loaded[1]


def _validate_complete(data: AnnotationSet, path: Path) -> None:
    ids = [task.get("task_id") for task in data.tasks]
    if not ids or len(ids) != len(set(ids)) or any(not task_id for task_id in ids):
        raise ValueError(f"{path}: missing or duplicate task coverage")
    for task in data.tasks:
        required = {"task_id", "claims", "action_sequence"}
        if (not required <= set(task) or not task.get("task_id") or
                not isinstance(task.get("claims"), list) or not task["claims"] or
                not isinstance(task.get("action_sequence"), list) or not task["action_sequence"]):
            raise ValueError(f"{path}: incomplete/null annotation for {task.get('task_id')}")
        keys = [claim.get("key") for claim in task["claims"]]
        if len(keys) != len(set(keys)) or any(not key for key in keys):
            raise ValueError(f"{path}: duplicate or missing claim key in {task['task_id']}")
        for claim in task["claims"]:
            if not _no_nulls({key: claim.get(key) for key in
                              ("key", "category", "status", "value", "criticality", "provenance")}):
                # JSON null is a valid typed value for unknown/not-applicable.
                if not (claim.get("value") is None and claim.get("status") in
                        {"unknown", "not_applicable"} and
                        _no_nulls({k: claim.get(k) for k in
                                   ("key", "category", "status", "criticality", "provenance")})):
                    raise ValueError(f"{path}: incomplete claim in {task['task_id']}")


def _value(claim: dict[str, Any]) -> str:
    return canonical_json(canonicalize(claim["value"]))


def _pointers(claim: dict[str, Any]) -> set[str]:
    return {canonical_json({key: pointer.get(key) for key in
                            ("trace_id", "source_type", "field_path")})
            for pointer in claim["provenance"]}


def _kappa(left: list[str], right: list[str]) -> float | None:
    labels = set(left) | set(right)
    if len(set(left)) < 2 or len(set(right)) < 2 or not left:
        return None
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    expected = sum((left.count(label) / len(left)) * (right.count(label) / len(right))
                   for label in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def _raw(matches: list[tuple[dict, dict]], field: str) -> dict[str, Any]:
    left = [str(a[field]) for a, _ in matches]
    right = [str(b[field]) for _, b in matches]
    agree = sum(a == b for a, b in zip(left, right))
    result = {"agree": agree, "denominator": len(matches),
              "rate": agree / len(matches) if matches else None}
    if field in {"category", "status", "criticality"}:
        result["cohen_kappa"] = _kappa(left, right)
    return result


def _task_counts(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    left, right = first["claims"], second["claims"]
    pairs = maximum_weight_pairs(left, right, lambda a, b: 1.0 if a["key"] == b["key"] else 0.0)
    matches = [(left[i], right[j]) for i, j in pairs]
    exact = sum(a["category"] == b["category"] and a["status"] == b["status"]
                and _value(a) == _value(b) for a, b in matches)
    pointer_tp = sum(len(_pointers(a) & _pointers(b)) for a, b in matches)
    pointer_left = sum(len(_pointers(claim)) for claim in left)
    pointer_right = sum(len(_pointers(claim)) for claim in right)
    disagreements = []
    for a, b in matches:
        fields = [field for field in ("category", "status", "criticality") if a[field] != b[field]]
        if _value(a) != _value(b): fields.append("value")
        if _pointers(a) != _pointers(b): fields.append("provenance")
        if fields:
            disagreements.append({"claim_key": a["key"], "fields": fields,
                                  "resolution_code": None})
    left_keys, right_keys = {c["key"] for c in left}, {c["key"] for c in right}
    disagreements.extend({"claim_key": key, "fields": ["missing_from_annotator_b"],
                          "resolution_code": None} for key in sorted(left_keys - right_keys))
    disagreements.extend({"claim_key": key, "fields": ["missing_from_annotator_a"],
                          "resolution_code": None} for key in sorted(right_keys - left_keys))
    return {
        "family": first.get("template_family") or second.get("template_family") or first["task_id"],
        "left_n": len(left), "right_n": len(right), "exact_claims": exact,
        "matches": matches, "pointer_tp": pointer_tp, "pointer_left": pointer_left,
        "pointer_right": pointer_right,
        "action_exact": canonical_json(first["action_sequence"]) == canonical_json(second["action_sequence"]),
        "disagreements": disagreements,
    }


def _aggregate(tasks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    tasks = list(tasks)
    left_n, right_n = sum(t["left_n"] for t in tasks), sum(t["right_n"] for t in tasks)
    tp = sum(t["exact_claims"] for t in tasks)
    precision, recall = (tp / right_n if right_n else 0), (tp / left_n if left_n else 0)
    matches = [match for task in tasks for match in task["matches"]]
    p_tp = sum(t["pointer_tp"] for t in tasks)
    p_left, p_right = sum(t["pointer_left"] for t in tasks), sum(t["pointer_right"] for t in tasks)
    p_precision, p_recall = (p_tp / p_right if p_right else 0), (p_tp / p_left if p_left else 0)
    value_matches = [(a | {"value_exact": _value(a)}, b | {"value_exact": _value(b)})
                     for a, b in matches]
    return {
        "claim": {"tp": tp, "annotator_a_denominator": left_n,
                  "annotator_b_denominator": right_n, "precision": precision, "recall": recall,
                  "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0},
        "category": _raw(matches, "category"), "status": _raw(matches, "status"),
        "value": _raw(value_matches, "value_exact"),
        "criticality": _raw(matches, "criticality"),
        "provenance": {"tp": p_tp, "annotator_a_denominator": p_left,
                       "annotator_b_denominator": p_right, "precision": p_precision,
                       "recall": p_recall,
                       "f1": 2 * p_precision * p_recall / (p_precision + p_recall)
                       if p_precision + p_recall else 0,
                       "exact_sets": sum(_pointers(a) == _pointers(b) for a, b in matches),
                       "exact_set_denominator": len(matches)},
        "action_sequence": {"agree": sum(t["action_exact"] for t in tasks),
                            "denominator": len(tasks),
                            "rate": sum(t["action_exact"] for t in tasks) / len(tasks)},
    }


def analyze_agreement(first: AnnotationSet, second: AnnotationSet, *, draws: int = 2000,
                      seed: int = 2027) -> dict[str, Any]:
    if draws < 1:
        raise ValueError("bootstrap draws must be positive")
    a = {task["task_id"]: task for task in first.tasks}
    b = {task["task_id"]: task for task in second.tasks}
    task_counts = [_task_counts(a[task_id], b[task_id]) for task_id in sorted(a)]
    point = _aggregate(task_counts)
    by_family: dict[str, list[dict[str, Any]]] = {}
    for task in task_counts:
        by_family.setdefault(task["family"], []).append(task)
    families = sorted(by_family)
    rng = random.Random(seed)
    paths = (("claim", "f1"), ("category", "rate"), ("status", "rate"),
             ("value", "rate"), ("criticality", "rate"), ("provenance", "f1"),
             ("action_sequence", "rate"))
    samples = {path: [] for path in paths}
    for _ in range(draws):
        chosen = [rng.choice(families) for _ in families]
        aggregate = _aggregate([task for family in chosen for task in by_family[family]])
        for path in paths:
            value = aggregate[path[0]][path[1]]
            if value is not None: samples[path].append(value)
    for path, values in samples.items():
        values.sort()
        if values:
            point[path[0]]["cluster_bootstrap_ci"] = [
                values[int(.025 * len(values))], values[max(0, int(.975 * len(values)) - 1)]
            ]
    queue = [{"task_id": task_id, **item} for task_id, task in zip(sorted(a), task_counts)
             for item in task["disagreements"]]
    queue.extend({"task_id": task_id, "claim_key": None,
                  "fields": ["action_sequence"], "resolution_code": None}
                 for task_id, task in zip(sorted(a), task_counts) if not task["action_exact"])
    return {"protocol": "annotation-agreement-v1", "bootstrap_seed": seed,
            "bootstrap_draws": draws, "annotators": [first.annotator_id, second.annotator_id],
            "n_tasks": len(task_counts), "n_families": len(families),
            "metrics": point, "adjudication_queue": queue}


def markdown_report(report: dict[str, Any]) -> str:
    lines = ["# Double-Annotation Agreement", "", f"Tasks: {report['n_tasks']}; families: {report['n_families']}.", "",
             "| Measure | Agreement | Denominator | Cluster bootstrap 95% CI |", "|---|---:|---:|---:|"]
    for label, key, metric in (("Claim F1", "claim", "f1"), ("Category", "category", "rate"),
                               ("Status", "status", "rate"), ("Typed value", "value", "rate"),
                               ("Provenance F1", "provenance", "f1"),
                               ("Criticality", "criticality", "rate"),
                               ("Exact action sequence", "action_sequence", "rate")):
        item = report["metrics"][key]; value = item[metric]
        denominator = item.get("denominator", item.get("annotator_a_denominator"))
        ci = item.get("cluster_bootstrap_ci", [None, None])
        lines.append(f"| {label} | {value:.4f} | {denominator} | {ci[0]:.4f}–{ci[1]:.4f} |")
    lines += ["", f"Adjudication queue entries: {len(report['adjudication_queue'])}.", ""]
    return "\n".join(lines)
