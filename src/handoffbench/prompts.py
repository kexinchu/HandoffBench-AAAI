"""Canonical receiver probe and action-output contract."""

from __future__ import annotations

import json
import hashlib
from typing import Any, Mapping

from .dataset import public_action_contract
from .transfer import STATE_FIELDS, TransferView, canonicalize_state


ROUTING_GUIDE = (
    "State routing guide: route a tool event's business value to verified_facts; route an unknown "
    "ordinary task parameter to unresolved_slots; route scoped authorization, confirmation, or "
    "acceptance to consent; and route a policy approval, clearance, or verification decision to "
    "policy_checks. Do not duplicate the same key across fields. In this pilot, tool_evidence is only "
    "for tool-execution metadata, not business facts, and next_step_preconditions is only for public "
    "action-contract conditions; both are usually empty. Use risk_flags or commitments only with "
    "explicit authenticated evidence."
)


STATE_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["key", "status", "value"],
    "properties": {"key": {"type": "string", "minLength": 1},
                   "status": {"enum": ["known", "unknown", "contradicted", "not_applicable"]},
                   "value": {}},
    "allOf": [{
        "if": {"properties": {"status": {"enum": ["unknown", "not_applicable"]}},
               "required": ["status"]},
        "then": {"properties": {"value": {"type": "null"}}},
    }],
}
STATE_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False, "required": list(STATE_FIELDS),
    "properties": {field: {"type": "array", "items": STATE_ITEM_SCHEMA} for field in STATE_FIELDS},
}

ACTION_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["receiver_state", "action"],
    "properties": {
        "receiver_state": STATE_SCHEMA,
        "action": {
            "type": "object", "additionalProperties": False,
            "required": ["name", "arguments", "rationale"],
            "properties": {"name": {"type": "string"}, "arguments": {"type": "object"},
                           "rationale": {"type": "string"}},
        },
    },
}

STRUCTURED_SOURCE_SCHEMA: dict[str, Any] = STATE_SCHEMA
EHC_SOURCE_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["state", "provenance", "checks"],
    "properties": {
        "state": STRUCTURED_SOURCE_SCHEMA,
        "provenance": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["field", "key", "trace_id", "source_type"],
            "properties": {"field": {"enum": list(STATE_FIELDS)}, "key": {"type": "string"},
                           "trace_id": {"type": "string"},
                           "source_type": {"enum": ["user", "tool", "policy", "environment"]}},
        }},
        "checks": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "required": ["condition", "status"],
                    "properties": {"condition": {"type": "string"},
                                   "status": {"enum": ["satisfied", "missing", "contradicted"]}}}},
    },
}
FACTORIAL_SOURCE_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["state", "provenance"],
    "properties": {
        "state": STRUCTURED_SOURCE_SCHEMA,
        "provenance": EHC_SOURCE_SCHEMA["properties"]["provenance"],
    },
}


def receiver_messages(target_role: str, view: TransferView) -> list[dict[str, str]]:
    system = (
        f"You are the receiving {target_role}. Reconstruct your state and select exactly one next action. "
        "Use only supplied evidence; unknown means unknown. For claims already present in a supplied "
        "handoff, preserve their key and value exactly. For raw-history claims, key must be the exact "
        "property name in the referenced event.content object and a known value must be that property's "
        "exact JSON value. If the content value is the string 'unknown' or null, use status unknown and "
        "value null. Never put a trace path or trace_id in value, and never use a claim value as its key. "
        "Claims with status unknown or not_applicable "
        "must use null as value. Status is restricted to exactly known, unknown, contradicted, or "
        "not_applicable. " + ROUTING_GUIDE + " Return JSON only matching this schema: "
        + json.dumps(ACTION_SCHEMA, sort_keys=True, separators=(",", ":"))
    )
    payload = {"handoff_kind": view.kind.value, "handoff": dict(view.content)}
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, sort_keys=True, ensure_ascii=False)}]


