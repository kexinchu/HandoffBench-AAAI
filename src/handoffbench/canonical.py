"""Canonical value normalization and exact claim matching."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import Any

from .models import Claim, ValueType


def canonicalize(value: Any, value_type: ValueType | str | None = None) -> Any:
    """Return a JSON-compatible canonical value (no fuzzy or semantic matching)."""
    kind = ValueType(value_type) if value_type is not None else None
    if kind is ValueType.NULL:
        return None
    if kind is ValueType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.casefold() in {"true", "false"}:
            return value.casefold() == "true"
        raise ValueError(f"not a canonical boolean: {value!r}")
    if kind is ValueType.NUMBER:
        try:
            return format(Decimal(str(value)).normalize(), "f")
        except InvalidOperation as exc:
            raise ValueError(f"not a number: {value!r}") from exc
    if kind is ValueType.MONEY:
        if isinstance(value, dict):
            currency, amount = value["currency"], value["amount"]
        else:
            currency, amount = "USD", value
        return {"amount": canonicalize(amount, ValueType.NUMBER), "currency": str(currency).upper()}
    if kind is ValueType.DATE:
        return date.fromisoformat(str(value)).isoformat()
    if kind is ValueType.DATETIME:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("datetime must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if kind is ValueType.SET:
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError("set values must be arrays")
        unique = {canonical_json(canonicalize(item)) for item in value}
        return [json.loads(item) for item in sorted(unique)]
    if isinstance(value, dict):
        return {str(k): canonicalize(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if kind in {ValueType.STRING, ValueType.IDENTIFIER}:
        return str(value).strip()
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_claim_value(claim: Claim) -> Any:
    return canonicalize(claim.value, claim.value_type)


def claims_match(left: Claim, right: Claim) -> bool:
    return (
        left.key == right.key
        and left.status == right.status
        and canonical_json(canonical_claim_value(left))
        == canonical_json(canonical_claim_value(right))
    )


def canonical_tool_signature(tool: str, arguments: dict[str, Any]) -> str:
    return f"{tool}:{canonical_json(canonicalize(arguments))}"
