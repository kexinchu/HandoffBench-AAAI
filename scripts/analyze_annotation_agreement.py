#!/usr/bin/env python3
"""Analyze two locked, completed independent annotation exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoffbench.annotation_agreement import analyze_agreement, load_locked_annotations, markdown_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotator_a"); parser.add_argument("annotator_b")
    parser.add_argument("--lock-manifest", required=True)
    parser.add_argument("--output-json", required=True); parser.add_argument("--output-markdown", required=True)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    args = parser.parse_args()
    first, second = load_locked_annotations(args.annotator_a, args.annotator_b, args.lock_manifest)
    report = analyze_agreement(first, second, draws=args.bootstrap_draws, seed=2027)
    Path(args.output_json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(args.output_markdown).write_text(markdown_report(report), encoding="utf-8")


if __name__ == "__main__":
    main()
