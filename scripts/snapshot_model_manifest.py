#!/usr/bin/env python3
"""Create or verify immutable local-model manifests without loading a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            value.update(chunk)
    return value.hexdigest()


def role(path: str) -> str:
    name = Path(path).name
    if name.endswith(".safetensors"):
        return "weight"
    if name in {"config.json", "generation_config.json", "params.json", "processor_config.json"}:
        return "config"
    if "tokenizer" in name or name in {"tekken.json", "merges.txt", "vocab.json"}:
        return "tokenizer"
    if "chat_template" in name or name == "SYSTEM_PROMPT.txt":
        return "chat_template"
    return "metadata"


def inventory(model: dict[str, Any]) -> dict[str, Any]:
    directory = Path(model["local_path"])
    if not directory.is_dir():
        raise ValueError(f"model directory missing: {directory}")
    paths = sorted(path for path in directory.rglob("*")
                   if path.is_file() and ".cache" not in path.relative_to(directory).parts)
    files = []
    for path in paths:
        relative = path.relative_to(directory).as_posix()
        files.append({"path": relative, "role": role(relative), "size": path.stat().st_size,
                      "sha256": file_sha256(path)})
    if not any(item["role"] == "weight" for item in files):
        raise ValueError(f"no weight file found in {directory}")
    summary_payload = [{key: item[key] for key in ("path", "size", "sha256")} for item in files]
    summary = hashlib.sha256(json.dumps(summary_payload, sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest()
    return {"provider": model["provider"], "snapshot": model["snapshot"],
            "served_model_name": model["served_model_name"],
            "local_path": str(directory), "source": model.get("source"),
            "source_revision": model.get("source_revision"), "license": model.get("license"),
            "serving_args": model.get("serving_args", []), "file_count": len(files),
            "total_size": sum(item["size"] for item in files),
            "directory_summary_sha256": summary, "files": files}


def create(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text())
    return {"schema_version": "handoffbench-model-snapshot-v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hash_algorithm": "sha256", "models": [inventory(model) for model in config["models"]]}


def verify(config_path: Path, manifest_path: Path) -> dict[str, Any]:
    expected = json.loads(manifest_path.read_text())
    config = yaml.safe_load(config_path.read_text())
    failures = []
    expected_by_snapshot = {model["snapshot"]: model for model in expected.get("models", [])}
    if set(expected_by_snapshot) != {model["snapshot"] for model in config["models"]}:
        failures.append("manifest snapshots differ from config")
    for model in config["models"]:
        recorded = expected_by_snapshot.get(model["snapshot"])
        if not recorded:
            continue
        try:
            current = inventory(model)
        except Exception as exc:
            failures.append(f"{model['snapshot']}: {exc}")
            continue
        for field in ("provider", "served_model_name", "local_path", "source", "source_revision", "license",
                      "serving_args", "file_count", "total_size", "directory_summary_sha256", "files"):
            if current.get(field) != recorded.get(field):
                failures.append(f"{model['snapshot']}: drift in {field}")
    return {"passed": not failures, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/confirmatory_v2.yaml")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if bool(args.output) == bool(args.verify):
        parser.error("provide exactly one of --output or --verify")
    if args.output:
        value = create(args.config); args.output.write_text(json.dumps(value, indent=2) + "\n")
        print(json.dumps({"written": str(args.output),
                          "models": [{"snapshot": x["snapshot"], "files": x["file_count"],
                                      "bytes": x["total_size"],
                                      "sha256": x["directory_summary_sha256"]}
                                     for x in value["models"]]}, indent=2))
        return 0
    value = verify(args.config, args.verify); print(json.dumps(value, indent=2))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
