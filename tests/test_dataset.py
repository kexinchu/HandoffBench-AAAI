import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from handoffbench.dataset import (
    execute_events,
    load_tasks,
    predicate_holds,
    primary_gold_claims,
    validate_dev_pilot,
)


ROOT = Path(__file__).parents[1]
PILOT = ROOT / "data" / "tasks" / "dev" / "pilot.json"
SCHEMA = ROOT / "data" / "schemas" / "episode.schema.json"


def test_dev_pilot_loads_and_has_independent_families() -> None:
    records = load_tasks(PILOT, schema_path=SCHEMA)
    validate_dev_pilot(records)
    assert Counter(record.episode.domain for record in records) == {
        "travel": 6,
        "commerce": 6,
        "procurement": 6,
        "it": 6,
        "scheduling": 6,
    }
    families = {record.episode.split_meta.template_family for record in records}
    assert len(families) == 30


def test_every_task_has_complete_evaluator_material() -> None:
    for record in load_tasks(PILOT, schema_path=SCHEMA):
        assert record.upstream_trace
        assert record.stressors
        assert record.mock_tool_world["tools"]
        assert record.episode.gold_state
        assert record.episode.allowed_next_actions
        assert record.episode.forbidden_next_actions
        provenance = {
            evidence.trace_id
            for claim in record.episode.gold_state
            for evidence in claim.provenance
        }
        trace_ids = {event["trace_id"] for event in record.upstream_trace}
        assert provenance <= trace_ids


def test_predicates_are_ordered_and_forbidden_events_fail() -> None:
    for record in load_tasks(PILOT, schema_path=SCHEMA):
        args = record.episode.success_predicate.args
        assert predicate_holds(record, args["required_events"])
        assert not predicate_holds(record, list(reversed(args["required_events"]))) or len(
            args["required_events"]
        ) == 1
        assert not predicate_holds(
            record, args["required_events"] + [args["forbidden_events"][0]]
        )


def test_ask_is_checked_while_unknown_then_reply_updates_state() -> None:
    record = load_tasks(PILOT, schema_path=SCHEMA)[0]
    required = record.episode.success_predicate.args["required_events"]
    consent_key = "change_fee_consent"
    result = execute_events(record, required)
    assert result.success
    assert result.final_state[consent_key] == {"status": "known", "value": True}

    duplicate_ask = execute_events(record, [required[0], required[0], required[1]])
    assert not duplicate_ask.success
    assert f"precondition:{required[0]['name']}" in duplicate_ask.violations
    assert f"max_calls:{required[0]['name']}" in duplicate_ask.violations


def test_irreversible_action_before_consent_fails_precondition() -> None:
    record = load_tasks(PILOT, schema_path=SCHEMA)[0]
    ask, book = record.episode.success_predicate.args["required_events"]
    result = execute_events(record, [book, ask])
    assert not result.success
    assert f"precondition:{book['name']}" in result.violations


def test_generic_actions_score_arguments_not_entity_bearing_names() -> None:
    record = load_tasks(PILOT, schema_path=SCHEMA)[0]
    ask, book = record.episode.success_predicate.args["required_events"]
    assert ":" not in ask["name"] and ":" not in book["name"]
    wrong = {"name": book["name"], "arguments": {"option_id": "F305"}}
    result = execute_events(record, [ask, wrong])
    assert not result.success
    assert f"arguments:{book['name']}" in result.violations


def test_wrong_option_forbidden_precondition_and_duplicate_are_distinct() -> None:
    record = load_tasks(PILOT, schema_path=SCHEMA)[0]
    ask, book = record.episode.success_predicate.args["required_events"]
    explicitly_wrong = {"name": "book_flight", "arguments": {"option_id": "F184"}}
    assert "forbidden:book_flight" in execute_events(record, [ask, explicitly_wrong]).violations
    assert "precondition:book_flight" in execute_events(record, [book, ask]).violations
    duplicate = execute_events(record, [ask, ask, book])
    assert "max_calls:ask_user" in duplicate.violations


