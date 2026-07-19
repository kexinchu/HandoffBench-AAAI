"""Deterministic state-transfer metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .canonical import canonical_claim_value, canonical_json, claims_match
from .matching import maximum_weight_pairs
from .models import Claim, ClaimCategory, ValueType


DEFAULT_CATEGORY_WEIGHTS: dict[ClaimCategory, float] = {category: 1.0 for category in ClaimCategory}


@dataclass(frozen=True)
class StateMetrics:
    precision: float
    recall: float
    f1: float
    contradiction_rate: float
    unsupported_rate: float
    category_recall: dict[str, float]


def _set_items(claim: Claim) -> set[str] | None:
    if claim.value_type is not ValueType.SET:
        return None
    return {canonical_json(item) for item in canonical_claim_value(claim)}


def _overlap_fraction(reference: Claim, candidate: Claim) -> float:
    if reference.key != candidate.key or reference.status != candidate.status:
        return 0.0
    ref_items, candidate_items = _set_items(reference), _set_items(candidate)
    if ref_items is None or candidate_items is None:
        return float(claims_match(reference, candidate))
    if not ref_items:
        return float(not candidate_items)
    return len(ref_items & candidate_items) / len(ref_items)


def _conflicts(gold: Claim, predicted: Claim) -> bool:
    if gold.key != predicted.key:
        return False
    return gold.status != predicted.status or canonical_json(canonical_claim_value(gold)) != canonical_json(
        canonical_claim_value(predicted)
    )


def score_state(
    gold: list[Claim],
    predicted: list[Claim],
    category_weights: dict[ClaimCategory, float] | None = None,
) -> StateMetrics:
    """Score claims with exact typed equality and element-micro overlap for sets."""
    if not gold:
        raise ValueError("gold state must not be empty")
    weights = DEFAULT_CATEGORY_WEIGHTS | (category_weights or {})
    gold_by_key: dict[tuple[ClaimCategory, str], list[Claim]] = defaultdict(list)
    predicted_by_key: dict[tuple[ClaimCategory, str], list[Claim]] = defaultdict(list)
    for claim in gold:
        gold_by_key[(claim.category, claim.key)].append(claim)
    for claim in predicted:
        predicted_by_key[(claim.category, claim.key)].append(claim)

    gold_keys = set(gold_by_key)
    matched: list[tuple[Claim, Claim]] = []
    for group in sorted(gold_keys | set(predicted_by_key), key=lambda item: (item[0].value, item[1])):
        gold_group, pred_group = gold_by_key.get(group, []), predicted_by_key.get(group, [])
        pairs = maximum_weight_pairs(
            gold_group,
            pred_group,
            lambda g, p: g.weight * _overlap_fraction(g, p)
            + weights[p.category] * _overlap_fraction(p, g),
        )
        matched.extend((gold_group[i], pred_group[j]) for i, j in pairs)

    matched_gold = sum(g.weight * _overlap_fraction(g, p) for g, p in matched)
    recall = matched_gold / sum(claim.weight for claim in gold)
    precision_den = sum(weights[claim.category] for claim in predicted)
    matched_pred = sum(weights[p.category] * _overlap_fraction(p, g) for g, p in matched)
    precision = matched_pred / precision_den if precision_den else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    shared = [p for p in predicted if (p.category, p.key) in gold_keys]
    contradictions = sum(
        any(_conflicts(g, p) for g in gold_by_key[(p.category, p.key)]) for p in shared
    )
    unsupported = sum((p.category, p.key) not in gold_keys for p in predicted)
    by_category: dict[str, float] = {}
    for category in ClaimCategory:
        subset = [g for g in gold if g.category == category]
        if subset:
            numerator = sum(
                g.weight * _overlap_fraction(g, p) for g, p in matched if g.category == category
            )
            by_category[category.value] = numerator / sum(g.weight for g in subset)
    return StateMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        contradiction_rate=contradictions / len(shared) if shared else 0.0,
        unsupported_rate=unsupported / len(predicted) if predicted else 0.0,
        category_recall=by_category,
    )
