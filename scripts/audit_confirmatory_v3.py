#!/usr/bin/env python3
"""Fail-closed static audit for the unsealed confirmatory-v3 task set.

This runner is deterministic and makes no provider/model calls.  Structural
overlap and shallow-baseline results are diagnostics; the checks enumerated in
``hard_checks`` are the gates that must all pass before a seal may be created.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from handoffbench.dataset import execute_events, load_tasks, public_action_contract
from handoffbench.prompts import action_catalog


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = tuple(
    ROOT / "data/tasks/confirmatory_v3" / f"{domain}.json"
    for domain in ("travel", "commerce", "procurement", "it", "scheduling")
)
DEV_FILES = tuple(sorted((ROOT / "data/tasks/dev").glob("*.json")))
EXPECTED_DOMAINS = {domain: 40 for domain in ("travel", "commerce", "procurement", "it", "scheduling")}
BLIND_FORBIDDEN_KEYS = {
    "gold_state", "allowed_next_actions", "forbidden_next_actions",
    "success_predicate", "scoring", "expected_arguments", "max_calls",
}


def _module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _path(event: dict[str, Any], field_path: str | None) -> tuple[bool, Any]:
    value: Any = event
    for component in (field_path or "").split("."):
        if not component or not isinstance(value, dict) or component not in value:
            return False, None
        value = value[component]
    return True, value


def _contains(value: Any, target: Any) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, target) for item in value)
    return False


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value), set())
    return set()


def legal_terminal_sequences(record: Any) -> list[list[dict[str, Any]]]:
    """Enumerate contract-legal sequences without consulting success predicate Phi."""
    invocations = [
        {"name": rule.action, "arguments": dict(rule.expected_arguments)}
        for rule in record.episode.allowed_next_actions
    ]
    irreversible = {
        rule.action for rule in record.episode.allowed_next_actions if rule.irreversible
    }
    legal: list[list[dict[str, Any]]] = []
    for length in range(1, len(invocations) + 1):
        for sequence in itertools.permutations(invocations, length):
            if sequence[-1]["name"] not in irreversible:
                continue
            if not execute_events(record, list(sequence)).violations:
                legal.append(list(sequence))
    return legal


def _raw_records(paths: Iterable[Path], label: str) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        for item in json.loads(path.read_text(encoding="utf-8")):
            rows.append({
                "set": label, "file": str(path),
                "task_id": item["episode"]["task_id"],
                "episode": item["episode"], "trace": item["upstream_trace"],
            })
    return rows


def _duplicate_groups(rows: list[dict[str, Any]], getter: Any) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[str(getter(row))].append(row["task_id"])
    return [
        {"value": value, "task_ids": sorted(task_ids)}
        for value, task_ids in sorted(groups.items()) if len(task_ids) > 1
    ]


def audit(task_files: Iterable[Path] = DEFAULT_FILES) -> dict[str, Any]:
    task_files = tuple(Path(path).resolve() for path in task_files)
    records = sum((load_tasks(path) for path in task_files), [])
    raw = _raw_records(task_files, "confirmatory_v3")
    ids = [record.episode.task_id for record in records]
    families = [record.episode.split_meta.template_family for record in records]
    domains = Counter(record.episode.domain for record in records)
    rows = []
    for record in records:
        trace = {event["trace_id"]: event for event in record.upstream_trace}
        trace_blob = list(record.upstream_trace)
        gold = record.episode.success_predicate.args["required_events"]
        provenance_ok = True
        known_values_grounded = True
        for claim in record.episode.gold_state:
            for pointer in claim.provenance:
                event = trace.get(pointer.trace_id)
                exists, value = _path(event or {}, pointer.field_path)
                provenance_ok &= bool(
                    exists and event and event.get("source_type") == pointer.source_type
                )
                if claim.status.value == "known":
                    known_values_grounded &= exists and value == claim.value
                elif claim.status.value in {"unknown", "not_applicable"}:
                    known_values_grounded &= claim.value is None and value in {None, "unknown", "not_applicable"}

        contract = list(public_action_contract(record))
        catalog = action_catalog(record)
        public_names = {item["action"] for item in contract}
        catalog_names = [item["name"] for item in catalog]
        catalog_ok = (
            catalog == action_catalog(record)
            and public_names <= set(catalog_names)
            and len(catalog_names) == len(set(catalog_names))
            and not (_keys(catalog) & BLIND_FORBIDDEN_KEYS)
        )
        gold_not_catalog_prefix = (
            catalog_names[:len(gold)] != [event["name"] for event in gold]
        )
        public_by_name = {item["action"]: item for item in contract}
        arguments_valid = True
        secret_arguments: list[dict[str, Any]] = []
        allowed = {
            (rule.action, _canonical(rule.expected_arguments))
            for rule in record.episode.allowed_next_actions
        }
        reply_blob = list(record.mock_tool_world["user_replies"].values())
        for event in gold:
            arguments_valid &= (
                event["name"] in public_by_name
                and (event["name"], _canonical(event["arguments"])) in allowed
            )
            signature = public_by_name.get(event["name"], {}).get("arguments", {})
            arguments_valid &= set(event["arguments"]) == set(signature)
            for key, value in event["arguments"].items():
                spec = signature.get(key)
                if isinstance(spec, dict) and isinstance(spec.get("enum"), list):
                    arguments_valid &= value in spec["enum"]
                elif isinstance(spec, dict) and spec.get("type") == "boolean":
                    arguments_valid &= isinstance(value, bool)
                grounded = _contains(trace_blob, value) or _contains(reply_blob, value)
                if not grounded:
                    secret_arguments.append({"event": event["name"], "argument": key})

        exact = execute_events(record, gold).success
        legal = legal_terminal_sequences(record)
        public_impacting = {item["action"] for item in contract if item["user_impacting"]}
        irreversible = {
            rule.action for rule in record.episode.allowed_next_actions if rule.irreversible
        }
        blind_surface = {"trace": trace_blob, "catalog": catalog}
        rows.append({
            "task_id": record.episode.task_id,
            "family": record.episode.split_meta.template_family,
            "domain": record.episode.domain,
            "schema_loaded": True,
            "provenance_valid": provenance_ok,
            "human_values_grounded": known_values_grounded,
            "exact_oracle_execution": exact,
            "unique_legal_terminal_without_phi": len(legal) == 1 and legal[0] == gold,
            "legal_terminal_sequence_count_without_phi": len(legal),
            "public_arguments_valid": arguments_valid,
            "secret_arguments": secret_arguments,
            "impact_consistent": public_impacting == irreversible,
            "gold_ends_irreversible": bool(gold and gold[-1]["name"] in irreversible),
            "catalog_permutation_safe": catalog_ok,
            "gold_sequence_not_catalog_prefix": gold_not_catalog_prefix,
            "blind_surface_evaluator_key_leaks": sorted(_keys(blind_surface) & BLIND_FORBIDDEN_KEYS),
        })

    overlap = _module("confirmatory_v3_overlap", ROOT / "scripts/audit_candidate_dev_overlap.py")
    development = _raw_records(DEV_FILES, "development")
    dev_overlap = overlap.audit(raw, development, lexical_threshold=.80, top_k=25)
    getters = {
        "task_id": lambda item: item["task_id"],
        "family_id": lambda item: item["episode"].get("split_meta", {}).get("template_family"),
        "entity_pool": lambda item: item["episode"].get("split_meta", {}).get("entity_pool"),
        "exact_trace_hash": lambda item: overlap.digest(item["trace"]),
        "normalized_trace_hash": lambda item: overlap.digest(overlap.normalized_trace(item["trace"])),
        "exact_action_graph_hash": lambda item: overlap.digest(
            overlap.action_graph(item["episode"], normalized=False)
        ),
        "normalized_action_graph_hash": lambda item: overlap.digest(
            overlap.action_graph(item["episode"], normalized=True)
        ),
    }
    internal = {name: _duplicate_groups(raw, getter) for name, getter in getters.items()}
    baseline = _module("confirmatory_v3_baselines", ROOT / "scripts/leakage_baselines.py")
    leakage = baseline.evaluate(records)
    leakage_counts = {
        method: sum(row["success"] for row in leakage["rows"] if row["method"] == method)
        for method in ("catalog_only", "predicate_only", "name_only", "exact_copy")
    }

    hard_checks = {
        "load_and_schema_200": len(records) == 200,
        "five_domains_x_40": domains == Counter(EXPECTED_DOMAINS),
        "task_ids_unique": len(set(ids)) == 200,
        "families_unique": len(set(families)) == 200 and None not in families,
        "exact_oracle_200": sum(row["exact_oracle_execution"] for row in rows) == 200,
        "unique_legal_terminal_without_phi_200": sum(
            row["unique_legal_terminal_without_phi"] for row in rows
        ) == 200,
        "provenance_200": sum(row["provenance_valid"] for row in rows) == 200,
        "human_values_grounded_200": sum(row["human_values_grounded"] for row in rows) == 200,
        "irreversible_arguments_grounded_200": sum(not row["secret_arguments"] for row in rows) == 200,
        "public_arguments_valid_200": sum(row["public_arguments_valid"] for row in rows) == 200,
        "impact_consistent_200": sum(row["impact_consistent"] for row in rows) == 200,
        "gold_terminal_is_irreversible_200": sum(row["gold_ends_irreversible"] for row in rows) == 200,
        "catalog_permutation_safe_200": sum(row["catalog_permutation_safe"] for row in rows) == 200,
        "blind_surface_has_no_evaluator_keys": not any(
            row["blind_surface_evaluator_key_leaks"] for row in rows
        ),
        "no_internal_identity_or_trace_collision": not any(
            internal[key] for key in (
                "task_id", "family_id", "entity_pool", "exact_trace_hash", "normalized_trace_hash"
            )
        ),
        "no_dev_identity_exact_or_trace_collision": not any(
            dev_overlap["collisions"][key] for key in (
                "family_id", "entity_pool", "generator_seed", "exact_trace_hash",
                "normalized_trace_hash", "exact_action_graph_hash",
            )
        ),
        "exact_copy_oracle_200": leakage_counts["exact_copy"] == 200,
    }
    return {
        "format": "handoffbench-confirmatory-v3-final-audit-v1",
        "status": "pass_unsealed" if all(hard_checks.values()) else "fail_unsealed",
        "model_calls": 0,
        "hard_checks": hard_checks,
        "summary": {
            "tasks": len(records), "domains": dict(sorted(domains.items())),
            "exact_oracle_execution": sum(row["exact_oracle_execution"] for row in rows),
            "unique_legal_terminal_without_phi": sum(
                row["unique_legal_terminal_without_phi"] for row in rows
            ),
            "provenance_valid": sum(row["provenance_valid"] for row in rows),
            "irreversible_arguments_grounded": sum(not row["secret_arguments"] for row in rows),
            "impact_consistent": sum(row["impact_consistent"] for row in rows),
            "catalog_permutation_safe": sum(row["catalog_permutation_safe"] for row in rows),
            "gold_sequence_not_catalog_prefix": sum(
                row["gold_sequence_not_catalog_prefix"] for row in rows
            ),
            "development_normalized_topology_flags": len(
                dev_overlap["collisions"]["normalized_action_graph_hash"]
            ),
            "development_lexical_near_duplicates": len(dev_overlap["lexical_near_duplicates"]),
            "internal_duplicate_groups": {key: len(value) for key, value in internal.items()},
            "leakage_successes": leakage_counts,
        },
        "diagnostic_policy": {
            "hard": "Only hard_checks gate readiness.",
            "reported_not_automatic_rejection": [
                "normalized action-graph overlap", "internal action-graph reuse",
                "lexical near-duplicate flags", "catalog/name/predicate-only probe success",
            ],
        },
        "candidate_vs_development": dev_overlap,
        "candidate_internal": internal,
        "leakage_baselines": leakage,
        "tasks": rows,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Confirmatory v3 final static audit", "",
        f"Status: **{report['status']}**. No model/provider call was made.", "",
        "## Hard gates", "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — `{name}`"
        for name, passed in report["hard_checks"].items()
    )
    lines += [
        "", "## Recomputed diagnostics", "",
        f"- Tasks/domain counts: {summary['tasks']} / {summary['domains']}.",
        f"- Unique legal terminal sequence without Phi: {summary['unique_legal_terminal_without_phi']}/200.",
        f"- Development normalized-topology flags: {summary['development_normalized_topology_flags']}.",
        f"- Development lexical pairs at Jaccard >= .80: {summary['development_lexical_near_duplicates']}.",
        f"- Internal duplicate groups: `{summary['internal_duplicate_groups']}`.",
        f"- Shallow success counts: `{summary['leakage_successes']}`.", "",
        "Normalized topology, lexical similarity, internal action-graph reuse, and shallow-probe "
        "success are reported diagnostics rather than automatic rejection rules. Identity, exact/"
        "normalized trace, exact development graph, provenance, grounding, impact, executability, "
        "and uniqueness checks are fail-closed hard gates.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-files", type=Path, nargs="+", default=list(DEFAULT_FILES))
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-markdown", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    report = audit(args.task_files)
    if args.verify_only:
        if not args.output_json:
            raise ValueError("--verify-only requires --output-json")
        existing = json.loads(args.output_json.read_text(encoding="utf-8"))
        if existing != report:
            raise ValueError("stored final audit differs from deterministic recomputation")
    else:
        for path in (args.output_json, args.output_markdown):
            if path and path.exists():
                raise FileExistsError(f"refusing to overwrite: {path}")
        if args.output_json:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.output_markdown:
            args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.output_markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "summary": report["summary"]}, indent=2))
    return 0 if report["status"] == "pass_unsealed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
