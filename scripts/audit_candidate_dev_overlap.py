#!/usr/bin/env python3
"""Deterministic candidate-vs-development overlap audit (no model calls)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ID_LIKE = re.compile(r"\b(?=[a-z0-9_-]*\d)[a-z0-9_-]+\b", re.I)
DATE_LIKE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ][0-9:+.-Z]+)?\b", re.I)
TOKEN = re.compile(r"[a-z][a-z_]{1,}|<id>", re.I)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        text = DATE_LIKE.sub("<date>", value.casefold())
        text = ID_LIKE.sub("<id>", text)
        return re.sub(r"\b\d+(?:\.\d+)?\b", "<num>", text)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "<num>"
    if isinstance(value, list):
        return [normalize_scalar(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_scalar(item) for key, item in sorted(value.items())
                if key not in {"task_id", "trace_id", "boundary_id"}}
    return value


def normalized_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_scalar(event) for event in trace]


def _placeholder(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _placeholder(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_placeholder(item) for item in value]
    if value is None:
        return None
    return f"<{type(value).__name__}>"


def action_graph(episode: dict[str, Any], *, normalized: bool) -> Any:
    rules = episode.get("allowed_next_actions", []) + episode.get("forbidden_next_actions", [])
    events = (episode.get("success_predicate", {}).get("args", {}).get("required_events", [])
              + episode.get("success_predicate", {}).get("args", {}).get("forbidden_events", []))
    if not normalized:
        return {"allowed": episode.get("allowed_next_actions", []),
                "forbidden": episode.get("forbidden_next_actions", []),
                "predicate": episode.get("success_predicate", {})}
    names: dict[str, str] = {}
    keys: dict[str, str] = {}

    def action_name(name: str) -> str:
        if name not in names:
            names[name] = f"A{len(names)}"
        return names[name]

    def key_name(key: str) -> str:
        if key not in keys:
            keys[key] = f"K{len(keys)}"
        return keys[key]

    normalized_rules = []
    for rule in rules:
        conditions = []
        for condition in rule.get("when", []):
            negated = condition.startswith("!")
            key, status = condition.removeprefix("!").split("=", 1)
            conditions.append((negated, key_name(key), status if status in {
                "known", "unknown", "contradicted", "not_applicable"} else "<value>"))
        normalized_rules.append({"action": action_name(rule["action"]),
                                 "arguments": {key_name(key): _placeholder(value)
                                               for key, value in sorted(rule.get("expected_arguments", {}).items())},
                                 "when": conditions, "irreversible": rule.get("irreversible", False),
                                 "kind": "allowed" if rule in episode.get("allowed_next_actions", []) else "forbidden"})
    normalized_events = []
    for event in events:
        event = {"name": event, "arguments": {}} if isinstance(event, str) else event
        normalized_events.append({"action": action_name(event["name"]),
                                  "arguments": {key_name(key): _placeholder(value)
                                                for key, value in sorted(event.get("arguments", {}).items())}})
    return {"rules": normalized_rules, "events": normalized_events,
            "required_count": len(episode.get("success_predicate", {}).get("args", {}).get("required_events", []))}


def lexical_tokens(trace: list[dict[str, Any]]) -> list[str]:
    # Include property names and natural-language values; exclude event/task IDs and tool plumbing.
    parts = []
    for event in trace:
        content = event.get("content", {})
        parts.append(canonical(normalize_scalar(content)))
    return TOKEN.findall(" ".join(parts).casefold())


def shingles(tokens: list[str], width: int = 2) -> set[tuple[str, ...]]:
    if len(tokens) < width:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index:index + width]) for index in range(len(tokens) - width + 1)}


def jaccard(left: set, right: set) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def load_records(paths: Iterable[Path], label: str) -> list[dict[str, Any]]:
    records = []
    for path in sorted(paths):
        value = json.loads(path.read_text())
        if not isinstance(value, list):
            raise ValueError(f"{path}: task file must contain an array")
        for item in value:
            records.append({"set": label, "file": str(path), "task_id": item["episode"]["task_id"],
                            "episode": item["episode"], "trace": item["upstream_trace"]})
    return records


def _collisions(candidate: list[dict], development: list[dict], getter) -> list[dict[str, Any]]:
    dev_index: dict[Any, list[str]] = {}
    for item in development:
        dev_index.setdefault(getter(item), []).append(item["task_id"])
    return [{"candidate": item["task_id"], "development": dev_index[value], "value": str(value)}
            for item in candidate if (value := getter(item)) in dev_index]


def audit(candidate: list[dict], development: list[dict], lexical_threshold: float = .80,
          top_k: int = 25) -> dict[str, Any]:
    getters = {
        "family_id": lambda x: x["episode"].get("split_meta", {}).get("template_family"),
        "entity_pool": lambda x: x["episode"].get("split_meta", {}).get("entity_pool"),
        "generator_seed": lambda x: x["episode"].get("split_meta", {}).get("seed"),
        "exact_trace_hash": lambda x: digest(x["trace"]),
        "normalized_trace_hash": lambda x: digest(normalized_trace(x["trace"])),
        "exact_action_graph_hash": lambda x: digest(action_graph(x["episode"], normalized=False)),
        "normalized_action_graph_hash": lambda x: digest(action_graph(x["episode"], normalized=True)),
    }
    collisions = {name: _collisions(candidate, development, getter) for name, getter in getters.items()}
    dev_shingles = [(item, shingles(lexical_tokens(item["trace"]))) for item in development]
    similarities = []
    for cand in candidate:
        cand_shingles = shingles(lexical_tokens(cand["trace"]))
        for dev, dev_tokens in dev_shingles:
            score = jaccard(cand_shingles, dev_tokens)
            similarities.append({"candidate": cand["task_id"], "development": dev["task_id"],
                                 "jaccard": score})
    similarities.sort(key=lambda item: (-item["jaccard"], item["candidate"], item["development"]))
    return {"scope": {"candidate_tasks": len(candidate), "development_tasks": len(development),
                      "candidate_files": sorted({x["file"] for x in candidate}),
                      "development_files": sorted({x["file"] for x in development})},
            "method": {"lexical_metric": "Jaccard over normalized trace-content token bigrams",
                       "lexical_threshold": lexical_threshold, "normalization":
                       "lowercase; replace dates, numeric/opaque-ID-like tokens; remove trace/task/boundary IDs",
                       "limitations": ["lexical similarity does not establish semantic or automaton equivalence",
                                       "normalization can over-collapse common schema vocabulary",
                                       "different wording can hide equivalent workflow logic"]},
            "collisions": collisions,
            "lexical_near_duplicates": [item for item in similarities
                                        if item["jaccard"] >= lexical_threshold],
            "top_lexical_pairs": similarities[:top_k]}


def markdown(result: dict[str, Any]) -> str:
    scope, method = result["scope"], result["method"]
    lines = ["# Candidate-vs-development overlap audit", "",
             "Static audit only: no model was called, no candidate was modified, and this report does not seal a split.", "",
             f"- Candidate tasks: {scope['candidate_tasks']} across {len(scope['candidate_files'])} files.",
             f"- Development tasks: {scope['development_tasks']} across {len(scope['development_files'])} files.",
             f"- Lexical rule: {method['lexical_metric']}; flag at Jaccard ≥ {method['lexical_threshold']:.2f}.",
             f"- Normalization: {method['normalization']}.", "", "## Exact/structural collisions", "",
             "| Signal | Candidate tasks flagged | Pair groups |", "|---|---:|---:|"]
    for name, values in result["collisions"].items():
        lines.append(f"| {name} | {len(values)} | {sum(len(x['development']) for x in values)} |")
    lines += ["", "## Lexical near duplicates", "",
              f"Pairs above threshold: {len(result['lexical_near_duplicates'])}.", "",
              "| Candidate | Development | Jaccard |", "|---|---|---:|"]
    for item in result["lexical_near_duplicates"][:100]:
        lines.append(f"| {item['candidate']} | {item['development']} | {item['jaccard']:.3f} |")
    lines += ["", "## Highest lexical similarities (including below threshold)", "",
              "| Candidate | Development | Jaccard |", "|---|---|---:|"]
    for item in result["top_lexical_pairs"]:
        lines.append(f"| {item['candidate']} | {item['development']} | {item['jaccard']:.3f} |")
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in method["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=ROOT / "data/tasks/candidate")
    parser.add_argument("--dev-dir", type=Path, default=ROOT / "data/tasks/dev")
    parser.add_argument("--lexical-threshold", type=float, default=.80)
    parser.add_argument("--top-k", type=int, default=25)
    parser.add_argument("--output-prefix", type=Path,
                        default=ROOT / "research/candidate_dev_overlap_audit")
    args = parser.parse_args()
    if not 0 <= args.lexical_threshold <= 1:
        parser.error("--lexical-threshold must be in [0,1]")
    candidate = load_records(args.candidate_dir.glob("*.json"), "candidate")
    development = load_records(args.dev_dir.glob("*.json"), "development")
    result = audit(candidate, development, args.lexical_threshold, args.top_k)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    args.output_prefix.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    args.output_prefix.with_suffix(".md").write_text(markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
