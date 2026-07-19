"""Typed, evaluator-facing records used by HandoffBench."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimStatus(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"
    NOT_APPLICABLE = "not_applicable"


class ClaimCategory(str, Enum):
    GOAL = "goal"
    CONSTRAINT = "constraint"
    VERIFIED_FACT = "verified_fact"
    UNRESOLVED_SLOT = "unresolved_slot"
    TOOL_EVIDENCE = "tool_evidence"
    POLICY_CHECK = "policy_check"
    CONSENT = "consent"
    COMMITMENT = "commitment"
    RISK = "risk"
    PRECONDITION = "precondition"


class Criticality(str, Enum):
    TERMINAL = "terminal"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    CONTEXT = "context"


class ValueType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    MONEY = "money"
    IDENTIFIER = "identifier"
    SET = "set"
    OBJECT = "object"
    NULL = "null"


class EvidenceRef(StrictModel):
    trace_id: str = Field(min_length=1)
    source_type: str = Field(pattern="^(user|tool|policy|environment)$")
    field_path: str | None = None
    content_hash: str | None = None


class Claim(StrictModel):
    claim_id: str = Field(min_length=1)
    category: ClaimCategory
    key: str = Field(min_length=1)
    status: ClaimStatus
    value: Any
    value_type: ValueType | None = None
    criticality: Criticality = Criticality.CONTEXT
    weight: float = Field(default=1.0, gt=0)
    provenance: list[EvidenceRef] = Field(min_length=1)
    supersedes: list[str] = Field(default_factory=list)
    valid_at_boundary: bool = True
    normalizer: str | None = None

    @model_validator(mode="after")
    def boundary_claim_is_current(self) -> "Claim":
        if not self.valid_at_boundary:
            raise ValueError("gold/transfer claims must be valid at the boundary")
        return self


class Boundary(StrictModel):
    boundary_id: str = Field(min_length=1)
    source_role: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    trace_cut: int = Field(ge=0)
    handoff_reason: str | None = None


class ActionRule(StrictModel):
    action: str = Field(min_length=1)
    expected_arguments: dict[str, Any] = Field(default_factory=dict)
    when: list[str] = Field(default_factory=list)
    max_calls: int | None = Field(default=None, ge=0)
    irreversible: bool = False


class SuccessPredicate(StrictModel):
    predicate_id: str = Field(min_length=1)
    args: dict[str, Any]


class Scoring(StrictModel):
    critical_keys: list[str]
    observable_events: list[str]
    determinacy: float = Field(ge=0, le=1)


class SplitMeta(StrictModel):
    template_family: str | None = None
    entity_pool: str | None = None
    generator_version: str | None = None
    seed: int | None = None


class Episode(StrictModel):
    task_id: str = Field(pattern="^[a-z0-9_-]+$")
    domain: str | None = Field(
        default=None,
        pattern="^(travel|commerce|procurement|it|scheduling|finance_ops|logistics)$",
    )
    boundary: Boundary
    gold_state: list[Claim] = Field(min_length=1)
    allowed_next_actions: list[ActionRule] = Field(default_factory=list)
    forbidden_next_actions: list[ActionRule] = Field(default_factory=list)
    success_predicate: SuccessPredicate
    scoring: Scoring
    split_meta: SplitMeta | None = None

    @model_validator(mode="after")
    def identifiers_are_unique_and_critical_keys_exist(self) -> "Episode":
        ids = [claim.claim_id for claim in self.gold_state]
        if len(ids) != len(set(ids)):
            raise ValueError("claim_id values must be unique")
        keys = {claim.key for claim in self.gold_state}
        missing = set(self.scoring.critical_keys) - keys
        if missing:
            raise ValueError(f"critical_keys absent from gold_state: {sorted(missing)}")
        return self


class ToolCall(StrictModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    volatile: bool = False
    retryable: bool = False


class ActionEvent(StrictModel):
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    role: str
    user_impacting: bool = False
    irreversible: bool = False
    consent_key: str | None = None
    consent_scope: Any = None


class ActionInvocation(StrictModel):
    """Canonical evaluator event; arguments are part of action identity."""

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AskEvent(StrictModel):
    slot_key: str
