#!/usr/bin/env python3
"""Fail-closed static preflight for confirmatory v2; performs no network calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from handoffbench.dataset import load_tasks


ROOT = Path(__file__).resolve().parents[1]


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(16 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def config_design(config: dict[str, Any]) -> dict[str, Any]:
    excluded = {"execution_authorized", "status", "sealed_manifest", "annotation_agreement",
                "final_audit_file", "model_snapshot_manifest", "project_root"}
    return {key: value for key, value in config.items() if key not in excluded}


def model_inventory(model: dict[str, Any]) -> dict[str, Any]:
    directory = Path(model["local_path"])
    files = []
    for path in sorted(path for path in directory.rglob("*")
                       if path.is_file() and ".cache" not in path.relative_to(directory).parts):
        files.append({"path": path.relative_to(directory).as_posix(), "size": path.stat().st_size,
                      "sha256": file_sha(path)})
    summary = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"files": files, "file_count": len(files), "total_size": sum(x["size"] for x in files),
            "directory_summary_sha256": summary}


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def episode_schema_path(config: dict[str, Any], base: Path) -> Path:
    if config.get("episode_schema"):
        return resolve(base, config["episode_schema"])
    matches = [value for value in config.get("protocol_files", [])
               if Path(value).name == "episode.schema.json"]
    if len(matches) != 1:
        raise ValueError("protocol_files must contain exactly one episode.schema.json")
    return resolve(base, matches[0])


def candidate_inventory(
    base: Path, paths: list[str], schema_path: Path | None = None,
) -> tuple[list[dict], dict[str, str]]:
    tasks, file_hashes = [], {}
    schema_path = schema_path or base / "data/schemas/episode.schema.json"
    for value in paths:
        path = resolve(base, value)
        load_tasks(path, schema_path=schema_path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"{path}: expected task array")
        tasks.extend(raw)
        file_hashes[value] = hashlib.sha256(path.read_bytes()).hexdigest()
    return tasks, file_hashes


def models_resolved_and_distinct(models: list[dict[str, Any]]) -> bool:
    """Require independent, immutable identities for every confirmatory model."""
    if len(models) < 2:
        return False
    providers = [model.get("provider") for model in models]
    if not all(isinstance(value, str) and value.strip()
               and value.strip().lower() != "unresolved" for value in providers):
        return False
    for field in ("snapshot", "source_revision"):
        values = [model.get(field) for model in models]
        if not all(isinstance(value, str) and value.strip()
                   and value.strip().lower() != "unresolved"
                   and not value.strip().upper().startswith("UNRESOLVED")
                   for value in values):
            return False
        if len({value.strip() for value in values}) != len(values):
            return False
    return True


def final_audit_valid(
    audit: Any, *, n_tasks: int, domain_counts: dict[str, int], dataset_sha256: str,
) -> bool:
    """Check the semantic audit gates, not only the surrounding file digest."""
    if not isinstance(audit, dict):
        return False
    hard_checks = audit.get("hard_checks")
    summary = audit.get("summary")
    return (audit.get("status") == "pass_unsealed"
            and audit.get("model_calls") == 0
            and isinstance(hard_checks, dict) and bool(hard_checks)
            and all(value is True for value in hard_checks.values())
            and isinstance(summary, dict)
            and summary.get("tasks") == n_tasks
            and summary.get("domains") == domain_counts
            and ("canonical_dataset_sha256" not in audit
                 or audit.get("canonical_dataset_sha256") == dataset_sha256))


def preflight(config_path: Path) -> dict[str, Any]:
    # Repository-relative paths remain anchored at the project root even when
    # callers invoke this script from another working directory.
    config = yaml.safe_load(config_path.read_text())
    base = Path(config.get("project_root", ROOT))
    failures, checks = [], {}
    try:
        schema_path = episode_schema_path(config, base)
        tasks, file_hashes = candidate_inventory(base, config["candidate_files"], schema_path)
    except Exception as exc:
        return {"passed": False, "failures": [f"candidate inventory: {exc}"], "checks": {}}
    ids = [item["episode"]["task_id"] for item in tasks]
    families = [item["episode"].get("split_meta", {}).get("template_family") for item in tasks]
    domains = Counter(item["episode"].get("domain") for item in tasks)
    expected = config["expected_population"]
    inventory_ok = (len(tasks) == expected["families"] == len(set(ids)) == len(set(families))
                    and domains == Counter({domain: expected["families_per_domain"]
                                            for domain in expected["domains"]}))
    checks["candidate_population"] = inventory_ok
    if not inventory_ok:
        failures.append(f"candidate population mismatch: tasks={len(tasks)}, unique_ids={len(set(ids))}, "
                        f"unique_families={len(set(families))}, domains={dict(domains)}")
    canonical_dataset_sha256 = sha(tasks)
    domain_counts = dict(sorted(domains.items()))

    manifest_path = resolve(base, config["sealed_manifest"])
    manifest = None
    if not manifest_path.exists():
        failures.append(f"sealed manifest missing: {manifest_path}")
        checks["sealed_manifest"] = False
    else:
        try:
            manifest = json.loads(manifest_path.read_text())
            expected_hashes = {item["episode"]["task_id"]: sha(item) for item in tasks}
            protocol_hashes = {value: file_sha(resolve(base, value))
                               for value in config.get("protocol_files", [])}
            preregistration = resolve(base, config["preregistration"])
            snapshot_manifest = resolve(base, config["model_snapshot_manifest"])
            design_matrix = resolve(base, config["design_matrix"])
            agreement_path = resolve(base, config["annotation_agreement"])
            final_audit_path = resolve(base, config["final_audit_file"])
            final_audit = json.loads(final_audit_path.read_text(encoding="utf-8"))
            manifest_ok = (manifest.get("status") == "sealed"
                           and manifest.get("sealed") is True
                           and manifest.get("manifest_version") == "handoffbench-freeze-v3"
                           and manifest.get("protocol") == config["protocol"]
                           and manifest.get("task_ids") == sorted(ids)
                           and manifest.get("task_hashes") == expected_hashes
                           and manifest.get("candidate_files") == config["candidate_files"]
                           and manifest.get("candidate_file_hashes") == file_hashes
                           and manifest.get("canonical_dataset_sha256") == canonical_dataset_sha256
                           and manifest.get("n_tasks") == len(tasks)
                           and manifest.get("n_independent_families") == len(set(families))
                           and manifest.get("domain_counts") == domain_counts
                           and bool(manifest.get("seal_id")) and bool(manifest.get("sealed_at"))
                           and manifest.get("annotation_agreement_file") == config["annotation_agreement"]
                           and manifest.get("annotation_agreement_sha256") == file_sha(agreement_path)
                           and manifest.get("final_audit_file") == config["final_audit_file"]
                           and manifest.get("final_audit_sha256") == file_sha(final_audit_path)
                           and final_audit_valid(final_audit, n_tasks=len(tasks),
                                                 domain_counts=domain_counts,
                                                 dataset_sha256=canonical_dataset_sha256)
                           and manifest.get("preregistration_file") == config["preregistration"]
                           and manifest.get("preregistration_sha256") == file_sha(preregistration)
                           and manifest.get("confirmatory_config_design_sha256") == sha(config_design(config))
                           and manifest.get("protocol_file_hashes") == protocol_hashes
                           and manifest.get("model_design_sha256") == sha(config["models"])
                           and manifest.get("model_snapshot_manifest") == config["model_snapshot_manifest"]
                           and manifest.get("model_snapshot_manifest_sha256") == file_sha(snapshot_manifest)
                           and manifest.get("design_matrix") == config["design_matrix"]
                           and manifest.get("design_matrix_sha256") == file_sha(design_matrix))
            checks["sealed_manifest"] = manifest_ok
            if not manifest_ok:
                failures.append("sealed manifest does not exactly bind protocol/tasks/files")
        except Exception as exc:
            checks["sealed_manifest"] = False
            failures.append(f"sealed manifest invalid: {exc}")

    agreement_path = resolve(base, config["annotation_agreement"])
    if not agreement_path.exists():
        failures.append(f"human agreement artifact missing: {agreement_path}")
        checks["human_agreement"] = False
    else:
        try:
            agreement = json.loads(agreement_path.read_text())
            final_audit_path = resolve(base, config["final_audit_file"])
            final_audit = json.loads(final_audit_path.read_text(encoding="utf-8"))
            agreement_ok = (agreement.get("status") == "complete"
                            and agreement.get("protocol") == config["protocol"]
                            and agreement.get("annotators_per_task", 0) >= 2
                            and agreement.get("double_annotated_tasks") == len(tasks)
                            and agreement.get("adjudication_complete") is True
                            and agreement.get("agreement_gate_passed") is True
                            and agreement.get("accepted_task_ids") == sorted(ids)
                            and agreement.get("canonical_dataset_sha256") == canonical_dataset_sha256
                            and agreement.get("n_tasks") == len(tasks)
                            and agreement.get("n_independent_families") == len(set(families))
                            and agreement.get("domain_counts") == domain_counts
                            and agreement.get("candidate_files") == config["candidate_files"]
                            and agreement.get("final_audit_file") == config["final_audit_file"]
                            and agreement.get("final_audit_sha256") == file_sha(final_audit_path)
                            and final_audit_valid(final_audit, n_tasks=len(tasks),
                                                  domain_counts=domain_counts,
                                                  dataset_sha256=canonical_dataset_sha256)
                            and manifest is not None
                            and agreement.get("seal_id") == manifest.get("seal_id")
                            and manifest.get("annotation_agreement_file") == config["annotation_agreement"]
                            and manifest.get("annotation_agreement_sha256") == file_sha(agreement_path))
            checks["human_agreement"] = agreement_ok
            if not agreement_ok:
                failures.append("human agreement/adjudication gate incomplete or not bound to seal")
        except Exception as exc:
            checks["human_agreement"] = False
            failures.append(f"human agreement artifact invalid: {exc}")

    models = config.get("models", [])
    models_ok = models_resolved_and_distinct(models)
    checks["resolved_model_snapshots"] = models_ok
    if not models_ok:
        failures.append("at least two models with non-empty providers and distinct snapshots/source revisions are required")
    snapshot_path = resolve(base, config.get("model_snapshot_manifest", ""))
    snapshot_ok = False
    if not checks.get("sealed_manifest") or not checks.get("human_agreement"):
        failures.append("model snapshot file hashing deferred until seal/agreement gates pass")
    elif not models_ok or not snapshot_path.is_file():
        failures.append(f"model snapshot manifest missing or models unresolved: {snapshot_path}")
    else:
        try:
            snapshot_manifest = json.loads(snapshot_path.read_text())
            recorded_items = snapshot_manifest.get("models", [])
            recorded = {item["snapshot"]: item for item in recorded_items}
            snapshot_ok = (len(recorded_items) == len(recorded) == len(models)
                           and set(recorded) == {model["snapshot"] for model in models})
            for model in config["models"]:
                current = model_inventory(model)
                expected_model = recorded.get(model["snapshot"], {})
                expected_files = [{key: item[key] for key in ("path", "size", "sha256")}
                                  for item in expected_model.get("files", [])]
                snapshot_ok &= current["files"] == expected_files
                snapshot_ok &= all(current[field] == expected_model.get(field)
                                   for field in ("file_count", "total_size", "directory_summary_sha256"))
                snapshot_ok &= all(expected_model.get(field) == model.get(field)
                                   for field in ("provider", "snapshot", "served_model_name",
                                                 "local_path", "source", "source_revision",
                                                 "license", "serving_args"))
            if not snapshot_ok:
                failures.append("model snapshot hash/config drift detected")
        except Exception as exc:
            failures.append(f"model snapshot verification failed: {exc}")
    checks["model_snapshot_hashes"] = bool(snapshot_ok)
    checks["execution_authorized"] = config.get("execution_authorized") is True
    if not checks["execution_authorized"]:
        failures.append("execution_authorized is false")
    return {"passed": not failures, "failures": failures, "checks": checks,
            "inventory": {"tasks": len(tasks), "domains": dict(domains)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/confirmatory_v2.yaml")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = preflight(args.config)
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.json_output:
        args.json_output.write_text(rendered + "\n")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
