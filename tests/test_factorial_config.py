import json

import pytest

from handoffbench.dataset import load_tasks
from handoffbench.prompts import FACTORIAL_SOURCE_SCHEMA
from handoffbench.runner import RunConfig, generate_transfer, run_pilot
from handoffbench.transfer import (
    FACTORIAL_CELLS,
    ChecksFactor,
    EnforcementFactor,
    ProvenanceFactor,
    TransferConfig,
    TransferKind,
    TypingFactor,
    legacy_transfer_config,
    make_factorial_view,
)


def test_factor_cell_label_excludes_enforcement():
    advisory = TransferConfig(TypingFactor.TYPED, ProvenanceFactor.TRACE_LINKED,
                              ChecksFactor.EXECUTABLE)
    enforced = TransferConfig(TypingFactor.TYPED, ProvenanceFactor.TRACE_LINKED,
                              ChecksFactor.EXECUTABLE, EnforcementFactor.ENFORCED)
    assert advisory.representation_cell_id == enforced.representation_cell_id
    assert advisory.cell_id != enforced.cell_id


def test_legacy_methods_have_explicit_backward_compatible_cells():
    assert legacy_transfer_config(TransferKind.FREE_SUMMARY).representation_cell_id == \
        "free_form__absent__absent"
    assert legacy_transfer_config(TransferKind.STRUCTURED_PAYLOAD).representation_cell_id == \
        "typed__absent__absent"
    assert legacy_transfer_config(TransferKind.EHC).representation_cell_id == \
        "typed__trace_linked__executable"
    assert legacy_transfer_config(TransferKind.FULL_HISTORY) is None
    assert legacy_transfer_config(TransferKind.GOLD_ORACLE) is None


def test_gate_is_an_orthogonal_run_label_not_an_ehc_privilege():
    structured = RunConfig("m", TransferKind.STRUCTURED_PAYLOAD,
                           enforce_action_gates=True).transfer_config
    ehc = RunConfig("m", TransferKind.EHC).transfer_config
    assert structured.enforcement is EnforcementFactor.ENFORCED
    assert ehc.enforcement is EnforcementFactor.ADVISORY
    assert structured.checks is ChecksFactor.ABSENT


def common_artifact(record):
    state = {field: [] for field in (
        "user_goal", "constraints", "verified_facts", "unresolved_slots", "tool_evidence",
        "policy_checks", "consent", "commitments", "risk_flags", "next_step_preconditions",
    )}
    event = record.upstream_trace[0]
    key, value = next(iter(event["content"].items()))
    state["verified_facts"] = [{"key": key, "status": "known", "value": value}]
    provenance = [{"field": "verified_facts", "key": key, "trace_id": event["trace_id"],
                   "source_type": event["source_type"]}]
    return {"state": state, "provenance": provenance}


def test_complete_cube_has_eight_explicit_serializations():
    record = load_tasks()[0]
    generated = common_artifact(record)
    assert len(FACTORIAL_CELLS) == 8
    for cell_id, cell in FACTORIAL_CELLS.items():
        view = make_factorial_view(record, cell, generated)
        assert view.content["representation_cell"] == cell_id
        assert set(view.content["fields"]) == set(generated["state"])
        first_field = view.content["fields"]["verified_facts"]
        assert isinstance(first_field, str) == (cell.typing is TypingFactor.FREE_FORM)
        assert ("provenance" in view.content) == (cell.provenance is ProvenanceFactor.TRACE_LINKED)
        assert ("checks" in view.content) == (cell.checks is ChecksFactor.EXECUTABLE)
        assert view.validator_sidecar["raw_artifact_unchanged"] is True


class CaptureProvider:
    def __init__(self, raw):
        self.raw = raw
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return self.raw


def test_all_cells_have_identical_source_evidence_predicates_schema_and_budget():
    record = load_tasks()[0]
    raw = json.dumps(common_artifact(record))
    observed = []
    for cell in FACTORIAL_CELLS.values():
        provider = CaptureProvider(raw)
        config = RunConfig("m", TransferKind.FACTORIAL, factorial_cell=cell,
                           max_output_tokens=777)
        generate_transfer(record, config, provider)
        observed.append(provider.calls[0])
    messages = [json.dumps(call[0], sort_keys=True) for call in observed]
    assert len(set(messages)) == 1
    assert all(call[1]["response_schema"] == FACTORIAL_SOURCE_SCHEMA for call in observed)
    assert {call[1]["max_output_tokens"] for call in observed} == {777}
    payload = json.loads(observed[0][0][1]["content"])
    assert payload["upstream_trace"] == list(record.upstream_trace)
    assert "public_policy_predicates" in payload


def test_factorial_config_is_required_and_enforcement_does_not_change_artifact():
    with pytest.raises(ValueError, match="factorial_cell"):
        RunConfig("m", TransferKind.FACTORIAL)
    cell = FACTORIAL_CELLS["typed__trace_linked__executable"]
    advisory = RunConfig("m", TransferKind.FACTORIAL, factorial_cell=cell)
    enforced = RunConfig("m", TransferKind.FACTORIAL, factorial_cell=cell,
                         enforce_action_gates=True)
    assert advisory.transfer_config.representation_cell_id == enforced.transfer_config.representation_cell_id
    assert advisory.transfer_config.enforcement is EnforcementFactor.ADVISORY
    assert enforced.transfer_config.enforcement is EnforcementFactor.ENFORCED
    record = load_tasks()[0]; generated = common_artifact(record)
    assert dict(make_factorial_view(record, advisory.transfer_config, generated).content) == \
        dict(make_factorial_view(record, enforced.transfer_config, generated).content)


def test_factorial_validator_never_repairs_or_quarantines_bad_claim():
    record = load_tasks()[0]
    generated = common_artifact(record)
    generated["state"]["verified_facts"][0]["value"] = "fabricated"
    original = json.loads(json.dumps(generated))
    view = make_factorial_view(
        record, FACTORIAL_CELLS["typed__trace_linked__executable"], generated
    )
    assert view.content["fields"]["verified_facts"][0]["value"] == "fabricated"
    assert view.content["provenance"] == original["provenance"]
    assert view.validator_sidecar["strict_validation_pass"] is False
    assert view.content["validation_annotations"]
    assert generated == original


def test_factorial_run_retains_validator_sidecar():
    record = load_tasks()[0]
    state = {field: [] for field in common_artifact(record)["state"]}
    source = json.dumps({"state": state, "provenance": []})
    receiver = json.dumps({
        "receiver_state": state,
        "action": {"name": "ask_user", "arguments": {"slot": "change_fee_consent"},
                   "rationale": "unknown"},
    })
    provider = CaptureProvider(source)
    provider.raws = [source, receiver]
    provider.complete = lambda messages, **kwargs: provider.raws.pop(0)
    config = RunConfig(
        "m", TransferKind.FACTORIAL,
        factorial_cell=FACTORIAL_CELLS["free_form__absent__absent"], max_turns=1,
    )
    artifact = run_pilot(record, config, provider)
    assert artifact.transfer_validation_sidecar["representation_cell"] == \
        "free_form__absent__absent"
