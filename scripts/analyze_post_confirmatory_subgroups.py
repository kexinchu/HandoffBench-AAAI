#!/usr/bin/env python3
"""Generate versioned exploratory subgroup results from validated sealed inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import handoffbench.post_confirmatory_analysis as post_analysis_module
from handoffbench.confirmatory_analysis import canonical_hash, load_and_validate, sha256
from handoffbench.post_confirmatory_analysis import (
    analyze_post_confirmatory,
    domains_from_validated_inputs,
)


def _repo_relative(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return str(resolved)


def _raw_inventory(root: Path) -> dict[str, object]:
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
        for path in sorted(root.rglob("*.json"))
    ]
    return {
        "algorithm": "sha256-canonical-json-relative-path-file-sha256-v1",
        "file_count": len(entries),
        "sha256": canonical_hash(entries),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sealed-manifest", required=True)
    parser.add_argument("--raw-run-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-draws", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=2027)
    args = parser.parse_args()

    manifest, runs, context = load_and_validate(args.sealed_manifest, args.raw_run_dir)
    domains = domains_from_validated_inputs(context["provenance"])
    report = analyze_post_confirmatory(
        manifest,
        runs,
        context["families"],
        domains,
        draws=args.bootstrap_draws,
        seed=args.bootstrap_seed,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "exploratory_subgroup_results.json"
    results_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    repo_root = Path(__file__).resolve().parent.parent
    script_path = Path(__file__).resolve()
    module_path = Path(post_analysis_module.__file__).resolve()
    raw_roots = [Path(value).resolve() for value in args.raw_run_dir]
    replacement = context["provenance"].get("execution_replacement", {})
    provenance = {
        "analysis_contract": report["analysis_contract"],
        "analysis_status": report["analysis_status"],
        "confirmatory_inference": False,
        "multiplicity_correction": report["multiplicity_correction"],
        "input_validation": "handoffbench.confirmatory_analysis.load_and_validate",
        "sealed_manifest": _repo_relative(Path(args.sealed_manifest), repo_root),
        "sealed_manifest_sha256": context["provenance"]["sealed_manifest_sha256"],
        "seal_id": manifest.get("seal_id"),
        "execution_attempt_id": manifest.get("execution_attempt", {}).get("attempt_id"),
        "canonical_dataset_sha256": context["provenance"]["canonical_dataset_sha256"],
        "n_raw_runs": context["provenance"]["n_raw_runs"],
        "raw_run_inventories": {
            _repo_relative(root, repo_root): _raw_inventory(root) for root in raw_roots
        },
        "qwen_execution_ledger_sha256": replacement.get(
            "qwen_execution_ledger_sha256"
        ),
        "analysis_script": _repo_relative(script_path, repo_root),
        "analysis_script_sha256": sha256(script_path),
        "analysis_module": _repo_relative(module_path, repo_root),
        "analysis_module_sha256": sha256(module_path),
        "results_file": _repo_relative(results_path, repo_root),
        "results_sha256": sha256(results_path),
        "bootstrap_seed": args.bootstrap_seed,
        "bootstrap_draws": args.bootstrap_draws,
    }
    provenance_path = output_dir / "provenance_manifest.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
