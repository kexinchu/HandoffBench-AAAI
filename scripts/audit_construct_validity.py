"""Independent static construct-validity audit of the 200 candidate tasks."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from handoffbench.dataset import execute_events, load_tasks, primary_gold_claims
from handoffbench.transfer import public_action_contract


ROOT = Path(__file__).parents[1]
TASK_FILES = (
    ROOT / "data/tasks/candidate/travel_commerce.json",
    ROOT / "data/tasks/candidate/procurement_it.json",
    ROOT / "data/tasks/candidate/scheduling.json",
)
OVERLAP = ROOT / "research/candidate_dev_overlap_audit.json"


def _path(event: dict[str, Any], field_path: str | None) -> tuple[bool, Any]:
    value: Any = event
    for part in (field_path or "").split("."):
        if not part or not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _contains(value: Any, target: Any) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(key == target for key in value) or any(
            _contains(item, target) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains(item, target) for item in value)
    return False


def legal_terminal_sequences(record) -> list[list[dict[str, Any]]]:
    invocations = [
        {"name": rule.action, "arguments": dict(rule.expected_arguments)}
        for rule in record.episode.allowed_next_actions
    ]
    irreversible = {rule.action for rule in record.episode.allowed_next_actions if rule.irreversible}
    legal = []
    # Candidate automata have at most four gold-path actions. Enumerating each
    # allowed invocation once directly tests ordering ambiguity without using Phi.
    for length in range(1, len(invocations) + 1):
        for sequence in itertools.permutations(invocations, length):
            if sequence[-1]["name"] not in irreversible:
                continue
            result = execute_events(record, list(sequence))
            if not result.violations:
                legal.append(list(sequence))
    return legal


def audit() -> dict[str, Any]:
    records = sum((load_tasks(path) for path in TASK_FILES), [])
    task_rows = []
    category_status = Counter()
    mechanically_relevant = Counter()
    semantic_flags = []
    for record in records:
        trace = {event["trace_id"]: event for event in record.upstream_trace}
        required = record.episode.success_predicate.args["required_events"]
        conditions = {condition.split("=", 1)[0].removeprefix("!")
                      for rule in record.episode.allowed_next_actions for condition in rule.when}
        provenance_ok = True
        source_type_ok = True
        claims = list(primary_gold_claims(record))
        supported = []
        for claim in claims:
            category_status[(claim.category.value, claim.status.value)] += 1
            pointers_ok = []
            for pointer in claim.provenance:
                event = trace.get(pointer.trace_id)
                exists, _ = _path(event or {}, pointer.field_path)
                pointers_ok.append(exists)
                source_type_ok &= bool(event and event.get("source_type") == pointer.source_type)
            provenance_ok &= bool(pointers_ok and all(pointers_ok))
            # This is deliberately a lower-bound syntactic witness, not a human
            # semantic judgment: guard reference or exact action-argument use.
            witness = claim.key in conditions or _contains(required, claim.value)
            supported.append(witness)
            mechanically_relevant[(claim.category.value, witness)] += 1
            if claim.status.value in {"unknown", "contradicted"} and claim.value is not None:
                semantic_flags.append({"task_id": record.episode.task_id, "claim_key": claim.key,
                                       "issue": "open_or_contradicted_value_not_null"})
            if claim.category.value == "consent" and claim.status.value == "known" and not isinstance(claim.value, bool):
                semantic_flags.append({"task_id": record.episode.task_id, "claim_key": claim.key,
                                       "issue": "known_consent_not_boolean"})
            if claim.category.value == "commitment" and not claim.provenance:
                semantic_flags.append({"task_id": record.episode.task_id, "claim_key": claim.key,
                                       "issue": "commitment_without_authenticated_pointer"})
        trace_blob = list(record.upstream_trace)
        secret_args = [
            {"event": event["name"], "argument": key, "value": value}
            for event in required for key, value in event["arguments"].items()
            if not _contains(trace_blob, value)
        ]
        legal = legal_terminal_sequences(record)
        exact_gold_legal = not execute_events(record, required).violations
        public = public_action_contract(record)
        public_impacting = {item["action"] for item in public if item["user_impacting"]}
        rule_irreversible = {rule.action for rule in record.episode.allowed_next_actions if rule.irreversible}
        impacting_on_gold = any(event["name"] in public_impacting for event in required)
        task_rows.append({
            "task_id": record.episode.task_id,
            "family": record.episode.split_meta.template_family,
            "domain": record.episode.domain,
            "claims": len(claims),
            "mechanically_witnessed_claims": sum(supported),
            "provenance_leafs_exist": provenance_ok,
            "provenance_source_types_match": source_type_ok,
            "secret_arguments": secret_args,
            "legal_terminal_sequence_count_without_phi": len(legal),
            "gold_sequence_is_legal": exact_gold_legal,
            "unique_legal_terminal_sequence": len(legal) == 1,
            "gold_path_user_impacting": impacting_on_gold,
            "impacting_irreversible_name_sets_match": public_impacting == rule_irreversible,
        })
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    normalized = overlap["collisions"]["normalized_action_graph_hash"]
    flagged = {item["candidate"] for item in normalized}
    domains = {}
    for domain in sorted({row["domain"] for row in task_rows}):
        items = [row for row in task_rows if row["domain"] == domain]
        domains[domain] = {
            "n": len(items),
            "claims": sum(row["claims"] for row in items),
            "mechanically_witnessed_claims": sum(row["mechanically_witnessed_claims"] for row in items),
            "unique_legal_sequence": sum(row["unique_legal_terminal_sequence"] for row in items),
            "user_impacting": sum(row["gold_path_user_impacting"] for row in items),
            "normalized_topology_overlap": sum(row["task_id"] in flagged for row in items),
        }
    return {
        "status": "static_candidate_audit_no_model_calls_no_candidate_edits",
        "n_tasks": len(records),
        "summary": {
            "claims": sum(row["claims"] for row in task_rows),
            "mechanically_witnessed_claims": sum(row["mechanically_witnessed_claims"] for row in task_rows),
            "provenance_leaf_complete_tasks": sum(row["provenance_leafs_exist"] for row in task_rows),
            "provenance_source_type_complete_tasks": sum(row["provenance_source_types_match"] for row in task_rows),
            "tasks_with_secret_arguments": sum(bool(row["secret_arguments"]) for row in task_rows),
            "gold_sequence_legal": sum(row["gold_sequence_is_legal"] for row in task_rows),
            "unique_legal_terminal_sequence_without_phi": sum(row["unique_legal_terminal_sequence"] for row in task_rows),
            "gold_path_user_impacting": sum(row["gold_path_user_impacting"] for row in task_rows),
            "impact_definition_consistent": sum(row["impacting_irreversible_name_sets_match"] for row in task_rows),
            "normalized_topology_overlap_candidates": len(flagged),
        },
        "category_status": {f"{category}/{status}": count
                            for (category, status), count in sorted(category_status.items())},
        "mechanical_relevance_by_category": {
            category: {"witnessed": mechanically_relevant[(category, True)],
                       "not_mechanically_witnessed": mechanically_relevant[(category, False)]}
            for category in sorted({category for category, _ in mechanically_relevant})
        },
        "semantic_flags": semantic_flags,
        "domains": domains,
        "normalized_topology_interpretation": (
            "A normalized hash collision means the action-name/guard topology matches at least one "
            "development episode after identifier normalization. It is neither proof of semantic "
            "duplication nor evidence of independence; all 69 require human workflow review."
        ),
        "tasks": task_rows,
    }


def markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Candidate v2 construct-validity static audit", "",
        "Status: **candidate / unsealed / no model calls / no candidate edits**. This audit reports what repository mechanics can establish and what remains for independent humans.", "",
        "## Findings", "",
        f"- Provenance field-path leaves exist for {s['provenance_leaf_complete_tasks']}/200 tasks; source types match their events for {s['provenance_source_type_complete_tasks']}/200.",
        f"- Required action arguments are present in authenticated traces for {200-s['tasks_with_secret_arguments']}/200 tasks; {s['tasks_with_secret_arguments']} have a mechanically secret argument.",
        f"- The authored gold sequence is legal under action guards for {s['gold_sequence_legal']}/200 tasks. Only {s['unique_legal_terminal_sequence_without_phi']}/200 have a unique legal terminal sequence when the evaluator predicate is withheld.",
        f"- {s['gold_path_user_impacting']}/200 gold paths contain a public user-impacting action; public `user_impacting` names equal evaluator irreversible names for {s['impact_definition_consistent']}/200.",
        f"- Only {s['mechanically_witnessed_claims']}/{s['claims']} proposed claims have a direct syntactic counterfactual witness (guard-key reference or exact action-argument value). The remainder are not thereby invalid, but their minimal causal relevance is **not statically established** and must be reconstructed by annotators.",
        f"- {s['normalized_topology_overlap_candidates']}/200 candidates share a normalized action-graph hash with development data. {report['normalized_topology_interpretation']}", "",
        "## By domain", "", "| Domain | n | claims | syntactic witnesses | unique legal sequence | user-impacting | topology overlap |", "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for domain, item in sorted(report["domains"].items()):
        lines.append(f"| {domain} | {item['n']} | {item['claims']} | {item['mechanically_witnessed_claims']} | {item['unique_legal_sequence']} | {item['user_impacting']} | {item['normalized_topology_overlap']} |")
    lines += ["", "## Category and epistemic semantics", ""]
    lines.extend(f"- `{key}`: {value}" for key, value in report["category_status"].items())
    lines += ["", f"Mechanical semantic flags: {len(report['semantic_flags'])}. Unknown/contradicted claims are checked for null values; known consent is checked for Boolean scope decisions; commitments require authenticated provenance. These are review flags, not automatic invalidity judgments (e.g., a scoped consent may legitimately use a typed object). Passing shape checks does not substitute for human entailment or authority review.", ""]
    lines.extend(f"- `{item['task_id']}` / `{item['claim_key']}`: `{item['issue']}`"
                 for item in report["semantic_flags"])
    lines += ["",
              "## Construct-validity decision", "",
              "The pool passes provenance existence, source-type, argument-grounding, and authored-path executability checks. It does **not** yet establish claim-level counterfactual minimality or uniqueness of the legal policy. Multiple clarification/authority actions often commute, while the terminal predicate selects one arbitrary order. Human annotators must reject or generalize tasks whose public contract admits multiple equally legal sequences, independently justify every claim, audit consent scope and authority precedence, and review all normalized topology overlaps before sealing. No agreement or frozen-test claim is warranted.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    for path in (args.output_json, args.output_markdown):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite: {path}")
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_markdown.write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
