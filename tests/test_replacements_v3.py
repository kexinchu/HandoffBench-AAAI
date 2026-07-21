import hashlib
import importlib.util
import itertools
import json
from collections import Counter
from pathlib import Path

from handoffbench.dataset import execute_events, load_tasks, public_action_contract
from handoffbench.prompts import action_catalog


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "data/tasks/replacements_v3/replacement_candidates.v3.json"
MANIFEST = ROOT / "data/tasks/replacements_v3/manifest.v3.json"
PACKETS = ROOT / "data/annotations/replacement_packets_v3"
PACKET_HASHES = ROOT / "data/annotations/replacement_packets_v3.sha256"
REPORT = ROOT / "research/coordinator_only/replacement_v3_build_audit.json"


def generator_module():
    path = ROOT / "scripts/generate_replacements_v3.py"
    spec = importlib.util.spec_from_file_location("replacement_v3_generator", path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def records():
    return load_tasks(SOURCE)


def test_replacement_quota_ids_and_families_are_new_and_versioned():
    items = records()
    assert Counter(item.episode.domain for item in items) == {
        "commerce": 5, "procurement": 23, "it": 35
    }
    for domain, count in (("it", 35), ("procurement", 23), ("commerce", 5)):
        assert sorted(item.episode.task_id for item in items if item.episode.domain == domain) == [
            f"repl_v3_{domain}_{index:03d}" for index in range(1, count + 1)
        ]
    families = [item.episode.split_meta.template_family for item in items]
    assert len(families) == len(set(families)) == 63
    assert all("_v3_" in family for family in families)

    existing_ids = set()
    existing_families = set()
    for path in (ROOT / "data/tasks/candidate").glob("*.json"):
        for item in json.loads(path.read_text(encoding="utf-8")):
            existing_ids.add(item["episode"]["task_id"])
            existing_families.add(item["episode"]["split_meta"]["template_family"])
    assert not ({item.episode.task_id for item in items} & existing_ids)
    assert not (set(families) & existing_families)


def test_exact_oracles_are_unique_legal_sequences_and_mutations_fail():
    module = generator_module()
    for item in records():
        required = item.episode.success_predicate.args["required_events"]
        assert execute_events(item, required).success
        assert module._legal_terminal_sequences(item) == [required]
        assert not execute_events(item, required[:-1]).success
        if len(required) > 1:
            assert not execute_events(item, list(reversed(required))).success
        forbidden = item.episode.success_predicate.args["forbidden_events"][0]
        assert not execute_events(item, required + [forbidden]).success


def test_public_semantics_have_three_decoys_and_are_catalog_order_invariant():
    module = generator_module()
    for item in records():
        packet = json.loads((PACKETS / f"{item.episode.task_id}.json").read_text(encoding="utf-8"))
        contract = list(packet["public_action_contract"])
        gold = item.episode.success_predicate.args["required_events"]
        gold_names = {event["name"] for event in gold}
        assert 5 <= len(contract) <= 7
        assert len([action for action in contract if action["action"] not in gold_names]) >= 3
        assert [action["action"] for action in contract][:len(gold)] != [
            event["name"] for event in gold
        ]
        assert action_catalog(item)[0]["name"] != gold[0]["name"]
        for order in itertools.permutations(contract):
            assert module._public_sequence(packet, list(order)) == gold


def test_irreversible_arguments_are_visible_and_wrong_values_fail():
    for item in records():
        trace = json.dumps(item.upstream_trace, sort_keys=True)
        public = {action["action"]: action for action in public_action_contract(item)}
        required = json.loads(json.dumps(item.episode.success_predicate.args["required_events"]))
        for event in required:
            for key, value in event["arguments"].items():
                assert json.dumps(value) in trace
                enum = public[event["name"]]["arguments"][key]["enum"]
                assert len(enum) == 3 and value in enum
        terminal = required[-1]
        key, correct = next(iter(terminal["arguments"].items()))
        terminal["arguments"][key] = next(
            value for value in public[terminal["name"]]["arguments"][key]["enum"]
            if value != correct
        )
        assert not execute_events(item, required).success


def test_blind_packets_exclude_evaluator_gold_and_match_hash_manifest():
    module = generator_module()
    paths = sorted(PACKETS.glob("*.json"))
    assert len(paths) == 63
    expected = {}
    for line in PACKET_HASHES.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    assert set(expected) == {path.name for path in paths}
    for path in paths:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected[path.name]
        value = json.loads(raw)
        module._assert_blind(value)
        rendered = json.dumps(value, sort_keys=True)
        assert all(key not in rendered for key in module.FORBIDDEN_PACKET_KEYS)
    assert not list(PACKETS.glob("*assignment*"))
    assert not list(PACKETS.glob("*response*"))


def test_build_report_records_all_static_gates_and_unsealed_status():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    summary = report["summary"]
    assert report["status"] == "replacement_candidates_unsealed_no_model_calls"
    for key in (
        "schema_valid", "exact_oracle_execution", "public_reconstruction",
        "catalog_permutation_invariant", "unique_legal_sequences",
        "irreversible_arguments_grounded", "impact_consistent",
    ):
        assert summary[key] == 63
    assert summary["identity_collisions"] == 0
    assert summary["unique_internal_topologies"] == 63
    assert summary["blind_packet_leaks"] == 0
    assert summary["candidate_lexical_near_duplicates"] == 0
    assert summary["development_lexical_near_duplicates"] == 0
    assert summary["leakage"]["catalog_only_success"] == 0
    assert summary["leakage"]["predicate_only_success"] == 0
    assert summary["leakage"]["exact_copy_success"] == 63

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "candidate_unsealed"
    assert manifest["model_calls"] == 0
    assert manifest["sealing_authority"] is None
    assert manifest["source_sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def test_claim_provenance_and_public_impact_contracts_are_consistent():
    for item in records():
        trace = {event["trace_id"]: event for event in item.upstream_trace}
        for claim in item.episode.gold_state:
            assert claim.provenance
            for pointer in claim.provenance:
                assert pointer.trace_id in trace
                assert trace[pointer.trace_id]["source_type"] == pointer.source_type
                assert pointer.field_path.rsplit(".", 1)[-1] == claim.key
        public_impacting = {
            action["action"] for action in public_action_contract(item) if action["user_impacting"]
        }
        irreversible = {
            rule.action for rule in item.episode.allowed_next_actions if rule.irreversible
        }
        assert public_impacting == irreversible
