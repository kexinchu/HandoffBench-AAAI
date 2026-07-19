import hashlib
import json
from collections import Counter
from pathlib import Path

from handoffbench.dataset import execute_events, load_tasks, primary_gold_claims
from handoffbench.transfer import public_action_contract


ROOT = Path(__file__).parents[1]
CANDIDATES = ROOT / "data" / "tasks" / "candidate" / "travel_commerce.json"
CATALOG = ROOT / "research" / "test_family_catalog_travel_commerce.md"
PRIMARY_STRESSORS = {
    "long_distractor",
    "user_revision",
    "conflicting_evidence",
    "missing_authority",
    "multi_step_evidence",
    "irreversible_action",
}


def records():
    return load_tasks(CANDIDATES)


def test_catalog_compiles_one_unique_candidate_per_family() -> None:
    items = records()
    assert len(items) == 80
    assert [r.episode.task_id for r in items[:40]] == [f"cand_travel_{i:03d}" for i in range(1, 41)]
    assert [r.episode.task_id for r in items[40:]] == [f"cand_commerce_{i:03d}" for i in range(1, 41)]
    families = [r.episode.split_meta.template_family for r in items]
    assert len(set(families)) == 80
    catalog = CATALOG.read_text(encoding="utf-8")
    assert all(f"`{family}`" in catalog for family in families)


def test_candidate_pool_expands_to_200_without_changing_other_domains() -> None:
    procurement_it = load_tasks(ROOT / "data" / "tasks" / "candidate" / "procurement_it.json")
    scheduling = load_tasks(ROOT / "data" / "tasks" / "candidate" / "scheduling.json")
    assert len(records()) + len(procurement_it) + len(scheduling) == 200
    assert Counter(r.episode.domain for r in procurement_it) == {"procurement": 40, "it": 40}
    assert Counter(r.episode.domain for r in scheduling) == {"scheduling": 40}


def test_gold_sequences_execute_and_arguments_are_trace_recoverable() -> None:
    for record in records():
        required = record.episode.success_predicate.args["required_events"]
        result = execute_events(record, required)
        assert result.success, (record.episode.task_id, result.violations)
        trace_text = json.dumps(record.upstream_trace, sort_keys=True)
        for event in required:
            for value in event["arguments"].values():
                assert json.dumps(value) in trace_text


def test_public_catalog_is_independent_and_has_plausible_choices() -> None:
    user_impacting_tasks = 0
    correct_positions = Counter()
    for record in records():
        public = public_action_contract(record)
        assert record.mock_tool_world.get("public_actions") is not None
        enums = [
            spec["enum"]
            for action in public
            for spec in action["arguments"].values()
            if isinstance(spec, dict) and isinstance(spec.get("enum"), list)
        ]
        assert enums and max(map(len, enums)) >= 3
        user_impacting_tasks += any(action["user_impacting"] for action in public)
        terminal = next(action for action in public if action["action"] == "commit_resolution")
        choices = terminal["arguments"]["target_id"]["enum"]
        expected = record.episode.success_predicate.args["required_events"][-1]["arguments"]["target_id"]
        correct_positions[choices.index(expected)] += 1
        # The public contract contains multiple plausible choices and no evaluator label.
        assert "allowed" not in json.dumps(public).lower()
        assert "forbidden" not in json.dumps(public).lower()
    assert user_impacting_tasks / 80 >= 0.40
    # First/last-position or catalog-only choice heuristics remain at chance.
    assert max(correct_positions.values()) / 80 <= 0.35


def test_primary_taxonomy_and_automata_are_auditable_and_unique() -> None:
    automata = set()
    stressors = Counter()
    for record in records():
        primary = record.stressors[0]
        assert primary in PRIMARY_STRESSORS
        stressors[primary] += 1
        initial = record.mock_tool_world["initial_state"]
        hash_input = initial["automaton_hash_input"]
        identity = hashlib.sha256(hash_input.encode()).hexdigest()
        assert initial["automaton_id"] == identity
        automata.add(identity)
        # Semantic family labels are evaluator metadata, absent from authenticated evidence;
        # opaque task/event IDs are permitted for provenance joins.
        trace = json.dumps(record.upstream_trace)
        assert record.episode.split_meta.template_family not in trace
    assert set(stressors) == PRIMARY_STRESSORS
    assert min(stressors.values()) >= 4
    assert len(automata) == 80


def test_primary_gold_has_no_manufactured_or_metadata_categories() -> None:
    excluded = {"risk", "commitment", "precondition", "tool_evidence"}
    for record in records():
        primary = primary_gold_claims(record)
        assert primary == tuple(record.episode.gold_state)
        assert not ({claim.category.value for claim in primary} & excluded)
        assert len({claim.key for claim in primary}) == len(primary)


def test_no_placeholder_values_and_sampled_business_semantics() -> None:
    forbidden_prefixes = ("required:", "authenticated:")

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for nested in value.values():
                yield from strings(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                yield from strings(nested)

    items = records()
    for record in items:
        payload = {
            "gold": [claim.model_dump(mode="json") for claim in record.episode.gold_state],
            "trace": list(record.upstream_trace),
        }
        assert not any(text.startswith(forbidden_prefixes) for text in strings(payload))
        tool_event = next(event for event in record.upstream_trace if event.get("tool") == "workflow_lookup")
        content = tool_event["content"]
        selected = content["eligible_action_target"]
        assert content["candidate_business_attributes"][selected]["policy_compatible"] is True
        assert "selection_basis" in content
        policy_text = json.dumps(
            [event["content"] for event in record.upstream_trace if event["source_type"] == "policy"]
        )
        assert selected not in policy_text

    by_family = {r.episode.split_meta.template_family: r for r in items}
    flight = by_family["travel_cancel_rebook_fee_consent"]
    assert "rebook" in next(c.value for c in flight.episode.gold_state if c.key == "goal")
    hotel = by_family["travel_hotel_deposit_currency"]
    deposit = next(c.value for c in hotel.episode.gold_state if c.key == "deposit")
    assert deposit == {"amount": "85.00", "currency": "USD"}
    commerce = by_family["commerce_damaged_exchange_substitution"]
    assert "exchange" in next(c.value for c in commerce.episode.gold_state if c.key == "goal")
