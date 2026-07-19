"""Generate a disagreement-only queue after strict completed/locked preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoffbench.annotation_agreement import analyze_agreement, load_locked_annotations


def generate(first: Path, second: Path, lock_manifest: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    # This rejects unlocked templates, null skeletons, hash mismatches, incomplete
    # claims/sequences, same annotator IDs, and incomplete double coverage.
    annotator_a, annotator_b = load_locked_annotations(first, second, lock_manifest)
    report = analyze_agreement(annotator_a, annotator_b, draws=2000, seed=2027)
    payload = {
        "format": "disagreement-queue-v2",
        "source_lock_manifest": str(lock_manifest),
        "annotators": report["annotators"],
        "n_tasks_compared": report["n_tasks"],
        "disagreements_only": True,
        "queue": report["adjudication_queue"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("annotator_a", type=Path)
    parser.add_argument("annotator_b", type=Path)
    parser.add_argument("--lock-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = generate(args.annotator_a, args.annotator_b, args.lock_manifest, args.output)
    print(json.dumps({"queue_entries": len(result["queue"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
