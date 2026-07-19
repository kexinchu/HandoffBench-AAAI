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
            call.update({"raw_output": raw, "usage": self.last_usage})
            return raw
        except Exception as exc:
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
        artifact = run_pilot(
            record, config, recorder,
            generated_transfer=shared_source["generated"] if shared_source else None,
            source_raw_output=shared_source["raw"] if shared_source else None,
        )
        score = score_boundary_transfer(record, artifact.receiver_states)
        usage = [c.get("usage") for c in recorder.calls if isinstance(c.get("usage"), dict)]
        input_tokens = sum(u.get("prompt_tokens", u.get("input_tokens", 0)) for u in usage) if usage else None
        result.update({"status": "ok", "source_raw": artifact.source_raw_output,
                       "receiver_raw": list(artifact.receiver_raw_outputs),
                       "receiver_states": [dict(x) for x in artifact.receiver_states],
                       "boundary_receiver_state": dict(artifact.receiver_states[0]) if artifact.receiver_states else None,
                       "final_receiver_state": dict(artifact.receiver_states[-1]) if artifact.receiver_states else None,
                       "events": list(artifact.events), "violations": list(artifact.execution.violations),
                       "success": artifact.execution.success, "usage": usage,
                       "metrics": score | {"strict_success": int(artifact.execution.success),
                                           "input_tokens": input_tokens}})
        if artifact.transfer_validation_sidecar is not None:
            result["transfer_validation_sidecar"] = dict(artifact.transfer_validation_sidecar)
        if shared_source is not None:
            result["source_reused_within_factorial_block"] = True
            result["source_hash"] = shared_source["source_hash"]
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        result["metrics"] = {"strict_success": 0, "macro_state_f1": 0,
                             "critical_errors": len(record.episode.scoring.critical_keys),
                             "input_tokens": None}
        # Receiver/provider failures remain ITT failures, but must not erase the
        # already-fixed factorial source manipulation from the audit record.
        if shared_source is not None:
            result["source_raw"] = shared_source["raw"]
            result["source_hash"] = shared_source["source_hash"]
            result["source_reused_within_factorial_block"] = True
    result["calls"] = recorder.calls
    result["prompt_hashes"] = [call["prompt_hash"] for call in recorder.calls]
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
        generated, raw = generate_transfer(record, config, recorder)
        if len(recorder.calls) != 1 or raw is None:
            raise RuntimeError(f"factorial source block {key} did not produce exactly one call")
        call = copy.deepcopy(recorder.calls[0])
        call["source_output_hash"] = hashlib.sha256(raw.encode()).hexdigest()
        return key, {"generated": generated, "raw": raw, "call": call,
                     "source_hash": call["source_output_hash"]}

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
                config = RunConfig(args.model, METHODS[method], seed=seed, max_turns=args.max_turns,
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
                    args.model, TransferKind.FACTORIAL, seed=seed, max_turns=args.max_turns,
                    max_output_tokens=args.max_output_tokens,
                    enforce_action_gates=args.enforce_action_gates, factorial_cell=cell,
                )
                arm = config.transfer_config.cell_id
                path = output / "runs" / task_id / arm / f"seed-{seed}-{config.config_hash[:12]}.json"
                if path.exists():
                    print(f"skip {path}", flush=True)
                    previous = json.loads(path.read_text())
                    if previous.get("status") == "ok" and previous.get("source_raw"):
                        key = factorial_block_key(by_id[task_id], config)
                        raw = previous["source_raw"]
                        call = copy.deepcopy(previous["calls"][0])
                        source_hash = previous.get("source_hash") or hashlib.sha256(raw.encode()).hexdigest()
                        shared = {"generated": json.loads(raw), "raw": raw, "call": call,
                                  "source_hash": source_hash}
                        existing = resumed_sources.get(key)
                        if existing is not None and existing["source_hash"] != source_hash:
                            raise ValueError(f"existing factorial block has inconsistent sources: {key}")
                        resumed_sources[key] = shared
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
