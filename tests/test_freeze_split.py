import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml


PATH = Path(__file__).parents[1] / "scripts/freeze_split.py"
ROOT = PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("freeze_split", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = json.loads((ROOT / "data/tasks/dev/pilot.json").read_text())[:2]
    tasks = []
    for index, (task_id, domain, family) in enumerate(
            (("t1", "travel", "f1"), ("t2", "it", "f2"))):
        task = deepcopy(source[index])
        task["episode"]["task_id"] = task_id
        task["episode"]["domain"] = domain
        task["episode"]["split_meta"]["template_family"] = family
        tasks.append([task])
    candidates = []
    for index, value in enumerate(tasks):
        path = tmp_path / f"candidate-{index}.json"; path.write_text(json.dumps(value))
        candidates.append(path)
    prereg = tmp_path / "preregistration_v3.md"; prereg.write_text("locked")
    protocol = tmp_path / "prompts.py"; protocol.write_text("PROMPT = 'locked'")
    schema = ROOT / "data/schemas/episode.schema.json"
    matrix = tmp_path / "matrix.json"; matrix.write_text("{}")
    snapshots = tmp_path / "snapshots.json"; snapshots.write_text('{"models":[]}')
    flattened = [item for group in tasks for item in group]
    dataset_sha256 = MODULE.canonical_digest(flattened)
    final_audit = tmp_path / "final-audit.json"
    final_audit.write_text(json.dumps({
        "status": "pass_unsealed", "model_calls": 0,
        "hard_checks": {"schema_valid": True, "population_valid": True},
        "summary": {"tasks": 2, "domains": {"it": 1, "travel": 1}},
        "canonical_dataset_sha256": dataset_sha256,
    }))
    seal_id = "fixture-seal"
    agreement = tmp_path / "agreement.json"
    config = {
        "project_root": str(tmp_path), "protocol": "fixture-protocol",
        "candidate_files": [path.name for path in candidates],
        "preregistration": prereg.name, "protocol_files": [str(schema), protocol.name],
        "design_matrix": matrix.name, "model_snapshot_manifest": snapshots.name,
        "annotation_agreement": agreement.name, "final_audit_file": final_audit.name,
        "models": [{"snapshot": "a"}, {"snapshot": "b"}],
        "expected_population": {"families": 2, "domains": ["travel", "it"],
                                "families_per_domain": 1},
    }
    agreement.write_text(json.dumps({
        "status": "complete", "protocol": "fixture-protocol", "seal_id": seal_id,
        "annotators_per_task": 2, "double_annotated_tasks": 2,
        "adjudication_complete": True, "agreement_gate_passed": True,
        "accepted_task_ids": ["t1", "t2"],
        "canonical_dataset_sha256": dataset_sha256,
        "n_tasks": 2, "n_independent_families": 2,
        "domain_counts": {"it": 1, "travel": 1},
        "candidate_files": config["candidate_files"],
        "final_audit_file": final_audit.name,
        "final_audit_sha256": MODULE.digest_bytes(final_audit.read_bytes()),
    }))
    config_path = tmp_path / "config.yaml"; config_path.write_text(yaml.safe_dump(config))
    return candidates, config_path, agreement, seal_id


def test_multifile_manifest_is_deterministic_and_binds_complete_contract(tmp_path):
    candidates, config, agreement, seal_id = fixture(tmp_path)
    kwargs = {"seal_id": seal_id, "sealed_at": "2099-01-01T00:00:00Z"}
    first = MODULE.build_manifest(candidates, config, agreement, **kwargs)
    second = MODULE.build_manifest(candidates, config, agreement, **kwargs)
    assert first == second
    assert first["status"] == "sealed" and first["task_ids"] == ["t1", "t2"]
    assert first["manifest_version"] == "handoffbench-freeze-v3"
    assert first["n_tasks"] == first["n_independent_families"] == 2
    assert first["domain_counts"] == {"it": 1, "travel": 1}
    assert first["annotation_agreement_file"] == agreement.name
    assert set(first["candidate_file_hashes"]) == {path.name for path in candidates}
    for key in ("annotation_agreement_sha256", "preregistration_sha256",
                "confirmatory_config_design_sha256", "model_design_sha256",
                "model_snapshot_manifest_sha256", "design_matrix_sha256",
                "canonical_dataset_sha256", "final_audit_sha256"):
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


def test_manifest_rejects_schema_invalid_candidate_and_dataset_binding_drift(tmp_path):
    candidates, config, agreement, seal_id = fixture(tmp_path)
    invalid = json.loads(candidates[0].read_text())
    del invalid[0]["upstream_trace"]
    candidates[0].write_text(json.dumps(invalid))
    with pytest.raises(ValueError, match="fields must be exactly"):
        MODULE.build_manifest(candidates, config, agreement, seal_id=seal_id, sealed_at="x")

    candidates, config, agreement, seal_id = fixture(tmp_path / "binding-case")
    value = json.loads(agreement.read_text())
    value["canonical_dataset_sha256"] = "0" * 64
    agreement.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="not bound"):
        MODULE.build_manifest(candidates, config, agreement, seal_id=seal_id, sealed_at="x")


def test_manifest_requires_configured_agreement_path(tmp_path):
    candidates, config, agreement, seal_id = fixture(tmp_path)
    alternate = tmp_path / "alternate-agreement.json"
    alternate.write_bytes(agreement.read_bytes())
    with pytest.raises(ValueError, match="exactly match config"):
        MODULE.build_manifest(candidates, config, alternate, seal_id=seal_id, sealed_at="x")


@pytest.mark.parametrize(("field", "replacement"), [
    ("status", "fail"),
    ("hard_checks", {"schema_valid": True, "population_valid": False}),
    ("model_calls", 1),
    ("summary", {"tasks": 1, "domains": {"it": 1}}),
])
def test_manifest_rejects_failed_final_audit_content(tmp_path, field, replacement):
    candidates, config_path, agreement, seal_id = fixture(tmp_path)
    config = yaml.safe_load(config_path.read_text())
    audit_path = tmp_path / config["final_audit_file"]
    audit = json.loads(audit_path.read_text())
    audit[field] = replacement
    audit_path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="final audit did not pass"):
        MODULE.build_manifest(candidates, config_path, agreement,
                              seal_id=seal_id, sealed_at="x")
