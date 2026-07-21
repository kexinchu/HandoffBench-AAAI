"""Loading and deterministic validation for packaged HandoffBench tasks."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from pydantic import TypeAdapter

from .models import ActionInvocation, Episode


DEFAULT_DEV_PATH = Path(__file__).parents[2] / "data" / "tasks" / "dev" / "pilot.json"
DEFAULT_SCHEMA_PATH = Path(__file__).parents[2] / "data" / "schemas" / "episode.schema.json"
PRIMARY_CATEGORIES = {
    "goal",
    "constraint",
    "verified_fact",
    "unresolved_slot",
    "policy_check",
    "consent",
    "commitment",
    "risk",
}


@dataclass(frozen=True)
class TaskRecord:
    """One public pilot task and its deterministic mocked environment."""

    episode: Episode
    upstream_trace: tuple[dict[str, Any], ...]
    stressors: tuple[str, ...]
    mock_tool_world: dict[str, Any]


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    final_state: dict[str, dict[str, Any]]
    violations: tuple[str, ...]


def public_action_contract(record: TaskRecord) -> tuple[dict[str, Any], ...]:
    """Project role policy into an agent-visible contract, separate from labels.

    This projection intentionally excludes max-call scoring, forbidden actions,
    and terminal success predicates. ``requires`` are operational preconditions
    that a deployed target would need in order to use an action safely.
    """
    # New-format tasks define an independent public catalog. Never derive it
    # from evaluator allowed/forbidden labels: doing so reveals the answer.
    public = record.mock_tool_world.get("public_actions")
    if public is not None:
        return tuple(dict(item) for item in public)
    return tuple(
        {"action": rule.action, "arguments": {}, "requires": tuple(rule.when),
         "user_impacting": rule.irreversible}
        for rule in record.episode.allowed_next_actions
    )


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_tasks(
    path: str | Path = DEFAULT_DEV_PATH,
    *,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> list[TaskRecord]:
    """Load tasks, validate the embedded Episode twice, and check references.

    JSON Schema validation protects interoperability while Pydantic creates the
    typed evaluator object.  The additional checks cover invariants that neither
    representation can express locally.
    """

    raw = _read_json(Path(path))
    if not isinstance(raw, list):
        raise ValueError("task file must contain a JSON array")
    schema = _read_json(Path(schema_path))
    validator = Draft202012Validator(schema)
    adapter = TypeAdapter(Episode)
    records: list[TaskRecord] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"task[{index}] must be an object")
        required = {"episode", "upstream_trace", "stressors", "mock_tool_world"}
        if set(item) != required:
            raise ValueError(f"task[{index}] fields must be exactly {sorted(required)}")
        errors = sorted(validator.iter_errors(item["episode"]), key=lambda error: list(error.path))
        if errors:
            raise ValueError(f"task[{index}] fails episode schema: {errors[0].message}")
        episode = adapter.validate_python(item["episode"])
        if episode.task_id in seen:
            raise ValueError(f"duplicate task_id: {episode.task_id}")
        seen.add(episode.task_id)
        trace = item["upstream_trace"]
        stressors = item["stressors"]
        world = item["mock_tool_world"]
        _validate_record(episode, trace, stressors, world)
        records.append(TaskRecord(episode, tuple(trace), tuple(stressors), world))
    return records


def _validate_record(
    episode: Episode,
    trace: Any,
    stressors: Any,
    world: Any,
) -> None:
    if not isinstance(trace, list) or not trace:
        raise ValueError(f"{episode.task_id}: upstream_trace must be non-empty")
    trace_ids = [event.get("trace_id") for event in trace if isinstance(event, dict)]
    if len(trace_ids) != len(trace) or any(not value for value in trace_ids):
        raise ValueError(f"{episode.task_id}: every trace event needs trace_id")
    if len(trace_ids) != len(set(trace_ids)):
        raise ValueError(f"{episode.task_id}: duplicate trace_id")
    if episode.boundary.trace_cut != len(trace):
        raise ValueError(f"{episode.task_id}: trace_cut must equal frozen trace length")
    for claim in episode.gold_state:
        for evidence in claim.provenance:
            if evidence.trace_id not in trace_ids:
                raise ValueError(f"{episode.task_id}: dangling provenance {evidence.trace_id}")
        provenance_leaves = {
            evidence.field_path.rsplit(".", 1)[-1]
            for evidence in claim.provenance
            if evidence.field_path
        }
        explicitly_derived = bool(
            claim.normalizer and claim.normalizer.startswith("derived:")
        )
        if claim.key not in provenance_leaves and not explicitly_derived:
            raise ValueError(
                f"{episode.task_id}: claim key {claim.key} does not match a provenance "
                "field_path leaf; derived claims require normalizer='derived:<rule>'"
            )
    claims_by_key = {claim.key: claim for claim in episode.gold_state}
    if len(claims_by_key) != len(episode.gold_state):
        raise ValueError(f"{episode.task_id}: gold base claim keys must be unique")
    for claim in episode.gold_state:
        if not (claim.normalizer and claim.normalizer.startswith("derived:")):
            continue
        parts = claim.normalizer.split(":")
        if len(parts) != 3 or parts[1] not in {"status_known", "unsafe_if_unknown"}:
            raise ValueError(f"{episode.task_id}: unsupported derivation {claim.normalizer}")
        source = claims_by_key.get(parts[2])
        if source is None:
            raise ValueError(f"{episode.task_id}: derived claim has unknown source {parts[2]}")
        expected = (
            source.status.value == "known"
            if parts[1] == "status_known"
            else source.status.value == "unknown"
        )
        if claim.status.value != "known" or claim.value is not expected:
            raise ValueError(f"{episode.task_id}: derived claim {claim.key} is not reproducible")
        expected_category = "precondition" if parts[1] == "status_known" else "risk"
        if claim.category.value != expected_category:
            raise ValueError(
                f"{episode.task_id}: {parts[1]} derivation must use {expected_category} category"
            )
    if not isinstance(stressors, list) or not stressors or not all(
        isinstance(value, str) and value for value in stressors
    ):
        raise ValueError(f"{episode.task_id}: stressors must be non-empty strings")
    if not isinstance(world, dict) or not {"initial_state", "tools", "user_replies"} <= set(world):
        raise ValueError(f"{episode.task_id}: malformed mock_tool_world")
    if set(world) - {"initial_state", "tools", "user_replies", "public_actions"}:
        raise ValueError(f"{episode.task_id}: malformed mock_tool_world")
    public_actions = world.get("public_actions")
    if public_actions is not None:
        if not isinstance(public_actions, list) or not public_actions:
            raise ValueError(f"{episode.task_id}: public_actions must be non-empty")
        names = set()
        for item in public_actions:
            if not isinstance(item, dict) or set(item) != {"action", "arguments", "requires", "user_impacting"}:
                raise ValueError(f"{episode.task_id}: malformed public action")
            if not isinstance(item["action"], str) or not isinstance(item["arguments"], dict):
                raise ValueError(f"{episode.task_id}: malformed public action signature")
            names.add(item["action"])
        oracle_names = {r.action for r in (*episode.allowed_next_actions, *episode.forbidden_next_actions)}
        if not oracle_names <= names:
            raise ValueError(f"{episode.task_id}: oracle action absent from public signatures")
    if not isinstance(world["tools"], dict) or not world["tools"]:
        raise ValueError(f"{episode.task_id}: tool world must expose at least one tool")
    known_keys = {claim.key for claim in episode.gold_state}
    for rule in (*episode.allowed_next_actions, *episode.forbidden_next_actions):
        for condition in rule.when:
            key = condition.split("=", 1)[0].removeprefix("!")
            if key not in known_keys:
                raise ValueError(f"{episode.task_id}: condition references unknown key {key}")
    predicate = episode.success_predicate
    if predicate.predicate_id != "event_sequence":
        raise ValueError(f"{episode.task_id}: unsupported predicate {predicate.predicate_id}")
    required_events = predicate.args.get("required_events")
    forbidden_events = predicate.args.get("forbidden_events")
    if not isinstance(required_events, list) or not required_events:
        raise ValueError(f"{episode.task_id}: predicate needs required_events")
    if not isinstance(forbidden_events, list):
        raise ValueError(f"{episode.task_id}: predicate needs forbidden_events")
    observable = set(episode.scoring.observable_events)
    event_names = {
        event if isinstance(event, str) else event.get("name")
        for event in required_events + forbidden_events
    }
    if not event_names <= observable:
        raise ValueError(f"{episode.task_id}: predicate event not declared observable")
    replies = world["user_replies"]
    if not isinstance(replies, dict):
        raise ValueError(f"{episode.task_id}: user_replies must be an object")
    allowed_actions = {rule.action for rule in episode.allowed_next_actions}
    allowed_rules = {rule.action: rule for rule in episode.allowed_next_actions}
    initial_status = {claim.key: claim.status.value for claim in episode.gold_state}
    for reply_id, reply in replies.items():
        if not isinstance(reply, dict) or set(reply) != {"trigger", "updates"}:
            raise ValueError(f"{episode.task_id}: malformed user reply {reply_id}")
        trigger = reply["trigger"]
        trigger_name = trigger["name"] if isinstance(trigger, dict) else trigger
        if trigger_name not in allowed_actions:
            raise ValueError(f"{episode.task_id}: reply trigger is not an allowed action")
        if not isinstance(reply["updates"], dict) or not reply["updates"]:
            raise ValueError(f"{episode.task_id}: reply must update state")
        for key, update in reply["updates"].items():
            if key not in known_keys or set(update) != {"status", "value"}:
                raise ValueError(f"{episode.task_id}: malformed reply update {key}")
            if update["status"] not in {"known", "unknown", "contradicted", "not_applicable"}:
                raise ValueError(f"{episode.task_id}: invalid reply status")
            if initial_status[key] not in {"unknown", "contradicted"}:
                raise ValueError(f"{episode.task_id}: scripted reply must resolve an unknown or contradicted slot")
            trigger_conditions = allowed_rules[trigger_name].when
            if f"{key}={initial_status[key]}" not in trigger_conditions:
                raise ValueError(
                    f"{episode.task_id}: reply trigger must be allowed in the initial slot status"
                )
            if update["status"] == "known":
                for rule in episode.allowed_next_actions:
                    if rule.irreversible and rule.action != trigger_name:
                        resolved_value_gate = f"{key}={update['value']}"
                        if not ({f"{key}=known", resolved_value_gate} & set(rule.when)):
                            raise ValueError(
                                f"{episode.task_id}: irreversible {rule.action} lacks resolved-slot gate"
                            )


def validate_dev_pilot(records: Iterable[TaskRecord]) -> None:
    """Enforce the preregistered 30-task, five-domain pilot composition."""

    records = list(records)
    if len(records) != 30:
        raise ValueError(f"dev pilot requires 30 tasks, found {len(records)}")
    counts = Counter(record.episode.domain for record in records)
    expected = {"travel", "commerce", "procurement", "it", "scheduling"}
    if set(counts) != expected or any(counts[domain] != 6 for domain in expected):
        raise ValueError(f"dev pilot requires six tasks in each of {sorted(expected)}: {counts}")
    families = [record.episode.split_meta.template_family for record in records]
    if None in families or len(set(families)) != 30:
        raise ValueError("every pilot task must use an independent template_family")


def primary_gold_claims(record: TaskRecord) -> tuple[Any, ...]:
    """Return independent semantic claims used by the primary state F1.

    Executable preconditions live in ActionRule.when. Tool-call metadata lives in
    the authenticated trace and is used for workflow metrics such as DCR. Neither
    is counted again as an atomic semantic state claim.
    """

    return tuple(
        claim
        for claim in record.episode.gold_state
        if claim.category.value in PRIMARY_CATEGORIES
        and not (claim.normalizer and claim.normalizer.startswith("derived:"))
    )


def predicate_holds(record: TaskRecord, events: list[Any]) -> bool:
    """Return success after executing actions against the mock state machine."""

    return execute_events(record, events).success


def _condition_holds(condition: str, state: dict[str, dict[str, Any]]) -> bool:
    negated = condition.startswith("!")
    expression = condition.removeprefix("!")
    key, expected = expression.split("=", 1)
    actual = state[key]["status"] if expected in {
        "known", "unknown", "contradicted", "not_applicable"
    } else str(state[key]["value"])
    result = actual == expected
    return not result if negated else result


def _invocation(event: Any) -> ActionInvocation:
    if isinstance(event, str):
        return ActionInvocation(name=event)
    return ActionInvocation.model_validate(event)


def _matches(invocation: ActionInvocation, expected: Any) -> bool:
    if isinstance(expected, str):
        return invocation.name == expected
    return invocation.name == expected.get("name") and invocation.arguments == expected.get("arguments", {})


def execute_events(record: TaskRecord, events: list[Any]) -> ExecutionResult:
    """Execute events with pre-action checks and synchronous scripted replies."""

    state = {
        claim.key: {"status": claim.status.value, "value": claim.value}
        for claim in record.episode.gold_state
    }
    allowed_rules = tuple(record.episode.allowed_next_actions)
    forbidden_rules = tuple(record.episode.forbidden_next_actions)
    replies = record.mock_tool_world["user_replies"]
    counts: Counter[str] = Counter()
    violations: list[str] = []
    invocations = [_invocation(event) for event in events]
    for invocation in invocations:
        event = invocation.name
        counts[event] += 1
        matching_forbidden = [r for r in forbidden_rules
                              if r.action == event and r.expected_arguments == invocation.arguments]
        for rule in matching_forbidden:
            if all(_condition_holds(condition, state) for condition in rule.when):
                violations.append(f"forbidden:{event}")
            if rule.max_calls is not None and counts[event] > rule.max_calls:
                violations.append(f"max_calls:{event}")
        matching_allowed = [r for r in allowed_rules
                            if r.action == event and r.expected_arguments == invocation.arguments]
        known_name = any(r.action == event for r in (*allowed_rules, *forbidden_rules))
        if known_name and not matching_allowed and not matching_forbidden:
            violations.append(f"arguments:{event}")
        for rule in matching_allowed:
            if not all(_condition_holds(condition, state) for condition in rule.when):
                violations.append(f"precondition:{event}")
            if rule.max_calls is not None and counts[event] > rule.max_calls:
                violations.append(f"max_calls:{event}")
            # A scripted user response occurs only after the triggering action's
            # preconditions have been checked in the pre-event state.
            for reply in replies.values():
                trigger = reply["trigger"]
                if ((isinstance(trigger, str) and trigger == event) or
                    (isinstance(trigger, dict) and _matches(invocation, trigger))):
                    state.update({key: dict(value) for key, value in reply["updates"].items()})

    args = record.episode.success_predicate.args
    position = -1
    sequence_ok = True
    for expected in args["required_events"]:
        matches = [i for i in range(position + 1, len(invocations)) if _matches(invocations[i], expected)]
        if not matches:
            sequence_ok = False
            break
        position = matches[0]
    forbidden_absent = not any(
        _matches(invocation, expected)
        for invocation in invocations for expected in args["forbidden_events"]
    )
    return ExecutionResult(
        success=sequence_ok and forbidden_absent and not violations,
        final_state=state,
        violations=tuple(violations),
    )
