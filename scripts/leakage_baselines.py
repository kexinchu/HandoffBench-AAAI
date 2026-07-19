#!/usr/bin/env python3
"""Deterministic non-LLM leakage probes for the counterfactual challenge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from handoffbench.dataset import TaskRecord, execute_events, load_tasks
from handoffbench.prompts import action_catalog


DEFAULT_PATH = Path(__file__).parents[1] / "data/tasks/dev/counterfactual_travel.json"


def _argument_guess(signature: dict[str, Any]) -> dict[str, Any]:
    guessed: dict[str, Any] = {}
    for key, spec in signature.items():
        if isinstance(spec, dict) and spec.get("enum"):
            guessed[key] = spec["enum"][0]
        elif isinstance(spec, dict) and spec.get("type") == "boolean":
            guessed[key] = False
        else:
            guessed[key] = "unknown"
    return guessed


def _canonical_catalog(record: TaskRecord, catalog: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    # Baselines must not accidentally depend on transport/list ordering.
    return sorted(catalog or action_catalog(record),
                  key=lambda item: (item["name"], json.dumps(item["arguments"], sort_keys=True)))


def predict(record: TaskRecord, method: str, *, catalog: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    public = _canonical_catalog(record, catalog)
    by_name = {item["name"]: item for item in public}
    if method == "catalog_only":
        item = public[0]
        return [{"name": item["name"], "arguments": _argument_guess(item["arguments"])}]
    if method == "name_only":
        # Upper bound for leakage through action names: oracle names, no args.
        names = [event["name"] for event in record.episode.success_predicate.args["required_events"]]
        return [{"name": name, "arguments": _argument_guess(by_name[name]["arguments"])}
                for name in names]
    if method == "predicate_only":
        # No state/trace: select a canonical action whose public predicate is empty.
        item = next((item for item in public if not item["requires"]), public[0])
        return [{"name": item["name"], "arguments": _argument_guess(item["arguments"])}]
    if method == "exact_copy":
        return json.loads(json.dumps(record.episode.success_predicate.args["required_events"]))
    raise ValueError(f"unknown leakage baseline: {method}")


def invocation_f1(predicted: list[dict[str, Any]], gold: list[dict[str, Any]]) -> float:
    def key(item: dict[str, Any]) -> str:
        return json.dumps(item, sort_keys=True, separators=(",", ":"))
    remaining = [key(item) for item in gold]
    tp = 0
    for item in predicted:
        encoded = key(item)
        if encoded in remaining:
            remaining.remove(encoded)
            tp += 1
    if not predicted and not gold:
        return 1.0
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def evaluate(records: Iterable[TaskRecord], methods: tuple[str, ...] = (
    "catalog_only", "name_only", "predicate_only", "exact_copy"
)) -> dict[str, Any]:
    rows = []
    for record in records:
        gold = record.episode.success_predicate.args["required_events"]
        for method in methods:
            events = predict(record, method)
            rows.append({"task_id": record.episode.task_id, "method": method,
                         "success": execute_events(record, events).success,
                         "invocation_f1": invocation_f1(events, gold), "events": events})
    summary = {}
    for method in methods:
        subset = [row for row in rows if row["method"] == method]
        summary[method] = {
            "n": len(subset),
            "success_rate": sum(row["success"] for row in subset) / len(subset),
            "invocation_f1": sum(row["invocation_f1"] for row in subset) / len(subset),
        }
    return {"summary": summary, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(load_tasks(args.tasks))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
