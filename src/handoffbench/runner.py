"""Immutable, content-addressed single-boundary runner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .dataset import ExecutionResult, TaskRecord, execute_events, public_action_contract
from .prompts import (
    ACTION_SCHEMA,
    EHC_SOURCE_SCHEMA,
    FACTORIAL_SOURCE_SCHEMA,
    STRUCTURED_SOURCE_SCHEMA,
    action_catalog,
    parse_receiver_output,
    receiver_messages,
    receiver_turn_messages,
    source_messages,
)
from .providers import Provider
from .transfer import (
    EnforcementFactor,
    TransferConfig,
    TransferKind,
    legacy_transfer_config,
    make_factorial_view,
    make_view,
)


@dataclass(frozen=True)
class RunConfig:
    model: str
    transfer_kind: TransferKind
    temperature: float = 0.0
    seed: int = 0
    protocol_version: str = "handoffbench-v1"
    max_turns: int = 4
    max_output_tokens: int = 1600
    enforce_action_gates: bool = False
    factorial_cell: TransferConfig | None = None

    def __post_init__(self) -> None:
        if (self.transfer_kind is TransferKind.FACTORIAL) != (self.factorial_cell is not None):
            raise ValueError("factorial_cell is required exactly when transfer_kind=factorial")

    @property
    def transfer_config(self) -> TransferConfig | None:
        """Factor label for legacy methods, including the separate gate arm."""
        base = self.factorial_cell if self.transfer_kind is TransferKind.FACTORIAL \
            else legacy_transfer_config(self.transfer_kind)
        if base is None:
            return None
        return TransferConfig(
            base.typing,
            base.provenance,
            base.checks,
            EnforcementFactor.ENFORCED if self.enforce_action_gates
            else EnforcementFactor.ADVISORY,
        )

    @property
    def config_hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class RunArtifact:
    task_id: str
    config: RunConfig
    config_hash: str
    prompt_hash: str
    raw_output: str
    parsed_output: Mapping[str, Any]


@dataclass(frozen=True)
class PilotRunArtifact:
    task_id: str
    config: RunConfig
    config_hash: str
    source_raw_output: str | None
    receiver_raw_outputs: tuple[str, ...]
    prompt_hashes: tuple[str, ...]
    receiver_states: tuple[Mapping[str, Any], ...]
    usage: tuple[Mapping[str, int], ...]
    events: tuple[Mapping[str, Any] | str, ...]
    interactions: tuple[Mapping[str, Any], ...]
    execution: ExecutionResult
    transfer_validation_sidecar: Mapping[str, Any] | None


def generate_transfer(record: TaskRecord, config: RunConfig, provider: Provider) -> tuple[Any, str | None]:
    """Generate source-side conditions without gold, using the base seed namespace."""
    if config.transfer_kind in {TransferKind.FULL_HISTORY, TransferKind.GOLD_ORACLE}:
        return None, None
    source_kind = "factorial" if config.factorial_cell is not None else config.transfer_kind.value
    messages = source_messages(
        record.episode.boundary.source_role,
        source_kind,
        record.upstream_trace,
        tuple(condition for item in public_action_contract(record) for condition in item["requires"]),
    )
    schema = (FACTORIAL_SOURCE_SCHEMA if config.factorial_cell is not None
              else STRUCTURED_SOURCE_SCHEMA if config.transfer_kind is TransferKind.STRUCTURED_PAYLOAD
              else EHC_SOURCE_SCHEMA if config.transfer_kind is TransferKind.EHC else None)
    schema_name = ("factorial_source_artifact" if config.factorial_cell is not None
                   else "structured_handoff" if config.transfer_kind is TransferKind.STRUCTURED_PAYLOAD
                   else "executable_handoff_capsule" if config.transfer_kind is TransferKind.EHC else None)
    raw = provider.complete(messages, model=config.model, temperature=config.temperature,
                            response_schema=schema, schema_name=schema_name, seed=config.seed,
                            max_output_tokens=config.max_output_tokens)
    if config.transfer_kind is TransferKind.FREE_SUMMARY:
        return raw, raw
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError as error:
        raise ValueError("source transfer is not valid JSON") from error


def _simulate(record: TaskRecord, action: Mapping[str, Any]) -> dict[str, Any]:
    name = action["name"]
    for reply_id, reply in record.mock_tool_world["user_replies"].items():
        trigger = reply["trigger"]
        if ((isinstance(trigger, str) and trigger == name) or
            (isinstance(trigger, dict) and trigger == {"name": name, "arguments": action["arguments"]})):
            return {"kind": "user_reply", "reply_id": reply_id, "updates": reply["updates"]}
    if name in record.mock_tool_world["tools"]:
        tool = record.mock_tool_world["tools"][name]
        return {"kind": "tool_response", "tool": name, "response": tool["response"]}
    return {"kind": "action_acknowledged", "action": name}


def _capsule_gate_state(view: Any) -> dict[str, dict[str, Any]]:
    return {
        item["key"]: {"status": item.get("status"), "value": item.get("value")}
        for values in view.content["state"].values()
        for item in values
        if isinstance(item, dict) and "key" in item
    }


def _predicate_satisfied(predicate: str, state: Mapping[str, Mapping[str, Any]]) -> bool:
    key, expected = predicate.split("=", 1)
    claim = state.get(key)
    if claim is None:
        return False
    actual = claim.get("status") if expected in {
        "known", "unknown", "contradicted", "not_applicable"
    } else str(claim.get("value"))
    return actual == expected


def run_pilot(
    record: TaskRecord,
    config: RunConfig,
    provider: Provider,
    *,
    generated_transfer: Any = None,
    source_raw_output: str | None = None,
) -> PilotRunArtifact:
    """Execute source transfer, receiver turns, and the deterministic dev simulator."""
    if config.factorial_cell is not None and generated_transfer is not None:
        # Factorial block orchestration may generate once and reuse the exact
        # source artifact across all eight representation cells.
        generated, source_raw = generated_transfer, source_raw_output
    else:
        generated, source_raw = generate_transfer(record, config, provider)
    view = (make_factorial_view(record, config.transfer_config, generated)
            if config.factorial_cell is not None else
            make_view(record, config.transfer_kind, generated=generated))
    allowed_names = {item["name"] for item in action_catalog(record)}
    interactions: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    raw_outputs: list[str] = []
    prompt_hashes: list[str] = []
    receiver_states: list[Mapping[str, Any]] = []
    usage: list[Mapping[str, int]] = []
    result = execute_events(record, events)
    # Enforcement is an orthogonal experimental factor, not a privilege of EHC.
    # The simulator's policy state is evaluator-side and is never placed in prompts.
    gate_state = ({claim.key: {"status": claim.status.value, "value": claim.value}
                   for claim in record.episode.gold_state}
                  if config.enforce_action_gates else {})
    contracts = {item["action"]: item for item in public_action_contract(record)}
    # Deterministic seed namespaces: source uses base seed; receiver turn t uses
    # base + 1000 + t. This prevents stages/turns from replaying one random stream.
    for turn in range(config.max_turns):
        messages = receiver_turn_messages(
            record.episode.boundary.target_role, view, record, interactions
        )
        canonical_prompt = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        prompt_hashes.append(hashlib.sha256(canonical_prompt.encode()).hexdigest())
        raw = provider.complete(messages, model=config.model, temperature=config.temperature,
                                response_schema=ACTION_SCHEMA, schema_name="receiver_action",
                                seed=config.seed + 1000 + turn,
                                max_output_tokens=config.max_output_tokens)
        provider_usage = getattr(provider, "last_usage", None)
        usage.append(MappingProxyType(dict(provider_usage or {})))
        raw_outputs.append(raw)
        parsed = parse_receiver_output(raw)
        receiver_states.append(MappingProxyType(json.loads(json.dumps(parsed["receiver_state"]))))
        action = parsed["action"]
        if action["name"] not in allowed_names:
            raise ValueError(f"receiver selected action outside visible catalog: {action['name']}")
        contract = contracts.get(action["name"])
        if config.enforce_action_gates and contract and contract["user_impacting"]:
            missing = [condition for condition in contract["requires"]
                       if not _predicate_satisfied(condition, gate_state)]
            if missing:
                interactions.append({
                    "action": action,
                    "simulator_response": {"kind": "gate_blocked", "missing": missing},
                })
                continue
        events.append({"name": action["name"], "arguments": dict(action["arguments"])})
        response = _simulate(record, action)
        interactions.append({"action": action, "simulator_response": response})
        if config.enforce_action_gates and response["kind"] == "user_reply":
            gate_state.update({key: dict(value) for key, value in response["updates"].items()})
        result = execute_events(record, events)
        if result.success:
            break
    detached = tuple(MappingProxyType(json.loads(json.dumps(item))) for item in interactions)
    return PilotRunArtifact(
        record.episode.task_id, config, config.config_hash, source_raw, tuple(raw_outputs),
        tuple(prompt_hashes), tuple(receiver_states), tuple(usage), tuple(events), detached, result,
        view.validator_sidecar,
    )


def run_receiver(
    record: TaskRecord, config: RunConfig, provider: Provider,
    *, generated_transfer: Mapping[str, Any] | str | None = None,
) -> RunArtifact:
    view = (make_factorial_view(record, config.transfer_config, generated_transfer)
            if config.factorial_cell is not None else
            make_view(record, config.transfer_kind, generated=generated_transfer))
    messages = receiver_messages(record.episode.boundary.target_role, view)
    canonical_prompt = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    prompt_hash = hashlib.sha256(canonical_prompt.encode()).hexdigest()
    raw = provider.complete(messages, model=config.model, temperature=config.temperature,
                            response_schema=ACTION_SCHEMA, schema_name="receiver_action",
                            seed=config.seed + 1000,
                            max_output_tokens=config.max_output_tokens)
    parsed = parse_receiver_output(raw)
    # JSON round-trip detaches provider/user-owned mutable objects.
    # Preserve the protocol-canonical STATE_FIELDS order established by the parser.
    frozen_copy = json.loads(json.dumps(parsed))
    return RunArtifact(record.episode.task_id, config, config.config_hash, prompt_hash, raw,
                       MappingProxyType(frozen_copy))
