"""Provider-independent handoff views with an explicit anti-leakage boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .dataset import TaskRecord, public_action_contract


class TransferKind(str, Enum):
    FULL_HISTORY = "full_history"
    FREE_SUMMARY = "free_summary"
    STRUCTURED_PAYLOAD = "structured_payload"
    EHC = "ehc"
    GOLD_ORACLE = "gold_oracle"
    FACTORIAL = "factorial"


class TypingFactor(str, Enum):
    FREE_FORM = "free_form"
    TYPED = "typed"


class ProvenanceFactor(str, Enum):
    ABSENT = "absent"
    TRACE_LINKED = "trace_linked"


class ChecksFactor(str, Enum):
    ABSENT = "absent"
    EXECUTABLE = "executable"


class EnforcementFactor(str, Enum):
    """Whether a framework blocks actions; not part of the transfer artifact."""

    ADVISORY = "advisory"
    ENFORCED = "enforced"


@dataclass(frozen=True)
class TransferConfig:
    """Orthogonal mechanism configuration used by the factorial experiment.

    ``checks=executable`` means that predicates are deterministically evaluated
    and their statuses are represented in the handoff.  It does *not* grant an
    action-blocking privilege.  Blocking is controlled solely by
    ``enforcement`` and must be reported as a separate intervention.
    """

    typing: TypingFactor
    provenance: ProvenanceFactor
    checks: ChecksFactor
    enforcement: EnforcementFactor = EnforcementFactor.ADVISORY

    @property
    def cell_id(self) -> str:
        return "__".join((self.typing.value, self.provenance.value, self.checks.value,
                           self.enforcement.value))

    @property
    def representation_cell_id(self) -> str:
        """The 2x2x2 cell label, intentionally excluding enforcement."""
        return "__".join((self.typing.value, self.provenance.value, self.checks.value))


LEGACY_TRANSFER_CONFIGS: Mapping[TransferKind, TransferConfig | None] = MappingProxyType({
    # Full history and gold oracle are controls outside the 2x2x2 design.
    TransferKind.FULL_HISTORY: None,
    TransferKind.GOLD_ORACLE: None,
    TransferKind.FREE_SUMMARY: TransferConfig(
        TypingFactor.FREE_FORM, ProvenanceFactor.ABSENT, ChecksFactor.ABSENT),
    TransferKind.STRUCTURED_PAYLOAD: TransferConfig(
        TypingFactor.TYPED, ProvenanceFactor.ABSENT, ChecksFactor.ABSENT),
    # Legacy EHC is the all-on representation cell.  Its checks are advisory;
    # action enforcement has never been an intrinsic EHC factor.
    TransferKind.EHC: TransferConfig(
        TypingFactor.TYPED, ProvenanceFactor.TRACE_LINKED, ChecksFactor.EXECUTABLE),
})


def legacy_transfer_config(kind: TransferKind) -> TransferConfig | None:
    """Return the explicitly labelled factor combination for an old method."""
    if kind is TransferKind.FACTORIAL:
        raise ValueError("factorial runs require an explicit TransferConfig")
    return LEGACY_TRANSFER_CONFIGS[kind]


FACTORIAL_CELLS: Mapping[str, TransferConfig] = MappingProxyType({
    config.representation_cell_id: config
    for typing in TypingFactor
    for provenance in ProvenanceFactor
    for checks in ChecksFactor
    for config in [TransferConfig(typing, provenance, checks)]
})


def factorial_cell(cell_id: str) -> TransferConfig:
    try:
        return FACTORIAL_CELLS[cell_id]
    except KeyError as error:
        raise ValueError(f"unknown factorial cell: {cell_id}") from error


# Structured, EHC, and oracle conditions have exactly these state slots.
STATE_FIELDS = (
    "user_goal", "constraints", "verified_facts", "unresolved_slots",
    "tool_evidence", "policy_checks", "consent", "commitments",
    "risk_flags", "next_step_preconditions",
)

_CATEGORY_FIELD = {
    "goal": "user_goal", "constraint": "constraints",
    "verified_fact": "verified_facts", "unresolved_slot": "unresolved_slots",
    "tool_evidence": "tool_evidence", "policy_check": "policy_checks",
    "consent": "consent", "commitment": "commitments", "risk": "risk_flags",
    "precondition": "next_step_preconditions",
}


def empty_state() -> dict[str, Any]:
    return {field: [] for field in STATE_FIELDS}


def validate_state_fields(state: Mapping[str, Any]) -> None:
    if set(state) != set(STATE_FIELDS):
        raise ValueError(f"state fields must be exactly: {STATE_FIELDS}")


def canonicalize_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Validate unordered JSON object keys and return protocol-canonical order."""
    validate_state_fields(state)
    return {field: state[field] for field in STATE_FIELDS}