def source_messages(
    source_role: str,
    kind: str,
    trace: tuple[dict[str, Any], ...],
    policy_predicates: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    """Ask the source agent to transfer only what is evidenced in the frozen trace."""
    if kind == "free_summary":
        contract = "Return only a concise natural-language handoff summary."
    elif kind == "structured_payload":
        contract = (
            "Return JSON only: an object with exactly these array-valued fields in this order: "
            + ", ".join(STATE_FIELDS) + ". Every array item must contain exactly key, status, value; "
            "status is known, unknown, contradicted, or not_applicable."
        )
    elif kind == "ehc":
        contract = (
            "Return JSON only with keys state, provenance, checks. state has exactly these "
            f"array-valued fields in this order: {', '.join(STATE_FIELDS)}. Every state array item "
            "contains exactly key, status, value. Each provenance item "
            "must contain exactly field, key, trace_id, source_type and must cite the trace. "
            "Do not generate content_hash; the framework attaches it deterministically. "
            "Each check has only condition and status (satisfied, missing, or contradicted). "
            "Emit exactly one check for each supplied public policy predicate. Public policy "
            "predicates are inputs only for top-level checks: never copy a predicate or its key into "
            "state or any state field. policy_checks state items are allowed only for an explicit "
            "policy decision, approval, clearance, or verification property present in trace "
            "event.content."
        )
    elif kind == "factorial":
        contract = (
            "Return JSON only with exactly state and provenance. state has exactly these "
            f"array-valued fields in this order: {', '.join(STATE_FIELDS)}. Every state item has "
            "exactly key, status, value. Every provenance item has exactly field, key, trace_id, "
            "source_type and cites the trace. Emit no checks: the framework evaluates the supplied "
            "public predicates. This common extraction artifact is serialized into the assigned "
            "representation cell after generation."
        )
    else:
        raise ValueError(f"no source generation prompt for {kind}")
    system = (
        f"You are the source {source_role}. Prepare a handoff using only the supplied frozen trace. "
        "Never infer consent, commitments, or completed actions. For every state claim, key must be the "
        "exact property name in the referenced event.content object and a known value must be that "
        "property's exact JSON value. If the content value is the string 'unknown' or null, use status "
        "unknown and value null. Use the event's trace_id only in provenance; never put a trace path or "
        "trace_id in value, and never use a claim value as its key. Claims with status unknown or "
        "not_applicable must use null as value. "
        "Status is restricted to exactly known, unknown, contradicted, or not_applicable. "
        "Unknown remains unknown. " + ROUTING_GUIDE + " " + contract
    )
    payload: dict[str, Any] = {"upstream_trace": trace}
    if kind in {"structured_payload", "ehc", "factorial"}:
        payload["public_policy_predicates"] = policy_predicates
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def action_catalog(record: Any) -> list[dict[str, Any]]:
    """Public role contract; deliberately excludes evaluator-only labels."""
    catalog = [
        {"name": item["action"], "arguments": item.get("arguments", {}),
         "requires": list(item["requires"]),
         "user_impacting": item["user_impacting"]}
        for item in public_action_contract(record)
    ]
    for name, spec in record.mock_tool_world["tools"].items():
        signature = {key: "any" for key in spec.get("request", {}) if key != "task_id"}
        if name not in {item["name"] for item in catalog}:
            catalog.append({"name": name, "arguments": signature, "requires": [],
                            "user_impacting": False})
    # Stable per-task permutation prevents list position from becoming a label.
    permutation_key = (record.episode.split_meta.entity_pool
                       if record.episode.split_meta and record.episode.split_meta.entity_pool
                       else record.episode.task_id)
    return sorted(catalog, key=lambda item: hashlib.sha256(
        f"{permutation_key}|{item['name']}|{json.dumps(item['arguments'], sort_keys=True)}".encode()
    ).hexdigest())


def receiver_turn_messages(
    target_role: str,
    view: TransferView,
    record: Any,
    interaction: list[dict[str, Any]],
) -> list[dict[str, str]]:
    messages = receiver_messages(target_role, view)
    visible = {"available_actions": action_catalog(record), "interaction_so_far": interaction}
    messages[0]["content"] += (
        " The public action catalog contains names, argument signatures, and required state "
        "predicates. These are operational policy, not evaluator success labels. "
        "Choose only a listed action whose requires predicates are all satisfied by the current "
        "receiver state. A known boolean false is explicit negative evidence, not an unknown value. "
        "Every argument value must be one of the listed enum values when an enum is present; use "
        "enum_descriptions to distinguish their operational meanings. Do not copy a state predicate "
        "into an argument and do not invent an action or argument value."
    )
    messages[1]["content"] += "\n" + json.dumps(visible, sort_keys=True, ensure_ascii=False)
    return messages


def parse_receiver_output(raw: str) -> Mapping[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"receiver_state", "action"}:
        raise ValueError("receiver output has wrong top-level fields")
    state, action = value["receiver_state"], value["action"]
    if not isinstance(state, dict):
        raise ValueError("receiver_state must be an object")
    try:
        state = canonicalize_state(state)
    except ValueError as error:
        raise ValueError("receiver_state fields do not match the probe") from error
    if any(not isinstance(value, list) for value in state.values()):
        raise ValueError("receiver_state slots must be arrays")
    statuses = {"known", "unknown", "contradicted", "not_applicable"}
    for field, items in state.items():
        for index, item in enumerate(items):
            if not isinstance(item, dict) or set(item) != {"key", "status", "value"}:
                raise ValueError(f"receiver_state {field}[{index}] must contain exactly key/status/value")
            if not isinstance(item["key"], str) or not item["key"]:
                raise ValueError(f"receiver_state {field}[{index}] key must be a non-empty string")
            if item["status"] not in statuses:
                raise ValueError(f"receiver_state {field}[{index}] has invalid status")
            if item["status"] in {"unknown", "not_applicable"} and item["value"] is not None:
                raise ValueError(f"receiver_state {field}[{index}] unknown/not_applicable value must be null")
    if not isinstance(action, dict) or set(action) != {"name", "arguments", "rationale"}:
        raise ValueError("action fields do not match schema")
    if not isinstance(action["name"], str) or not isinstance(action["arguments"], dict) or not isinstance(action["rationale"], str):
        raise ValueError("action value types do not match schema")
    return {"receiver_state": state, "action": action}
