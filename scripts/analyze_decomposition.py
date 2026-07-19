"""Analyze saved runs without changing the online runner protocol."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from handoffbench.dataset import load_tasks
from handoffbench.decomposition import analyze_paired_runs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", nargs="+")
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reconstruct-checked-ehc", action="store_true")
    args = parser.parse_args()
    runs = []
    for directory in args.directories:
        for filename in glob.glob(str(Path(directory) / "runs" / "**" / "*.json"), recursive=True):
            runs.append(json.loads(Path(filename).read_text(encoding="utf-8")))
    rows = analyze_paired_runs(
        load_tasks(args.task_file), runs,
        reconstruct_checked_ehc=args.reconstruct_checked_ehc,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"runs": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"n_runs": len(rows), "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
