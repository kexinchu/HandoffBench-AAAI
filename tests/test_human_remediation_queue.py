import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_human_remediation_queue", ROOT / "scripts" / "build_human_remediation_queue.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_queue_covers_all_blind_packets_and_binds_hashes() -> None:
    payload = MODULE.build()
    assert payload["task_count"] == len(payload["items"]) == 200
    assert len({item["task_id"] for item in payload["items"]}) == 200
    assert payload["priority_counts"] == {"P0": 6, "P1": 83, "P2": 72, "P3": 39}
    assert payload["risk_counts"] == {
        "counterfactual_relevance_review": 200,
        "epistemic_semantics_review": 8,
        "impact_contract_review": 1,
        "interface_ordering_probe_hit": 69,
        "legal_policy_ambiguity_review": 63,
        "normalized_topology_review": 69,
    }
    assert Counter(item["domain"] for item in payload["items"]) == {
        "travel": 40, "commerce": 40, "procurement": 40, "it": 40, "scheduling": 40
    }
    for item in payload["items"]:
        packet = ROOT / item["packet"]
        assert packet.exists()
        assert item["packet_sha256"] == hashlib.sha256(packet.read_bytes()).hexdigest()
        assert item["coordinator_status"] == "unassigned"
        assert item["human_decision"] is None


def test_queue_omits_gold_evaluator_and_family_details() -> None:
    payload = MODULE.build()
    text = json.dumps(payload)
    for forbidden in (
        "gold_state", "template_family", "claim_key", "claim_id", "category_status",
        "success_predicate", "allowed_next_actions", "forbidden_next_actions",
        "expected_arguments", "critical_keys", "enum_position_pattern", "sequence_length",
    ):
        assert forbidden not in text
    construct = json.loads(MODULE.CONSTRUCT.read_text())
    assert not any(row["family"] in text for row in construct["tasks"])
    assert not any(flag["claim_key"] in text for flag in construct["semantic_flags"])
    allowed_fields = {
        "task_id", "domain", "packet", "packet_sha256", "priority", "risk_codes",
        "blind_review_operations", "coordinator_status", "human_decision",
    }
    assert all(set(item) == allowed_fields for item in payload["items"])


def test_risk_tags_are_aggregated_without_answers() -> None:
    payload = MODULE.build()
    construct = json.loads(MODULE.CONSTRUCT.read_text())
    by_id = {row["task_id"]: row for row in construct["tasks"]}
    for item in payload["items"]:
        row = by_id[item["task_id"]]
        assert ("legal_policy_ambiguity_review" in item["risk_codes"]) == (
            not row["unique_legal_terminal_sequence"]
        )
        assert len(item["risk_codes"]) == len(item["blind_review_operations"])
        assert all(operation in MODULE.OPERATIONS.values()
                   for operation in item["blind_review_operations"])


def test_queue_writer_refuses_to_overwrite(tmp_path: Path) -> None:
    paths = [tmp_path / f"queue.{suffix}" for suffix in ("json", "csv", "md")]
    paths[1].write_text("keep")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        MODULE.write_new(MODULE.build(), *paths)
    assert paths[1].read_text() == "keep"
