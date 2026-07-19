import json

import pytest
import jsonschema

from handoffbench.dataset import load_tasks
from handoffbench.providers import DeterministicFakeProvider
from handoffbench.prompts import (
    ACTION_SCHEMA, ROUTING_GUIDE, parse_receiver_output, receiver_messages, source_messages,
)
from handoffbench.runner import RunConfig, run_pilot, run_receiver
from handoffbench.transfer import STATE_FIELDS, TransferKind, make_view, oracle_state, trace_digest


def _output():
    state = {field: [] for field in STATE_FIELDS}
    return json.dumps({"receiver_state": state,
                       "action": {"name": "ask_user", "arguments": {}, "rationale": "missing"}})


def test_fake_provider_end_to_end_is_content_addressed():
    record = load_tasks()[0]
    fake = DeterministicFakeProvider([_output(), _output()])
    config = RunConfig(model="fake", transfer_kind=TransferKind.FULL_HISTORY)
    first = run_receiver(record, config, fake)
    second = run_receiver(record, config, fake)
    assert first.config_hash == second.config_hash
    assert first.prompt_hash == second.prompt_hash
    assert first.raw_output == _output()
    assert len(fake.calls) == 2


def test_oracle_drops_evaluator_only_labels_and_matches_structured_fields():
    record = load_tasks()[0]
    state = oracle_state(record)
    assert tuple(state) == STATE_FIELDS
    serialized = json.dumps(dict(make_view(record, TransferKind.GOLD_ORACLE).content))
    for forbidden in ("claim_id", "criticality", "weight", "success_predicate",
                      "allowed_next_actions", "forbidden_next_actions"):
        assert forbidden not in serialized
    structured = make_view(record, TransferKind.STRUCTURED_PAYLOAD, generated=state)
    assert tuple(structured.content["state"]) == tuple(state)


def test_ehc_quarantines_unfrozen_or_mismatched_provenance():
    record = load_tasks()[0]
    state = {field: [] for field in STATE_FIELDS}
    state["user_goal"] = [{"key": "user_goal", "status": "known", "value": "x"}]
    capsule = {"state": state, "provenance": [{"field": "user_goal", "key": "user_goal",
                                                "trace_id": "nope", "source_type": "user"}],
               "checks": [
                   {"condition": "change_fee_consent=unknown", "status": "missing"},
                   {"condition": "change_fee_consent=known", "status": "missing"},
               ]}
    view = make_view(record, TransferKind.EHC, generated=capsule)
    assert view.content["state"]["user_goal"] == []
    assert view.content["validation_errors"][0]["reason"] == "trace_not_found"


def test_ehc_accepts_real_pilot_source_type_and_framework_adds_hash():
    record = load_tasks()[0]
    event = record.upstream_trace[0]
    state = {field: [] for field in STATE_FIELDS}
    state["user_goal"] = [{"key": "goal", "status": "known",
                           "value": event["content"]["goal"]}]
    capsule = {
        "state": state,
        "provenance": [{"field": "user_goal", "key": "goal",
                        "trace_id": event["trace_id"], "source_type": event["source_type"]}],
        "checks": [{"condition": "change_fee_consent=unknown", "status": "missing"},
                   {"condition": "change_fee_consent=known", "status": "missing"}],
    }
    provenance = make_view(record, TransferKind.EHC, generated=capsule).content["provenance"]
    assert provenance[0]["content_hash"] == trace_digest(event)


def test_ehc_rejects_model_supplied_content_hash():
    record = load_tasks()[0]
    event = record.upstream_trace[0]
    state = {field: [] for field in STATE_FIELDS}
    capsule = {
        "state": state,
        "provenance": [{"field": "user_goal", "key": "user_goal",
                        "trace_id": event["trace_id"], "source_type": event["source_type"],
                        "content_hash": "model-must-not-supply-this"}],
        "checks": [],
    }
    with pytest.raises(ValueError, match="requires only"):
        make_view(record, TransferKind.EHC, generated=capsule)


def test_pilot_loop_ask_reply_then_book():
    record = load_tasks()[0]
    outputs = [
        json.dumps({"receiver_state": {field: [] for field in STATE_FIELDS},
                    "action": {"name": "ask_user", "arguments": {"slot": "change_fee_consent"},
                               "rationale": "need consent"}}),
        json.dumps({"receiver_state": {field: [] for field in STATE_FIELDS},
                    "action": {"name": "book_flight", "arguments": {"option_id": "F218"},
                               "rationale": "consent received"}}),
    ]
    fake = DeterministicFakeProvider(outputs)
    artifact = run_pilot(
        record, RunConfig(model="fake", transfer_kind=TransferKind.FULL_HISTORY), fake
    )
    assert [item["name"] for item in artifact.events] == ["ask_user", "book_flight"]
    assert artifact.interactions[0]["simulator_response"]["kind"] == "user_reply"
    assert artifact.execution.success
    assert [call["seed"] for call in fake.calls] == [1000, 1001]


