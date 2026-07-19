import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
PACKETS = ROOT / "data" / "annotations" / "candidate_packets_v1"
OUTPUT = ROOT / "data" / "annotations" / "assignments_v1"
SCRIPT = ROOT / "scripts" / "generate_annotation_assignments.py"
SPEC = importlib.util.spec_from_file_location("generate_annotation_assignments", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def generated():
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    a = json.loads((OUTPUT / "annotator_a.json").read_text(encoding="utf-8"))["assignments"]
    b = json.loads((OUTPUT / "annotator_b.json").read_text(encoding="utf-8"))["assignments"]
    return manifest, a, b


def test_two_independent_annotators_each_cover_all_120_packets_once() -> None:
    manifest, a, b = generated()
    packet_ids = {path.stem for path in PACKETS.glob("cand_*.json")}
    assert len(packet_ids) == manifest["packet_count"] == 120
    assert len(a) == len(b) == 120
    assert {row["task_id"] for row in a} == packet_ids
    assert {row["task_id"] for row in b} == packet_ids
    assert len({row["task_id"] for row in a}) == len(a)
    assert len({row["task_id"] for row in b}) == len(b)
    assert [row["task_id"] for row in a] != [row["task_id"] for row in b]
    assert {row["assignment_id"] for row in a}.isdisjoint(
        {row["assignment_id"] for row in b}
    )


def test_assignments_are_blank_blinded_and_contain_no_evaluator_labels() -> None:
    manifest, a, b = generated()
    assert all(row["response"] is None for row in a + b)
    assert manifest["adjudication"]["mode"] == "disagreements_only"
    assert manifest["adjudication"]["preassigned_tasks"] == []
    forbidden = {
        "gold_state", "critical_keys", "allowed_next_actions", "forbidden_next_actions",
        "success_predicate", "scoring", "template_family", "expected_arguments",
    }
    serialized = json.dumps({"manifest": manifest, "a": a, "b": b})
    assert not any(label in serialized for label in forbidden)


def test_manifest_is_reproducible_and_packet_hashes_are_bound() -> None:
    expected_manifest, expected = MODULE.build_assignments(PACKETS, seed=20270117)
    manifest, a, b = generated()
    assert manifest == expected_manifest
    assert a == expected["annotator_a"]
    assert b == expected["annotator_b"]
    for row in a + b:
        digest = __import__("hashlib").sha256((PACKETS / row["packet"]).read_bytes()).hexdigest()
        assert row["packet_sha256"] == digest


def test_generator_refuses_to_overwrite_any_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "annotator_a.json"
    sentinel.write_text("do not replace", encoding="utf-8")
    manifest, assignments = MODULE.build_assignments(PACKETS, seed=1)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        MODULE.write_new(output, manifest, assignments)
    assert sentinel.read_text(encoding="utf-8") == "do not replace"
