"""Exploratory subgroup analyses over validated confirmatory inputs.

This module is deliberately separate from the sealed, preregistered confirmatory
analysis.  Its outputs are post-confirmatory and do not receive confirmatory
multiplicity-adjusted inference.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from handoffbench.confirmatory_analysis import ADVISORY_FACTORIAL, STRUCTURED_CONDITION


ANALYSIS_CONTRACT = "post_confirmatory_v1"
ANALYSIS_STATUS = "exploratory"
CHECKS_OFF = tuple(
    condition for condition in ADVISORY_FACTORIAL if "__absent__advisory" in condition
)
CHECKS_ON = tuple(
    condition for condition in ADVISORY_FACTORIAL if "__executable__advisory" in condition
)


def _strict_success(run: dict[str, Any]) -> float:
    return float(run.get("status") == "ok" and bool(run.get("success")))


def _percentile_interval(values: list[float], draws: int) -> list[float]:
    values.sort()
    return [values[int(0.025 * draws)], values[max(0, int(0.975 * draws) - 1)]]


def _cluster_bootstrap(
    family_values: dict[str, list[float]],
    *,
    draws: int,
    seed: int,
) -> dict[str, Any]:
    if draws < 100:
        raise ValueError("at least 100 bootstrap draws are required")
    family_ids = sorted(family_values)
    if not family_ids or any(not family_values[family] for family in family_ids):
        raise ValueError("family-cluster bootstrap requires non-empty family observations")
    point = mean(value for family in family_ids for value in family_values[family])
    rng = random.Random(seed)
    bootstrap = []
    for _ in range(draws):
        selected = [rng.choice(family_ids) for _ in family_ids]
        bootstrap.append(mean(value for family in selected for value in family_values[family]))
    return {
        "effect": point,
        "family_cluster_bootstrap_ci": _percentile_interval(bootstrap, draws),
        "n_families": len(family_ids),
        "n_paired_units": sum(len(values) for values in family_values.values()),
    }


def domains_from_validated_inputs(provenance: dict[str, Any]) -> dict[str, str]:
    """Recover task domains only from candidate files already validated by the loader."""
    domain_by_task: dict[str, str] = {}
    candidate_files = provenance.get("candidate_files")
    if not isinstance(candidate_files, list) or not candidate_files:
        raise ValueError("validated provenance does not identify candidate files")
    for filename in candidate_files:
        payload = json.loads(Path(filename).read_text(encoding="utf-8"))
        for item in payload:
            try:
                episode = item["episode"]
                task_id, domain = episode["task_id"], episode["domain"]
            except (KeyError, TypeError) as error:
                raise ValueError("validated task lacks task_id or domain") from error
            if not isinstance(domain, str) or not domain:
                raise ValueError(f"validated task has invalid domain: {task_id}")
            if task_id in domain_by_task:
                raise ValueError(f"duplicate task while recovering domains: {task_id}")
            domain_by_task[task_id] = domain
    return domain_by_task


def _index_runs(runs: list[dict[str, Any]]) -> dict[tuple[str, str, int, str], dict[str, Any]]:
    indexed: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for run in runs:
        key = (run["task_id"], run["model"], int(run["seed"]), run["method"])
        if key in indexed:
            raise ValueError(f"duplicate run in post-confirmatory input: {key}")
        indexed[key] = run
    return indexed


def _paired_effects(
    *,
    task_ids: list[str],
    models: list[str],
    seeds: list[int],
    indexed: dict[tuple[str, str, int, str], dict[str, Any]],
    families: dict[str, str],
    domains: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checks, structured = [], []
    required = {"gold_oracle", STRUCTURED_CONDITION, *CHECKS_OFF, *CHECKS_ON}
    for task_id in task_ids:
        for model in models:
            for run_seed in seeds:
                missing = [
                    method
                    for method in required
                    if (task_id, model, run_seed, method) not in indexed
                ]
                if missing:
                    raise ValueError(
                        "missing run needed for post-confirmatory pairing: "
                        f"{(task_id, model, run_seed, sorted(missing)[0])}"
                    )
                off = mean(
                    _strict_success(indexed[(task_id, model, run_seed, method)])
                    for method in CHECKS_OFF
                )
                on = mean(
                    _strict_success(indexed[(task_id, model, run_seed, method)])
                    for method in CHECKS_ON
                )
                oracle = _strict_success(
                    indexed[(task_id, model, run_seed, "gold_oracle")]
                )
                target = _strict_success(
                    indexed[(task_id, model, run_seed, STRUCTURED_CONDITION)]
                )
                common = {
                    "task_id": task_id,
                    "family": families[task_id],
                    "domain": domains[task_id],
                    "model": model,
                    "seed": run_seed,
                }
                checks.append(common | {"effect": on - off})
                structured.append(common | {"effect": target - oracle})
    return checks, structured


def _estimate(
    rows: list[dict[str, Any]],
    *,
    draws: int,
    seed: int,
) -> dict[str, Any]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["family"]].append(float(row["effect"]))
    return _cluster_bootstrap(grouped, draws=draws, seed=seed)


def _stratify(
    rows: list[dict[str, Any]],
    key: str | Callable[[dict[str, Any]], str],
    *,
    draws: int,
    seed: int,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        label = key(row) if callable(key) else str(row[key])
        grouped[label].append(row)
    return {
        label: _estimate(grouped[label], draws=draws, seed=seed)
        for label in sorted(grouped)
    }


def _checks_model_differences(
    checks: list[dict[str, Any]],
    models: list[str],
) -> list[dict[str, Any]]:
    if len(models) != 2:
        raise ValueError("checks model difference requires exactly two models")
    first, second = models
    indexed = {
        (row["task_id"], row["seed"], row["model"]): row for row in checks
    }
    differences = []
    blocks = sorted({(row["task_id"], row["seed"]) for row in checks})
    for task_id, run_seed in blocks:
        left = indexed.get((task_id, run_seed, first))
        right = indexed.get((task_id, run_seed, second))
        if left is None or right is None:
            raise ValueError(f"incomplete model pairing for checks interaction: {task_id}")
        differences.append(
            {
                "task_id": task_id,
                "family": left["family"],
                "domain": left["domain"],
                "seed": run_seed,
                "effect": left["effect"] - right["effect"],
            }
        )
    return differences


def analyze_post_confirmatory(
    manifest: dict[str, Any],
    runs: list[dict[str, Any]],
    families: dict[str, str],
    domains: dict[str, str],
    *,
    draws: int = 10_000,
    seed: int = 2027,
) -> dict[str, Any]:
    """Compute explicitly exploratory strict-success subgroup contrasts."""
    if draws < 100:
        raise ValueError("at least 100 bootstrap draws are required")
    design = manifest["confirmatory_design"]
    models = list(design["models"])
    seeds = [int(value) for value in design["seeds"]]
    task_ids = sorted(families)
    if set(domains) != set(task_ids):
        raise ValueError("domain mapping must exactly cover the validated task IDs")
    if len(set(families.values())) != len(families):
        raise ValueError("post-confirmatory analysis requires independent task families")

    checks, structured = _paired_effects(
        task_ids=task_ids,
        models=models,
        seeds=seeds,
        indexed=_index_runs(runs),
        families=families,
        domains=domains,
    )
    model_difference = _checks_model_differences(checks, models)
    model_contrast = f"{models[0]} minus {models[1]}"

    def strata(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "by_model": _stratify(rows, "model", draws=draws, seed=seed),
            "by_domain": _stratify(rows, "domain", draws=draws, seed=seed),
            "by_model_domain": _stratify(
                rows,
                lambda row: f"{row['model']}|{row['domain']}",
                draws=draws,
                seed=seed,
            ),
        }

    return {
        "analysis_contract": ANALYSIS_CONTRACT,
        "analysis_status": ANALYSIS_STATUS,
        "confirmatory_inference": False,
        "multiplicity_correction": "none; exploratory estimates only",
        "endpoint": "strict_success_intention_to_treat",
        "bootstrap": {
            "unit": "template_family",
            "method": "percentile family-cluster bootstrap",
            "draws": draws,
            "seed": seed,
            "rng_policy": "each reported estimate initializes Python random.Random(seed)",
        },
        "n_tasks": len(task_ids),
        "n_families": len(set(families.values())),
        "n_models": len(models),
        "n_seeds": len(seeds),
        "n_validated_runs": len(runs),
        "models": models,
        "domains": sorted(set(domains.values())),
        "estimands": {
            "advisory_checks_main_effect": {
                "definition": "mean strict success(checks executable) minus checks absent, "
                "averaged over typing and provenance in the advisory 2x2x2 factorial",
                **strata(checks),
            },
            "structured_vs_oracle": {
                "definition": f"strict success({STRUCTURED_CONDITION}) minus gold_oracle",
                **strata(structured),
            },
            "checks_model_difference_interaction": {
                "definition": "difference between model-specific advisory checks main effects",
                "contrast": model_contrast,
                "overall": _estimate(model_difference, draws=draws, seed=seed),
                "by_domain": _stratify(
                    model_difference, "domain", draws=draws, seed=seed
                ),
            },
        },
    }
