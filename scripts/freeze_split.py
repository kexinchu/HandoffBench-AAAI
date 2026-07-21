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

from handoffbench.dataset import load_tasks
from handoffbench.runner import RunConfig
from handoffbench.transfer import FACTORIAL_CELLS, TransferKind, factorial_cell


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
                "final_audit_file", "model_snapshot_manifest", "project_root"}
    return {key: value for key, value in config.items() if key not in excluded}


def episode_schema_path(config: dict[str, Any], base: Path) -> Path:
    """Resolve the episode schema that is itself part of the locked protocol."""
    if config.get("episode_schema"):
        return resolve(base, config["episode_schema"])
    matches = [value for value in config.get("protocol_files", [])
               if Path(value).name == "episode.schema.json"]
    if len(matches) != 1:
        raise ValueError("protocol_files must contain exactly one episode.schema.json")
    return resolve(base, matches[0])


def validate_final_audit(
    audit: Any, *, n_tasks: int, domain_counts: dict[str, int], dataset_sha256: str,
) -> None:
    """Reject a structurally valid audit file unless every sealing gate passed."""
    if not isinstance(audit, dict):
        raise ValueError("final audit must be a JSON object")
    hard_checks = audit.get("hard_checks")
    summary = audit.get("summary")
    valid = (audit.get("status") == "pass_unsealed"
             and audit.get("model_calls") == 0
             and isinstance(hard_checks, dict) and bool(hard_checks)
             and all(value is True for value in hard_checks.values())
             and isinstance(summary, dict)
             and summary.get("tasks") == n_tasks
             and summary.get("domains") == domain_counts
             and ("canonical_dataset_sha256" not in audit
                  or audit.get("canonical_dataset_sha256") == dataset_sha256))
    if not valid:
        raise ValueError("final audit did not pass all unsealed, zero-model-call dataset checks")


