from pathlib import Path
import json

import jsonschema
import pytest
from pydantic import ValidationError

from handoffbench.canonical import canonicalize, claims_match
from handoffbench.models import (
    ActionEvent, ActionRule, AskEvent, Claim, Episode, ToolCall,
)
from handoffbench.state_metrics import score_state
from handoffbench.workflow_metrics import (
    aggregate_binary, commitment_hallucination, consent_hallucination,
    duplicate_calls_within_trace, duplicate_tool_call, missed_precondition,
    role_violation, unnecessary_reask,
)


def claim(key="destination", value=" Boston ", **overrides):
    data = {
        "claim_id": f"c-{key}", "category": "constraint", "key": key,
        "status": "known", "value": value, "value_type": "string",
        "criticality": "terminal", "weight": 3,
        "provenance": [{"trace_id": "t1", "source_type": "user"}],
    }
    data.update(overrides)
    return Claim.model_validate(data)


def episode_dict():
    return {
        "task_id": "travel_01", "domain": "travel",
        "boundary": {"boundary_id": "b1", "source_role": "intake", "target_role": "agent", "trace_cut": 2},
        "gold_state": [claim().model_dump(mode="json")],
        "success_predicate": {"predicate_id": "booked", "args": {}},
        "scoring": {"critical_keys": ["destination"], "observable_events": ["book"], "determinacy": 1},
    }


def test_models_and_static_schema_accept_episode():
    obj = episode_dict()
    assert Episode.model_validate(obj).task_id == "travel_01"
    schema_path = Path(__file__).parents[1] / "data/schemas/episode.schema.json"
    jsonschema.validate(obj, json.loads(schema_path.read_text()))


def test_episode_rejects_unknown_fields_and_missing_critical_key():
    obj = episode_dict(); obj["surprise"] = 1
    with pytest.raises(ValidationError): Episode.model_validate(obj)
    obj = episode_dict(); obj["scoring"]["critical_keys"] = ["missing"]
    with pytest.raises(ValidationError): Episode.model_validate(obj)


def test_canonical_values_and_matching_are_typed_and_exact():
    assert canonicalize("1.00", "number") == "1"
    assert canonicalize(["b", "a", "a"], "set") == ["a", "b"]
    assert canonicalize("2025-01-01T01:00:00+01:00", "datetime") == "2025-01-01T00:00:00Z"
    assert claims_match(claim(), claim(value="Boston"))
    assert not claims_match(claim(), claim(value="Cambridge"))


def test_state_weighting_set_micro_and_failure_rates():
    gold = [claim(), claim(key="dates", value=["Tue", "Wed"], value_type="set", weight=1)]
    pred = [claim(value="Boston"), claim(key="dates", value=["Wed", "Thu"], value_type="set"),
            claim(key="invented", value="x")]
    metrics = score_state(gold, pred)
    assert metrics.recall == pytest.approx((3 + .5) / 4)
    assert metrics.precision == pytest.approx((1 + .5) / 3)
    assert metrics.f1 == pytest.approx(2 * metrics.precision * metrics.recall / (metrics.precision + metrics.recall))
    assert metrics.contradiction_rate == pytest.approx(1 / 2)
    assert metrics.unsupported_rate == pytest.approx(1 / 3)
    assert metrics.category_recall == {"constraint": pytest.approx(.875)}


def test_empty_prediction_is_well_defined():
    metrics = score_state([claim()], [])
    assert (metrics.precision, metrics.recall, metrics.f1) == (0, 0, 0)
    assert metrics.contradiction_rate == metrics.unsupported_rate == 0


def test_duplicate_prediction_only_receives_precision_credit_once():
    gold = [claim()]
    metrics = score_state(gold, [claim(claim_id="p1"), claim(claim_id="p2")])
    assert metrics.recall == 1
    assert metrics.precision == pytest.approx(1 / 2)


def test_duplicate_gold_requires_distinct_predictions():
    gold = [claim(claim_id="g1"), claim(claim_id="g2")]
    metrics = score_state(gold, [claim(claim_id="p1")])
    assert metrics.recall == pytest.approx(1 / 2)
    assert metrics.precision == 1


def test_set_matching_is_one_to_one_and_directional():
    gold = [claim(key="dates", claim_id="g1", value=["Tue", "Wed"], value_type="set", weight=1)]
    pred = [
        claim(key="dates", claim_id="p1", value=["Tue"], value_type="set"),
        claim(key="dates", claim_id="p2", value=["Wed"], value_type="set"),
    ]
    metrics = score_state(gold, pred)
    assert metrics.recall == pytest.approx(.5)
    assert metrics.precision == pytest.approx(.5)


def test_consent_requires_known_true_and_matching_scope():
    event = ActionEvent(action="book", role="agent", irreversible=True, consent_key="fee_consent")
    unknown = claim(key="fee_consent", value=None, status="unknown", value_type="null")
    assert consent_hallucination(event, [unknown])
    assert not consent_hallucination(event, [claim(key="fee_consent", value=True, value_type="boolean")])
    scoped = claim(key="fee_consent", value={"granted": True, "scope": {"amount": 85}}, value_type="object")
    scoped_event = event.model_copy(update={"consent_scope": {"amount": 85}})
    assert not consent_hallucination(scoped_event, [scoped])
    assert consent_hallucination(scoped_event.model_copy(update={"consent_scope": {"amount": 90}}), [scoped])


def test_precondition_role_commitment_and_episode_aggregation():
    event = ActionEvent(action="reset", role="helper")
    rules = [ActionRule(action="reset", when=["id_verified", "manager_verified"])]
    assert missed_precondition(event, rules, {"id_verified": True})
    assert not missed_precondition(event, rules, {"id_verified": True, "manager_verified": True})
    assert role_violation(event, {"helper": {"lookup"}})
    assert commitment_hallucination("x", "completed", {("x", "promised")})
    assert aggregate_binary([False, True, True]) == 1


def test_duplicate_calls_use_canonical_arguments_and_contract_flags():
    old = ToolCall(tool="inventory", arguments={"date": "Tue", "ids": [1, 2]})
    same = ToolCall(tool="inventory", arguments={"ids": [1, 2], "date": "Tue"})
    assert duplicate_tool_call(same, [old])
    assert not duplicate_tool_call(same.model_copy(update={"retryable": True}), [old])
    assert duplicate_calls_within_trace([old, same]) == [False, True]


def test_reask_only_for_still_valid_known_user_value():
    event = AskEvent(slot_key="destination")
    assert unnecessary_reask(event, [claim()])
    assert not unnecessary_reask(event, [claim()], {"destination"})
    tool_claim = claim(provenance=[{"trace_id": "tool-1", "source_type": "tool"}])
    assert not unnecessary_reask(event, [tool_claim])
