"""Build a coordinator-safe task-level remediation queue from static audits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parents[1]
CONSTRUCT = ROOT / "research/construct_validity_audit_v2.json"
OVERLAP = ROOT / "research/candidate_dev_overlap_audit.json"
LEAKAGE = ROOT / "research/action_name_leakage_audit_v2.json"
PACKETS = ROOT / "data/annotations/candidate_packets_v2"

OPERATIONS = {
    "counterfactual_relevance_review": "reconstruct_minimal_state_from_packet",
    "legal_policy_ambiguity_review": "enumerate_all_legal_sequences_from_public_contract",
    "epistemic_semantics_review": "independently_check_status_scope_and_authority",
    "impact_contract_review": "compare_public_impact_semantics_without_evaluator_labels",
    "normalized_topology_review": "compare_blind_workflow_logic_not_surface_words",
    "interface_ordering_probe_hit": "audit_public_interface_for_shallow_cues",
}
WEIGHTS = {
    "counterfactual_relevance_review": 1,
    "legal_policy_ambiguity_review": 4,
    "epistemic_semantics_review": 4,
    "impact_contract_review": 4,
    "normalized_topology_review": 2,
    "interface_ordering_probe_hit": 2,
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    construct, overlap, leakage = _read(CONSTRUCT), _read(OVERLAP), _read(LEAKAGE)
    task_rows = {row["task_id"]: row for row in construct["tasks"]}
    semantic = {item["task_id"] for item in construct["semantic_flags"]}
    topology = {item["candidate"] for item in
                overlap["collisions"]["normalized_action_graph_hash"]}
    interface = {item["task_id"] for item in leakage["successful_families"]}
    items = []
    for task_id, row in sorted(task_rows.items()):
        packet = PACKETS / f"{task_id}.json"
        public = _read(packet)
        if public.get("task_id") != task_id:
            raise ValueError(f"packet mismatch: {packet}")
        risks = []
        if row["mechanically_witnessed_claims"] < row["claims"]:
            risks.append("counterfactual_relevance_review")
        if not row["unique_legal_terminal_sequence"]:
            risks.append("legal_policy_ambiguity_review")
        if task_id in semantic:
            risks.append("epistemic_semantics_review")
        if not row["impacting_irreversible_name_sets_match"]:
            risks.append("impact_contract_review")
        if task_id in topology:
            risks.append("normalized_topology_review")
        if task_id in interface:
            risks.append("interface_ordering_probe_hit")
        score = sum(WEIGHTS[risk] for risk in risks)
        tier = "P0" if score >= 8 else "P1" if score >= 5 else "P2" if score >= 3 else "P3"
        items.append({
            "task_id": task_id,
            "domain": public["domain"],
            "packet": f"data/annotations/candidate_packets_v2/{packet.name}",
            "packet_sha256": _sha(packet),
            "priority": tier,
            "risk_codes": risks,
            "blind_review_operations": [OPERATIONS[risk] for risk in risks],
            "coordinator_status": "unassigned",
            "human_decision": None,
        })
    items.sort(key=lambda item: (item["priority"], item["domain"], item["task_id"]))
    return {
        "format": "human-remediation-priority-queue-v2",
        "status": "candidate_unreviewed_unsealed",
        "audience": "annotation_coordinator_not_independent_annotators",
        "safety_note": (
            "Assign only the referenced blind packet and generic operation to a reviewer; "
            "do not disclose source audits, evaluator records, or another annotation."
        ),
        "task_count": len(items),
        "priority_counts": dict(sorted(Counter(item["priority"] for item in items).items())),
        "risk_counts": dict(sorted(Counter(risk for item in items for risk in item["risk_codes"]).items())),
        "items": items,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Candidate v2 human-remediation priority queue", "",
        "Status: **candidate / unreviewed / unsealed**. This coordinator-facing queue contains no gold claims, evaluator sequence, or human answers.", "",
        payload["safety_note"], "",
        f"Tasks: {payload['task_count']}. Priority counts: {payload['priority_counts']}. Risk counts: {payload['risk_counts']}.", "",
        "| Priority | Task | Domain | Risk codes | Blind review operations | Packet |", "|---|---|---|---|---|---|",
    ]
    for item in payload["items"]:
        lines.append("| {priority} | `{task_id}` | {domain} | {risks} | {operations} | `{packet}` |".format(
            priority=item["priority"], task_id=item["task_id"], domain=item["domain"],
            risks=", ".join(item["risk_codes"]),
            operations=", ".join(item["blind_review_operations"]), packet=item["packet"]))
    lines += ["", "Reviewers record only accept/reject/rewrite-needed plus rationale in a separate versioned response. They must derive any claims and legal actions from the packet itself. Queue generation performs no annotation and never edits candidates.", ""]
    return "\n".join(lines)


def write_new(payload: dict[str, Any], json_path: Path, csv_path: Path, md_path: Path) -> None:
    for path in (json_path, csv_path, md_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        fields = ["task_id", "domain", "packet", "packet_sha256", "priority", "risk_codes",
                  "blind_review_operations", "coordinator_status", "human_decision"]
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for item in payload["items"]:
            row = dict(item); row["risk_codes"] = ";".join(row["risk_codes"])
            row["blind_review_operations"] = ";".join(row["blind_review_operations"])
            writer.writerow(row)
    md_path.write_text(markdown(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    payload = build()
    prefix = args.output_prefix
    write_new(payload, prefix.with_suffix(".json"), prefix.with_suffix(".csv"), prefix.with_suffix(".md"))


if __name__ == "__main__":
    main()
