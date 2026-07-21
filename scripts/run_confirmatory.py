#!/usr/bin/env python3
"""Fail-closed, resumable executor for the sealed HandoffBench confirmatory cube."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import preflight_confirmatory as preflight_cli  # noqa: E402
import run_pilot as pilot_cli  # noqa: E402
from handoffbench.dataset import load_tasks  # noqa: E402
from handoffbench.pilot_analysis import write_summary  # noqa: E402
from handoffbench.providers import OpenAICompatibleProvider  # noqa: E402
from handoffbench.runner import RunConfig  # noqa: E402
from handoffbench.transfer import TransferKind, factorial_cell  # noqa: E402


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(16 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def run_config_for(config: dict[str, Any], model: str, seed: int,
                   condition: str) -> RunConfig:
    controls = set(config["conditions"]["controls"])
    if condition in controls:
        kind = TransferKind(condition)
        cell = None
        enforced = False
    else:
        cell_label, enforcement = condition.rsplit("__", 1)
        kind = TransferKind.FACTORIAL
        cell = factorial_cell(cell_label)
        enforced = enforcement == "enforced"
    generation = config["generation"]
    return RunConfig(
        model=model, transfer_kind=kind,
        temperature=generation["temperature"], seed=seed,
        protocol_version=config["protocol"],
        max_turns=generation["max_receiver_turns"],
        max_output_tokens=generation["max_output_tokens"],
        enforce_action_gates=enforced, factorial_cell=cell,
    )


def load_records(config: dict[str, Any], base: Path) -> tuple[list[Any], dict[str, str]]:
    records: list[Any] = []
    sources: dict[str, str] = {}
    schema = preflight_cli.episode_schema_path(config, base)
    for value in config["candidate_files"]:
        path = resolve(base, value)
        loaded = load_tasks(path, schema_path=schema)
        for record in loaded:
            task_id = record.episode.task_id
            if task_id in sources:
                raise ValueError(f"duplicate task across candidate files: {task_id}")
            sources[task_id] = value
        records.extend(loaded)
    return records, sources


def validated_plan(config_path: Path, *, verify_preflight: bool = True) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("confirmatory config must be an object")
    base = Path(config.get("project_root", ROOT)).resolve()
    if verify_preflight:
        preflight = preflight_cli.preflight(config_path)
        if preflight.get("passed") is not True:
            raise ValueError(f"confirmatory preflight failed: {preflight.get('failures')}")
    else:
        preflight = {"passed": True, "test_bypass": True}

    manifest_path = resolve(base, config["sealed_manifest"]).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_design = preflight_cli.confirmatory_design(config, base)
    if manifest.get("confirmatory_design") != expected_design:
        raise ValueError("sealed manifest confirmatory design does not match config RunConfig hashes")
    records, task_sources = load_records(config, base)
    task_ids = [record.episode.task_id for record in records]
    if sorted(task_ids) != manifest.get("task_ids"):
        raise ValueError("candidate task IDs do not exactly match the sealed manifest")

    rows: list[dict[str, Any]] = []
    keys: set[tuple[str, str, int, str]] = set()
    for record in records:
        task_id = record.episode.task_id
        for model in expected_design["models"]:
            for seed in expected_design["seeds"]:
                for condition in expected_design["conditions"]:
                    run_config = run_config_for(config, model, seed, condition)
                    expected_hash = expected_design["config_hashes"].get(
                        f"{model}|{seed}|{condition}"
                    )
                    if run_config.config_hash != expected_hash:
                        raise ValueError(
                            f"RunConfig hash mismatch: {(model, seed, condition)}"
                        )
                    key = (task_id, model, int(seed), condition)
                    if key in keys:
                        raise ValueError(f"duplicate scheduled row: {key}")
                    keys.add(key)
                    rows.append({
                        "task_id": task_id, "candidate_file": task_sources[task_id],
                        "model": model, "seed": int(seed), "condition": condition,
                        "config_hash": run_config.config_hash,
                    })
    expected_rows = manifest["n_tasks"] * len(expected_design["models"]) * \
        len(expected_design["seeds"]) * len(expected_design["conditions"])
    if expected_rows != 8800 or len(rows) != expected_rows or len(keys) != expected_rows:
        raise ValueError(
            f"confirmatory schedule must contain exactly 8800 unique rows; got {len(rows)}"
        )
    return {
        "config": config, "base": base, "manifest": manifest,
        "manifest_path": manifest_path, "records": records, "rows": rows,
        "preflight": preflight, "design": expected_design,
        "hashes": {
            "config_sha256": file_sha256(config_path),
            "sealed_manifest_sha256": file_sha256(manifest_path),
            "canonical_dataset_sha256": manifest["canonical_dataset_sha256"],
            "design_matrix_sha256": manifest["design_matrix_sha256"],
            "confirmatory_config_design_sha256": manifest["confirmatory_config_design_sha256"],
        },
    }


def dry_run_payload(plan: dict[str, Any], selected_models: list[str] | None = None) -> dict[str, Any]:
    all_models = plan["design"]["models"]
    models = selected_models or all_models
    unknown = set(models) - set(all_models)
    if unknown:
        raise ValueError(f"unknown served model name(s): {sorted(unknown)}")
    if len(models) != len(set(models)):
        raise ValueError("selected served model names must be unique")
    rows = [row for row in plan["rows"] if row["model"] in models]
    return {
        "format": "handoffbench-confirmatory-dry-run-v1",
        "status": "validated_no_provider_calls",
        "seal_id": plan["manifest"]["seal_id"],
        "preflight": plan["preflight"], "hashes": plan["hashes"],
        "counts": {
            "all_scheduled_rows": len(plan["rows"]),
            "selected_scheduled_rows": len(rows),
            "unique_selected_rows": len({
                (row["task_id"], row["model"], row["seed"], row["condition"])
                for row in rows
            }),
            "tasks": plan["manifest"]["n_tasks"],
            "models": len(models), "seeds": len(plan["design"]["seeds"]),
            "conditions": len(plan["design"]["conditions"]),
        },
        "schedule": rows,
    }


def parse_base_urls(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--base-url must be SERVED_MODEL_NAME=URL")
        model, url = value.split("=", 1)
        if not model or not url or model in result:
            raise ValueError(f"invalid or duplicate --base-url mapping: {value}")
        result[model] = url.rstrip("/")
    return result


def configured_base_url(model: dict[str, Any]) -> str:
    args = model.get("serving_args")
    if not isinstance(args, list):
        raise ValueError(f"model {model.get('served_model_name')} lacks serving_args")
    try:
        host = args[args.index("--host") + 1]
        port = args[args.index("--port") + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError(
            f"model {model.get('served_model_name')} lacks configured host/port"
        ) from exc
    return f"http://{host}:{port}/v1"


def health_check(base_url: str, model: str, api_key: str,
                 timeout: float) -> dict[str, Any]:
    """Verify the exact served model before any candidate prompt is submitted."""
    endpoint = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(
        endpoint, headers={"Authorization": f"Bearer {api_key}"}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = getattr(response, "status", response.getcode())
            server = response.headers.get("Server")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise ValueError(f"provider health check failed for {model} at {endpoint}: {exc}") from exc
    if status < 200 or status >= 300:
        raise ValueError(f"provider health check returned HTTP {status} for {model}")
    try:
        payload = json.loads(raw)
        data = payload["data"]
        ids = [item["id"] for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"provider /models response is malformed for {model}") from exc
    if model not in ids:
        raise ValueError(f"served model {model!r} absent from {endpoint}; available={ids}")
    return {
        "endpoint": endpoint, "http_status": status, "served_model_ids": ids,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "server_header": server,
    }


def output_path(output_root: Path, row: dict[str, Any]) -> Path:
    return (output_root / row["model"] / "runs" / row["task_id"] /
            row["condition"] /
            f"seed-{row['seed']}-{row['config_hash'][:12]}.json")


def validate_existing(path: Path, row: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"existing scheduled record is unreadable: {path}: {exc}") from exc
    expected = {"task_id": row["task_id"], "model": row["model"],
                "seed": row["seed"], "method": row["condition"],
                "config_hash": row["config_hash"]}
    if not isinstance(value, dict) or any(value.get(key) != item for key, item in expected.items()):
        raise ValueError(f"existing scheduled record identity/hash mismatch: {path}")
    config = value.get("config")
    if not isinstance(config, dict) or canonical_hash(config) != row["config_hash"]:
        raise ValueError(f"existing scheduled record config content mismatch: {path}")
    metrics = value.get("metrics")
    if not isinstance(metrics, dict) or not all(key in metrics for key in (
            "input_tokens", "output_tokens", "validator_cost")):
        raise ValueError(f"existing scheduled record lacks required accounting: {path}")
    validator_cost = metrics["validator_cost"]
    if (not isinstance(validator_cost, (int, float)) or isinstance(validator_cost, bool)
            or not math.isfinite(float(validator_cost)) or validator_cost < 0):
        raise ValueError(f"existing scheduled record has invalid validator_cost: {path}")
    return value


def execute(plan: dict[str, Any], selected_models: list[str], output_root: Path,
            base_urls: dict[str, str], api_key: str, timeout: float, workers: int) -> dict[str, Any]:
    model_specs = {item["served_model_name"]: item for item in plan["config"]["models"]}
    unknown = set(selected_models) - set(model_specs)
    if unknown:
        raise ValueError(f"unknown served model name(s): {sorted(unknown)}")
    if len(selected_models) != len(set(selected_models)):
        raise ValueError("selected served model names must be unique")
    if any(Path(model).name != model for model in selected_models):
        raise ValueError("served model names must be safe single path components")
    unknown_urls = set(base_urls) - set(selected_models)
    if unknown_urls:
        raise ValueError(f"base URL supplied for an unselected model: {sorted(unknown_urls)}")
    records = {record.episode.task_id: record for record in plan["records"]}
    totals = {"scheduled": 0, "resumed": 0, "written": 0}

    # Check every selected endpoint first. If either endpoint or served model is
    # wrong, abort globally before any candidate source/receiver call is made.
    endpoints = {
        model: base_urls.get(model) or configured_base_url(model_specs[model])
        for model in selected_models
    }
    health = {
        model: health_check(endpoints[model], model, api_key, timeout)
        for model in selected_models
    }

    for model in selected_models:
        model_rows = [row for row in plan["rows"] if row["model"] == model]
        totals["scheduled"] += len(model_rows)
        jobs: list[tuple[Any, str, RunConfig, Path]] = []
        resumed_sources: dict[tuple[str, str, int], dict[str, Any]] = {}
        for row in model_rows:
            record = records[row["task_id"]]
            run_config = run_config_for(plan["config"], model, row["seed"], row["condition"])
            path = output_path(output_root, row)
            if path.exists():
                previous = validate_existing(path, row)
                totals["resumed"] += 1
                if run_config.factorial_cell is not None:
                    recovered = pilot_cli.shared_source_from_run(previous)
                    if recovered is None:
                        raise ValueError(f"cannot recover factorial source from {path}")
                    key = pilot_cli.factorial_block_key(record, run_config)
                    existing = resumed_sources.get(key)
                    if (existing is not None and
                            pilot_cli.source_signature(existing) != pilot_cli.source_signature(recovered)):
                        raise ValueError(f"existing factorial block has inconsistent sources: {key}")
                    resumed_sources[key] = recovered
            else:
                jobs.append((record, row["condition"], run_config, path))

        url = endpoints[model]
        factory = lambda url=url: OpenAICompatibleProvider(url, api_key, timeout)
        shared = resumed_sources | pilot_cli.prepare_factorial_sources(
            jobs, factory, workers, set(resumed_sources)
        )
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(
                pilot_cli.execute_job, record, condition, run_config, path, factory,
                shared.get(pilot_cli.factorial_block_key(record, run_config))
                if run_config.factorial_cell is not None else None,
            ) for record, condition, run_config, path in jobs]
            for future in as_completed(futures):
                future.result()
                totals["written"] += 1

        model_root = output_root / model
        runs = [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((model_root / "runs").rglob("*.json"))]
        expected_keys = {(row["task_id"], row["model"], row["seed"], row["condition"])
                         for row in model_rows}
        observed_keys = [(run.get("task_id"), run.get("model"), run.get("seed"),
                          run.get("method")) for run in runs]
        if len(observed_keys) != len(set(observed_keys)) or set(observed_keys) != expected_keys:
            raise ValueError(f"persisted run set for {model} is duplicate, foreign, or incomplete")
        write_summary(model_root, runs)
        pilot_cli.atomic_json(model_root / "execution_ledger.json", {
            "format": "handoffbench-confirmatory-execution-ledger-v1",
            "seal_id": plan["manifest"]["seal_id"], "model": model,
            "base_url": url, "provider_health": health[model], "hashes": plan["hashes"],
            "scheduled_rows_for_model": len(model_rows),
            "persisted_rows_for_model": len(runs),
        })
    return totals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/confirmatory_v3.yaml")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--model", action="append", default=[],
                        help="served_model_name; repeat to select multiple models")
    parser.add_argument("--base-url", action="append", default=[],
                        help="optional SERVED_MODEL_NAME=URL override; repeatable")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run-output", type=Path)
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "EMPTY"))
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    plan = validated_plan(args.config)
    selected_models = args.model or plan["design"]["models"]
    if args.dry_run:
        payload = dry_run_payload(plan, selected_models)
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.dry_run_output:
            pilot_cli.atomic_json(args.dry_run_output, payload)
        print(rendered)
        return 0

    output_root = (args.output_dir or resolve(plan["base"], plan["config"]["outputs"]["root"])).resolve()
    totals = execute(plan, selected_models, output_root, parse_base_urls(args.base_url),
                     args.api_key, args.timeout, args.workers)
    print(json.dumps({"status": "execution_complete", "output_root": str(output_root),
                      **totals}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