def test_travel_public_catalog_has_decoys_and_hides_oracle_labels() -> None:
    from handoffbench.prompts import action_catalog
    for record in load_tasks(PILOT, schema_path=SCHEMA)[:6]:
        catalog = action_catalog(record)
        serialized = json.dumps(catalog)
        assert len(catalog) >= 3
        commit = next(item for item in catalog
                      if any(isinstance(spec, dict) and "enum" in spec
                             for spec in item["arguments"].values())
                      and item["name"] != "ask_user")
        enum = next(iter(commit["arguments"].values()))["enum"]
        assert len(enum) >= 3
        for secret in ("expected_arguments", "success_predicate", "forbidden", "max_calls"):
            assert secret not in serialized
        required_names = [item["name"] for item in record.episode.success_predicate.args["required_events"]]
        assert [item["name"] for item in catalog][:len(required_names)] != required_names


def test_migrated_commerce_and_procurement_catalogs_are_leakage_resistant() -> None:
    from handoffbench.prompts import action_catalog

    records = load_tasks(PILOT, schema_path=SCHEMA)[6:18]
    assert {record.episode.domain for record in records} == {"commerce", "procurement"}
    for record in records:
        catalog = action_catalog(record)
        serialized = json.dumps(catalog, sort_keys=True)
        assert len(catalog) >= 3
        assert all(":" not in item["name"] for item in catalog)
        for secret in ("expected_arguments", "success_predicate", "forbidden", "max_calls"):
            assert secret not in serialized

        evaluator_events = record.episode.success_predicate.args["required_events"]
        evaluator_events += record.episode.success_predicate.args["forbidden_events"]
        for event in evaluator_events:
            for entity in event["arguments"].values():
                if isinstance(entity, str):
                    assert entity not in event["name"]

        required_names = [event["name"] for event in
                          record.episode.success_predicate.args["required_events"]]
        assert [item["name"] for item in catalog][:len(required_names)] != required_names


def test_migrated_tasks_reject_a_plausible_wrong_argument() -> None:
    records = load_tasks(PILOT, schema_path=SCHEMA)[6:18]
    for record in records:
        required = copy.deepcopy(
            record.episode.success_predicate.args["required_events"]
        )
        public = {item["action"]: item for item in
                  record.mock_tool_world["public_actions"]}
        target_index = next(
            index for index, event in enumerate(required)
            if event["arguments"] and event["name"] in public
        )
        target = required[target_index]
        argument, correct = next(iter(target["arguments"].items()))
        candidates = public[target["name"]]["arguments"][argument]["enum"]
        assert len(candidates) >= 3
        wrong = next(candidate for candidate in candidates if candidate != correct)
        target["arguments"][argument] = wrong
        result = execute_events(record, required)
        assert not result.success
        assert f"arguments:{target['name']}" in result.violations or any(
            violation.startswith("forbidden:") for violation in result.violations
        )


def test_it_and_scheduling_use_leakage_resistant_generic_action_catalogs() -> None:
    from handoffbench.prompts import action_catalog, receiver_turn_messages
    from handoffbench.transfer import TransferKind, make_view

    generic_names = {
        "ask_user", "verify_condition", "commit_change", "run_check",
        "notify_parties", "assert_fact",
    }
    for record in load_tasks(PILOT, schema_path=SCHEMA)[18:30]:
        required = record.episode.success_predicate.args["required_events"]
        forbidden = record.episode.success_predicate.args["forbidden_events"]
        evaluator_names = {item["name"] for item in required + forbidden}
        assert evaluator_names <= generic_names
        assert all(":" not in name for name in evaluator_names)

        catalog = action_catalog(record)
        assert catalog == action_catalog(record), "per-task permutation must be stable"
        required_names = [item["name"] for item in required]
        assert [item["name"] for item in catalog][:len(required_names)] != required_names
        enums = [
            spec["enum"]
            for action in catalog
            for spec in action["arguments"].values()
            if isinstance(spec, dict) and "enum" in spec
        ]
        assert enums and all(len(values) >= 3 for values in enums)

        final = required[-1]
        key = next(iter(final["arguments"]))
        wrong = {"name": final["name"], "arguments": {**final["arguments"], key: "not_the_gold_value"}}
        result = execute_events(record, required[:-1] + [wrong])
        assert not result.success
        assert f"arguments:{final['name']}" in result.violations

        prompt = json.dumps(receiver_turn_messages(
            record.episode.boundary.target_role,
            make_view(record, TransferKind.FULL_HISTORY),
            record,
            [],
        ))
        for secret in ("expected_arguments", "success_predicate", "forbidden_next_actions", "max_calls"):
            assert secret not in prompt


