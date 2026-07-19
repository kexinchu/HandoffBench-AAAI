import importlib.util
import json
from pathlib import Path

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


def test_repository_preflight_fails_closed_before_seal_and_agreement():
    result = module().preflight(CONFIG)
    assert not result["passed"]
    assert not result["checks"]["sealed_manifest"]
    assert not result["checks"]["human_agreement"]
    assert result["checks"]["resolved_model_snapshots"]
    # Hashing is intentionally deferred while seal/agreement gates are absent.
    # The production manifest exists, but execution remains closed.
    assert not result["checks"]["model_snapshot_hashes"]
    assert not result["checks"]["execution_authorized"]


def test_synthetic_sealed_fixture_passes_all_static_gates(tmp_path):
    preflight = module()
    freeze = freeze_module()
    config = yaml.safe_load(CONFIG.read_text())
    config["project_root"] = str(ROOT)
    models = []
    for label in ("a", "b"):
        directory = tmp_path / f"model-{label}"; directory.mkdir()
        (directory / "config.json").write_text("{}")
        (directory / "tokenizer.json").write_text(f'{{"model":"{label}"}}')
        (directory / "chat_template.jinja").write_text("{{ messages }}")
        (directory / "consolidated.safetensors").write_bytes(f"weights-{label}".encode())
        models.append({"provider": "fixture", "snapshot": f"fixture-model-{label}@sha256",
                       "served_model_name": f"fixture-{label}", "local_path": str(directory),
                       "source": None, "source_revision": None, "license": None,
                       "serving_args": ["--fixture"]})
    config["models"] = models
    config["execution_authorized"] = True
    tasks, file_hashes = preflight.candidate_inventory(ROOT, config["candidate_files"])
    ids = sorted(item["episode"]["task_id"] for item in tasks)
    seal_id = "synthetic-test-seal-not-production"
    agreement = {"status": "complete", "protocol": config["protocol"], "seal_id": seal_id,
                 "annotators_per_task": 2, "double_annotated_tasks": 200,
                 "adjudication_complete": True, "agreement_gate_passed": True,
                 "accepted_task_ids": ids}
    manifest_path, agreement_path = tmp_path / "sealed.json", tmp_path / "agreement.json"
    agreement_path.write_text(json.dumps(agreement))
    config["sealed_manifest"] = str(manifest_path)
    config["annotation_agreement"] = str(agreement_path)
    snapshots = []
    for model in models:
        inventory = preflight.model_inventory(model)
        snapshots.append(model | inventory)
    snapshot_path = tmp_path / "models.json"
    snapshot_path.write_text(json.dumps({"models": snapshots}))
    config["model_snapshot_manifest"] = str(snapshot_path)
    config_path = tmp_path / "config.yaml"; config_path.write_text(yaml.safe_dump(config))
    candidate_paths = [ROOT / value for value in config["candidate_files"]]
    manifest = freeze.build_manifest(
        candidate_paths, config_path, agreement_path, seal_id=seal_id,
        sealed_at="2099-01-01T00:00:00Z")
    manifest_path.write_text(json.dumps(manifest))
    result = preflight.preflight(config_path)
    assert result["passed"], result["failures"]
    assert all(result["checks"].values())

    # A one-byte drift must close the gate even though all human/seal checks pass.
    (Path(models[0]["local_path"]) / "config.json").write_text('{"drift":true}')
    drifted = preflight.preflight(config_path)
    assert not drifted["passed"]
    assert not drifted["checks"]["model_snapshot_hashes"]


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