def test_config_seed_reaches_receiver_generation():
    record = load_tasks()[0]
    first = DeterministicFakeProvider([_output()])
    second = DeterministicFakeProvider([_output()])
    run_receiver(record, RunConfig(model="fake", transfer_kind=TransferKind.FULL_HISTORY, seed=7), first)
    run_receiver(record, RunConfig(model="fake", transfer_kind=TransferKind.FULL_HISTORY, seed=19), second)
    assert first.calls[0]["seed"] == 1007
    assert second.calls[0]["seed"] == 1019


@pytest.mark.parametrize("kind", [
    TransferKind.FREE_SUMMARY, TransferKind.STRUCTURED_PAYLOAD, TransferKind.EHC,
])
def test_generated_transfer_methods_run_source_then_receiver(kind):
    record = load_tasks()[0]
    state = {field: [] for field in STATE_FIELDS}
    if kind is TransferKind.FREE_SUMMARY:
        source = "Consent remains unknown."
    elif kind is TransferKind.STRUCTURED_PAYLOAD:
        source = json.dumps(state)
    else:
        source = json.dumps({
            "state": state,
            "provenance": [],
            "checks": [
                {"condition": "change_fee_consent=unknown", "status": "missing"},
                {"condition": "change_fee_consent=known", "status": "missing"},
            ],
        })
    ask = json.dumps({"receiver_state": state,
                      "action": {"name": "ask_user", "arguments": {"slot": "change_fee_consent"},
                                 "rationale": "need consent"}})
    book = json.dumps({"receiver_state": state,
                       "action": {"name": "book_flight", "arguments": {"option_id": "F218"},
                                  "rationale": "now known"}})
    fake = DeterministicFakeProvider([source, ask, book])
    artifact = run_pilot(record, RunConfig(model="fake", transfer_kind=kind), fake)
    assert artifact.source_raw_output == source
    assert artifact.execution.success
    # Source prompt contains only the trace, never evaluator-only labels.
    source_prompt = json.dumps(fake.calls[0]["messages"])
    assert "gold_state" not in source_prompt and "success_predicate" not in source_prompt
    if kind is TransferKind.FREE_SUMMARY:
        assert fake.calls[0]["schema_name"] is None
        assert fake.calls[0]["response_schema_hash"] is None
    elif kind is TransferKind.STRUCTURED_PAYLOAD:
        assert fake.calls[0]["schema_name"] == "structured_handoff"
    else:
        assert fake.calls[0]["schema_name"] == "executable_handoff_capsule"
    assert fake.calls[1]["schema_name"] == "receiver_action"
    assert fake.calls[1]["response_schema_hash"]


def test_shuffled_receiver_state_keys_are_accepted_and_canonicalized():
    record = load_tasks()[0]
    shuffled = {field: [] for field in reversed(STATE_FIELDS)}
    raw = json.dumps({"action": {"rationale": "missing", "arguments": {},
                                 "name": "ask_user"},
                      "receiver_state": shuffled})
    fake = DeterministicFakeProvider([raw])
    artifact = run_receiver(
        record, RunConfig(model="fake", transfer_kind=TransferKind.FULL_HISTORY), fake
    )
    assert tuple(artifact.parsed_output["receiver_state"]) == STATE_FIELDS


def test_receiver_state_rejects_non_claim_items():
    state = {field: [] for field in STATE_FIELDS}
    state["user_goal"] = ["rebook cancelled flight"]
    raw = json.dumps({"receiver_state": state,
                      "action": {"name": "ask:x", "arguments": {}, "rationale": "x"}})
    with pytest.raises(ValueError, match="key/status/value"):
        parse_receiver_output(raw)


def test_unknown_claim_requires_null_in_schema_and_parser():
    state = {field: [] for field in STATE_FIELDS}
    state["consent"] = [{"key": "fee_consent", "status": "unknown", "value": "unknown"}]
    value = {"receiver_state": state,
             "action": {"name": "ask:x", "arguments": {}, "rationale": "x"}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, ACTION_SCHEMA)
    with pytest.raises(ValueError, match="must be null"):
        parse_receiver_output(json.dumps(value))


def test_contradicted_claim_may_retain_structured_value():
    state = {field: [] for field in STATE_FIELDS}
    state["verified_facts"] = [{"key": "address", "status": "contradicted",
                                "value": {"user": "A", "tool": "B"}}]
    value = {"receiver_state": state,
             "action": {"name": "ask:x", "arguments": {}, "rationale": "x"}}
    jsonschema.validate(value, ACTION_SCHEMA)
    assert parse_receiver_output(json.dumps(value))["receiver_state"]["verified_facts"]


