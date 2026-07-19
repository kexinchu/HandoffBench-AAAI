"""Audit the candidate oracle-name/canonical-argument leakage diagnostic."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from handoffbench.dataset import TaskRecord, execute_events, load_tasks
from handoffbench.prompts import action_catalog


ROOT = Path(__file__).parents[1]
TASK_FILES = (
    ROOT / "data/tasks/candidate/travel_commerce.json",
    ROOT / "data/tasks/candidate/procurement_it.json",
    ROOT / "data/tasks/candidate/scheduling.json",
)


def _name_predictor():
    spec = importlib.util.spec_from_file_location("leakage_baselines", ROOT / "scripts/leakage_baselines.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def wilson(successes: int, n: int, z: float = 1.96) -> list[float]:
    if not n:
        return [math.nan, math.nan]
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [centre - radius, centre + radius]


def _argument_probability(spec: Any) -> float:
    if isinstance(spec, dict) and spec.get("enum"):
        return 1 / len(spec["enum"])
    if isinstance(spec, dict) and spec.get("type") == "boolean":
        return 0.5
    return 0.0


def task_features(record: TaskRecord, baseline: Any) -> dict[str, Any]:
    gold = record.episode.success_predicate.args["required_events"]
    catalog = {item["name"]: item for item in action_catalog(record)}
    probability = 1.0
    positions = []
    for event in gold:
        signature = catalog[event["name"]]["arguments"]
        for key, value in event["arguments"].items():
            spec = signature[key]
            probability *= _argument_probability(spec)
            if isinstance(spec, dict) and spec.get("enum"):
                positions.append(spec["enum"].index(value))
    predicted = baseline.predict(record, "name_only")
    success = execute_events(record, predicted).success
    return {
        "task_id": record.episode.task_id,
        "template_family": record.episode.split_meta.template_family,
        "domain": record.episode.domain,
        "sequence_length": len(gold),
        "enum_position_pattern": ",".join(map(str, positions)) if positions else "none",
        "enum_positions": positions,
        "uniform_argument_success_probability": probability,
        "name_first_success": bool(success),
    }


def _strata(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    result = []
    for value, items in sorted(groups.items()):
        successes = sum(item["name_first_success"] for item in items)
        result.append({
            "stratum": value, "n": len(items), "successes": successes,
            "success_rate": successes / len(items), "wilson_95": wilson(successes, len(items)),
            "uniform_random_expected_rate": sum(
                item["uniform_argument_success_probability"] for item in items
            ) / len(items),
        })
    return result


def poisson_binomial_tail(probabilities: list[float], observed: int) -> float:
    distribution = [1.0] + [0.0] * len(probabilities)
    for probability in probabilities:
        for count in range(len(probabilities), 0, -1):
            distribution[count] = distribution[count] * (1 - probability) + distribution[count - 1] * probability
        distribution[0] *= 1 - probability
    return sum(distribution[observed:])


def audit(records: list[TaskRecord], *, draws: int = 10000, seed: int = 2027) -> dict[str, Any]:
    baseline = _name_predictor()
    rows = [task_features(record, baseline) for record in records]
    successes = sum(row["name_first_success"] for row in rows)
    probabilities = [row["uniform_argument_success_probability"] for row in rows]
    rng = random.Random(seed)
    bootstrap = sorted(
        sum(rng.choice(rows)["name_first_success"] for _ in rows) / len(rows)
        for _ in range(draws)
    )
    all_positions = Counter(position for row in rows for position in row["enum_positions"])
    majority_position = min(position for position, count in all_positions.items()
                            if count == max(all_positions.values()))
    # The implemented name-only diagnostic guesses enum index zero. In this pool,
    # that is exactly the global enum-position majority rule.
    majority_successes = successes if majority_position == 0 else None
    return {
        "status": "static_candidate_audit_no_model_calls",
        "probe_definition": (
            "oracle action-name sequence plus canonical first-enum/false/unknown argument guesses; "
            "not a pure action-name-only learner"
        ),
        "n": len(rows),
        "observed": {
            "successes": successes, "rate": successes / len(rows),
            "wilson_95": wilson(successes, len(rows)),
            "family_bootstrap_95": [bootstrap[int(.025 * draws)], bootstrap[int(.975 * draws) - 1]],
        },
        "uniform_argument_random": {
            "expected_successes": sum(probabilities),
            "expected_rate": sum(probabilities) / len(rows),
            "poisson_binomial_tail_p": poisson_binomial_tail(probabilities, successes),
        },
        "global_enum_position_majority": {
            "position_counts": dict(sorted(all_positions.items())),
            "majority_position": majority_position,
            "successes": majority_successes,
            "rate": majority_successes / len(rows) if majority_successes is not None else None,
        },
        "strata": {
            "domain": _strata(rows, "domain"),
            "sequence_length": _strata(rows, "sequence_length"),
            "enum_position_pattern": _strata(rows, "enum_position_pattern"),
        },
        "successful_families": [
            {key: row[key] for key in ("task_id", "template_family", "domain", "sequence_length",
                                        "enum_position_pattern")}
            for row in rows if row["name_first_success"]
        ],
        "interpretation": (
            "The diagnostic is above uniform argument chance, but its 34.5% rate equals the global "
            "first-enum-position majority baseline. It demonstrates combined oracle-name exposure "
            "and enum-order imbalance, not independently identified action-name leakage."
        ),
        "recommended_paper_wording": (
            "An oracle-name/canonical-argument diagnostic succeeds on 69/200 tasks (34.5%; report CI), "
            "versus 13.9% expected under uniform argument guessing. Because index 0 is the global "
            "enum-position majority and the probe is given the gold action names, this is a material "
            "combined interface/ordering leakage diagnostic, not evidence that action names alone solve 34.5%."
        ),
        "rows": rows,
    }


def markdown(report: dict[str, Any]) -> str:
    observed, chance = report["observed"], report["uniform_argument_random"]
    lines = [
        "# Action-name diagnostic audit", "",
        "Static candidate audit; no model calls. The existing `name_only` label is a misnomer: the probe receives the oracle action-name sequence and guesses canonical arguments.", "",
        f"Observed: **{observed['successes']}/{report['n']} ({observed['rate']:.1%})**, Wilson 95% CI [{observed['wilson_95'][0]:.1%}, {observed['wilson_95'][1]:.1%}], family bootstrap 95% CI [{observed['family_bootstrap_95'][0]:.1%}, {observed['family_bootstrap_95'][1]:.1%}].",
        f"Uniform argument guessing: expected **{chance['expected_successes']:.2f}/{report['n']} ({chance['expected_rate']:.1%})**; Poisson-binomial tail p={chance['poisson_binomial_tail_p']:.3g}.", "",
        f"Enum positions: {report['global_enum_position_majority']['position_counts']}. The index-0 majority baseline is identical to the implemented probe and also succeeds on {report['global_enum_position_majority']['successes']}/{report['n']}.", "",
        "## Interpretation", "", report["interpretation"], "",
        "## Recommended paper correction", "", report["recommended_paper_wording"], "",
    ]
    for name, items in report["strata"].items():
        lines += [f"## By {name.replace('_', ' ')}", "", "| Stratum | n | success | Wilson 95% CI | uniform chance |", "|---|---:|---:|---:|---:|"]
        for item in items:
            lines.append(f"| {item['stratum']} | {item['n']} | {item['success_rate']:.1%} | [{item['wilson_95'][0]:.1%}, {item['wilson_95'][1]:.1%}] | {item['uniform_random_expected_rate']:.1%} |")
        lines.append("")
    lines += ["## Successful families (69)", ""]
    lines.extend(f"- `{item['task_id']}` / `{item['template_family']}` ({item['domain']}; length {item['sequence_length']}; enum pattern {item['enum_position_pattern']})"
                 for item in report["successful_families"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    parser.add_argument("--bootstrap-draws", type=int, default=10000)
    args = parser.parse_args()
    records = sum((load_tasks(path) for path in TASK_FILES), [])
    report = audit(records, draws=args.bootstrap_draws)
    for path in (args.output_json, args.output_markdown):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_markdown.write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
