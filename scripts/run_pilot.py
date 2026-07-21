#!/usr/bin/env python3
"""Resumable, fail-recording HandoffBench pilot CLI."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from handoffbench.dataset import load_tasks  # noqa: E402
from handoffbench.pilot_analysis import score_boundary_transfer, write_summary  # noqa: E402
from handoffbench.providers import OpenAICompatibleProvider  # noqa: E402
from handoffbench.runner import RunConfig, generate_transfer, run_pilot  # noqa: E402
from handoffbench.transfer import FACTORIAL_CELLS, TransferKind, factorial_cell  # noqa: E402


METHODS = {kind.value: kind for kind in TransferKind if kind is not TransferKind.FACTORIAL} | {"executable_capsule": TransferKind.EHC,
                                                         "gold_state_oracle": TransferKind.GOLD_ORACLE}


class RecordingProvider:
    def __init__(self, provider: OpenAICompatibleProvider):
        self.provider = provider
        self.calls: list[dict[str, Any]] = []
        self.last_usage: dict[str, int] | None = None

    def complete(self, messages: Sequence[dict[str, str]], *, model: str, temperature: float,
                 response_schema: dict[str, Any] | None = None,
                 schema_name: str | None = None, seed: int | None = None,
                 max_output_tokens: int | None = None) -> str:
        canonical = json.dumps(list(messages), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        schema_raw = json.dumps(response_schema, sort_keys=True, separators=(",", ":")) if response_schema else None
        call: dict[str, Any] = {"prompt_hash": hashlib.sha256(canonical.encode()).hexdigest(),
                                "messages": list(messages), "schema_name": schema_name,
                                "seed": seed,
                                "max_output_tokens": max_output_tokens,
                                "response_schema_hash": hashlib.sha256(schema_raw.encode()).hexdigest()
                                if schema_raw else None}
        self.calls.append(call)
        try:
            raw = self.provider.complete(messages, model=model, temperature=temperature,
                                         response_schema=response_schema, schema_name=schema_name,
                                         seed=seed, max_output_tokens=max_output_tokens)
            self.last_usage = getattr(self.provider, "last_usage", None)
            call.update({"raw_output": raw,
                         "usage": self.last_usage if isinstance(self.last_usage, dict) else {}})
            return raw
        except Exception as exc:
            self.last_usage = getattr(self.provider, "last_usage", None)
            call["usage"] = self.last_usage if isinstance(self.last_usage, dict) else {}
            call["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def selected(values: str, available: list[str]) -> list[str]:
    if values == "all": return available
    requested = [x.strip() for x in values.split(",") if x.strip()]
    unknown = set(requested) - set(available)
    if unknown: raise ValueError(f"unknown selection: {sorted(unknown)}")
    return requested


def observed_usage(calls: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    """Return only provider-reported usage and its explicit token totals."""
    usage = [dict(call["usage"]) for call in calls if isinstance(call.get("usage"), dict)]
    input_tokens = sum(
        item.get("prompt_tokens", item.get("input_tokens", 0)) for item in usage
    )
    output_tokens = sum(
        item.get("completion_tokens", item.get("output_tokens", 0)) for item in usage
    )
    return usage, input_tokens, output_tokens


def source_signature(shared: dict[str, Any]) -> tuple[str, str, str, str]:
    call = shared["call"]
    return (
        shared["source_hash"], call["prompt_hash"], call["response_schema_hash"],
        hashlib.sha256(json.dumps(call.get("usage"), sort_keys=True,
                                  separators=(",", ":")).encode()).hexdigest(),
    )


def shared_source_from_run(run: dict[str, Any]) -> dict[str, Any] | None:
    """Recover an immutable factorial source, including a recorded source failure."""
    calls = run.get("calls")
    if not isinstance(calls, list) or not calls or not isinstance(calls[0], dict):
        return None
    call = copy.deepcopy(calls[0])
    required = ("prompt_hash", "response_schema_hash", "source_output_hash", "usage")
    if any(key not in call or call[key] is None for key in required):
        return None
    source_hash = run.get("source_hash") or call["source_output_hash"]
    if source_hash != call["source_output_hash"]:
        raise ValueError("persisted factorial source hash disagrees with source call")
    raw = run.get("source_raw")
    failure = run.get("source_error") if run.get("source_stage_failure") is True else None
    if failure is None:
        if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != source_hash:
            return None
        try:
            generated = json.loads(raw)
        except json.JSONDecodeError:
            return None
    else:
        if isinstance(raw, str) and hashlib.sha256(raw.encode()).hexdigest() != source_hash:
            raise ValueError("persisted failed factorial source raw/hash mismatch")
        generated = None
    return {"generated": generated, "raw": raw, "call": call,
            "source_hash": source_hash, "error": copy.deepcopy(failure)}


def execute_job(record: Any, method: str, config: RunConfig, path: Path,
                provider_factory: Any, shared_source: dict[str, Any] | None = None) -> Path:
    """Run and atomically persist one independent task/method/seed cell."""
    recorder = RecordingProvider(provider_factory())
    if shared_source is not None:
        # Retain the identical logical source-call metadata in every cell. A
        # deep copy prevents concurrent receiver jobs from sharing mutation.
        recorder.calls.append(copy.deepcopy(shared_source["call"]))
    result: dict[str, Any] = {"task_id": record.episode.task_id, "method": method,
                              "seed": config.seed, "model": config.model,
                              "config": asdict(config), "config_hash": config.config_hash,
                              "status": "error"}
    try:
        if shared_source is not None and shared_source.get("error") is not None:
            error = shared_source["error"]
            result.update({
                "error": copy.deepcopy(error), "source_error": copy.deepcopy(error),
                "source_stage_failure": True, "source_raw": shared_source.get("raw"),
            })
        else:
            artifact = run_pilot(
                record, config, recorder,
                generated_transfer=shared_source["generated"] if shared_source else None,
                source_raw_output=shared_source["raw"] if shared_source else None,
            )
            score = score_boundary_transfer(record, artifact.receiver_states)
            result.update({"status": "ok", "source_raw": artifact.source_raw_output,
                           "receiver_raw": list(artifact.receiver_raw_outputs),
                           "receiver_states": [dict(x) for x in artifact.receiver_states],
                           "boundary_receiver_state": dict(artifact.receiver_states[0]) if artifact.receiver_states else None,
                           "final_receiver_state": dict(artifact.receiver_states[-1]) if artifact.receiver_states else None,
                           "events": list(artifact.events), "violations": list(artifact.execution.violations),
                           "success": artifact.execution.success,
                           "metrics": score | {"strict_success": int(artifact.execution.success)}})
            if artifact.transfer_validation_sidecar is not None:
                result["transfer_validation_sidecar"] = dict(artifact.transfer_validation_sidecar)
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    if result["status"] != "ok":
        result.setdefault("metrics", {}).update({
            "strict_success": 0, "macro_state_f1": 0,
            "critical_errors": len(record.episode.scoring.critical_keys),
        })
    # Validation is deterministic local computation and makes no separately
    # billed provider call; its explicit accounting value is therefore zero.
    usage, input_tokens, output_tokens = observed_usage(recorder.calls)
    result["usage"] = usage
    result.setdefault("metrics", {}).update({
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "validator_cost": 0.0,
    })
    # Receiver/provider failures remain ITT failures, but must not erase the
    # already-fixed factorial source manipulation from the audit record.
    if shared_source is not None:
        result["source_raw"] = shared_source.get("raw")
        result["source_hash"] = shared_source["source_hash"]
        result["source_reused_within_factorial_block"] = True
    result["calls"] = recorder.calls
    result["prompt_hashes"] = [call["prompt_hash"] for call in recorder.calls
                               if call.get("prompt_hash") is not None]
    atomic_json(path, result)
    return path


def factorial_block_key(record: Any, config: RunConfig) -> tuple[str, str, int]:
    return record.episode.task_id, config.model, config.seed


def prepare_factorial_sources(
    jobs: list[tuple[Any, str, RunConfig, Path]], provider_factory: Any, workers: int,
    skip_keys: set[tuple[str, str, int]] | None = None,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Generate exactly one immutable source artifact per factorial block."""
    representatives: dict[tuple[str, str, int], tuple[Any, RunConfig]] = {}
    skip_keys = skip_keys or set()
    for record, _method, config, _path in jobs:
        if config.factorial_cell is not None:
            key = factorial_block_key(record, config)
            if key not in skip_keys:
                representatives.setdefault(key, (record, config))

    def generate(item: tuple[tuple[str, str, int], tuple[Any, RunConfig]]):
        key, (record, config) = item
        recorder = RecordingProvider(provider_factory())
        try:
            generated, raw = generate_transfer(record, config, recorder)
            error = None
        except Exception as exc:
            generated = None
            raw = recorder.calls[0].get("raw_output") if len(recorder.calls) == 1 else None
            error = {"type": type(exc).__name__, "message": str(exc),
                     "stage": "source_parse" if raw is not None else "source_provider"}
        if len(recorder.calls) != 1:
            raise RuntimeError(f"factorial source block {key} did not produce exactly one call")
        call = copy.deepcopy(recorder.calls[0])
        call.setdefault("usage", {})
        if error is not None:
            call["source_error"] = copy.deepcopy(error)
        source_material: Any = raw if raw is not None else {
            "prompt_hash": call["prompt_hash"], "response_schema_hash": call["response_schema_hash"],
            "seed": call.get("seed"), "error": error,
        }
        encoded = (source_material.encode() if isinstance(source_material, str) else
                   json.dumps(source_material, sort_keys=True, separators=(",", ":")).encode())
        call["source_output_hash"] = hashlib.sha256(encoded).hexdigest()
        return key, {"generated": generated, "raw": raw, "call": call,
                     "source_hash": call["source_output_hash"], "error": error}

    cache = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(generate, item) for item in representatives.items()]
        for future in as_completed(futures):
            key, shared = future.result()
            cache[key] = shared
    return cache


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(ROOT / "data/tasks/dev/pilot.json"))
    parser.add_argument("--base-url", required=True); parser.add_argument("--model", required=True)
    parser.add_argument("--methods", default="all"); parser.add_argument("--tasks", default="all")
    parser.add_argument(
        "--factorial-cells", default="none",
        help="none, all, or comma-separated typing__provenance__checks cells",
    )
    parser.add_argument("--enforce-action-gates", action="store_true",
                        help="secondary execution intervention; representation cell label is unchanged")
    parser.add_argument("--seeds", default="101,202"); parser.add_argument("--output-dir", required=True)
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "EMPTY"))
    parser.add_argument("--timeout", type=float, default=120); parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--max-output-tokens", type=int, default=1600)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--protocol-version", default="handoffbench-v1")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    records = load_tasks(args.data); by_id = {r.episode.task_id: r for r in records}
    task_ids = selected(args.tasks, list(by_id)); methods = selected(args.methods, list(METHODS))
    cells = ([] if args.factorial_cells == "none" else
             selected(args.factorial_cells, list(FACTORIAL_CELLS)))
    seeds = [int(x) for x in args.seeds.split(",")]; output = Path(args.output_dir)
    jobs = []
    resumed_sources: dict[tuple[str, str, int], dict[str, Any]] = {}
    for task_id in task_ids:
        for method in methods:
            for seed in seeds:
                config = RunConfig(args.model, METHODS[method], temperature=args.temperature,
                                   seed=seed, protocol_version=args.protocol_version,
                                   max_turns=args.max_turns,
                                   max_output_tokens=args.max_output_tokens,
                                   enforce_action_gates=args.enforce_action_gates)
                path = output / "runs" / task_id / method / f"seed-{seed}-{config.config_hash[:12]}.json"
                if path.exists():
                    print(f"skip {path}", flush=True)
                else:
                    jobs.append((by_id[task_id], method, config, path))
        for cell_id in cells:
            for seed in seeds:
                cell = factorial_cell(cell_id)
                config = RunConfig(
                    args.model, TransferKind.FACTORIAL, temperature=args.temperature,
                    seed=seed, protocol_version=args.protocol_version,
                    max_turns=args.max_turns,
                    max_output_tokens=args.max_output_tokens,
                    enforce_action_gates=args.enforce_action_gates, factorial_cell=cell,
                )
                arm = config.transfer_config.cell_id
                path = output / "runs" / task_id / arm / f"seed-{seed}-{config.config_hash[:12]}.json"
                if path.exists():
                    print(f"skip {path}", flush=True)
                    previous = json.loads(path.read_text())
                    recovered = shared_source_from_run(previous)
                    if recovered is None:
                        raise ValueError(f"cannot recover factorial source from {path}")
                    key = factorial_block_key(by_id[task_id], config)
                    existing = resumed_sources.get(key)
                    if existing is not None and source_signature(existing) != source_signature(recovered):
                        raise ValueError(f"existing factorial block has inconsistent sources: {key}")
                    resumed_sources[key] = recovered
                else:
                    jobs.append((by_id[task_id], arm, config, path))
    factory = lambda: OpenAICompatibleProvider(args.base_url, args.api_key, args.timeout)
    shared_sources = resumed_sources | prepare_factorial_sources(
        jobs, factory, args.workers, set(resumed_sources)
    )
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(
            execute_job, record, method, config, path, factory,
            shared_sources.get(factorial_block_key(record, config))
            if config.factorial_cell is not None else None,
        )
                   for record, method, config, path in jobs]
        for future in as_completed(futures):
            print(f"write {future.result()}", flush=True)
    runs = [json.loads(path.read_text()) for path in (output / "runs").rglob("*.json")]
    write_summary(output, runs)
    return 0


if __name__ == "__main__": raise SystemExit(main())
