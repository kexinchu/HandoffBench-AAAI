import hashlib
import json
from collections import Counter
from pathlib import Path

from handoffbench.dataset import execute_events, load_tasks, primary_gold_claims, public_action_contract


PATH = Path(__file__).parents[1] / "data/tasks/candidate/scheduling.json"


def records():
    return load_tasks(PATH)


def test_candidate_schema_count_ids_and_unique_families():
    items = records()
    assert len(items) == 40
    assert [r.episode.task_id for r in items] == [f"cand_scheduling_{i:03d}" for i in range(1, 41)]
    families = [r.episode.split_meta.template_family for r in items]
    assert len(set(families)) == 40
    assert all(r.episode.domain == "scheduling" for r in items)
    assert all(r.episode.split_meta.generator_version.startswith("candidate-") for r in items)


def test_candidate_oracle_sequences_execute_successfully():
    for record in records():
        oracle = record.episode.success_predicate.args["required_events"]
        result = execute_events(record, oracle)
        assert result.success, (record.episode.task_id, result.violations)


def test_expected_arguments_are_trace_or_scripted_reply_grounded():
    for record in records():
        visible_values = set()
        for event in record.upstream_trace:
            visible_values.update(json.dumps(value, sort_keys=True) for value in event["content"].values())
        for reply in record.mock_tool_world["user_replies"].values():
            visible_values.update(json.dumps(update["value"], sort_keys=True)
                                  for update in reply["updates"].values())
        for rule in record.episode.allowed_next_actions:
            if rule.action == "ask_user":
                # The queried slot is itself a gold/trace property name.
                assert rule.expected_arguments["slot"] in {claim.key for claim in record.episode.gold_state}
            else:
                assert all(json.dumps(value, sort_keys=True) in visible_values
                           for value in rule.expected_arguments.values())


def test_public_catalog_has_decoys_without_evaluator_label_leakage():
    correct_positions = []
    for record in records():
        catalog = public_action_contract(record)
        serialized = json.dumps(catalog, sort_keys=True)
        for forbidden in ("expected_arguments", "success_predicate", "forbidden_next_actions",
                          "max_calls", "critical_keys"):
            assert forbidden not in serialized
        terminal = next(rule for rule in record.episode.allowed_next_actions if rule.irreversible)
        public_terminal = next(item for item in catalog if item["action"] == terminal.action)
        for signature in public_terminal["arguments"].values():
            assert len(signature["enum"]) >= 3
        key, expected = next(iter(terminal.expected_arguments.items()))
        enum = public_terminal["arguments"][key]["enum"]
        correct_positions.append(enum.index(expected))
        # The independent public catalog includes plausible wrong choices, not just the oracle argument.
        assert len(set(enum) - {expected}) >= 2
        ask = [item for item in catalog if item["action"] == "ask_user"]
        if ask:
            assert len(ask[0]["arguments"]["slot"]["enum"]) >= 3
    assert set(correct_positions) == {0, 1, 2}


def test_primary_stressor_balance_and_primary_ontology():
    counts = Counter(record.stressors[0] for record in records())
    assert counts == {"long_distractor": 7, "user_revision": 7,
                      "conflicting_evidence": 7, "missing_authority": 7,
                      "multi_step_evidence": 6, "irreversible_action": 6}
    allowed = {"goal", "constraint", "verified_fact", "unresolved_slot", "consent", "policy_check"}
    for record in records():
        categories = {claim.category.value for claim in primary_gold_claims(record)}
        assert categories <= allowed
        assert not ({"risk", "commitment", "precondition", "tool_evidence"} & categories)


def test_candidate_automaton_identities_are_unique():
    identities = []
    for record in records():
        structure = {
            "roles": [record.episode.boundary.source_role, record.episode.boundary.target_role],
            "allowed": [(rule.action, tuple(rule.when), rule.irreversible)
                        for rule in record.episode.allowed_next_actions],
            "required_names": [event["name"] for event in record.episode.success_predicate.args["required_events"]],
        }
        identities.append(hashlib.sha256(json.dumps(structure, sort_keys=True).encode()).hexdigest())
    assert len(set(identities)) == 40
