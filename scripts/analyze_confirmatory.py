#!/usr/bin/env python3
"""Produce preregistered confirmatory JSON, LaTeX tables, and provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import handoffbench.confirmatory_analysis as analysis_module
from handoffbench.confirmatory_analysis import analyze, latex_tables, load_and_validate, sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sealed-manifest", required=True)
    parser.add_argument("--raw-run-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-draws", type=int, default=10000)
    args = parser.parse_args()
    manifest, runs, context = load_and_validate(args.sealed_manifest, args.raw_run_dir)
    report = analyze(manifest, runs, context["families"], draws=args.bootstrap_draws, seed=2027)
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    report_path, table_path = output / "confirmatory_results.json", output / "main_tables.tex"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    table_path.write_text(latex_tables(report), encoding="utf-8")
    provenance = context["provenance"] | {
        "analysis_script": str(Path(__file__).resolve()),
        "analysis_script_sha256": sha256(Path(__file__).resolve()),
        "analysis_module": str(Path(analysis_module.__file__).resolve()),
        "analysis_module_sha256": sha256(Path(analysis_module.__file__).resolve()),
        "results_sha256": sha256(report_path), "latex_tables_sha256": sha256(table_path),
        "bootstrap_seed": 2027, "bootstrap_draws": args.bootstrap_draws,
    }
    (output / "provenance_manifest.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
