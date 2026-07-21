import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from handoffbench.annotation_agreement import load_locked_annotations


ROOT = Path(__file__).parents[1]
ASSIGNMENTS = ROOT / "data" / "annotations" / "assignments_v2"
BLANK = ROOT / "data" / "annotations" / "execution_v2_blank"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


PREPARE = module("prepare_annotation_execution", ROOT / "scripts" / "prepare_annotation_execution.py")
QUEUE = module("generate_disagreement_queue", ROOT / "scripts" / "generate_disagreement_queue.py")


def test_v2_blank_skeletons_cover_200_each_and_contain_no_gold() -> None:
    task_sets = []
    for annotator in ("annotator_a", "annotator_b"):
        payload = json.loads((BLANK / f"{annotator}_responses.blank.json").read_text())
        assert payload["status"] == "blank_unlocked"
        assert payload["annotator_id"] == annotator
        assert len(payload["annotations"]) == 200
        assert all(item["response"] is None and item["claims"] == [] for item in payload["annotations"])
        assert all(item["action_sequence"] is None for item in payload["annotations"])
        task_sets.append({item["task_id"] for item in payload["annotations"]})
        text = json.dumps(payload)
        for forbidden in ("gold_state", "allowed_next_actions", "forbidden_next_actions",
                          "success_predicate", "critical_keys", "template_family"):
            assert forbidden not in text
    assert task_sets[0] == task_sets[1] and len(task_sets[0]) == 200


def test_blank_and_unlocked_inputs_cannot_enter_agreement_analyzer() -> None:
    with pytest.raises(ValueError):
        load_locked_annotations(
            BLANK / "annotator_a_responses.blank.json",
            BLANK / "annotator_b_responses.blank.json",
            BLANK / "lock_manifest.template.json",
        )
    lock = json.loads((BLANK / "lock_manifest.template.json").read_text())
    assert lock["locked"] is False
    assert all(item["sha256"] is None and item["locked_at"] is None for item in lock["inputs"])


def test_preparation_and_queue_writers_refuse_overwrite(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "keep"; sentinel.write_text("locked")
    with pytest.raises(FileExistsError):
        PREPARE.write_new(existing, PREPARE.build(ASSIGNMENTS))
    assert sentinel.read_text() == "locked"
    output = tmp_path / "queue.json"; output.write_text("do not replace")
    with pytest.raises(FileExistsError):
        QUEUE.generate(Path("a"), Path("b"), Path("lock"), output)
    assert output.read_text() == "do not replace"


def test_preparation_supports_versioned_replacement_only_batches(tmp_path: Path) -> None:
    assignments = tmp_path / "assignments"
    assignments.mkdir()
    (assignments / "manifest.json").write_text(json.dumps({"packet_count": 2}))
    for annotator, task_ids in (("annotator_a", ["repl_1", "repl_2"]),
                                ("annotator_b", ["repl_2", "repl_1"])):
        rows = [{"task_id": task_id, "assignment_id": f"{annotator}-{task_id}",
                 "packet": f"{task_id}.json", "packet_sha256": "a" * 64}
                for task_id in task_ids]
        (assignments / f"{annotator}.json").write_text(json.dumps({"assignments": rows}))
    files = PREPARE.build(assignments)
    assert len(files["annotator_a_responses.blank.json"]["annotations"]) == 2
    assert files["lock_manifest.template.json"]["expected_task_ids"] == ["repl_1", "repl_2"]


def _completed(annotator, category, *, inferable=True, leakage=False):
    return {"annotator_id": annotator, "annotations": [{
        "task_id": "candidate_opaque_001",
        "claims": [{"key": "destination", "category": category, "status": "known",
                    "value": "Cambridge", "criticality": "terminal",
                    "provenance": [{"trace_id": "e1", "source_type": "user",
                                    "field_path": "content.destination"}]}],
        "action_sequence": [{"name": "act", "arguments": {"target": "x"}}],
        "irreversible_args_inferable": inferable,
        "catalog_leakage_flag": leakage,
    }]}


def test_disagreement_queue_requires_completed_locked_inputs_and_contains_only_disagreements(tmp_path: Path) -> None:
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    payloads = [_completed("annotator_a", "constraint"), _completed("annotator_b", "verified_fact")]
    for path, payload in zip(paths, payloads):
        path.write_text(json.dumps(payload))
    unlocked = tmp_path / "unlocked.json"
    unlocked.write_text(json.dumps({"locked": False, "inputs": []}))
    with pytest.raises(ValueError):
        QUEUE.generate(paths[0], paths[1], unlocked, tmp_path / "must_not_exist.json")
    assert not (tmp_path / "must_not_exist.json").exists()
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"locked": True, "expected_task_ids": ["candidate_opaque_001"],
                                "inputs": [{"path": str(path),
                                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                            "annotator_id": payload["annotator_id"]}
                                           for path, payload in zip(paths, payloads)]}))
    output = tmp_path / "queue.json"
    result = QUEUE.generate(paths[0], paths[1], lock, output)
    assert result["disagreements_only"] is True
    assert result["queue"] == [{"task_id": "candidate_opaque_001", "claim_key": "destination",
                                "fields": ["category"], "resolution_code": None}]


def test_disagreement_queue_includes_task_level_inferability_and_leakage(tmp_path: Path) -> None:
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    payloads = [_completed("annotator_a", "constraint", inferable=True, leakage=False),
                _completed("annotator_b", "constraint", inferable=False, leakage=True)]
    for path, payload in zip(paths, payloads):
        path.write_text(json.dumps(payload))
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"locked": True, "expected_task_ids": ["candidate_opaque_001"],
                                "inputs": [{"path": str(path),
                                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                            "annotator_id": payload["annotator_id"]}
                                           for path, payload in zip(paths, payloads)]}))
    result = QUEUE.generate(paths[0], paths[1], lock, tmp_path / "queue.json")
    assert result["queue"] == [
        {"task_id": "candidate_opaque_001", "claim_key": None,
         "fields": ["irreversible_args_inferable"], "resolution_code": None},
        {"task_id": "candidate_opaque_001", "claim_key": None,
         "fields": ["catalog_leakage_flag"], "resolution_code": None},
    ]
