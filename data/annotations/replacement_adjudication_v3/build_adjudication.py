#!/usr/bin/env python3
"""Reproducibly adjudicate replacement-v3 disagreement records only."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import ijson


ROOT = Path(__file__).resolve().parents[3]
EXEC = ROOT / "data/annotations/replacement_execution_v3"
PACKETS = ROOT / "data/annotations/replacement_packets_v3"
OUT = ROOT / "data/annotations/replacement_adjudication_v3"
QUEUE = EXEC / "disagreement_queue.v1.json"
LOCK = EXEC / "lock_manifest.locked.v1.json"
A_PATH = EXEC / "annotator_a_responses.completed.v1.json"
B_PATH = EXEC / "annotator_b_responses.completed.v1.json"
EXPECTED = {
    A_PATH: "f2b8e0c76741c5b2856199369e4eb6f3030f16da0959ac411618d651c913e825",
    B_PATH: "036b01dd96125685d19c8554c7b6c3371455d3a1580e90e37cd9bcc1ded55e6b",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def select_queue_tasks(path: Path, task_ids: set[str]) -> dict[str, dict]:
    """Retain only queue-addressed records; agreement-only records are discarded."""
    selected = {}
    with path.open("rb") as stream:
        for task in ijson.items(stream, "annotations.item"):
            task_id = task.get("task_id")
            if task_id in task_ids:
                selected[task_id] = task
    if set(selected) != task_ids:
        raise ValueError(f"missing queue-addressed records in {path}")
    return selected


def get_claim(task: dict, key: str) -> dict:
    return next(claim for claim in task["claims"] if claim["key"] == key)


def main() -> None:
    for path, digest in EXPECTED.items():
        assert sha256(path) == digest, f"locked hash mismatch: {path}"
    lock = load(LOCK)
    queue_payload = load(QUEUE)
    assert lock["locked"] is True
    assert queue_payload["format"] == "disagreement-queue-v2"
    assert queue_payload["disagreements_only"] is True
    assert queue_payload["n_tasks_compared"] == 63
    queue = queue_payload["queue"]
    assert len(queue) == 47
    identities = [(x["task_id"], x["claim_key"], tuple(x["fields"])) for x in queue]
    assert len(identities) == len(set(identities))
    task_ids = {x["task_id"] for x in queue}
    assert len(task_ids) == 47

    annotator_a = select_queue_tasks(A_PATH, task_ids)
    annotator_b = select_queue_tasks(B_PATH, task_ids)
    packets = {tid: load(PACKETS / f"{tid}.json") for tid in sorted(task_ids)}

    finals = {tid: copy.deepcopy(annotator_a[tid]) for tid in sorted(task_ids)}
    records = []
    for index, entry in enumerate(queue, 1):
        tid, key = entry["task_id"], entry["claim_key"]
        assert entry["fields"] == ["criticality"]
        claim_a = get_claim(annotator_a[tid], key)
        claim_b = get_claim(annotator_b[tid], key)
        assert key == "operation_scope_ref"
        assert claim_a["category"] == claim_b["category"] == "constraint"
        assert claim_a["status"] == claim_b["status"] == "known"
        assert claim_a["value"] == claim_b["value"]
        assert claim_a["provenance"] == claim_b["provenance"]
        assert claim_a["criticality"] == "terminal"
        assert claim_b["criticality"] == "safety"
        pointer = claim_a["provenance"][0]
        packet = packets[tid]
        event = next(e for e in packet["authenticated_upstream_trace"]
                     if e["trace_id"] == pointer["trace_id"])
        assert event["source_type"] == pointer["source_type"]
        assert event["content"][key] == claim_a["value"]
        records.append({
            "queue_index": index,
            "task_id": tid,
            "record_identity": key,
            "claim_key": key,
            "fields": ["criticality"],
            "annotator_a_value": {"criticality": "terminal"},
            "annotator_b_value": {"criticality": "safety"},
            "resolution_code": "ACCEPT_A",
            "final_annotation": {"criticality": "terminal"},
            "reject_task": False,
            "blind_evidence_notes": (
                f"Blind evidence {pointer['trace_id']}:{pointer['source_type']}:"
                f"{pointer['field_path']}. operation_scope_ref is a user constraint that "
                "selects the requested operation scope and changes terminal validity. "
                "The distinct authorization_state claim carries the authority/safety gate."
            ),
            "adjudicator_id": "adjudicator_c",
        })

    assert len(records) == len(queue)
    assert [(r["task_id"], r["claim_key"], tuple(r["fields"])) for r in records] == identities
    assert all(r["resolution_code"] == "ACCEPT_A" and not r["reject_task"] for r in records)

    OUT.mkdir(parents=True, exist_ok=True)
    payloads = {
        OUT / "adjudication_records.v1.json": {
            "format": "replacement-v3-adjudication-records-v1",
            "source_queue_sha256": sha256(QUEUE),
            "source_lock_manifest_sha256": sha256(LOCK),
            "disagreements_only": True,
            "adjudicator_id": "adjudicator_c",
            "n_queue_entries": len(queue),
            "records": records,
        },
        OUT / "final_annotations.v1.json": {
            "format": "replacement-v3-adjudicated-subset-v1",
            "status": "adjudicated_subset_unsealed",
            "scope": "queue-addressed tasks only; agreement-only tasks intentionally omitted",
            "n_tasks_compared": 63,
            "adjudicated_task_count": len(finals),
            "agreement_only_task_count_not_opened": 63 - len(finals),
            "rejected_task_count": 0,
            "annotations": [finals[tid] for tid in sorted(finals)],
        },
        OUT / "rejected_tasks.v1.json": {
            "format": "replacement-v3-rejected-tasks-v1",
            "rejected_task_count": 0,
            "tasks": [],
        },
    }
    for path, payload in payloads.items():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    counts = Counter(r["resolution_code"] for r in records)
    summary = [
        "# Replacement v3 Disagreement-Only Adjudication", "",
        "Status: adjudicated subset, unsealed.", "",
        f"- Compared tasks in locked inputs: {queue_payload['n_tasks_compared']}",
        f"- Queue coverage: {len(records)}/{len(queue)} entries, exactly once",
        f"- Queue-addressed tasks adjudicated: {len(finals)}",
        f"- Agreement-only tasks intentionally not opened: {63 - len(finals)}",
        "- Rejected tasks: 0", "- Adjudicator: `adjudicator_c`", "",
        "## Resolution counts", "",
    ]
    summary += [f"- `{key}`: {value}" for key, value in sorted(counts.items())]
    summary += ["", "## Decision rule", "",
                "All queued disagreements concern `operation_scope_ref`: both annotators agree on its "
                "identity, `constraint` category, known typed value, and provenance. It determines the "
                "requested operational scope and terminal validity, whereas a separate "
                "`authorization_state` claim carries the authority/safety gate. Therefore all 47 "
                "entries resolve to A's `terminal` criticality.", "",
                "## Source integrity", "",
                f"- Annotator A SHA-256: `{sha256(A_PATH)}`",
                f"- Annotator B SHA-256: `{sha256(B_PATH)}`",
                f"- Lock manifest SHA-256: `{sha256(LOCK)}`",
                f"- Disagreement queue SHA-256: `{sha256(QUEUE)}`", ""]
    path = OUT / "adjudication_summary.v1.md"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
