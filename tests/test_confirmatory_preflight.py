import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/preflight_confirmatory.py"
FREEZE_SCRIPT = ROOT / "scripts/freeze_split.py"
CONFIG = ROOT / "configs/confirmatory_v2.yaml"


def module():
    spec = importlib.util.spec_from_file_location("confirmatory_preflight", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def freeze_module():
    spec = importlib.util.spec_from_file_location("freeze_split_e2e", FREEZE_SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def sealed_fixture(tmp_path, *, execution_authorized=True):
    preflight = module()
    freeze = freeze_module()
    config = yaml.safe_load(CONFIG.read_text())
    config["project_root"] = str(ROOT)
    models = []
    for index, label in enumerate(("a", "b")):
        directory = tmp_path / f"model-{label}"; directory.mkdir()
        (directory / "config.json").write_text("{}")
        (directory / "tokenizer.json").write_text(f'{{"model":"{label}"}}')
        (directory / "chat_template.jinja").write_text("{{ messages }}")
        (directory / "consolidated.safetensors").write_bytes(f"weights-{label}".encode())
        models.append({"provider": f"fixture_provider_{label}",
                       "snapshot": f"fixture-model-{label}@sha256",
                       "served_model_name": f"fixture-{label}", "local_path": str(directory),
                       "source": f"fixture/model-{label}", "source_revision": f"revision-{index}",
                       "license": "fixture-only", "serving_args": ["--fixture"]})
    config["models"] = models
    config["execution_authorized"] = execution_authorized
    tasks, _ = preflight.candidate_inventory(
        ROOT, config["candidate_files"], preflight.episode_schema_path(config, ROOT))
    ids = sorted(item["episode"]["task_id"] for item in tasks)
    families = {item["episode"]["split_meta"]["template_family"] for item in tasks}
    domains = dict(sorted(Counter(item["episode"]["domain"] for item in tasks).items()))
    seal_id = "synthetic-test-seal-not-production"
    manifest_path = tmp_path / "sealed.json"
    agreement_path = tmp_path / "agreement.json"
    final_audit_path = tmp_path / "final-audit.json"
    dataset_sha256 = preflight.sha(tasks)
    final_audit_path.write_text(json.dumps({
        "status": "pass_unsealed", "model_calls": 0,
        "hard_checks": {"schema_valid": True, "population_valid": True},
        "summary": {"tasks": len(tasks), "domains": domains},
        "canonical_dataset_sha256": dataset_sha256,
    }))
    config["sealed_manifest"] = str(manifest_path)
    config["annotation_agreement"] = str(agreement_path)
    config["final_audit_file"] = str(final_audit_path)
    agreement = {"status": "complete", "protocol": config["protocol"], "seal_id": seal_id,
                 "annotators_per_task": 2, "double_annotated_tasks": len(tasks),
                 "adjudication_complete": True, "agreement_gate_passed": True,
                 "accepted_task_ids": ids, "canonical_dataset_sha256": dataset_sha256,
                 "n_tasks": len(tasks), "n_independent_families": len(families),
                 "domain_counts": domains, "candidate_files": config["candidate_files"],
                 "final_audit_file": config["final_audit_file"],
                 "final_audit_sha256": preflight.file_sha(final_audit_path)}
    agreement_path.write_text(json.dumps(agreement))
    snapshots = []
    for model_value in models:
        inventory = preflight.model_inventory(model_value)
        snapshots.append(model_value | inventory)
    snapshot_path = tmp_path / "models.json"
    snapshot_path.write_text(json.dumps({"models": snapshots}))
    config["model_snapshot_manifest"] = str(snapshot_path)
    config_path = tmp_path / "config.yaml"; config_path.write_text(yaml.safe_dump(config))
    candidate_paths = [ROOT / value for value in config["candidate_files"]]
    manifest = freeze.build_manifest(
        candidate_paths, config_path, agreement_path, seal_id=seal_id,
        sealed_at="2099-01-01T00:00:00Z")
    manifest_path.write_text(json.dumps(manifest))
    return preflight, config_path, manifest_path, models


def test_repository_preflight_fails_closed_before_seal_and_agreement():
    result = module().preflight(CONFIG)
    assert not result["passed"]
    assert not result["checks"]["sealed_manifest"]
    assert not result["checks"]["human_agreement"]
    # Hashing is intentionally deferred while seal/agreement gates are absent.
    # The production manifest exists, but execution remains closed.
    assert not result["checks"]["model_snapshot_hashes"]
    assert not result["checks"]["execution_authorized"]


def test_synthetic_sealed_fixture_passes_all_static_gates(tmp_path):
    preflight, config_path, _, models = sealed_fixture(tmp_path)
    result = preflight.preflight(config_path)
    assert result["passed"], result["failures"]
    assert all(result["checks"].values())

    # A one-byte drift must close the gate even though all human/seal checks pass.
    (Path(models[0]["local_path"]) / "config.json").write_text('{"drift":true}')
    drifted = preflight.preflight(config_path)
    assert not drifted["passed"]
    assert not drifted["checks"]["model_snapshot_hashes"]


def test_authorization_false_is_the_only_failure_after_all_static_gates_pass(tmp_path):
    preflight, config_path, _, _ = sealed_fixture(tmp_path, execution_authorized=False)
    result = preflight.preflight(config_path)
    assert not result["passed"]
    assert result["failures"] == ["execution_authorized is false"]
    assert all(value for key, value in result["checks"].items()
               if key != "execution_authorized")


@pytest.mark.parametrize(("field", "replacement"), [
    ("canonical_dataset_sha256", "0" * 64),
    ("n_tasks", 199),
    ("n_independent_families", 199),
    ("domain_counts", {"travel": 200}),
    ("candidate_files", ["tampered.json"]),
    ("annotation_agreement_file", "tampered-agreement.json"),
])
def test_manifest_candidate_and_agreement_bindings_detect_tamper(tmp_path, field, replacement):
    preflight, config_path, manifest_path, _ = sealed_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest[field] = replacement
    manifest_path.write_text(json.dumps(manifest))
    result = preflight.preflight(config_path)
    assert not result["passed"]
    assert not result["checks"]["sealed_manifest"]


def test_model_identities_require_provider_and_distinct_immutable_revisions():
    check = module().models_resolved_and_distinct
    valid = [{"snapshot": "a@1", "provider": "local_vllm", "source_revision": "rev-a"},
             {"snapshot": "b@1", "provider": "local_vllm", "source_revision": "rev-b"}]
    assert check(valid)
    for field in ("snapshot", "source_revision"):
        duplicate = [dict(item) for item in valid]
        duplicate[1][field] = duplicate[0][field]
        assert not check(duplicate)
        missing = [dict(item) for item in valid]
        missing[1][field] = ""
        assert not check(missing)
    missing_provider = [dict(item) for item in valid]
    missing_provider[1]["provider"] = ""
    assert not check(missing_provider)


@pytest.mark.parametrize(("field", "replacement"), [
    ("status", "fail"),
    ("hard_checks", {"schema_valid": True, "population_valid": False}),
    ("model_calls", 1),
    ("summary", {"tasks": 199, "domains": {"travel": 200}}),
])
def test_preflight_rejects_failed_audit_even_when_outer_hashes_match(
        tmp_path, field, replacement):
    preflight, config_path, manifest_path, _ = sealed_fixture(tmp_path)
    config = yaml.safe_load(config_path.read_text())
    audit_path = Path(config["final_audit_file"])
    agreement_path = Path(config["annotation_agreement"])
    audit = json.loads(audit_path.read_text())
    audit[field] = replacement
    audit_path.write_text(json.dumps(audit))

    # Simulate an attacker updating every outer digest. Semantic validation
    # must still reject the content rather than relying only on hash drift.
    agreement = json.loads(agreement_path.read_text())
    agreement["final_audit_sha256"] = preflight.file_sha(audit_path)
    agreement_path.write_text(json.dumps(agreement))
    manifest = json.loads(manifest_path.read_text())
    manifest["final_audit_sha256"] = preflight.file_sha(audit_path)
    manifest["annotation_agreement_sha256"] = preflight.file_sha(agreement_path)
    manifest_path.write_text(json.dumps(manifest))

    result = preflight.preflight(config_path)
    assert not result["passed"]
    assert not result["checks"]["sealed_manifest"]
    assert not result["checks"]["human_agreement"]


def test_tampered_manifest_or_incomplete_agreement_fails(tmp_path):
    preflight = module()
    config = yaml.safe_load(CONFIG.read_text())
    config["project_root"] = str(ROOT)
    config["models"] = [{"provider": "x", "snapshot": "x@1"},
                        {"provider": "y", "snapshot": "y@1"}]
    config["execution_authorized"] = True
    bad_manifest = tmp_path / "bad.json"; bad_manifest.write_text(json.dumps({"status": "sealed"}))
    bad_agreement = tmp_path / "bad-agreement.json"
    bad_agreement.write_text(json.dumps({"status": "incomplete"}))
    config["sealed_manifest"] = str(bad_manifest); config["annotation_agreement"] = str(bad_agreement)
    config_path = tmp_path / "config.yaml"; config_path.write_text(yaml.safe_dump(config))
    result = preflight.preflight(config_path)
    assert not result["passed"]
    assert not result["checks"]["sealed_manifest"]
    assert not result["checks"]["human_agreement"]
