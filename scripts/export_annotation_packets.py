"""Export evaluator-blind packets for independent human gold annotation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from handoffbench.dataset import load_tasks, public_action_contract


FORBIDDEN_KEYS = {
    "gold_state", "allowed_next_actions", "forbidden_next_actions",
    "success_predicate", "scoring", "expected_arguments",
}


def packet(record) -> dict:
    return {
        "task_id": record.episode.task_id,
        "domain": record.episode.domain,
        "boundary": record.episode.boundary.model_dump(),
        "authenticated_upstream_trace": list(record.upstream_trace),
        "public_action_contract": list(public_action_contract(record)),
        "deterministic_tool_semantics": record.mock_tool_world["tools"],
        "scripted_user_responses": record.mock_tool_world["user_replies"],
        "annotation_instructions": (
            "Independently reconstruct task-critical boundary claims and the legal next-action "
            "sequence. Do not consult model outputs, another annotator, or evaluator files."
        ),
    }


def assert_blind(value) -> None:
    if isinstance(value, dict):
        overlap = FORBIDDEN_KEYS & set(value)
        if overlap:
            raise ValueError(f"annotation packet leaked evaluator keys: {sorted(overlap)}")
        for child in value.values():
            assert_blind(child)
    elif isinstance(value, list):
        for child in value:
            assert_blind(child)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite annotation export: {args.output_dir}")
    records = [record for path in args.tasks for record in load_tasks(path)]
    args.output_dir.mkdir(parents=True)
    for record in records:
        value = packet(record)
        assert_blind(value)
        (args.output_dir / f"{record.episode.task_id}.json").write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        )
    print(f"exported {len(records)} blinded packets")


if __name__ == "__main__":
    main()