def test_all_happy_paths_transition_before_irreversible_actions() -> None:
    for record in load_tasks(PILOT, schema_path=SCHEMA):
        result = execute_events(
            record, record.episode.success_predicate.args["required_events"]
        )
        assert result.success, (record.episode.task_id, result.violations)


def _write_mutation(tmp_path: Path, mutate) -> Path:
    payload = json.loads(PILOT.read_text(encoding="utf-8"))
    mutate(payload[0])
    target = tmp_path / "bad.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "mutate,match",
    [
        (
            lambda task: task["episode"]["gold_state"][0]["provenance"][0].update(
                trace_id="missing"
            ),
            "dangling provenance",
        ),
        (
            lambda task: task["episode"]["boundary"].update(trace_cut=99),
            "trace_cut",
        ),
        (
            lambda task: task["episode"]["success_predicate"].update(
                predicate_id="natural_language_judge"
            ),
            "unsupported predicate",
        ),
        (
            lambda task: task["episode"]["gold_state"][0]["provenance"][0].update(
                field_path="content.mismatched_goal"
            ),
            "does not match a provenance field_path leaf",
        ),
    ],
)
def test_cross_record_mutations_are_rejected(tmp_path: Path, mutate, match: str) -> None:
    target = _write_mutation(tmp_path, mutate)
    with pytest.raises(ValueError, match=match):
        load_tasks(target, schema_path=SCHEMA)


def test_schema_mutation_is_rejected(tmp_path: Path) -> None:
    target = _write_mutation(
        tmp_path, lambda task: task["episode"].update(task_id="not schema safe")
    )
    with pytest.raises(ValueError, match="fails episode schema"):
        load_tasks(target, schema_path=SCHEMA)


def test_irreversible_action_requires_gate_from_scripted_resolution(tmp_path: Path) -> None:
    def remove_resolved_slot_gate(task):
        irreversible = next(
            rule for rule in task["episode"]["allowed_next_actions"]
            if rule["irreversible"]
        )
        irreversible["when"] = []

    target = _write_mutation(tmp_path, remove_resolved_slot_gate)
    with pytest.raises(ValueError, match="lacks resolved-slot gate"):
        load_tasks(target, schema_path=SCHEMA)


def test_all_claim_keys_match_provenance_leaf_or_are_explicitly_derived() -> None:
    for record in load_tasks(PILOT, schema_path=SCHEMA):
        for claim in record.episode.gold_state:
            leaves = {
                evidence.field_path.rsplit(".", 1)[-1]
                for evidence in claim.provenance
                if evidence.field_path
            }
            assert claim.key in leaves or (
                claim.normalizer and claim.normalizer.startswith("derived:")
            )


def test_category_routing_has_construct_coverage_without_per_task_collapse() -> None:
    records = load_tasks(PILOT, schema_path=SCHEMA)
    counts = Counter(
        claim.category.value for record in records for claim in record.episode.gold_state
    )
    assert counts == {
        "goal": 30,
        "constraint": 30,
        "verified_fact": 31,
        "unresolved_slot": 8,
        "policy_check": 11,
        "consent": 11,
    }
    for record in records:
        assert len({claim.category for claim in record.episode.gold_state}) >= 4


def test_primary_f1_view_contains_only_unique_base_claims() -> None:
    for record in load_tasks(PILOT, schema_path=SCHEMA):
        primary = primary_gold_claims(record)
        assert primary == tuple(record.episode.gold_state)
        assert len({claim.key for claim in primary}) == len(primary)
        assert not any(claim.normalizer and claim.normalizer.startswith("derived:") for claim in primary)


def test_duplicate_base_claim_identity_is_rejected(tmp_path: Path) -> None:
    def duplicate(task):
        clone = copy.deepcopy(task["episode"]["gold_state"][0])
        clone["claim_id"] = "duplicate-id"
        task["episode"]["gold_state"].append(clone)

    target = _write_mutation(tmp_path, duplicate)
    with pytest.raises(ValueError, match="gold base claim keys must be unique"):
        load_tasks(target, schema_path=SCHEMA)
