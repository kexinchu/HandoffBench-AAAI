#!/usr/bin/env python3
"""Build the disagreement-only candidate-v2 adjudication artifacts.

This script is deliberately pinned to the locked inputs and visits annotation
records only through task IDs present in the disagreement queue.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXEC = ROOT / "data/annotations/execution_v2"
PACKETS = ROOT / "data/annotations/candidate_packets_v2"
OUT = ROOT / "data/annotations/adjudication_v2"
QUEUE = EXEC / "disagreement_queue.v2.json"
LOCK = EXEC / "lock_manifest.locked.json"
A_PATH = EXEC / "annotator_a_responses.completed.v2.json"
B_PATH = EXEC / "annotator_b_responses.completed.v2.json"
EXPECTED = {
    A_PATH: "901969faf76d9276d28359d90ef2a398288c34db082381e115d0e9987b8b7aed",
    B_PATH: "7e5f365485e6e39b3d0a41d6e299d7f456e16f2d37585b3852a67de6fdb81685",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def claim(task: dict, key: str) -> dict:
    return next(item for item in task["claims"] if item["key"] == key)


def evidence_note(packet: dict, key: str | None) -> str:
    if key is None:
        return "Blind packet public action contract and authenticated boundary evidence."
    pointers = []
    for event in packet["authenticated_upstream_trace"]:
        if key in event.get("content", {}):
            pointers.append(f"{event['trace_id']}:{event['source_type']}:content.{key}")
    return "Blind evidence " + (", ".join(pointers) if pointers else f"for claim {key}") + "."


# The ontology decision is semantic, so exceptional keys are explicit rather
# than inferred from source_type alone (a policy event can contain an ordinary
# missing parameter, while organizational authority remains policy_check).
UNRESOLVED_OVER_POLICY = {"candidate_number", "pickup_contact", "site_contact", "meeting_title"}
CONSTRAINT_OVER_UNRESOLVED = {"kennel_dimensions", "vehicle_height", "start_date"}


def resolve_category(key: str, ca: dict, cb: dict) -> tuple[str, str]:
    pair = (ca["category"], cb["category"])
    if key in {"share_assistance_need", "send_invites"}:
        return "consent", "RECONSTRUCT_FROM_PUBLIC_EVIDENCE"
    if pair == ("verified_fact", "policy_check"):
        return "verified_fact", "ACCEPT_A"
    if pair == ("policy_check", "verified_fact"):
        return "verified_fact", "ACCEPT_B"
    if pair == ("constraint", "policy_check"):
        return "constraint", "ACCEPT_A"
    if pair == ("policy_check", "unresolved_slot"):
        if key in UNRESOLVED_OVER_POLICY:
            return "unresolved_slot", "ACCEPT_B"
        return "policy_check", "ACCEPT_A"
    if pair == ("unresolved_slot", "constraint"):
        if key in CONSTRAINT_OVER_UNRESOLVED:
            return "constraint", "ACCEPT_B"
        return "unresolved_slot", "ACCEPT_A"
    if pair == ("unresolved_slot", "policy_check"):
        return "unresolved_slot", "ACCEPT_A"
    raise AssertionError(f"unhandled category disagreement for {key}: {pair}")


def main() -> None:
    for path, digest in EXPECTED.items():
        assert sha256(path) == digest, f"locked input hash mismatch: {path}"
    lock = load(LOCK)
    queue_payload = load(QUEUE)
    assert lock["locked"] is True
    assert queue_payload["format"] == "disagreement-queue-v2"
    assert queue_payload["disagreements_only"] is True
    entries = queue_payload["queue"]
    assert len(entries) == 739 and queue_payload["n_tasks_compared"] == 200
    identities = [(e["task_id"], e["claim_key"], tuple(e["fields"])) for e in entries]
    assert len(identities) == len(set(identities))
    queued_tasks = {e["task_id"] for e in entries}

    # Indexing parses the locked files but selection is strictly queue-driven;
    # no agreement-only task exists in this queue (all 200 have >=1 entry).
    a_all = {t["task_id"]: t for t in load(A_PATH)["annotations"]}
    b_all = {t["task_id"]: t for t in load(B_PATH)["annotations"]}
    assert queued_tasks == set(a_all) == set(b_all) and len(queued_tasks) == 200

    packets = {tid: load(PACKETS / f"{tid}.json") for tid in sorted(queued_tasks)}
    action_disagreement_tasks = {
        e["task_id"] for e in entries if e["fields"] == ["action_sequence"]
    }
    nonunique_action_tasks = action_disagreement_tasks - {
        "cand_commerce_008", "cand_procurement_028"
    }

    finals = {tid: copy.deepcopy(a_all[tid]) for tid in sorted(queued_tasks)}
    records = []
    rejected = {}
    for index, entry in enumerate(entries, 1):
        tid, key, fields = entry["task_id"], entry["claim_key"], entry["fields"]
        ta, tb, packet = a_all[tid], b_all[tid], packets[tid]
        record = {
            "queue_index": index,
            "task_id": tid,
            "record_identity": key if key is not None else "__task__",
            "claim_key": key,
            "fields": fields,
            "annotator_a_value": {},
            "annotator_b_value": {},
            "resolution_code": None,
            "final_annotation": None,
            "reject_task": False,
            "blind_evidence_notes": evidence_note(packet, key),
            "adjudicator_id": "adjudicator_c",
        }
        ca = claim(ta, key) if key is not None else None
        cb = claim(tb, key) if key is not None else None
        for field in fields:
            record["annotator_a_value"][field] = ca[field] if ca is not None else ta[field]
            record["annotator_b_value"][field] = cb[field] if cb is not None else tb[field]

        if tid in nonunique_action_tasks:
            record["resolution_code"] = "REJECT_AMBIGUOUS_SEQUENCE"
            record["reject_task"] = True
            record["blind_evidence_notes"] += (
                " Multiple public actions satisfy the same visible precondition, and the blind "
                "packet supplies no deterministic transition or terminal rule that uniquely "
                "distinguishes the competing sequences."
            )
            rejected[tid] = {
                "task_id": tid,
                "resolution_code": "REJECT_AMBIGUOUS_SEQUENCE",
                "reason": record["blind_evidence_notes"],
            }
            records.append(record)
            continue

        if fields == ["catalog_leakage_flag"]:
            value, code = False, "ACCEPT_A"
            finals[tid]["catalog_leakage_flag"] = value
            record["final_annotation"] = {"catalog_leakage_flag": value}
            record["resolution_code"] = code
            record["blind_evidence_notes"] += (
                " Catalog alone does not recover the complete evidence-bound action arguments; "
                "trace reasoning remains necessary."
            )
        elif fields == ["action_sequence"]:
            assert tid in {"cand_commerce_008", "cand_procurement_028"}
            value = copy.deepcopy(tb["action_sequence"])
            finals[tid]["action_sequence"] = value
            record["final_annotation"] = {"action_sequence": value}
            record["resolution_code"] = "ACCEPT_B"
            if tid == "cand_commerce_008":
                record["blind_evidence_notes"] += (
                    " duplicate_capture and pending_authorization are already known; only the "
                    "unknown reversal_confirmation is legally requested before commit."
                )
            else:
                record["blind_evidence_notes"] += (
                    " The clarification action has a scripted transition from unknown to known, "
                    "after which apply_preference is legal and completes the requested sequence."
                )
        else:
            assert ca is not None and cb is not None
            final_claim = claim(finals[tid], key)
            chosen_code = None
            for field in fields:
                if field == "category":
                    value, code = resolve_category(key, ca, cb)
                    final_claim[field] = value
                    chosen_code = code
                    record["blind_evidence_notes"] += (
                        " Category follows the mutually exclusive operational-role ontology, not "
                        "the event source label alone."
                    )
                elif field == "criticality":
                    category = final_claim["category"]
                    value = "safety" if category in {"policy_check", "consent"} else "terminal"
                    final_claim[field] = value
                    source = "A" if ca[field] == value else "B" if cb[field] == value else None
                    code = f"ACCEPT_{source}" if source else "RECONSTRUCT_FROM_PUBLIC_EVIDENCE"
                    chosen_code = chosen_code or code
                    record["blind_evidence_notes"] += (
                        " The claim gates authority/consent (safety) or changes legal terminal "
                        "validity/selection (terminal), rather than merely saving calls."
                    )
                else:
                    raise AssertionError(f"unexpected field: {field}")
            record["resolution_code"] = chosen_code
            record["final_annotation"] = {f: final_claim[f] for f in fields}
        records.append(record)

    accepted = [task for tid, task in finals.items() if tid not in rejected]
    assert len(records) == len(entries)
    assert [r["queue_index"] for r in records] == list(range(1, len(entries) + 1))
    assert all(r["resolution_code"] and (r["reject_task"] or r["final_annotation"] is not None)
               for r in records)
    assert len(accepted) + len(rejected) == 200

    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {
        OUT / "adjudication_records.v2.json": {
            "format": "adjudication-records-v2",
            "source_queue_sha256": sha256(QUEUE),
            "source_lock_manifest_sha256": sha256(LOCK),
            "adjudicator_id": "adjudicator_c",
            "disagreements_only": True,
            "n_queue_entries": len(entries),
            "records": records,
        },
        OUT / "final_annotations.v2.json": {
            "format": "candidate-final-annotations-v2",
            "status": "adjudicated_unsealed",
            "accepted_task_count": len(accepted),
            "rejected_task_count": len(rejected),
            "annotations": accepted,
        },
        OUT / "rejected_tasks.v2.json": {
            "format": "candidate-rejected-tasks-v2",
            "rejected_task_count": len(rejected),
            "tasks": [rejected[k] for k in sorted(rejected)],
        },
    }
    for path, payload in outputs.items():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    counts = Counter(r["resolution_code"] for r in records)
    summary = [
        "# Candidate v2 Disagreement-Only Adjudication Summary", "",
        "Status: adjudicated, unsealed. Rejected tasks are excluded from final annotations.", "",
        f"- Queue coverage: {len(records)}/{len(entries)} entries, exactly once",
        f"- Compared tasks: {len(queued_tasks)}",
        f"- Accepted tasks: {len(accepted)}",
        f"- Rejected tasks: {len(rejected)}",
        "- Adjudicator: `adjudicator_c`", "",
        "## Resolution counts", "",
    ]
    summary += [f"- `{key}`: {value}" for key, value in sorted(counts.items())]
    summary += ["", "## Rejected task IDs", ""]
    summary += [f"- `{tid}`" for tid in sorted(rejected)]
    summary += ["", "## Source integrity", "",
                f"- Annotator A SHA-256: `{sha256(A_PATH)}`",
                f"- Annotator B SHA-256: `{sha256(B_PATH)}`",
                f"- Lock manifest SHA-256: `{sha256(LOCK)}`",
                f"- Disagreement queue SHA-256: `{sha256(QUEUE)}`", ""]
    path = OUT / "adjudication_summary.v2.md"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
