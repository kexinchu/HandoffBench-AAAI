#!/usr/bin/env python3
"""Seal multiple accepted candidate files against the complete confirmatory contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return digest_bytes(raw.encode())


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def config_design(config: dict[str, Any]) -> dict[str, Any]:
    """Return execution design fields; mutable authorization/output paths are excluded."""
    excluded = {"execution_authorized", "status", "sealed_manifest", "annotation_agreement",
                "model_snapshot_manifest", "project_root"}
    return {key: value for key, value in config.items() if key not in excluded}


def build_manifest(
    candidate_files: list[Path], config_path: Path, agreement_file: Path, *,
    seal_id: str, sealed_at: str,
) -> dict[str, Any]:
    if not seal_id.strip() or not sealed_at.strip():
        raise ValueError("seal_id and sealed_at must be explicit non-empty values")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    base = Path(config.get("project_root", ROOT))
    configured = [resolve(base, value).resolve() for value in config["candidate_files"]]
    supplied = [path.resolve() for path in candidate_files]
    if supplied != configured:
        raise ValueError("candidate files must exactly match config order and paths")
    tasks: list[dict[str, Any]] = []
    candidate_hashes: dict[str, str] = {}
    for configured_name, path in zip(config["candidate_files"], supplied):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or not value:
            raise ValueError(f"candidate file must contain a non-empty JSON array: {path}")
        tasks.extend(value)
        candidate_hashes[configured_name] = digest_bytes(path.read_bytes())
    ids = [task["episode"]["task_id"] for task in tasks]
    families = [task["episode"]["split_meta"]["template_family"] for task in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError("task ids must be unique across all candidate files")
    if len(set(families)) != len(families):
        raise ValueError("confirmatory split requires one independent template_family per task")
    agreement = json.loads(agreement_file.read_text(encoding="utf-8"))
    if (agreement.get("status") != "complete" or agreement.get("protocol") != config["protocol"]
            or agreement.get("seal_id") != seal_id
            or agreement.get("accepted_task_ids") != sorted(ids)
            or agreement.get("double_annotated_tasks") != len(tasks)
            or agreement.get("annotators_per_task", 0) < 2
            or agreement.get("adjudication_complete") is not True
            or agreement.get("agreement_gate_passed") is not True):
        raise ValueError("agreement artifact is incomplete or not bound to tasks/protocol/seal")
    protocol_hashes = {}
    for value in config.get("protocol_files", []):
        path = resolve(base, value)
        protocol_hashes[value] = digest_bytes(path.read_bytes())
    preregistration = resolve(base, config["preregistration"])
    snapshot_manifest = resolve(base, config["model_snapshot_manifest"])
    design_matrix = resolve(base, config["design_matrix"])
    expected = config["expected_population"]
    domains = Counter(task["episode"]["domain"] for task in tasks)
    if (len(tasks) != expected["families"] or domains != Counter(
            {domain: expected["families_per_domain"] for domain in expected["domains"]})):
        raise ValueError("candidate population does not match configured confirmatory population")
    return {
        "status": "sealed", "sealed": True,
        "manifest_version": "handoffbench-freeze-v2",
        "protocol": config["protocol"], "seal_id": seal_id, "sealed_at": sealed_at,
        "task_ids": sorted(ids),
        "task_hashes": {task["episode"]["task_id"]: canonical_digest(task) for task in tasks},
        "candidate_files": config["candidate_files"],
        "candidate_file_hashes": candidate_hashes,
        "canonical_dataset_sha256": canonical_digest(tasks),
        "n_tasks": len(tasks), "n_independent_families": len(set(families)),
        "domain_counts": dict(sorted(domains.items())),
        "annotation_agreement_file": str(agreement_file),
        "annotation_agreement_sha256": digest_bytes(agreement_file.read_bytes()),
        "preregistration_file": config["preregistration"],
        "preregistration_sha256": digest_bytes(preregistration.read_bytes()),
        "confirmatory_config_design_sha256": canonical_digest(config_design(config)),
        "protocol_file_hashes": protocol_hashes,
        "model_design_sha256": canonical_digest(config["models"]),
        "model_snapshot_manifest": config["model_snapshot_manifest"],
        "model_snapshot_manifest_sha256": digest_bytes(snapshot_manifest.read_bytes()),
        "design_matrix": config["design_matrix"],
        "design_matrix_sha256": digest_bytes(design_matrix.read_bytes()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-files", type=Path, nargs="+", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--agreement", type=Path, required=True)
    parser.add_argument("--seal-id", required=True)
    parser.add_argument("--sealed-at", required=True, help="locked UTC timestamp, e.g. 2027-01-01T00:00:00Z")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seal", action="store_true", help="required acknowledgement")
    args = parser.parse_args()
    if not args.seal:
        parser.error("--seal is required because a freeze manifest must not be overwritten")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite sealed manifest: {args.output}")
    manifest = build_manifest(args.candidate_files, args.config, args.agreement,
                              seal_id=args.seal_id, sealed_at=args.sealed_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest["canonical_dataset_sha256"])


if __name__ == "__main__":
    main()
