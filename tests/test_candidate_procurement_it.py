import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from handoffbench.dataset import execute_events, load_tasks, public_action_contract
from handoffbench.prompts import action_catalog


ROOT = Path(__file__).parents[1]
CANDIDATES = ROOT / "data/tasks/candidate/procurement_it.json"


def records():
    return load_tasks(CANDIDATES)


def test_candidate_file_has_80_unique_unsealed_families():
    items = records()
    assert Counter(item.episode.domain for item in items) == {"procurement": 40, "it": 40}
    assert [item.episode.task_id for item in items[:40]] == [
        f"cand_procurement_{index:03d}" for index in range(1, 41)
    ]
    assert [item.episode.task_id for item in items[40:]] == [
        f"cand_it_{index:03d}" for index in range(1, 41)
    ]
    families = [item.episode.split_meta.template_family for item in items]
    assert len(families) == len(set(families)) == 80
    raw = CANDIDATES.read_text(encoding="utf-8").lower()
    assert '"split": "test"' not in raw and '"sealed"' not in raw


def test_exact_gold_sequences_execute_successfully():
    for item in records():
        expected = item.episode.success_predicate.args["required_events"]
        result = execute_events(item, expected)
        assert result.success, (item.episode.task_id, result.violations)


def test_expected_arguments_are_authenticated_and_wrong_enums_fail():
    for item in records():
        trace = json.dumps(item.upstream_trace, sort_keys=True)
        public = {action["action"]: action for action in public_action_contract(item)}
        sequence = copy.deepcopy(item.episode.success_predicate.args["required_events"])
        for event in sequence:
            for value in event["arguments"].values():
                assert value in trace
            signature = public[event["name"]]
            for key, value in event["arguments"].items():
                assert len(signature["arguments"][key]["enum"]) >= 3
                assert value in signature["arguments"][key]["enum"]
        final = sequence[-1]
        key, correct = next(iter(final["arguments"].items()))
        wrong = next(value for value in public[final["name"]]["arguments"][key]["enum"]
                     if value != correct)
        final["arguments"][key] = wrong
        assert not execute_events(item, sequence).success


def test_public_catalog_and_predicates_resist_shallow_answer_leakage():
    correct_enum_positions = Counter()
    first_action_positions = Counter()
    for item in records():
        catalog = action_catalog(item)
        assert catalog == action_catalog(item)
        assert len(catalog) >= 3
        serialized = json.dumps(catalog, sort_keys=True)
        for secret in ("expected_arguments", "success_predicate", "forbidden", "max_calls"):
            assert secret not in serialized
        required = item.episode.success_predicate.args["required_events"]
        names = [action["name"] for action in catalog]
        first_action_positions[names.index(required[0]["name"])] += 1
        assert names[:len(required)] != [event["name"] for event in required]
        first = required[0]
        spec = next(action for action in catalog if action["name"] == first["name"])
        correct = first["arguments"]["choice"]
        correct_enum_positions[spec["arguments"]["choice"]["enum"].index(correct)] += 1
        assert all("eligible" not in description.lower() and "correct" not in description.lower()
                   for description in spec["arguments"]["choice"]["enum_descriptions"].values())
        predicates = [condition for action in catalog for condition in action["requires"]]
        assert all("success" not in condition and "forbidden" not in condition
                   for condition in predicates)
    assert set(correct_enum_positions) == {0, 1, 2}
    assert max(correct_enum_positions.values()) - min(correct_enum_positions.values()) <= 1
    assert len(first_action_positions) >= 3


def test_user_impacting_coverage_exceeds_forty_percent_in_each_domain():
    by_domain = {domain: [item for item in records() if item.episode.domain == domain]
                 for domain in ("procurement", "it")}
    for domain, items in by_domain.items():
        impacted = sum(any(action["user_impacting"] for action in public_action_contract(item))
                       for item in items)
        assert impacted / len(items) >= .4, (domain, impacted)


def test_primary_gold_normalization_and_stressor_automaton_audit():
    taxonomy = {"long_distractor", "user_revision", "conflicting_evidence", "missing_authority",
                "multi_step_evidence", "irreversible_action"}
    for item in records():
        claims = item.episode.gold_state
        assert all(claim.category.value not in {"precondition", "tool_evidence", "risk"}
                   for claim in claims)
        trace_properties = {
            key for event in item.upstream_trace for key in event.get("content", {})
        }
        assert all(claim.key in trace_properties for claim in claims)
        assert all(claim.key in trace_properties for claim in claims
                   if claim.category.value == "commitment")
        assert item.stressors[0] in taxonomy
        identity = next(value.removeprefix("automaton_identity:") for value in item.stressors
                        if value.startswith("automaton_identity:"))
        hash_input = next(value.removeprefix("automaton_hash_input:") for value in item.stressors
                          if value.startswith("automaton_hash_input:"))
        digest = next(value.removeprefix("automaton_sha256:") for value in item.stressors
                      if value.startswith("automaton_sha256:"))
        assert identity == item.episode.split_meta.template_family
        assert hashlib.sha256(hash_input.encode()).hexdigest() == digest
        assert all(condition.split("=", 1)[0].removeprefix("!") in
                   {claim.key for claim in claims}
                   for rule in item.episode.allowed_next_actions for condition in rule.when)


