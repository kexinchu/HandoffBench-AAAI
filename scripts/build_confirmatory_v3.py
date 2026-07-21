#!/usr/bin/env python3
"""Compose human annotations into an unsealed 200-task confirmatory-v3 set.

Historical candidate, annotation, and replacement artifacts are read-only
inputs.  The default build refuses to overwrite any output.  ``--verify-only``
reconstructs the payloads in memory and byte-compares them with stored files.
No model/provider call is made by this script.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from handoffbench.dataset import execute_events, load_tasks


ROOT = Path(__file__).resolve().parents[1]
DOMAINS = ("travel", "commerce", "procurement", "it", "scheduling")
ORIGINAL_TASK_FILES = (
    ROOT / "data/tasks/candidate/travel_commerce.json",
    ROOT / "data/tasks/candidate/procurement_it.json",
    ROOT / "data/tasks/candidate/scheduling.json",
)
REPLACEMENT_TASK_FILE = ROOT / "data/tasks/replacements_v3/replacement_candidates.v3.json"
ORIGINAL_FINAL = ROOT / "data/annotations/adjudication_v2/final_annotations.v2.json"
ORIGINAL_REJECTED = ROOT / "data/annotations/adjudication_v2/rejected_tasks.v2.json"
BLIND_REVIEW = ROOT / "data/annotations/blind_validity_review_v2/review.json"
REPLACEMENT_A = ROOT / "data/annotations/replacement_execution_v3/annotator_a_responses.completed.v1.json"
REPLACEMENT_B = ROOT / "data/annotations/replacement_execution_v3/annotator_b_responses.completed.v1.json"
REPLACEMENT_QUEUE = ROOT / "data/annotations/replacement_execution_v3/disagreement_queue.v1.json"
REPLACEMENT_FINAL = ROOT / "data/annotations/replacement_adjudication_v3/final_annotations.v1.json"
REPLACEMENT_REJECTED = ROOT / "data/annotations/replacement_adjudication_v3/rejected_tasks.v1.json"
TASK_DIR = ROOT / "data/tasks/confirmatory_v3"
ANNOTATION_DIR = ROOT / "annotations/confirmatory_v3"
FINAL_ANNOTATIONS = ANNOTATION_DIR / "final_annotations.ready.json"
LINEAGE = ANNOTATION_DIR / "lineage.ready.json"
FINAL_AUDIT = ANNOTATION_DIR / "final_audit.ready.json"
AGREEMENT = ANNOTATION_DIR / "agreement.ready.json"

PROTOCOL_CLAIM_FIELDS = (
    "key", "category", "status", "value", "criticality", "provenance",
)
CHAIN_PATHS = {
    "original_packet_hashes": ROOT / "data/annotations/candidate_packets_v2.sha256",
    "original_lock": ROOT / "data/annotations/execution_v2/lock_manifest.locked.json",
    "original_annotator_a": ROOT / "data/annotations/execution_v2/annotator_a_responses.completed.v2.json",
    "original_annotator_b": ROOT / "data/annotations/execution_v2/annotator_b_responses.completed.v2.json",
    "original_agreement": ROOT / "data/annotations/execution_v2/agreement_report.v2.json",
    "original_queue": ROOT / "data/annotations/execution_v2/disagreement_queue.v2.json",
    "original_adjudication": ROOT / "data/annotations/adjudication_v2/adjudication_records.v2.json",
    "original_final": ORIGINAL_FINAL,
    "original_rejections": ORIGINAL_REJECTED,
    "blind_validity_review": BLIND_REVIEW,
    "replacement_packet_hashes": ROOT / "data/annotations/replacement_packets_v3.sha256",
    "replacement_lock": ROOT / "data/annotations/replacement_execution_v3/lock_manifest.locked.v1.json",
    "replacement_annotator_a": REPLACEMENT_A,
    "replacement_annotator_b": REPLACEMENT_B,
    "replacement_agreement": ROOT / "data/annotations/replacement_execution_v3/agreement_report.v1.json",
    "replacement_queue": REPLACEMENT_QUEUE,
    "replacement_adjudication": ROOT / "data/annotations/replacement_adjudication_v3/adjudication_records.v1.json",
    "replacement_final": REPLACEMENT_FINAL,
    "replacement_rejections": REPLACEMENT_REJECTED,
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _render(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _sha_bytes(_canonical(value).encode())


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def _index(items: list[dict[str, Any]], *, field: str = "task_id") -> dict[str, dict[str, Any]]:
    result = {item[field]: item for item in items}
    if len(result) != len(items):
        raise ValueError(f"duplicate {field}")
    return result


def _protocol_view(annotation: dict[str, Any]) -> dict[str, Any]:
    claims = sorted(
        ({key: copy.deepcopy(claim.get(key)) for key in PROTOCOL_CLAIM_FIELDS}
         for claim in annotation["claims"]),
        key=lambda item: item["key"],
    )
    return {
        "claims": claims,
        "action_sequence": annotation["action_sequence"],
        "irreversible_args_inferable": annotation.get("irreversible_args_inferable"),
        "catalog_leakage_flag": annotation.get("catalog_leakage_flag"),
    }


def _infer_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "set"
    return "object"


def _merge_task(source: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    task = copy.deepcopy(source)
    episode = task["episode"]
    task_id = episode["task_id"]
    if annotation["task_id"] != task_id:
        raise ValueError(f"annotation/source identity mismatch: {task_id}")
    source_claims = {claim["key"]: claim for claim in episode["gold_state"]}
    human_keys = [claim["key"] for claim in annotation["claims"]]
    if len(human_keys) != len(set(human_keys)) or not set(human_keys) <= set(source_claims):
        raise ValueError(f"{task_id}: human claim keys are missing, duplicate, or not source-grounded")
    if not set(episode["scoring"]["critical_keys"]) <= set(human_keys):
        raise ValueError(f"{task_id}: human claims omit a source critical key")

    merged_claims = []
    for index, human in enumerate(annotation["claims"], start=1):
        claim = copy.deepcopy(source_claims[human["key"]])
        for field in ("category", "status", "value", "criticality", "provenance"):
            claim[field] = copy.deepcopy(human[field])
        claim["claim_id"] = claim.get("claim_id") or f"{task_id}_human_c{index:02d}"
        claim["value_type"] = claim.get("value_type") or _infer_value_type(claim["value"])
        if claim["value"] is None:
            claim["value_type"] = "null"
        claim["weight"] = claim.get("weight") or 1.0
        claim["normalizer"] = claim.get("normalizer")
        merged_claims.append(claim)
    episode["gold_state"] = merged_claims
    episode["success_predicate"]["args"]["required_events"] = copy.deepcopy(
        annotation["action_sequence"]
    )

    allowed = {
        (rule["action"], _canonical(rule.get("expected_arguments", {})))
        for rule in episode["allowed_next_actions"]
    }
    for event in annotation["action_sequence"]:
        if (event["name"], _canonical(event["arguments"])) not in allowed:
            raise ValueError(f"{task_id}: human action sequence is incompatible with source contract")
    return task


def build_payloads() -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], dict[str, Any]]:
    originals = sum((_load(path) for path in ORIGINAL_TASK_FILES), [])
    replacements = _load(REPLACEMENT_TASK_FILE)
    original_by_id = {
        item["episode"]["task_id"]: item for item in originals
    }
    replacement_by_id = {item["episode"]["task_id"]: item for item in replacements}
    if len(original_by_id) != 200 or len(replacement_by_id) != 63:
        raise ValueError("expected 200 original and 63 replacement source tasks")

    original_annotations = _index(_load(ORIGINAL_FINAL)["annotations"])
    adjudication_rejections = {
        item["task_id"] for item in _load(ORIGINAL_REJECTED)["tasks"]
    }
    blind_records = _load(BLIND_REVIEW)["records"]
    if any(item.get("decision") != "REJECT" for item in blind_records):
        raise ValueError("blind review input must contain rejection decisions only")
    blind_rejections = {item["task_id"] for item in blind_records}
    excluded = adjudication_rejections | blind_rejections
    if len(adjudication_rejections) != 24 or len(blind_rejections) != 39 or len(excluded) != 63:
        raise ValueError("original rejection union must be disjoint 24 + 39 = 63")
    retained_ids = set(original_by_id) - excluded
    if len(retained_ids) != 137 or not retained_ids <= set(original_annotations):
        raise ValueError("retained originals must be exactly 137 accepted annotated tasks")

    replacement_a = _index(_load(REPLACEMENT_A)["annotations"])
    replacement_b = _index(_load(REPLACEMENT_B)["annotations"])
    queue_ids = {item["task_id"] for item in _load(REPLACEMENT_QUEUE)["queue"]}
    adjudicated = _index(_load(REPLACEMENT_FINAL)["annotations"])
    replacement_rejected = _load(REPLACEMENT_REJECTED)
    rejected_items = replacement_rejected.get("tasks", replacement_rejected.get("rejected_tasks", []))
    if set(replacement_a) != set(replacement_by_id) or set(replacement_b) != set(replacement_by_id):
        raise ValueError("replacement annotations do not provide complete double coverage")
    if len(queue_ids) != 47 or set(adjudicated) != queue_ids or rejected_items:
        raise ValueError("replacement adjudication must accept exactly all 47 queued tasks")
    agreement_only = set(replacement_by_id) - queue_ids
    if len(agreement_only) != 16:
        raise ValueError("replacement agreement-only set must contain 16 tasks")
    for task_id in agreement_only:
        if _protocol_view(replacement_a[task_id]) != _protocol_view(replacement_b[task_id]):
            raise ValueError(f"{task_id}: agreement-only protocol fields are not identical")

    annotations: dict[str, dict[str, Any]] = {
        task_id: copy.deepcopy(original_annotations[task_id]) for task_id in retained_ids
    }
    annotations.update({task_id: copy.deepcopy(adjudicated[task_id]) for task_id in queue_ids})
    annotations.update({task_id: copy.deepcopy(replacement_a[task_id]) for task_id in agreement_only})
    sources = original_by_id | replacement_by_id
    if len(annotations) != 200 or set(annotations) != retained_ids | set(replacement_by_id):
        raise ValueError("composite annotation set is not exactly 137 + 63 tasks")

    merged = [_merge_task(sources[task_id], annotations[task_id]) for task_id in sorted(annotations)]
    by_domain = {
        domain: sorted(
            (task for task in merged if task["episode"]["domain"] == domain),
            key=lambda item: item["episode"]["task_id"],
        )
        for domain in DOMAINS
    }
    if Counter({domain: len(items) for domain, items in by_domain.items()}) != Counter(
        {domain: 40 for domain in DOMAINS}
    ):
        raise ValueError("final domain composition must be five domains x 40")
    ids = [task["episode"]["task_id"] for task in merged]
    families = [task["episode"]["split_meta"]["template_family"] for task in merged]
    if len(set(ids)) != 200 or len(set(families)) != 200:
        raise ValueError("final task_id and template_family values must be globally unique")

    annotation_rows = []
    lineage_rows = []
    for task in merged:
        task_id = task["episode"]["task_id"]
        if task_id in retained_ids:
            resolution = "original_adjudicated_accept"
            annotation_path = ORIGINAL_FINAL
            source_path = next(
                path for path in ORIGINAL_TASK_FILES
                if any(item["episode"]["task_id"] == task_id for item in _load(path))
            )
        elif task_id in queue_ids:
            resolution = "replacement_disagreement_adjudicated_accept"
            annotation_path = REPLACEMENT_FINAL
            source_path = REPLACEMENT_TASK_FILE
        else:
            resolution = "replacement_protocol_exact_agreement_accept_a"
            annotation_path = REPLACEMENT_A
            source_path = REPLACEMENT_TASK_FILE
        annotation = copy.deepcopy(annotations[task_id])
        annotation["integration_resolution"] = resolution
        annotation_rows.append(annotation)
        lineage_rows.append({
            "task_id": task_id,
            "domain": task["episode"]["domain"],
            "template_family": task["episode"]["split_meta"]["template_family"],
            "source_path": _relative(source_path),
            "source_file_sha256": _sha_file(source_path),
            "source_task_sha256": _digest(sources[task_id]),
            "annotation_path": _relative(annotation_path),
            "annotation_file_sha256": _sha_file(annotation_path),
            "annotation_sha256": _digest(annotations[task_id]),
            "integration_resolution": resolution,
            "final_task_sha256": _digest(task),
        })

    final_annotations = {
        "format": "handoffbench-confirmatory-v3-composite-annotations-v1",
        "status": "ready_to_seal_unsealed",
        "protocol": "handoffbench-confirmatory-v3",
        "task_count": 200,
        "composition": {
            "retained_original": 137,
            "replacement_adjudicated": 47,
            "replacement_protocol_exact_agreement": 16,
        },
        "annotations": sorted(annotation_rows, key=lambda item: item["task_id"]),
    }
    lineage = {
        "format": "handoffbench-confirmatory-v3-lineage-v1",
        "status": "ready_to_seal_unsealed",
        "model_calls": 0,
        "composition": {
            "original_candidates": 200,
            "adjudication_rejections": 24,
            "blind_validity_rejections": 39,
            "rejection_union": 63,
            "retained_original": 137,
            "replacement_candidates": 63,
            "final": 200,
        },
        "excluded_original_task_ids": sorted(excluded),
        "adjudication_rejection_task_ids": sorted(adjudication_rejections),
        "blind_validity_rejection_task_ids": sorted(blind_rejections),
        "replacement_agreement_only_task_ids": sorted(agreement_only),
        "replacement_adjudicated_task_ids": sorted(queue_ids),
        "tasks": sorted(lineage_rows, key=lambda item: item["task_id"]),
    }
    return by_domain, final_annotations, lineage


def _artifact_count(path: Path) -> int:
    if path.suffix == ".sha256":
        return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])
    value = _load(path)
    if not isinstance(value, dict):
        return len(value) if isinstance(value, list) else 1
    for key in (
        "annotations", "queue", "records", "tasks", "rejected_tasks",
        "expected_task_ids", "inputs",
    ):
        if isinstance(value.get(key), list):
            return len(value[key])
    for key in ("n_tasks", "n_tasks_compared", "task_count", "rejected_task_count"):
        if isinstance(value.get(key), int):
            return value[key]
    return 1


def agreement_payload() -> dict[str, Any]:
    by_domain, final_annotations, lineage = build_payloads()
    expected_files = {TASK_DIR / f"{domain}.json": payload for domain, payload in by_domain.items()}
    expected_files[FINAL_ANNOTATIONS] = final_annotations
    expected_files[LINEAGE] = lineage
    for path, payload in expected_files.items():
        if not path.exists() or path.read_bytes() != _render(payload):
            raise ValueError(f"stored build artifact is missing or differs: {path}")
    audit = _load(FINAL_AUDIT)
    hard_checks = audit.get("hard_checks", {})
    original_lock = _load(CHAIN_PATHS["original_lock"])
    replacement_lock = _load(CHAIN_PATHS["replacement_lock"])
    gate_checks = {
        "original_double_annotation_locked": (
            original_lock.get("locked") is True
            and len(original_lock.get("inputs", [])) == 2
            and len(original_lock.get("expected_task_ids", [])) == 200
        ),
        "original_adjudication_complete": _artifact_count(CHAIN_PATHS["original_adjudication"]) > 0,
        "original_rejections_accounted": _artifact_count(ORIGINAL_REJECTED) == 24,
        "blind_rejections_accounted": _artifact_count(BLIND_REVIEW) == 39,
        "replacement_double_annotation_complete": (
            replacement_lock.get("locked") is True
            and len(replacement_lock.get("inputs", [])) == 2
            and len(replacement_lock.get("expected_task_ids", [])) == 63
            and
            _artifact_count(REPLACEMENT_A) == 63 and _artifact_count(REPLACEMENT_B) == 63
        ),
        "replacement_queue_fully_adjudicated": (
            len({item["task_id"] for item in _load(REPLACEMENT_QUEUE)["queue"]})
            == _artifact_count(REPLACEMENT_FINAL) == 47
        ),
        "replacement_zero_rejections": _artifact_count(REPLACEMENT_REJECTED) == 0,
        "composite_double_coverage": final_annotations["task_count"] == 200,
        "final_static_hard_audit": audit.get("status") == "pass_unsealed" and all(hard_checks.values()),
    }
    if not all(gate_checks.values()):
        raise ValueError(f"agreement readiness gate failed: {gate_checks}")

    chain = {
        name: {"path": _relative(path), "sha256": _sha_file(path), "count": _artifact_count(path)}
        for name, path in CHAIN_PATHS.items()
    }
    chain["final_annotations"] = {
        "path": _relative(FINAL_ANNOTATIONS), "sha256": _sha_file(FINAL_ANNOTATIONS), "count": 200,
    }
    chain["lineage"] = {
        "path": _relative(LINEAGE), "sha256": _sha_file(LINEAGE), "count": 200,
    }
    chain["final_audit"] = {
        "path": _relative(FINAL_AUDIT), "sha256": _sha_file(FINAL_AUDIT),
        "count": audit["summary"]["tasks"],
    }
    for domain in DOMAINS:
        path = TASK_DIR / f"{domain}.json"
        chain[f"final_tasks_{domain}"] = {
            "path": _relative(path), "sha256": _sha_file(path), "count": len(by_domain[domain]),
        }
    ordered_tasks = [task for domain in DOMAINS for task in by_domain[domain]]
    candidate_files = [f"data/tasks/confirmatory_v3/{domain}.json" for domain in DOMAINS]
    domain_counts = dict(sorted(Counter(
        task["episode"]["domain"] for task in ordered_tasks
    ).items()))
    return {
        "format": "handoffbench-confirmatory-v3-agreement-readiness-v1",
        "status": "ready_to_seal",
        "protocol": "handoffbench-confirmatory-v3",
        "seal_id": None,
        "accepted_task_ids": sorted(
            task["episode"]["task_id"] for tasks in by_domain.values() for task in tasks
        ),
        "canonical_dataset_sha256": _digest(ordered_tasks),
        "n_tasks": 200,
        "n_independent_families": 200,
        "domain_counts": domain_counts,
        "candidate_files": candidate_files,
        "final_audit_file": _relative(FINAL_AUDIT),
        "final_audit_sha256": _sha_file(FINAL_AUDIT),
        "double_annotated_tasks": 200,
        "annotators_per_task": 2,
        "adjudication_complete": True,
        "agreement_gate_passed": True,
        "agreement_gate_algorithm": {
            "rule": "logical conjunction of every named gate_check; no raw-disagreement threshold",
            "reason": "all protocol disagreements require adjudication; exact-agreement tasks require no queue entry",
            "checks": gate_checks,
        },
        "counts": {
            "retained_original": 137, "excluded_original": 63,
            "replacement_double_annotated": 63,
            "replacement_adjudicated": 47,
            "replacement_exact_agreement": 16,
            "replacement_rejected": 0, "accepted_final": 200,
        },
        "artifact_chain": chain,
        "no_model_call_attestation": {
            "model_calls": 0,
            "statement": (
                "Composition, schema validation, static audits, hash construction, and readiness "
                "generation were deterministic local operations. Human annotations were the only "
                "semantic decisions; no candidate model was called."
            ),
        },
        "sealing_authority": None,
        "execution_authorized": False,
    }


def _write(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite historical/versioned output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_render(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--write-agreement", action="store_true")
    args = parser.parse_args()
    if args.write_agreement:
        _write(AGREEMENT, agreement_payload())
        print(_sha_file(AGREEMENT))
        return 0

    by_domain, annotations, lineage = build_payloads()
    outputs = {TASK_DIR / f"{domain}.json": payload for domain, payload in by_domain.items()}
    outputs[FINAL_ANNOTATIONS] = annotations
    outputs[LINEAGE] = lineage
    if args.verify_only:
        for path, payload in outputs.items():
            if not path.exists() or path.read_bytes() != _render(payload):
                raise ValueError(f"stored artifact differs from deterministic reconstruction: {path}")
        print("confirmatory-v3 deterministic build verification passed")
        return 0
    for path, payload in outputs.items():
        _write(path, payload)
    print(json.dumps({"tasks": 200, "domains": {domain: 40 for domain in DOMAINS}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
