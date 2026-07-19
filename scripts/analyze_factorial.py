"""Audit and estimate the balanced 2x2x2 representation experiment."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable


FACTORS = ("typing", "provenance", "checks")


def levels(method: str) -> dict[str, int]:
    parts = method.split("__")
    if len(parts) != 4 or parts[3] not in {"advisory", "enforced"}:
        raise ValueError(f"not a factorial run id: {method}")
    return {
        "typing": 1 if parts[0] == "typed" else -1,
        "provenance": 1 if parts[1] == "trace_linked" else -1,
        "checks": 1 if parts[2] == "executable" else -1,
    }


def load_runs(directories: list[str]) -> list[dict[str, Any]]:
    """Load several immutable run trees without silently double counting a cell."""
    runs: list[dict[str, Any]] = []
    seen: dict[tuple[str, str, int, str], str] = {}
    for directory in directories:
        for path in glob.glob(str(Path(directory) / "runs" / "**" / "*.json"), recursive=True):
            run = json.loads(Path(path).read_text())
            key = (run["task_id"], run["model"], int(run["seed"]), run["method"])
            if key in seen:
                raise ValueError(f"duplicate scheduled cell {key}: {seen[key]} and {path}")
            seen[key] = path
            runs.append(run)
    return runs


def family(task_id: str) -> str:
    return task_id.rsplit("_", 1)[0]


def terms() -> list[tuple[str, ...]]:
    return [("typing",), ("provenance",), ("checks",),
            ("typing", "provenance"), ("typing", "checks"),
            ("provenance", "checks"), tuple(FACTORS)]


def _effect(runs: list[dict[str, Any]], term: tuple[str, ...], metric: Callable[[dict], float]) -> float:
    # In a balanced effect-coded cube, high-minus-low effect = 2 E[y product(x)].
    values = []
    for run in runs:
        sign = 1
        cell = levels(run["method"])
        for factor in term:
            sign *= cell[factor]
        values.append(metric(run) * sign)
    return 2 * mean(values)


def fairness_audit(runs: list[dict[str, Any]]) -> dict[str, Any]:
    blocks: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        blocks[(run["task_id"], run["model"], int(run["seed"]))].append(run)
    failures = []
    for block, items in sorted(blocks.items()):
        if len(items) != 8 or len({i["method"] for i in items}) != 8:
            failures.append({"block": block, "reason": "incomplete_cube", "n": len(items)})
            continue
        call_output_hashes = {
            i["calls"][0].get("source_output_hash") or
            hashlib.sha256((i["calls"][0].get("raw_output") or
                            i.get("source_raw") or "").encode()).hexdigest()
            for i in items
        }
        # The immutable source-call output is authoritative. Legacy error rows
        # may lack duplicated top-level source_raw even though the shared call
        # record is complete; do not turn receiver missingness into a source
        # fairness failure.
        source_hashes = {
            i.get("source_hash") or i["calls"][0].get("source_output_hash") or
            hashlib.sha256((i["calls"][0].get("raw_output") or
                            i.get("source_raw") or "").encode()).hexdigest()
            for i in items
        }
        prompt_hashes = {i["calls"][0]["prompt_hash"] for i in items}
        schema_hashes = {i["calls"][0]["response_schema_hash"] for i in items}
        source_usage = {json.dumps(i["calls"][0].get("usage"), sort_keys=True) for i in items}
        if (len(source_hashes) != 1 or len(call_output_hashes) != 1 or
                len(prompt_hashes) != 1 or len(schema_hashes) != 1 or len(source_usage) != 1):
            failures.append({"block": block, "reason": "source_not_identical",
                             "source_hashes": len(source_hashes),
                             "call_output_hashes": len(call_output_hashes),
                             "prompt_hashes": len(prompt_hashes),
                             "schema_hashes": len(schema_hashes),
                             "source_usage_variants": len(source_usage)})
    return {"n_blocks": len(blocks), "n_complete_blocks": len(blocks) - len(failures),
            "pass": not failures, "failures": failures}


def estimate(runs: list[dict[str, Any]], draws: int = 10000) -> dict[str, Any]:
    # Intent-to-treat: parse/provider failures retain their scheduled cell and
    # explicit zero metrics rather than unbalancing the cube.
    ok = list(runs)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in ok:
        by_family[family(run["task_id"])].append(run)
    family_ids = sorted(by_family)
    metrics = {
        "strict_success": lambda run: float(bool(run.get("success"))),
        "macro_state_f1": lambda run: float(run["metrics"]["macro_state_f1"]),
        "critical_errors": lambda run: float(run["metrics"]["critical_errors"]),
    }
    rng = random.Random(2027)
    report: dict[str, Any] = {}
    for metric_name, metric in metrics.items():
        report[metric_name] = {}
        for term in terms():
            label = ":".join(term)
            point = _effect(ok, term, metric)
            boot = []
            for _ in range(draws):
                sampled = [rng.choice(family_ids) for _ in family_ids]
                sample_runs = [run for selected in sampled for run in by_family[selected]]
                boot.append(_effect(sample_runs, term, metric))
            boot.sort()
            report[metric_name][label] = {
                "effect": point,
                "cluster_bootstrap_ci_low": boot[int(0.025 * draws)],
                "cluster_bootstrap_ci_high": boot[int(0.975 * draws) - 1],
            }
    return {"n_runs": len(runs),
            "n_ok": sum(run.get("status") == "ok" for run in runs),
            "n_errors": sum(run.get("status") != "ok" for run in runs),
            "n_families": len(family_ids),
            "effects": report}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    runs = load_runs(args.directories)
    result = {"input_directories": args.directories,
              "fairness_audit": fairness_audit(runs), "estimates": estimate(runs)}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
