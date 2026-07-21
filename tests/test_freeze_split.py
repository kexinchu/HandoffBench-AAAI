import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from handoffbench.runner import RunConfig
from handoffbench.transfer import TransferKind, factorial_cell


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
    factorial = [
        "free_form__absent__absent", "free_form__absent__executable",
        "free_form__trace_linked__absent", "free_form__trace_linked__executable",
        "typed__absent__absent", "typed__absent__executable",
        "typed__trace_linked__absent", "typed__trace_linked__executable",
    ]
    controls = ["full_history", "gold_oracle"]
    secondary = ["typed__trace_linked__executable__enforced"]
    matrix = tmp_path / "matrix.json"
    scheduled = controls + [f"{cell}__advisory" for cell in factorial] + secondary
    matrix.write_text(json.dumps({"conditions": scheduled}))
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
        "models": [{"snapshot": "a", "served_model_name": "model-a"},
                   {"snapshot": "b", "served_model_name": "model-b"}],
        "seeds": [101, 202],
        "generation": {"temperature": 0.7, "max_receiver_turns": 4,
                       "max_output_tokens": 1600},
        "conditions": {"controls": controls, "factorial": factorial,
                       "secondary_enforcement": secondary},
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
    design = first["confirmatory_design"]
    assert design["models"] == ["model-a", "model-b"]
    assert design["seeds"] == [101, 202]
    assert len(design["conditions"]) == 11
    assert design["conditions"][:2] == ["full_history", "gold_oracle"]
    assert all(value.endswith("__advisory") for value in design["conditions"][2:10])
    assert design["conditions"][-1] == "typed__trace_linked__executable__enforced"
    assert len(design["config_hashes"]) == 44
    expected_control = RunConfig(
        "model-a", TransferKind.FULL_HISTORY, temperature=0.7, seed=101,
        protocol_version="fixture-protocol", max_turns=4, max_output_tokens=1600,
    )
    assert design["config_hashes"]["model-a|101|full_history"] == expected_control.config_hash
    expected_enforced = RunConfig(
        "model-b", TransferKind.FACTORIAL, temperature=0.7, seed=202,
        protocol_version="fixture-protocol", max_turns=4, max_output_tokens=1600,
        enforce_action_gates=True,
        factorial_cell=factorial_cell("typed__trace_linked__executable"),
    )
    enforced_key = "model-b|202|typed__trace_linked__executable__enforced"
    assert design["config_hashes"][enforced_key] == expected_enforced.config_hash
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


def test_manifest_rejects_design_matrix_or_condition_drift(tmp_path):
    candidates, config_path, agreement, seal_id = fixture(tmp_path)
    config = yaml.safe_load(config_path.read_text())
    config["conditions"]["factorial"][0] = "not-a-factorial-cell"
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="complete 2x2x2 cube"):
        MODULE.build_manifest(candidates, config_path, agreement,
                              seal_id=seal_id, sealed_at="x")


def test_manifest_binds_superseded_dataset_seal_without_rewriting_agreement(tmp_path):
    candidates, config_path, agreement, dataset_seal_id = fixture(tmp_path)
    config = yaml.safe_load(config_path.read_text())
    agreement_value = json.loads(agreement.read_text())
    prior = tmp_path / "prior-seal.json"
    prior.write_text(json.dumps({
        "status": "sealed", "sealed": True, "seal_id": dataset_seal_id,
        "canonical_dataset_sha256": agreement_value["canonical_dataset_sha256"],
    }))
    config["dataset_seal_id"] = dataset_seal_id
    config["supersedes_manifest"] = {
        "path": prior.name,
        "reason": "execution contract correction before any confirmatory model call",
    }
    config_path.write_text(yaml.safe_dump(config))
    manifest = MODULE.build_manifest(
        candidates, config_path, agreement, seal_id="fixture-execution-seal",
        sealed_at="2099-01-01T00:00:00Z")
    assert manifest["seal_id"] == "fixture-execution-seal"
    assert manifest["dataset_seal_id"] == dataset_seal_id == agreement_value["seal_id"]
    assert manifest["supersedes_manifest"] == {
        "path": prior.name, "sha256": MODULE.digest_bytes(prior.read_bytes()),
        "reason": config["supersedes_manifest"]["reason"],
    }

    prior_value = json.loads(prior.read_text())
    prior_value["seal_id"] = "fixture-previous-execution-seal"
    prior_value["dataset_seal_id"] = dataset_seal_id
    prior.write_text(json.dumps(prior_value))
    chained = MODULE.build_manifest(
        candidates, config_path, agreement, seal_id="fixture-next-execution-seal",
        sealed_at="2099-01-02T00:00:00Z")
    assert chained["supersedes_manifest"]["sha256"] == \
        MODULE.digest_bytes(prior.read_bytes())

    prior_value["canonical_dataset_sha256"] = "0" * 64
    prior.write_text(json.dumps(prior_value))
    with pytest.raises(ValueError, match="matching sealed canonical dataset"):
        MODULE.build_manifest(candidates, config_path, agreement,
                              seal_id="fixture-execution-seal", sealed_at="x")
