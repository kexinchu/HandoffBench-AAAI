import importlib.util
import json
from pathlib import Path

import pytest
import yaml


PATH = Path(__file__).parents[1] / "scripts/freeze_split.py"
SPEC = importlib.util.spec_from_file_location("freeze_split", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    tasks = [[{"episode": {"task_id": "t1", "domain": "travel",
                            "split_meta": {"template_family": "f1"}}}],
             [{"episode": {"task_id": "t2", "domain": "it",
                            "split_meta": {"template_family": "f2"}}}]]
    candidates = []
    for index, value in enumerate(tasks):
        path = tmp_path / f"candidate-{index}.json"; path.write_text(json.dumps(value))
        candidates.append(path)
    prereg = tmp_path / "preregistration_v3.md"; prereg.write_text("locked")
    protocol = tmp_path / "schema.json"; protocol.write_text("{}")
    matrix = tmp_path / "matrix.json"; matrix.write_text("{}")
    snapshots = tmp_path / "snapshots.json"; snapshots.write_text('{"models":[]}')
    seal_id = "fixture-seal"
    agreement = tmp_path / "agreement.json"
    agreement.write_text(json.dumps({
        "status": "complete", "protocol": "fixture-protocol", "seal_id": seal_id,
        "annotators_per_task": 2, "double_annotated_tasks": 2,
        "adjudication_complete": True, "agreement_gate_passed": True,
        "accepted_task_ids": ["t1", "t2"],
    }))
    config = {
        "project_root": str(tmp_path), "protocol": "fixture-protocol",
        "candidate_files": [path.name for path in candidates],
        "preregistration": prereg.name, "protocol_files": [protocol.name],
        "design_matrix": matrix.name, "model_snapshot_manifest": snapshots.name,
        "models": [{"snapshot": "a"}, {"snapshot": "b"}],
        "expected_population": {"families": 2, "domains": ["travel", "it"],
                                "families_per_domain": 1},
    }
    config_path = tmp_path / "config.yaml"; config_path.write_text(yaml.safe_dump(config))
    return candidates, config_path, agreement, seal_id


def test_multifile_manifest_is_deterministic_and_binds_complete_contract(tmp_path):
    candidates, config, agreement, seal_id = fixture(tmp_path)
    kwargs = {"seal_id": seal_id, "sealed_at": "2099-01-01T00:00:00Z"}
    first = MODULE.build_manifest(candidates, config, agreement, **kwargs)
    second = MODULE.build_manifest(candidates, config, agreement, **kwargs)
    assert first == second
    assert first["status"] == "sealed" and first["task_ids"] == ["t1", "t2"]
    assert set(first["candidate_file_hashes"]) == {path.name for path in candidates}
    for key in ("annotation_agreement_sha256", "preregistration_sha256",
                "confirmatory_config_design_sha256", "model_design_sha256",
                "model_snapshot_manifest_sha256", "design_matrix_sha256"):
        assert len(first[key]) == 64


def test_multifile_manifest_rejects_duplicate_family_and_incomplete_agreement(tmp_path):
    candidates, config, agreement, seal_id = fixture(tmp_path)
    second = json.loads(candidates[1].read_text())
    second[0]["episode"]["split_meta"]["template_family"] = "f1"
    candidates[1].write_text(json.dumps(second))
    with pytest.raises(ValueError, match="independent template_family"):
        MODULE.build_manifest(candidates, config, agreement, seal_id=seal_id, sealed_at="x")

    candidates, config, agreement, seal_id = fixture(tmp_path / "agreement-case")
    value = json.loads(agreement.read_text()); value["agreement_gate_passed"] = False
    agreement.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="agreement artifact"):
        MODULE.build_manifest(candidates, config, agreement, seal_id=seal_id, sealed_at="x")
