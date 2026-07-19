#!/usr/bin/env python3
"""Record an offline, non-model-call audit trail for the submission build."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKED_INPUTS = (
    "paper/main.tex",
    "paper/references.bib",
    "paper/sections/method.tex",
    "paper/sections/benchmark.tex",
    "paper/sections/evidence.tex",
    "paper/sections/ethics.tex",
    "outputs/cf_combined_v2_qwen_ministral/counterfactual_analysis.json",
    "outputs/factorial_cf_v4_qwen_ministral/factorial_analysis.json",
    "research/power_simulation_v1.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(args: list[str]) -> str | None:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def environment_record() -> dict:
    packages = {}
    for name in ("jsonschema", "pydantic", "PyYAML", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
        "git_commit": _git(["rev-parse", "HEAD"]),
        "git_worktree_dirty": bool(_git(["status", "--porcelain"])),
    }


def table_source_record() -> dict:
    legacy = json.loads((ROOT / TRACKED_INPUTS[6]).read_text(encoding="utf-8"))
    factorial = json.loads((ROOT / TRACKED_INPUTS[7]).read_text(encoding="utf-8"))
    power = json.loads((ROOT / TRACKED_INPUTS[8]).read_text(encoding="utf-8"))
    overall = {row["method"]: row for row in legacy["summary"] if row["variant"] == "all"}
    effects = factorial["estimates"]["effects"]["strict_success"]
    power_cells = {(row["n_families"], row["icc"], row["target_absolute_effect"]): row["power"]
                   for row in power["cells"]}
    return {
        "development_only": True,
        "legacy_success": {
            method: {"n_expected": overall[method]["n_expected"],
                     "success_rate": overall[method]["success_rate"]}
            for method in ("full_history", "free_summary", "structured_payload", "ehc", "gold_oracle")
        },
        "ehc_minus_structured": legacy["ehc_vs_structured"],
        "factorial": {
            "n_runs": factorial["estimates"]["n_runs"],
            "n_ok": factorial["estimates"]["n_ok"],
            "source_fairness": factorial["fairness_audit"],
            "strict_success_effects": {name: effects[name]
                                       for name in ("typing", "provenance", "checks", "provenance:checks")},
        },
        "planning_only_power_icc_0.10": {
            f"n{n}_effect{effect:.2f}": power_cells[(n, 0.1, effect)]
            for n in (120, 200) for effect in (0.08, 0.10)
        },
    }


def table_rows_tex(record: dict) -> str:
    labels = {"full_history": "Full History", "free_summary": "Free Summary",
              "structured_payload": "Structured Payload", "ehc": "All-on EHC",
              "gold_oracle": "Gold Oracle"}
    lines = ["% Generated offline from immutable development analysis JSON; do not edit.",
             "% Development-only legacy table rows:"]
    for method, item in record["legacy_success"].items():
        successes = round(item["success_rate"] * item["n_expected"])
        lines.append(f"% {labels[method]} & {successes}/{item['n_expected']} & "
                     f"{100 * item['success_rate']:.1f}\\% " + "\\\\")
    lines.append("% Development-only factorial strict-success rows (decimal effects and CIs):")
    for name, item in record["factorial"]["strict_success_effects"].items():
        lines.append(f"% {name}: {item['effect']:.12g} "
                     f"[{item['cluster_bootstrap_ci_low']:.12g}, "
                     f"{item['cluster_bootstrap_ci_high']:.12g}]")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="build/reproducibility")
    args = parser.parse_args()
    output = (ROOT / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = {name: sha256(ROOT / name) for name in TRACKED_INPUTS}
    (output / "environment.json").write_text(
        json.dumps(environment_record(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    table_record = table_source_record()
    (output / "table_sources.json").write_text(
        json.dumps(table_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "development_table_rows.tex").write_text(
        table_rows_tex(table_record), encoding="utf-8")
    (output / "input_hashes.json").write_text(
        json.dumps(files, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