def test_source_and_receiver_prompts_define_visible_content_copy_rule():
    record = load_tasks()[0]
    source = source_messages("intake", "structured_payload", record.upstream_trace)[0]["content"]
    receiver = receiver_messages("resolver", make_view(record, TransferKind.FULL_HISTORY))[0]["content"]
    for prompt in (source, receiver):
        assert "exact property name" in prompt
        assert "exact JSON value" in prompt
        assert "never use a claim value as its key" in prompt
        assert "Never put a trace path or trace_id in value" in prompt or "never put a trace path or" in prompt
        assert "unknown or not_applicable" in prompt
    assert "trace_id only in provenance" in source
    assert "preserve their key and value exactly" in receiver


def test_source_and_receiver_share_frozen_public_routing_guide():
    record = load_tasks()[0]
    source = source_messages("intake", "structured_payload", record.upstream_trace)[0]["content"]
    receiver = receiver_messages("resolver", make_view(record, TransferKind.FULL_HISTORY))[0]["content"]
    assert ROUTING_GUIDE in source
    assert ROUTING_GUIDE in receiver
    for rule in ("business value to verified_facts", "ordinary task parameter to unresolved_slots",
                 "authorization, confirmation, or acceptance to consent",
                 "approval, clearance, or verification decision to policy_checks",
                 "Do not duplicate the same key across fields"):
        assert rule in ROUTING_GUIDE


def test_only_ehc_source_receives_public_policy_predicates():
    record = load_tasks()[0]
    predicates = ("change_fee_consent=known",)
    payloads = {}
    for kind in ("free_summary", "structured_payload", "ehc"):
        messages = source_messages("intake", kind, record.upstream_trace, predicates)
        payloads[kind] = json.loads(messages[1]["content"])
    assert "public_policy_predicates" not in payloads["free_summary"]
    assert payloads["structured_payload"]["public_policy_predicates"] == list(predicates)
    assert payloads["ehc"]["public_policy_predicates"] == list(predicates)


def test_ehc_predicates_are_restricted_to_top_level_checks():
    record = load_tasks()[0]
    system = source_messages("intake", "ehc", record.upstream_trace,
                             ("change_fee_consent=known",))[0]["content"]
    assert "only for top-level checks" in system
    assert "never copy a predicate or its key into state" in system
    assert "present in trace event.content" in system


@pytest.mark.parametrize("kind", [TransferKind.STRUCTURED_PAYLOAD, TransferKind.EHC])
def test_shuffled_generated_state_keys_are_accepted_and_canonicalized(kind):
    record = load_tasks()[0]
    shuffled = {field: [] for field in reversed(STATE_FIELDS)}
    generated = shuffled if kind is TransferKind.STRUCTURED_PAYLOAD else {
        "state": shuffled, "provenance": [],
        "checks": [
            {"condition": "change_fee_consent=unknown", "status": "missing"},
            {"condition": "change_fee_consent=known", "status": "missing"},
        ],
    }
    view = make_view(record, kind, generated=generated)
    assert tuple(view.content["state"]) == STATE_FIELDS


def test_ehc_gate_records_block_without_selecting_replacement_then_allows_after_reply():
    record = load_tasks()[0]
    state = {field: [] for field in STATE_FIELDS}
    state["consent"] = [{"key": "change_fee_consent", "status": "unknown", "value": None}]
    state["tool_evidence"] = [{"key": "tool_used", "status": "known", "value": "air"}]
    policy_event = record.upstream_trace[2]
    capsule_object = {
        "state": state,
        "provenance": [
            {"field": "consent", "key": "change_fee_consent",
             "trace_id": policy_event["trace_id"], "source_type": policy_event["source_type"]},
            {"field": "tool_evidence", "key": "tool_used",
             "trace_id": record.upstream_trace[1]["trace_id"], "source_type": "tool"},
        ],
        "checks": [
            {"condition": "change_fee_consent=unknown", "status": "satisfied"},
            {"condition": "change_fee_consent=known", "status": "missing"},
        ],
    }
    sanitized = make_view(record, TransferKind.EHC, generated=capsule_object)
    assert sanitized.content["state"]["tool_evidence"] == []
    assert sanitized.content["state"]["consent"]
    capsule = json.dumps(capsule_object)
    def action(name, arguments):
        return json.dumps({"receiver_state": state,
                           "action": {"name": name, "arguments": arguments, "rationale": "test"}})
    fake = DeterministicFakeProvider([
        capsule, action("book_flight", {"option_id": "F218"}),
        action("ask_user", {"slot": "change_fee_consent"}),
        action("book_flight", {"option_id": "F218"})
    ])
    artifact = run_pilot(
        record,
        RunConfig(model="fake", transfer_kind=TransferKind.EHC, max_turns=3,
                  enforce_action_gates=True),
        fake,
    )
    assert artifact.interactions[0]["simulator_response"] == {
        "kind": "gate_blocked", "missing": ["change_fee_consent=known"]
    }
    assert [item["name"] for item in artifact.events] == ["ask_user", "book_flight"]
    assert artifact.execution.success


