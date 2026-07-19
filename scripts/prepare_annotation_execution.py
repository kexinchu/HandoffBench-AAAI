"""Create blank v2 response skeletons and an explicitly unlocked lock template."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_assignments(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("assignments")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: assignments must be a non-empty array")
    if len({row.get("task_id") for row in rows}) != len(rows):
        raise ValueError(f"{path}: duplicate task IDs")
    return rows


def build(assignments_dir: Path) -> dict[str, Any]:
    manifest_path = assignments_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("packet_count") != 200:
        raise ValueError("v2 execution requires exactly 200 assigned packets")
    skeletons = {}
    task_sets = []
    for annotator in ("annotator_a", "annotator_b"):
        rows = load_assignments(assignments_dir / f"{annotator}.json")
        task_sets.append({row["task_id"] for row in rows})
        skeletons[f"{annotator}_responses.blank.json"] = {
            "format": "annotation-response-skeleton-v2",
            "annotator_id": annotator,
            "status": "blank_unlocked",
            "assignment_manifest_sha256": sha256(manifest_path),
            "annotations": [
                {
                    "task_id": row["task_id"],
                    "assignment_id": row["assignment_id"],
                    "packet": row["packet"],
                    "packet_sha256": row["packet_sha256"],
                    "response": None,
                    "claims": [],
                    "claim_continuation_rows": [],
                    "action_sequence": None,
                    "irreversible_args_inferable": None,
                    "catalog_leakage_flag": None,
                    "notes": None,
                }
                for row in rows
            ],
        }
    if task_sets[0] != task_sets[1] or len(task_sets[0]) != 200:
        raise ValueError("annotators must independently cover the same 200 tasks")
    skeletons["lock_manifest.template.json"] = {
        "format": "annotation-lock-manifest-v2",
        "locked": False,
        "status": "template_unlocked",
        "expected_task_ids": sorted(task_sets[0]),
        "inputs": [
            {"path": "annotator_a_responses.completed.json", "annotator_id": "annotator_a",
             "sha256": None, "locked_at": None},
            {"path": "annotator_b_responses.completed.json", "annotator_id": "annotator_b",
             "sha256": None, "locked_at": None},
        ],
    }
    return skeletons


def write_new(output_dir: Path, files: dict[str, Any]) -> None:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    output_dir.mkdir(parents=True)
    for name, payload in files.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignments-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    files = build(args.assignments_dir)
    write_new(args.output_dir, files)
    print(json.dumps({"output": str(args.output_dir), "blank_responses": 400}))


if __name__ == "__main__":
    main()
