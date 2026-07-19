import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_construct_validity", ROOT / "scripts" / "audit_construct_validity.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_construct_audit_static_invariants_and_known_gaps() -> None:
    report = MODULE.audit()
    summary = report["summary"]
    assert report["n_tasks"] == 200
    assert summary["claims"] == 990
    assert summary["provenance_leaf_complete_tasks"] == 200
    assert summary["provenance_source_type_complete_tasks"] == 200
    assert summary["tasks_with_secret_arguments"] == 0
    assert summary["gold_sequence_legal"] == 200
    assert summary["unique_legal_terminal_sequence_without_phi"] == 137
    assert summary["gold_path_user_impacting"] == 195
    assert summary["impact_definition_consistent"] == 199
    assert summary["normalized_topology_overlap_candidates"] == 69
    assert summary["mechanically_witnessed_claims"] == 305


def test_domain_strata_and_semantic_review_flags_are_explicit() -> None:
    report = MODULE.audit()
    assert {domain: item["n"] for domain, item in report["domains"].items()} == {
        "travel": 40, "commerce": 40, "procurement": 40, "it": 40, "scheduling": 40
    }
    assert report["category_status"]["commitment/known"] == 2
    assert report["category_status"]["consent/unknown"] == 59
    assert report["category_status"]["policy_check/contradicted"] == 3
    assert len(report["semantic_flags"]) == 9
    assert {item["issue"] for item in report["semantic_flags"]} == {
        "open_or_contradicted_value_not_null", "known_consent_not_boolean"
    }
    inconsistent = [row["task_id"] for row in report["tasks"]
                    if not row["impacting_irreversible_name_sets_match"]]
    assert inconsistent == ["cand_it_017"]


def test_report_does_not_overclaim_static_construct_validity() -> None:
    text = MODULE.markdown(MODULE.audit())
    assert "not statically established" in text
    assert "not automatic invalidity" in text
    assert "neither proof of semantic duplication nor evidence of independence" in text
    assert "No agreement or frozen-test claim is warranted" in text
