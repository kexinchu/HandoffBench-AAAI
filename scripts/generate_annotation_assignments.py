"""Create blinded, reproducible double-annotation assignments from public packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any


def packet_inventory(packet_dir: Path) -> list[dict[str, str]]:
    packets = []
    for path in sorted(packet_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        task_id = payload.get("task_id")
        if not isinstance(task_id, str) or path.stem != task_id:
            raise ValueError(f"packet/task mismatch: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        packets.append({"task_id": task_id, "packet": path.name, "packet_sha256": digest})
    if not packets:
        raise ValueError("no candidate packets found")
    return packets


def _blind_id(seed: int, annotator: str, task_id: str) -> str:
    material = f"assignment-v1|{seed}|{annotator}|{task_id}".encode()
    return hashlib.sha256(material).hexdigest()[:16]


def build_assignments(packet_dir: Path, *, seed: int) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    inventory = packet_inventory(packet_dir)
    orders: dict[str, list[dict[str, Any]]] = {}
    for annotator, offset in (("annotator_a", 0), ("annotator_b", 1)):
        shuffled = list(inventory)
        random.Random(seed + offset).shuffle(shuffled)
        orders[annotator] = [
            {
                "assignment_id": _blind_id(seed, annotator, item["task_id"]),
                "position": position,
                "task_id": item["task_id"],
                "packet": item["packet"],
                "packet_sha256": item["packet_sha256"],
                "response": None,
            }
            for position, item in enumerate(shuffled, 1)
        ]
    if [x["task_id"] for x in orders["annotator_a"]] == [x["task_id"] for x in orders["annotator_b"]]:
        raise RuntimeError("annotator orders unexpectedly identical")
    manifest = {
        "manifest_version": "assignment-v1",
        "seed": seed,
        "packet_set": packet_dir.name,
        "packet_count": len(inventory),
        "independent_annotators_per_task": 2,
        "blinding": {
            "annotators_do_not_receive_other_annotations": True,
            "annotators_do_not_receive_adjudication_queue": True,
            "assignment_ids_are_annotator_specific": True,
        },
        "adjudication": {
            "mode": "disagreements_only",
            "preassigned_tasks": [],
            "minimum_independent_annotations_before_queueing": 2,
        },
        "assignment_files": ["annotator_a.json", "annotator_b.json"],
    }
    return manifest, orders


def write_new(output_dir: Path, manifest: dict[str, Any], orders: dict[str, Any]) -> None:
    """Write atomically enough for authoring and categorically refuse overwrite."""
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    output_dir.mkdir(parents=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name, rows in orders.items():
        (output_dir / f"{name}.json").write_text(
            json.dumps({"assignments": rows}, indent=2) + "\n", encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20270117)
    args = parser.parse_args()
    manifest, assignments = build_assignments(args.packet_dir, seed=args.seed)
    write_new(args.output_dir, manifest, assignments)
    print(json.dumps({"output": str(args.output_dir), "tasks": manifest["packet_count"]}))


if __name__ == "__main__":
    main()