def confirmatory_design(config: dict[str, Any], base: Path) -> dict[str, Any]:
    """Construct the exact scheduled design using the runner's hash contract."""
    models = [model.get("served_model_name") for model in config.get("models", [])]
    if len(models) < 2 or not all(isinstance(model, str) and model.strip() for model in models) \
            or len(set(models)) != len(models):
        raise ValueError("confirmatory models require unique non-empty served_model_name values")
    seeds = config.get("seeds")
    if (not isinstance(seeds, list) or not seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError("confirmatory seeds must be a non-empty list of unique integers")
    condition_config = config.get("conditions")
    if not isinstance(condition_config, dict) or set(condition_config) != {
            "controls", "factorial", "secondary_enforcement"}:
        raise ValueError("confirmatory conditions must define exactly three scheduled groups")
    controls = condition_config["controls"]
    factorial = condition_config["factorial"]
    secondary = condition_config["secondary_enforcement"]
    if controls != ["full_history", "gold_oracle"]:
        raise ValueError("confirmatory controls must be exactly full_history and gold_oracle")
    if (not isinstance(factorial, list) or len(factorial) != 8
            or len(set(factorial)) != 8 or set(factorial) != set(FACTORIAL_CELLS)):
        raise ValueError("confirmatory factorial conditions must be the complete 2x2x2 cube")
    if secondary != ["typed__trace_linked__executable__enforced"]:
        raise ValueError("confirmatory design requires exactly the registered enforcement arm")
    conditions = controls + [f"{cell}__advisory" for cell in factorial] + secondary
    if len(conditions) != 11 or len(set(conditions)) != 11:
        raise ValueError("confirmatory execution design must contain exactly 11 unique conditions")
    matrix = json.loads(resolve(base, config["design_matrix"]).read_text(encoding="utf-8"))
    if not isinstance(matrix, dict) or matrix.get("conditions") != conditions:
        raise ValueError("scheduled conditions must exactly match the locked design matrix labels")

    generation = config.get("generation", {})
    required_generation = {"temperature", "max_receiver_turns", "max_output_tokens"}
    if not required_generation <= set(generation):
        raise ValueError("generation config lacks RunConfig execution fields")
    hashes: dict[str, str] = {}
    for model in models:
        for seed in seeds:
            for condition in conditions:
                if condition in controls:
                    kind = TransferKind(condition)
                    cell = None
                    enforced = False
                else:
                    cell_label, enforcement = condition.rsplit("__", 1)
                    kind = TransferKind.FACTORIAL
                    cell = factorial_cell(cell_label)
                    enforced = enforcement == "enforced"
                run_config = RunConfig(
                    model=model, transfer_kind=kind,
                    temperature=generation["temperature"], seed=seed,
                    protocol_version=config["protocol"],
                    max_turns=generation["max_receiver_turns"],
                    max_output_tokens=generation["max_output_tokens"],
                    enforce_action_gates=enforced, factorial_cell=cell,
                )
                hashes[f"{model}|{seed}|{condition}"] = run_config.config_hash
    return {"models": models, "seeds": seeds, "conditions": conditions,
            "config_hashes": hashes}


def supersedes_binding(
    config: dict[str, Any], base: Path, *, dataset_seal_id: str, dataset_sha256: str,
) -> dict[str, str] | None:
    """Content-address the prior data seal when issuing a corrected execution seal."""
    value = config.get("supersedes_manifest")
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"path", "reason"}:
        raise ValueError("supersedes_manifest config requires exactly path and reason")
    if not all(isinstance(value.get(key), str) and value[key].strip()
               for key in ("path", "reason")):
        raise ValueError("supersedes_manifest path/reason must be non-empty strings")
    path = resolve(base, value["path"])
    prior = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(prior, dict) or prior.get("sealed") is not True
            or prior.get("dataset_seal_id", prior.get("seal_id")) != dataset_seal_id
            or prior.get("canonical_dataset_sha256") != dataset_sha256):
        raise ValueError("superseded manifest must be the matching sealed canonical dataset")
    return {"path": value["path"], "sha256": digest_bytes(path.read_bytes()),
            "reason": value["reason"]}


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
    configured_agreement = resolve(base, config["annotation_agreement"]).resolve()
    if agreement_file.resolve() != configured_agreement:
        raise ValueError("agreement file must exactly match config annotation_agreement")
    schema_path = episode_schema_path(config, base)
    tasks: list[dict[str, Any]] = []
    candidate_hashes: dict[str, str] = {}
    for configured_name, path in zip(config["candidate_files"], supplied):
        # This validates the complete record with JSON Schema, Pydantic, and the
        # cross-field invariants in handoffbench.dataset.  Raw JSON remains the
        # canonical serialized object hashed below.
        load_tasks(path, schema_path=schema_path)
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
    dataset_sha256 = canonical_digest(tasks)
    domains = Counter(task["episode"]["domain"] for task in tasks)
    domain_counts = dict(sorted(domains.items()))
    expected = config["expected_population"]
    if (len(tasks) != expected["families"] or domains != Counter(
            {domain: expected["families_per_domain"] for domain in expected["domains"]})):
        raise ValueError("candidate population does not match configured confirmatory population")

    final_audit_path = resolve(base, config["final_audit_file"])
    # Parsing catches accidental Markdown/placeholders while the byte digest
    # binds the exact audited artifact.
    final_audit = json.loads(final_audit_path.read_text(encoding="utf-8"))
    validate_final_audit(final_audit, n_tasks=len(tasks), domain_counts=domain_counts,
                         dataset_sha256=dataset_sha256)
    final_audit_sha256 = digest_bytes(final_audit_path.read_bytes())
    agreement = json.loads(agreement_file.read_text(encoding="utf-8"))
    dataset_seal_id = config.get("dataset_seal_id", seal_id)
    if not isinstance(dataset_seal_id, str) or not dataset_seal_id.strip():
        raise ValueError("dataset_seal_id must be a non-empty string")
    if (agreement.get("status") != "complete" or agreement.get("protocol") != config["protocol"]
            or agreement.get("seal_id") != dataset_seal_id
            or agreement.get("accepted_task_ids") != sorted(ids)
            or agreement.get("double_annotated_tasks") != len(tasks)
            or agreement.get("annotators_per_task", 0) < 2
            or agreement.get("adjudication_complete") is not True
            or agreement.get("agreement_gate_passed") is not True
            or agreement.get("canonical_dataset_sha256") != dataset_sha256
            or agreement.get("n_tasks") != len(tasks)
            or agreement.get("n_independent_families") != len(set(families))
            or agreement.get("domain_counts") != domain_counts
            or agreement.get("candidate_files") != config["candidate_files"]
            or agreement.get("final_audit_file") != config["final_audit_file"]
            or agreement.get("final_audit_sha256") != final_audit_sha256):
        raise ValueError("agreement artifact is incomplete or not bound to tasks/protocol/seal")
    protocol_hashes = {}
    for value in config.get("protocol_files", []):
        path = resolve(base, value)
        protocol_hashes[value] = digest_bytes(path.read_bytes())
    preregistration = resolve(base, config["preregistration"])
    snapshot_manifest = resolve(base, config["model_snapshot_manifest"])
    design_matrix = resolve(base, config["design_matrix"])
    execution_design = confirmatory_design(config, base)
    supersedes = supersedes_binding(config, base, dataset_seal_id=dataset_seal_id,
                                    dataset_sha256=dataset_sha256)
    return {
        "status": "sealed", "sealed": True,
        "manifest_version": "handoffbench-freeze-v3",
        "protocol": config["protocol"], "seal_id": seal_id,
        "dataset_seal_id": dataset_seal_id, "sealed_at": sealed_at,
        "task_ids": sorted(ids),
        "task_hashes": {task["episode"]["task_id"]: canonical_digest(task) for task in tasks},
        "candidate_files": config["candidate_files"],
        "candidate_file_hashes": candidate_hashes,
        "canonical_dataset_sha256": dataset_sha256,
        "n_tasks": len(tasks), "n_independent_families": len(set(families)),
        "domain_counts": domain_counts,
        "annotation_agreement_file": config["annotation_agreement"],
        "annotation_agreement_sha256": digest_bytes(agreement_file.read_bytes()),
        "final_audit_file": config["final_audit_file"],
        "final_audit_sha256": final_audit_sha256,
        "preregistration_file": config["preregistration"],
        "preregistration_sha256": digest_bytes(preregistration.read_bytes()),
        "confirmatory_config_design_sha256": canonical_digest(config_design(config)),
        "protocol_file_hashes": protocol_hashes,
        "model_design_sha256": canonical_digest(config["models"]),
        "model_snapshot_manifest": config["model_snapshot_manifest"],
        "model_snapshot_manifest_sha256": digest_bytes(snapshot_manifest.read_bytes()),
        "design_matrix": config["design_matrix"],
        "design_matrix_sha256": digest_bytes(design_matrix.read_bytes()),
        "confirmatory_design": execution_design,
        "supersedes_manifest": supersedes,
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
