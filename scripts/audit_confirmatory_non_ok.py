#!/usr/bin/env python3
"""Create a post-confirmatory descriptive audit of non-OK v3.4.1 rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import handoffbench.non_ok_audit as audit_module
from handoffbench.confirmatory_analysis import canonical_hash, load_and_validate, sha256
from handoffbench.non_ok_audit import analyze_non_ok_rows


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"path must be within repository: {path}") from error


def _inventory(root: Path) -> dict[str, object]:
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
        for path in sorted(root.rglob("*.json"))
    ]
    return {
        "algorithm": "sha256-canonical-json-relative-path-file-sha256-v1",
        "file_count": len(entries),
        "sha256": canonical_hash(entries),
    }


def _table(rows: list[dict[str, object]], title: str) -> str:
    lines = [f"### {title}", "", "| Group | Non-OK / total | Rate |", "|---|---:|---:|"]
    lines.extend(
        f"| {row['group']} | {row['non_ok_rows']} / {row['total_rows']} | {float(row['non_ok_percent']):.2f}% |"
        for row in rows
    )
    return "\n".join(lines)


def _markdown(report: dict[str, object], provenance: dict[str, object], json_sha256: str) -> str:
    overall = report["overall"]
    breakdowns = report["breakdowns"]
    factors = breakdowns["by_factor_level"]
    chunks = [
        "# Post-confirmatory non-OK row audit (v1)",
        "",
        "Status: **exploratory/descriptive only**. This audit describes the "
        "validated v3.4.1 inputs; it does not modify the execution seal, raw runs, "
        "sealed confirmatory analyzer, or confirmatory inference.",
        "",
        f"- Contract: `{report['analysis_contract']}`",
        f"- Seal: `{provenance['seal_id']}`",
        f"- Denominator: {overall['total_rows']} scheduled ITT rows",
        f"- Non-OK: {overall['non_ok_rows']} ({float(overall['non_ok_percent']):.2f}%)",
        f"- JSON SHA-256: `{json_sha256}`",
        "",
        _table(breakdowns["by_model"], "By model"),
        "",
        _table(breakdowns["by_condition"], "By condition"),
        "",
        _table(breakdowns["by_error_stage"], "By recorded failure stage"),
        "",
        _table(breakdowns["by_error_type"], "By recorded error type"),
        "",
        _table(factors["typing"], "By typing factor"),
        "",
        _table(factors["provenance"], "By provenance factor"),
        "",
        _table(factors["checks"], "By checks factor"),
        "",
        _table(factors["enforcement"], "By enforcement factor"),
        "",
        "## ITT treatment",
        "",
        "Every non-OK row remains in the formal denominator. Under the sealed "
        "analyzer, it receives zero strict-success and macro-state-F1 credit; this "
        "was independently checked here against all non-OK records. The table is "
        "descriptive and has no p-values, confidence intervals, or multiplicity "
        "claims.",
        "",
        "## Provenance",
        "",
        f"- Sealed manifest SHA-256: `{provenance['sealed_manifest_sha256']}`",
        f"- Canonical dataset SHA-256: `{provenance['canonical_dataset_sha256']}`",
        f"- Audit script SHA-256: `{provenance['audit_script_sha256']}`",
        f"- Audit module SHA-256: `{provenance['audit_module_sha256']}`",
    ]
    return "\n".join(chunks) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sealed-manifest", required=True)
    parser.add_argument("--raw-run-dir", action="append", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    args = parser.parse_args()

    manifest, runs, context = load_and_validate(args.sealed_manifest, args.raw_run_dir)
    report = analyze_non_ok_rows(manifest, runs)
    root = Path(__file__).resolve().parent.parent
    output_json, output_markdown = Path(args.output_json), Path(args.output_markdown)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    script_path, module_path = Path(__file__).resolve(), Path(audit_module.__file__).resolve()
    provenance = {
        "sealed_manifest": _relative(Path(args.sealed_manifest), root),
        "sealed_manifest_sha256": context["provenance"]["sealed_manifest_sha256"],
        "seal_id": manifest.get("seal_id"),
        "canonical_dataset_sha256": context["provenance"]["canonical_dataset_sha256"],
        "n_validated_raw_runs": len(runs),
        "raw_run_inventories": {
            _relative(Path(value), root): _inventory(Path(value)) for value in args.raw_run_dir
        },
        "audit_script": _relative(script_path, root),
        "audit_script_sha256": sha256(script_path),
        "audit_module": _relative(module_path, root),
        "audit_module_sha256": sha256(module_path),
    }
    payload = {"report": report, "provenance": provenance}
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_markdown.write_text(
        _markdown(report, provenance, sha256(output_json)), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