def oracle_state(record: TaskRecord) -> dict[str, Any]:
    """Project gold claims into model-visible slots, dropping all evaluator labels."""
    state = empty_state()
    for claim in record.episode.gold_state:
        field = _CATEGORY_FIELD[claim.category.value]
        state[field].append({"key": claim.key, "status": claim.status.value, "value": claim.value})
    return state


def trace_digest(event: Mapping[str, Any]) -> str:
    raw = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def checked_ehc(
    record: TaskRecord,
    state: Mapping[str, Any],
    provenance: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate EHC evidence against the frozen upstream trace.

    Provenance names state field/key and trace id, but cannot embed evaluator
    claim identifiers. The framework binds evidence to the complete trace event
    with a deterministic digest after validation; the model never supplies it.
    Checks are declarative receiver preconditions, never gold action rules.
    """
    canonical_state = canonicalize_state(state)
    events = {event["trace_id"]: event for event in record.upstream_trace}
    bound_provenance: list[dict[str, Any]] = []
    validation_errors: list[dict[str, str]] = []
    claims: dict[tuple[str, str], dict[str, Any]] = {}
    for field, values in canonical_state.items():
        if not isinstance(values, list):
            raise ValueError("EHC top-level state fields must be arrays")
        for index, claim in enumerate(values):
            if (
                not isinstance(claim, dict)
                or set(claim) != {"key", "status", "value"}
                or not isinstance(claim.get("key"), str)
                or claim.get("status") not in {
                    "known", "unknown", "contradicted", "not_applicable"
                }
            ):
                marker = claim.get("key") if isinstance(claim, dict) else None
                validation_errors.append({
                    "field": field,
                    "key": str(marker) if marker is not None else f"<item:{index}>",
                    "reason": "malformed_claim",
                })
                continue
            identity = (field, claim["key"])
            if identity in claims:
                raise ValueError("EHC state claim keys must be unique within each field")
            claims[identity] = claim
    evidenced_claims: set[tuple[str, str]] = set()
    quarantined_claims: set[tuple[str, str]] = set()
    required_ref_fields = {"field", "key", "trace_id", "source_type"}
    for ref in provenance:
        if set(ref) != required_ref_fields:
            raise ValueError("EHC provenance requires only field, key, trace_id, source_type")
        identity = (ref["field"], ref["key"])
        claim = claims.get(identity)
        event = events.get(ref["trace_id"])
        reason: str | None = None
        if ref["field"] not in STATE_FIELDS or claim is None:
            reason = "field_or_key_not_in_capsule"
        elif event is None:
            reason = "trace_not_found"
        elif ref["source_type"] != event.get("source_type"):
            reason = "source_type_mismatch"
        else:
            content = event.get("content")
            if not isinstance(content, dict) or ref["key"] not in content:
                reason = "key_not_in_event"
            else:
                evidence_value = content[ref["key"]]
                status = claim.get("status")
                if status == "unknown":
                    supported = claim.get("value") is None and (
                        evidence_value is None or evidence_value == "unknown"
                    )
                else:
                    supported = claim.get("value") == evidence_value
                if not supported:
                    reason = "value_or_status_unsupported"
        if reason is not None:
            validation_errors.append({"field": ref["field"], "key": ref["key"],
                                      "reason": reason})
            if claim is not None:
                quarantined_claims.add(identity)
            continue
        evidenced_claims.add(identity)
        bound_provenance.append({**ref, "content_hash": trace_digest(event)})
    missing_evidence = set(claims) - evidenced_claims
    for identity in sorted(missing_evidence):
        quarantined_claims.add(identity)
        if not any(error["field"] == identity[0] and error["key"] == identity[1]
                   for error in validation_errors):
            validation_errors.append({"field": identity[0], "key": identity[1],
                                      "reason": "missing_valid_provenance"})
    clean_state = {field: [] for field in STATE_FIELDS}
    for (field, key), claim in claims.items():
        if (field, key) not in quarantined_claims:
            clean_state[field].append(claim)
    bound_provenance = [ref for ref in bound_provenance
                        if (ref["field"], ref["key"]) not in quarantined_claims]
    expected_conditions = {
        condition
        for contract in public_action_contract(record)
        for condition in contract["requires"]
    }
    supplied_conditions = [check.get("condition") for check in checks]
    if len(supplied_conditions) != len(set(supplied_conditions)) or set(supplied_conditions) != expected_conditions:
        raise ValueError("EHC checks must cover each public policy predicate exactly once")
    claims_by_key = {
        item["key"]: item
        for values in clean_state.values()
        for item in values
        if isinstance(item, dict) and "key" in item
    }
    evidenced_keys = {ref["key"] for ref in bound_provenance}
    verified_checks: list[dict[str, str]] = []
    for check in checks:
        if set(check) != {"condition", "status"}:
            raise ValueError("EHC checks require only condition and status")
        if check["status"] not in {"satisfied", "missing", "contradicted"}:
            raise ValueError("invalid EHC check status")
        key, expected = check["condition"].split("=", 1)
        claim = claims_by_key.get(key)
        if claim is None or key not in evidenced_keys:
            status = "missing"
        elif claim.get("status") == "contradicted":
            status = "contradicted"
        else:
            actual = claim.get("status") if expected in {
                "known", "unknown", "contradicted", "not_applicable"
            } else str(claim.get("value"))
            status = "satisfied" if actual == expected else "missing"
        verified_checks.append({"condition": check["condition"], "status": status})
    return {
        "state": clean_state,
        "provenance": bound_provenance,
        "checks": verified_checks,
        "validation_errors": validation_errors,
        "audit": {
            "strict_validation_pass": not validation_errors,
            "quarantined_claim_count": len(quarantined_claims) + sum(
                error["reason"] == "malformed_claim" for error in validation_errors
            ),
        },
    }


@dataclass(frozen=True)
class TransferView:
    kind: TransferKind
    content: Mapping[str, Any]
    validator_sidecar: Mapping[str, Any] | None = None


def _factorial_provenance_audit(
    record: TaskRecord, state: Mapping[str, Any], provenance: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate links without altering, adding, or quarantining any claim."""
    events = {event["trace_id"]: event for event in record.upstream_trace}
    claims = {
        (field, item.get("key")): item
        for field, items in state.items() if isinstance(items, list)
        for item in items if isinstance(item, dict)
    }
    valid_refs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    required = {"field", "key", "trace_id", "source_type"}
    for index, ref in enumerate(provenance):
        reason = None
        event = events.get(ref.get("trace_id")) if isinstance(ref, dict) else None
        claim = claims.get((ref.get("field"), ref.get("key"))) if isinstance(ref, dict) else None
        if not isinstance(ref, dict) or set(ref) != required:
            reason = "malformed_reference"
        elif claim is None:
            reason = "claim_not_found"
        elif event is None:
            reason = "trace_not_found"
        elif ref["source_type"] != event.get("source_type"):
            reason = "source_type_mismatch"
        elif not isinstance(event.get("content"), dict) or ref["key"] not in event["content"]:
            reason = "key_not_in_event"
        elif claim.get("status") == "unknown":
            if claim.get("value") is not None or event["content"][ref["key"]] not in (None, "unknown"):
                reason = "value_or_status_unsupported"
        elif claim.get("value") != event["content"][ref["key"]]:
            reason = "value_or_status_unsupported"
        if reason:
            errors.append({"reference_index": index, "reason": reason})
        else:
            valid_refs.append({**ref, "content_hash": trace_digest(event)})
    audit = {
        "raw_artifact_unchanged": True,
        "provenance_reference_count": len(provenance),
        "valid_provenance_count": len(valid_refs),
        "provenance_errors": errors,
        "strict_validation_pass": not errors,
    }
    return valid_refs, audit


def _evaluate_public_checks(record: TaskRecord, state: Mapping[str, Any]) -> list[dict[str, str]]:
    claims = {
        item["key"]: item for values in state.values() for item in values
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    }
    conditions = sorted({condition for contract in public_action_contract(record)
                         for condition in contract["requires"]})
    evaluated = []
    for condition in conditions:
        key, expected = condition.split("=", 1)
        claim = claims.get(key)
        if claim is None:
            status = "missing"
        elif claim.get("status") == "contradicted":
            status = "contradicted"
        else:
            actual = claim.get("status") if expected in {
                "known", "unknown", "contradicted", "not_applicable"
            } else str(claim.get("value"))
            status = "satisfied" if actual == expected else "missing"
        evaluated.append({"condition": condition, "status": status})
    return evaluated


def _prose_state(state: Mapping[str, Any]) -> dict[str, str]:
    """Fixed ten-field prose envelope containing exactly the typed atoms' information."""
    rendered: dict[str, str] = {}
    for field in STATE_FIELDS:
        atoms = state[field]
        rendered[field] = "No claims." if not atoms else "\n".join(
            f"Claim {index + 1}: key {json.dumps(item['key'], ensure_ascii=False)}; "
            f"status {item['status']}; value {json.dumps(item['value'], sort_keys=True, ensure_ascii=False)}."
            for index, item in enumerate(atoms)
        )
    return rendered


def make_factorial_view(
    record: TaskRecord, config: TransferConfig, generated: Mapping[str, Any]
) -> TransferView:
    """Serialize one representation-only cell from a common source artifact."""
    if config.enforcement is not EnforcementFactor.ADVISORY:
        # Enforcement belongs to execution; its value must never change serialization.
        config = TransferConfig(config.typing, config.provenance, config.checks)
    if set(generated) != {"state", "provenance"}:
        raise ValueError("factorial source artifact requires exactly state and provenance")
    state = canonicalize_state(generated["state"])
    raw_provenance = generated["provenance"]
    if not isinstance(raw_provenance, list):
        raise ValueError("factorial provenance must be an array")
    valid_refs, sidecar = _factorial_provenance_audit(record, state, raw_provenance)
    content: dict[str, Any] = {
        "representation_cell": config.representation_cell_id,
        "fields": _prose_state(state) if config.typing is TypingFactor.FREE_FORM else state,
        "validation_annotations": (
            sidecar["provenance_errors"]
            if config.provenance is ProvenanceFactor.TRACE_LINKED else []
        ),
    }
    if config.provenance is ProvenanceFactor.TRACE_LINKED:
        # Preserve raw links exactly; hashes are sidecar-only and never repair source output.
        content["provenance"] = raw_provenance
    if config.checks is ChecksFactor.EXECUTABLE:
        content["checks"] = _evaluate_public_checks(record, state)
    sidecar = sidecar | {
        "representation_cell": config.representation_cell_id,
        "evaluated_checks": _evaluate_public_checks(record, state),
        "serialized_valid_reference_count": len(valid_refs),
    }
    return TransferView(TransferKind.FACTORIAL, MappingProxyType(content), MappingProxyType(sidecar))


def make_view(
    record: TaskRecord,
    kind: TransferKind,
    *,
    generated: Mapping[str, Any] | str | None = None,
) -> TransferView:
    if kind is TransferKind.FULL_HISTORY:
        content = {"history": list(record.upstream_trace)}
    elif kind is TransferKind.GOLD_ORACLE:
        content = {"state": oracle_state(record)}
    elif kind is TransferKind.FREE_SUMMARY:
        if not isinstance(generated, str):
            raise ValueError("free_summary requires generated text")
        content = {"summary": generated}
    elif kind is TransferKind.STRUCTURED_PAYLOAD:
        if not isinstance(generated, Mapping):
            raise ValueError("structured_payload requires generated state")
        content = {"state": canonicalize_state(generated)}
    elif kind is TransferKind.EHC:
        if not isinstance(generated, Mapping):
            raise ValueError("ehc requires generated capsule")
        content = checked_ehc(record, generated["state"], generated["provenance"], generated["checks"])
    else:  # pragma: no cover
        raise ValueError(kind)
    # A shallow read-only wrapper prevents accidental reassignment; serialization
    # always copies nested values into immutable run artifacts.
    return TransferView(kind, MappingProxyType(content))