def test_primary_stressors_are_canonical_balanced_and_values_are_plausible():
    items = records()
    primary = Counter(item.stressors[0] for item in items)
    assert set(primary) == {"long_distractor", "user_revision", "conflicting_evidence",
                            "missing_authority", "multi_step_evidence", "irreversible_action"}
    assert max(primary.values()) - min(primary.values()) <= 1
    for item in items:
        claims = {claim.key: claim.value for claim in item.episode.gold_state}
        categories = {claim.key: claim.category.value for claim in item.episode.gold_state}
        if "minimum_quote_count" in claims:
            assert claims["minimum_quote_count"] == 3
        for key, value in claims.items():
            if any(token in key for token in ("qty", "quantity", "count")) and value is not None:
                assert isinstance(value, (int, float)) and 1 <= value <= 20
            if "capacity" in key and value is not None and categories[key] != "goal":
                assert isinstance(value, (int, float)) and 1 <= value <= 100
        goal_values = [claim.value for claim in item.episode.gold_state
                       if claim.category.value == "goal"]
        family_slug = item.episode.split_meta.template_family.replace("_", " ")
        assert all(family_slug not in str(value).lower() for value in goal_values)


def test_candidate_evidence_is_multisource_and_has_no_synthetic_answer_labels():
    for item in records():
        assert {event["source_type"] for event in item.upstream_trace} == {
            "user", "tool", "policy", "environment"
        }
        assert len({event["trace_id"] for event in item.upstream_trace}) == 4
        serialized = json.dumps({
            "trace": item.upstream_trace,
            "catalog": list(public_action_contract(item)),
            "gold_values": [claim.value for claim in item.episode.gold_state],
        }, sort_keys=True).lower()
        assert "workflow_fit" not in serialized
        assert "meets_all_observed_requirements" not in serialized
        assert not any(isinstance(claim.value, str) and claim.value.endswith("_v")
                       for claim in item.episode.gold_state)
        descriptions = [
            description
            for action in public_action_contract(item)
            for spec in action["arguments"].values() if isinstance(spec, dict)
            for description in spec.get("enum_descriptions", {}).values()
        ]
        assert descriptions
        assert all("candidate 1" not in text.lower() and "candidate 2" not in text.lower()
                   and "candidate 3" not in text.lower() for text in descriptions)


def test_negative_notice_fact_and_explicit_supplier_promise_are_routed_differently():
    by_family = {item.episode.split_meta.template_family: item for item in records()}
    notice = next(claim for claim in
                  by_family["proc_auto_renewal_notice"].episode.gold_state
                  if claim.key == "notice_unsent")
    assert notice.category.value == "verified_fact"
    assert {ref.source_type for ref in notice.provenance} == {"tool"}

    promise = next(claim for claim in
                   by_family["proc_insurance_certificate_expiry"].episode.gold_state
                   if claim.key == "renewal_promised")
    assert promise.category.value == "commitment"
    assert {ref.source_type for ref in promise.provenance} == {"user"}


def test_catalog_blueprints_compile_one_to_one_and_action_graphs_are_independent():
    catalog = (ROOT / "research/test_family_catalog_procurement_it.md").read_text(encoding="utf-8")
    catalog_ids = re.findall(r"^\| `(proc_[a-z0-9_]+|it_[a-z0-9_]+)`", catalog, re.MULTILINE)
    items = records()
    assert len(catalog_ids) == len(set(catalog_ids)) == len(items) == 80
    assert catalog_ids == [item.episode.split_meta.template_family for item in items]
    graph_signatures = []
    for item in items:
        graph_signatures.append(tuple(
            (rule.action, tuple(rule.when), rule.irreversible)
            for rule in item.episode.allowed_next_actions
        ))
    assert len(set(graph_signatures)) == 80


def test_static_oracles_reject_sequence_and_forbidden_mutations():
    for item in records():
        required = item.episode.success_predicate.args["required_events"]
        forbidden = item.episode.success_predicate.args["forbidden_events"][0]
        assert execute_events(item, required).success
        if len(required) > 1:
            assert not execute_events(item, required[1:]).success
            assert not execute_events(item, list(reversed(required))).success
        assert not execute_events(item, required + [forbidden]).success
