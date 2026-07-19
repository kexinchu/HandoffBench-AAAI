import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

from handoffbench.dataset import execute_events, load_tasks
from handoffbench.prompts import action_catalog


ROOT = Path(__file__).parents[1]
CHALLENGE = ROOT / "data/tasks/dev/counterfactual_travel.json"


def _baselines():
    path = ROOT / "scripts/leakage_baselines.py"
    spec = importlib.util.spec_from_file_location("leakage_baselines", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _catalog_hash(record) -> str:
    raw = json.dumps(action_catalog(record), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def test_six_families_have_four_executable_symmetric_variants() -> None:
    records = load_tasks(CHALLENGE)
    families = defaultdict(list)
    for record in records:
        families[record.episode.split_meta.entity_pool].append(record)
        gold = record.episode.success_predicate.args["required_events"]
        assert execute_events(record, gold).success
    assert len(records) == 24 and len(families) == 6
    for variants in families.values():
        assert {r.episode.task_id.rsplit("_", 1)[-1] for r in variants} == {
            "unknown", "granted", "denied", "stale"
        }
        assert len({_catalog_hash(r) for r in variants}) == 1
        # Same public problem, different hidden first-action labels.
        first = Counter(r.episode.success_predicate.args["required_events"][0]["name"]
                        for r in variants)
        assert first == {"ask_user": 2, "decline_or_offer_alternative": 1,
                         variants[0].episode.allowed_next_actions[-1].action: 1} or sorted(first.values()) == [1, 1, 2]


def test_variant_changes_do_not_modify_public_catalog_or_candidate_enums() -> None:
    records = load_tasks(CHALLENGE)
    families = defaultdict(list)
    for record in records:
        families[record.episode.split_meta.entity_pool].append(record)
    for variants in families.values():
        reference = action_catalog(variants[0])
        assert all(action_catalog(record) == reference for record in variants[1:])
        enum_sizes = [len(spec["enum"]) for item in reference
                      for spec in item["arguments"].values()
                      if isinstance(spec, dict) and "enum" in spec]
        assert enum_sizes and min(enum_sizes) >= 3


def test_leakage_baseline_release_thresholds_and_exact_copy_oracle() -> None:
    module = _baselines()
    report = module.evaluate(load_tasks(CHALLENGE))["summary"]
    assert report["catalog_only"]["success_rate"] <= 0.25
    assert report["predicate_only"]["success_rate"] <= 0.35
    assert report["exact_copy"]["success_rate"] == 1.0
    assert report["exact_copy"]["invocation_f1"] == 1.0


def test_baselines_are_invariant_to_catalog_transport_order() -> None:
    module = _baselines()
    for record in load_tasks(CHALLENGE):
        catalog = action_catalog(record)
        for method in ("catalog_only", "name_only", "predicate_only"):
            assert module.predict(record, method, catalog=catalog) == module.predict(
                record, method, catalog=list(reversed(catalog))
            )


def test_negative_reason_codes_are_semantically_typed_by_family() -> None:
    expected = {
        "01": "user_declined",
        "02": "invalid_input",
        "03": "invalid_input",
        "04": "invalid_input",
        "05": "invalid_input",
        "06": "user_declined",
    }
    for record in load_tasks(CHALLENGE):
        if not record.episode.task_id.endswith("_denied"):
            continue
        family = record.episode.task_id.split("_")[2]
        rule = next(
            rule for rule in record.episode.allowed_next_actions
            if rule.action == "decline_or_offer_alternative"
        )
        assert rule.expected_arguments == {"reason_code": expected[family]}


def test_nonconsent_slots_use_explicit_validity_not_ambiguous_booleans() -> None:
    validity_slots = {
        "02": "guest_name",
        "03": "passenger_dob",
        "04": "license_country",
        "05": "passport_expiry",
    }
    for record in load_tasks(CHALLENGE):
        family = record.episode.task_id.split("_")[2]
        if family not in validity_slots:
            continue
        claim = next(c for c in record.episode.gold_state if c.key == validity_slots[family])
        if record.episode.task_id.endswith("_granted"):
            assert claim.value == "valid"
        elif record.episode.task_id.endswith("_denied"):
            assert claim.value == "invalid"
