"""Merge resumable runs and produce preregistered counterfactual pilot summaries."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


METHOD_ALIASES = {"executable_capsule": "ehc", "gold_state_oracle": "gold_oracle"}


def method_id(value: str) -> str:
    return METHOD_ALIASES.get(value, value)


def load_runs(directories: list[str]) -> list[dict[str, Any]]:
    indexed: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for directory in directories:
        for path in glob.glob(str(Path(directory) / "runs" / "**" / "*.json"), recursive=True):
            run = json.loads(Path(path).read_text())
            run["method"] = method_id(run["method"])
            key = (run["task_id"], run["method"], run["model"], int(run["seed"]))
            if key in indexed and indexed[key] != run:
                raise ValueError(f"conflicting duplicate run: {key}")
            indexed[key] = run
    return list(indexed.values())


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return centre - radius, centre + radius


def summarize(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        variant = run["task_id"].rsplit("_", 1)[-1]
        method = method_id(run["method"])
        groups[(method, "all")].append(run)
        groups[(method, variant)].append(run)
    rows = []
    for (method, variant), items in sorted(groups.items()):
        # Intent-to-treat: every scheduled artifact remains in the denominator.
        # Provider/parse errors are strict failures with the CLI's explicit zero
        # state metrics; dropping them would create method-dependent sample sizes.
        ok = [item for item in items if item.get("status") == "ok"]
        token_values = [item["metrics"]["input_tokens"] for item in items
                        if item["metrics"].get("input_tokens") is not None]
        successes = sum(bool(item.get("success")) for item in items)
        low, high = wilson(successes, len(items))
        rows.append({
            "method": method,
            "variant": variant,
            "n_expected": len(items),
            "n_ok": len(ok),
            "success_rate": successes / len(items) if items else math.nan,
            "success_ci_low": low,
            "success_ci_high": high,
            "macro_state_f1": mean(item["metrics"]["macro_state_f1"] for item in items),
            "critical_errors": mean(item["metrics"]["critical_errors"] for item in items),
            "input_tokens": mean(token_values) if token_values else math.nan,
        })
    return rows


def paired_ehc_vs_structured(runs: list[dict[str, Any]], draws: int = 10000) -> dict[str, Any]:
    indexed = {(r["task_id"], r["model"], r["seed"], method_id(r["method"])): r
               for r in runs}
    pairs = []
    bases = {(task, model, seed) for task, model, seed, method in indexed
             if method in {"ehc", "structured_payload"}}
    for task, model, seed in sorted(bases):
        ehc = indexed.get((task, model, seed, "ehc"))
        structured = indexed.get((task, model, seed, "structured_payload"))
        if ehc and structured:
            pairs.append((task.rsplit("_", 1)[0],
                          int(bool(ehc.get("success"))),
                          int(bool(structured.get("success")))))
    if not pairs:
        return {"n_pairs": 0}
    differences = [a - b for _, a, b in pairs]
    rng = random.Random(2027)
    clustered: dict[str, list[int]] = defaultdict(list)
    for family_id, a, b_value in pairs:
        clustered[family_id].append(a - b_value)
    family_ids = sorted(clustered)
    boot = []
    for _ in range(draws):
        sampled = [rng.choice(family_ids) for _ in family_ids]
        boot.append(mean(value for family_id in sampled for value in clustered[family_id]))
    boot.sort()
    b = sum(a == 1 and s == 0 for _, a, s in pairs)
    c = sum(a == 0 and s == 1 for _, a, s in pairs)
    discordant = b + c
    exact_p = min(1.0, 2 * sum(math.comb(discordant, k) for k in range(min(b, c) + 1))
                  / (2 ** discordant)) if discordant else 1.0
    return {
        "n_pairs": len(pairs),
        "n_family_clusters": len(family_ids),
        "ehc_minus_structured_success": mean(differences),
        "bootstrap_ci_low": boot[int(0.025 * draws)],
        "bootstrap_ci_high": boot[int(0.975 * draws) - 1],
        "ehc_only_success": b,
        "structured_only_success": c,
        "mcnemar_exact_unclustered_sensitivity_p": exact_p,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", nargs="+")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    runs = load_runs(args.directories)
    rows = summarize(runs)
    report = {"n_runs": len(runs), "summary": rows,
              "ehc_vs_structured": paired_ehc_vs_structured(runs)}
    (output / "counterfactual_analysis.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    if rows:
        write_csv(output / "counterfactual_summary.csv", rows)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