def test_public_contract_is_visible_without_evaluator_labels():
    record = load_tasks()[0]
    fake = DeterministicFakeProvider([_output()])
    run_receiver(record, RunConfig(model="fake", transfer_kind=TransferKind.FULL_HISTORY), fake)
    # Single-step probe has no action catalog; multi-turn prompt coverage is asserted above.
    from handoffbench.prompts import receiver_turn_messages
    view = make_view(record, TransferKind.FULL_HISTORY)
    serialized = json.dumps(receiver_turn_messages(
        record.episode.boundary.target_role, view, record, []
    ))
    assert "change_fee_consent=known" in serialized
    assert "enum_descriptions" in serialized
    assert "known boolean false is explicit negative evidence" in serialized
    assert "success_predicate" not in serialized
    assert "book_without_consent" not in serialized
    assert "max_calls" not in serialized


@pytest.mark.parametrize("mutation", ["wrong_key", "wrong_field", "mutated_value"])
def test_ehc_quarantines_unsound_claim_to_event_binding(mutation):
    record = load_tasks()[0]
    event = record.upstream_trace[0]
    state = {field: [] for field in STATE_FIELDS}
    claim = {"key": "user_goal", "status": "known", "value": event["content"]["goal"]}
    # Use the exact event key in the valid base case.
    claim["key"] = "goal"
    state["user_goal"] = [claim]
    ref = {"field": "user_goal", "key": "goal", "trace_id": event["trace_id"],
           "source_type": event["source_type"]}
    if mutation == "wrong_key":
        ref["key"] = "does_not_exist"
    elif mutation == "wrong_field":
        ref["field"] = "constraints"
    else:
        claim["value"] = "mutated objective"
    capsule = {
        "state": state,
        "provenance": [ref],
        "checks": [
            {"condition": "change_fee_consent=unknown", "status": "missing"},
            {"condition": "change_fee_consent=known", "status": "missing"},
        ],
    }
    view = make_view(record, TransferKind.EHC, generated=capsule)
    assert view.content["state"]["user_goal"] == []
    assert view.content["validation_errors"]
    assert view.content["audit"] == {
        "strict_validation_pass": False, "quarantined_claim_count": 1
    }


def test_quarantined_critical_claim_fails_safe_at_gate():
    record = load_tasks()[0]
    state = {field: [] for field in STATE_FIELDS}
    # Claims known consent, but the cited policy event says unknown.
    state["consent"] = [{"key": "change_fee_consent", "status": "known", "value": True}]
    event = record.upstream_trace[2]
    source = json.dumps({
        "state": state,
        "provenance": [{"field": "consent", "key": "change_fee_consent",
                        "trace_id": event["trace_id"], "source_type": event["source_type"]}],
        "checks": [
            {"condition": "change_fee_consent=unknown", "status": "missing"},
            {"condition": "change_fee_consent=known", "status": "satisfied"},
        ],
    })
    book = json.dumps({"receiver_state": state,
                       "action": {"name": "book_flight", "arguments": {"option_id": "F218"}, "rationale": "test"}})
    artifact = run_pilot(
        record,
        RunConfig(model="fake", transfer_kind=TransferKind.EHC, max_turns=1,
                  enforce_action_gates=True),
        DeterministicFakeProvider([source, book]),
    )
    assert artifact.events == ()
    assert artifact.interactions[0]["simulator_response"] == {
        "kind": "gate_blocked", "missing": ["change_fee_consent=known"]
    }


@pytest.mark.parametrize("malformed", [
    {"key": "policy_note", "status": "known"},
    {"key": "policy_note", "status": "known", "value": "x", "condition": "consent=known"},
])
def test_malformed_claim_item_is_quarantined_not_episode_fatal(malformed):
    record = load_tasks()[0]
    state = {field: [] for field in STATE_FIELDS}
    state["policy_checks"] = [malformed]
    capsule = {
        "state": state,
        "provenance": [],
        "checks": [
            {"condition": "change_fee_consent=unknown", "status": "missing"},
            {"condition": "change_fee_consent=known", "status": "missing"},
        ],
    }
    view = make_view(record, TransferKind.EHC, generated=capsule)
    assert view.content["state"]["policy_checks"] == []
    assert view.content["validation_errors"] == [
        {"field": "policy_checks", "key": "policy_note", "reason": "malformed_claim"}
    ]
    assert not view.content["audit"]["strict_validation_pass"]
