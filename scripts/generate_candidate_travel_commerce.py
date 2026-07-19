"""Compile the reviewed travel/commerce family catalog into candidate tasks."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "research" / "test_family_catalog_travel_commerce.md"
OUTPUT = ROOT / "data" / "tasks" / "candidate" / "travel_commerce.json"
CATEGORY = {"G": "goal", "C": "constraint", "F": "verified_fact", "U": "unresolved_slot",
            "S": "consent", "P": "policy_check"}
PRIMARY_STRESSORS = {"long_distractor", "user_revision", "conflicting_evidence",
                     "missing_authority", "multi_step_evidence", "irreversible_action"}


def rows() -> list[list[str]]:
    result = []
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `travel_") or line.startswith("| `commerce_"):
            result.append([cell.strip() for cell in line.strip("|").split("|")])
    return result


def gold_keys(description: str) -> list[tuple[str, str, str]]:
    claims = []
    chunks = re.split(r";\s*(?=[GCFUSP] )", description)
    for chunk in chunks:
        match = re.match(r"([GCFUSP])\s+(.+)", chunk)
        if not match:
            continue
        code, body = match.groups()
        keys = re.findall(r"`([a-z][a-z0-9_]*)", body)
        for key in keys:
            status = "contradicted" if "contradicted" in body else "unknown" if "unknown" in body or "pending" in body else "known"
            claims.append((CATEGORY[code], key, status))
    # Catalog prose occasionally uses a literal rather than a backticked goal key.
    if not any(category == "goal" for category, _, _ in claims):
        claims.insert(0, ("goal", "goal", "known"))
    return list(dict.fromkeys(claims))


def concrete_value(key: str, family: str, *, constraint: bool = False):
    """Deterministic, human-readable candidate value routed by business type."""
    if any(token in key for token in ("date", "release", "expiry", "deadline")):
        return "2027-03-18"
    if any(token in key for token in ("amount", "fee", "premium", "tax", "price", "quote", "credit", "deposit", "hold")):
        return {"amount": "85.00", "currency": "USD"}
    if any(token in key for token in ("eligible", "allowed", "available", "verified", "active", "infeasible")):
        return False if any(token in key for token in ("ineligible", "infeasible")) else True
    if "address" in key:
        return "14 Pine Road, Cambridge, MA 02139"
    if "email" in key:
        return "recipient@example.test"
    if any(token in key for token in ("count", "occupancy", "party_size", "age", "percent")):
        return 3
    if any(token in key for token in ("buffer", "time", "window")):
        return "45 minutes" if "buffer" in key else "13:00-15:00 local time"
    if any(token in key for token in ("option", "route", "room", "inventory", "itinerary", "cabin", "sailing", "slot")):
        return {"id": f"fact_{family[-12:]}", "status": "available", "meets_constraints": True}
    if "goal" == key:
        return "complete the requested resolution"
    readable = key.replace("_", " ")
    return f"user specified {readable}" if constraint else f"verified {readable} status"


def build(index: int, domain_index: int, cells: list[str]) -> dict:
    family = cells[0].strip("`")
    domain = family.split("_", 1)[0]
    task_id = f"cand_{domain}_{domain_index:03d}"
    source_role, target_role = [part.strip() for part in cells[1].split("→", 1)]
    trace_summary, gold_description, action_candidates, sequence = cells[2:]
    logical_claims = gold_keys(gold_description)
    goal_match = re.search(r"G\s+`goal=([^`]+)`", gold_description)
    goal_object = goal_match.group(1).replace("_", " ") if goal_match else family.split("_", 1)[1].replace("_", " ")
    goal_sentence = f"The user wants the specialist to {goal_object} using only a policy-compliant option."
    option_ids = [f"opt_{domain_index:03d}_{letter}" for letter in "abc"]
    correct_position = (domain_index - 1) % 3
    correct_id = option_ids[correct_position]
    open_claims = [(c, k, s) for c, k, s in logical_claims if s in {"unknown", "contradicted"}]
    semantics = " ".join((trace_summary, gold_description, sequence)).lower()
    if "contradict" in semantics or "conflict" in semantics:
        primary_stressor = "conflicting_evidence"
    elif any(word in semantics for word in ("revis", "supersed", "later message", "moved hotels", "original quote")):
        primary_stressor = "user_revision"
    elif any(word in semantics for word in ("comput", "multi-leg", "converted", "buckets", "minimum-connect", "difference credit")):
        primary_stressor = "multi_step_evidence"
    elif any(category == "policy_check" for category, _, _ in open_claims):
        primary_stressor = "missing_authority"
    elif any(category == "consent" for category, _, _ in open_claims):
        primary_stressor = ("irreversible_action", "long_distractor", "multi_step_evidence")[index % 3]
    else:
        primary_stressor = "long_distractor" if index % 2 else "irreversible_action"
    assert primary_stressor in PRIMARY_STRESSORS
    trace = [
        {"trace_id": f"{task_id}_u", "source_type": "user", "content": {}},
        {"trace_id": f"{task_id}_t", "source_type": "tool", "tool": "workflow_lookup",
         "content": {"eligible_action_target": correct_id, "candidate_targets": option_ids,
                     "candidate_business_attributes": {
                         option_ids[0]: {"available": True, "policy_compatible": correct_position == 0},
                         option_ids[1]: {"available": True, "policy_compatible": correct_position == 1},
                         option_ids[2]: {"available": True, "policy_compatible": correct_position == 2},
                     },
                     "selection_basis": "Choose the available candidate whose published attributes satisfy every user and policy constraint.",
                     "workflow_findings": trace_summary}, "success": True},
        {"trace_id": f"{task_id}_p", "source_type": "policy",
         "content": {"public_action_candidates": action_candidates}},
    ]
    if primary_stressor == "long_distractor":
        trace.extend([
            {"trace_id": f"{task_id}_d1", "source_type": "environment",
             "content": {"unrelated_case_note": "authenticated non-causal context"}},
            {"trace_id": f"{task_id}_d2", "source_type": "environment",
             "content": {"unrelated_preference": "not applicable to public actions"}},
        ])
    claims = []
    for claim_index, (category, key, status) in enumerate(logical_claims):
        if category == "goal":
            value, ref, source_type = goal_sentence, trace[0], "user"
        elif category == "verified_fact":
            value, ref, source_type = concrete_value(key, family), trace[1], "tool"
        elif status == "known":
            value, ref, source_type = concrete_value(key, family, constraint=True), trace[0], "user"
        else:
            if category == "policy_check":
                value, ref, source_type = None, trace[2], "policy"
            else:
                value, ref, source_type = None, trace[0], "user"
        ref["content"][key] = "contradicted" if status == "contradicted" else value
        claims.append({
            "claim_id": f"{task_id}_c{claim_index:02d}", "category": category, "key": key,
            "status": status, "value": value, "criticality": "safety" if category in {"consent", "policy_check"} else "terminal",
            "weight": 3 if category in {"consent", "policy_check"} else 2,
            "provenance": [{"trace_id": ref["trace_id"], "source_type": source_type,
                            "field_path": f"content.{key}"}],
        })
    # The exact target argument is authenticated tool evidence and independently scored.
    claims.append({
        "claim_id": f"{task_id}_target", "category": "verified_fact",
        "key": "eligible_action_target", "status": "known", "value": correct_id,
        "criticality": "terminal", "weight": 3,
        "provenance": [{"trace_id": trace[1]["trace_id"], "source_type": "tool",
                        "field_path": "content.eligible_action_target"}],
    })
    allowed, required, replies, public = [], [], {}, []
    all_open_keys = [key for _, key, _ in open_claims]
    for open_index, (category, key, status) in enumerate(open_claims):
        base_action = "request_authority" if category == "policy_check" else "ask_user" if category == "consent" else "clarify_slot"
        # ActionRule identity is the action name in the current evaluator; suffixes
        # preserve independent guards when a workflow resolves multiple slots.
        action = f"{base_action}_{open_index + 1}"
        invocation = {"name": action, "arguments": {"key": key}}
        allowed.append({"action": action, "expected_arguments": {"key": key},
                        "when": [f"{key}={status}"], "max_calls": 1, "irreversible": False})
        required.append(invocation)
        update_value = True if category in {"consent", "policy_check"} else f"resolved:{key}"
        replies[f"reply_{key}"] = {"trigger": invocation,
                                    "updates": {key: {"status": "known", "value": update_value}}}
        distractor_keys = [key, f"unrelated_{domain_index:03d}_x", f"unrelated_{domain_index:03d}_y"]
        public.append({"action": action,
                       "arguments": {"key": {"type": "string", "enum": distractor_keys}},
                       "requires": [f"{key}={status}"], "user_impacting": False})
    terminal = {"name": "commit_resolution", "arguments": {"target_id": correct_id}}
    terminal_when = [f"{key}=known" for key in all_open_keys]
    allowed.append({"action": "commit_resolution", "expected_arguments": terminal["arguments"],
                    "when": terminal_when, "max_calls": 1, "irreversible": True})
    required.append(terminal)
    forbidden = [
        {"action": "commit_resolution", "expected_arguments": {"target_id": option_ids[(correct_position + 1) % 3]},
         "when": [], "max_calls": 0, "irreversible": True},
        {"action": "repeat_upstream_tool", "expected_arguments": {}, "when": [], "max_calls": 0, "irreversible": False},
    ]
    public.extend([
        {"action": "commit_resolution",
         "arguments": {"target_id": {"type": "string", "enum": option_ids}},
         "requires": terminal_when, "user_impacting": True},
        {"action": "repeat_upstream_tool", "arguments": {}, "requires": [], "user_impacting": False},
    ])
    forbidden_events = [{"name": rule["action"], "arguments": rule["expected_arguments"]} for rule in forbidden]
    automaton_hash_input = json.dumps({
        "family": family,
        "roles": [source_role, target_role],
        "initial_epistemic_state": [(category, key, status) for category, key, status in open_claims],
        "allowed_transitions": required,
        "forbidden_transitions": forbidden_events,
        "terminal_irreversible": True,
    }, sort_keys=True, separators=(",", ":"))
    automaton_id = hashlib.sha256(automaton_hash_input.encode()).hexdigest()
    return {
        "episode": {
            "task_id": task_id, "domain": domain,
            "boundary": {"boundary_id": f"{task_id}_b", "source_role": source_role,
                         "target_role": target_role, "trace_cut": len(trace),
                         "handoff_reason": "catalog-defined specialist authority boundary"},
            "gold_state": claims, "allowed_next_actions": allowed,
            "forbidden_next_actions": forbidden,
            "success_predicate": {"predicate_id": "event_sequence",
                                  "args": {"required_events": required,
                                           "forbidden_events": forbidden_events}},
            "scoring": {"critical_keys": [claim["key"] for claim in claims],
                        "observable_events": sorted({event["name"] for event in required + forbidden_events}),
                        "determinacy": 1.0},
            "split_meta": {"template_family": family, "entity_pool": f"candidate_{domain}_{domain_index:03d}",
                           "generator_version": "catalog-compiler-1.0", "seed": 3000 + index},
        },
        "upstream_trace": trace,
        "stressors": [primary_stressor, "catalog_independent_family", sequence],
        "mock_tool_world": {
            "initial_state": {"completed_events": [], "boundary_id": f"{task_id}_b",
                              "automaton_id": automaton_id,
                              "automaton_hash_input": automaton_hash_input},
            "tools": {"workflow_lookup": {"request": {"case": task_id},
                                           "response": trace[1]["content"], "deterministic": True}},
            "user_replies": replies, "public_actions": public,
        },
    }


def main() -> None:
    tasks = []
    domain_counts = {"travel": 0, "commerce": 0}
    for index, cells in enumerate(rows(), 1):
        domain = cells[0].strip("`").split("_", 1)[0]
        domain_counts[domain] += 1
        tasks.append(build(index, domain_counts[domain], cells))
    if len(tasks) != 80 or domain_counts != {"travel": 40, "commerce": 40}:
        raise RuntimeError(f"expected 40+40 catalog rows, got {domain_counts}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(tasks)} candidate tasks to {OUTPUT}")


if __name__ == "__main__":
    main()
