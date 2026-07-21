import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "snapshot_model_manifest", ROOT / "scripts/snapshot_model_manifest.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_snapshot_manifest_binds_provider_used_by_preflight(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "weights.safetensors").write_bytes(b"fixture")
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"models": [{
        "provider": "local_vllm",
        "snapshot": "fixture@1",
        "served_model_name": "fixture",
        "local_path": str(model_dir),
        "source": "fixture/source",
        "source_revision": "revision-1",
        "license": "apache-2.0",
        "serving_args": ["--fixture"],
    }]}))
    manifest = MODULE.create(config)
    assert manifest["models"][0]["provider"] == "local_vllm"
