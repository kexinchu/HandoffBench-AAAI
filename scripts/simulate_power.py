#!/usr/bin/env python3
"""Pre-freeze power simulation for paired confirmatory HandoffBench outcomes.

The simulation never reads candidate/test tasks or model outputs.  Baseline rate
and effect sizes are planning assumptions to be estimated on development data
and then locked before confirmatory evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np


DEFAULT_N = (80, 120, 160, 200)
DEFAULT_ICC = (0.05, 0.10, 0.20)
DEFAULT_EFFECTS = (0.05, 0.08, 0.10)


def _csv_numbers(text: str, cast=float) -> tuple:
    values = tuple(cast(value.strip()) for value in text.split(",") if value.strip())
    if not values:
        raise argparse.ArgumentTypeError("list must not be empty")
    return values


def latent_sd(icc: float) -> float:
    """Random-intercept SD under the logistic latent-variable ICC convention."""
    if not 0 <= icc < 1:
        raise ValueError("ICC must lie in [0, 1)")
    return math.sqrt((icc * math.pi**2 / 3) / (1 - icc))


def _logit(value: float) -> float:
    return math.log(value / (1 - value))


def simulate_cell(
    *, n_families: int, icc: float, effect: float, baseline_rate: float,
    n_models: int, n_seeds: int, replications: int, bootstrap_draws: int,
    alpha: float, rng: np.random.Generator,
) -> dict:
    """Estimate power using paired family-cluster percentile-bootstrap CIs."""
    if n_families < 2 or n_models < 1 or n_seeds < 1:
        raise ValueError("families must be >=2 and models/seeds >=1")
    if not 0 < baseline_rate < 1 or not 0 <= effect < 1:
        raise ValueError("baseline_rate must be in (0,1) and effect in [0,1)")
    model_offsets = np.linspace(-0.30, 0.30, n_models) if n_models > 1 else np.zeros(1)
    significant = 0
    estimates: list[float] = []
    discordances: list[float] = []
    for _ in range(replications):
        family_effect = rng.normal(0, latent_sd(icc), size=(n_families, 1, 1))
        logits = _logit(baseline_rate) + family_effect + model_offsets[None, :, None]
        control_probability = 1 / (1 + np.exp(-logits))
        control_probability = np.broadcast_to(control_probability, (n_families, n_models, n_seeds))
        treatment_probability = np.minimum(control_probability + effect, 1.0)
        control = rng.binomial(1, control_probability)
        treatment = rng.binomial(1, treatment_probability)
        paired = treatment - control
        # Models and seeds are repeated observations within a family, never new sample units.
        family_difference = paired.mean(axis=(1, 2))
        estimate = float(family_difference.mean())
        estimates.append(estimate)
        discordances.append(float((paired != 0).mean()))
        indices = rng.integers(0, n_families, size=(bootstrap_draws, n_families))
        boot = family_difference[indices].mean(axis=1)
        lower, upper = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
        significant += int(lower > 0 or upper < 0)
    power = significant / replications
    mc_se = math.sqrt(power * (1 - power) / replications)
    return {"n_families": n_families, "icc": icc, "target_absolute_effect": effect,
            "estimated_effect": float(np.mean(estimates)),
            "mean_discordance": float(np.mean(discordances)), "power": power,
            "power_mc_se": mc_se, "replications": replications,
            "bootstrap_draws": bootstrap_draws}


def simulate_grid(
    *, sample_sizes: Iterable[int] = DEFAULT_N, iccs: Iterable[float] = DEFAULT_ICC,
    effects: Iterable[float] = DEFAULT_EFFECTS, baseline_rate: float = 0.55,
    n_models: int = 2, n_seeds: int = 1, replications: int = 1000,
    bootstrap_draws: int = 1000, alpha: float = 0.05, random_seed: int = 270127,
) -> dict:
    rng = np.random.default_rng(random_seed)
    cells = [simulate_cell(n_families=n, icc=icc, effect=effect,
                           baseline_rate=baseline_rate, n_models=n_models, n_seeds=n_seeds,
                           replications=replications, bootstrap_draws=bootstrap_draws,
                           alpha=alpha, rng=rng)
             for effect in effects for icc in iccs for n in sample_sizes]
    return {
        "design": {"analysis": "paired family-cluster percentile bootstrap",
                   "inference_unit": "independent task family",
                   "models_and_seeds": "repeated measurements nested within family",
                   "baseline_rate": baseline_rate, "n_models": n_models, "n_seeds": n_seeds,
                   "alpha_two_sided": alpha, "random_seed": random_seed,
                   "latent_icc_convention": "logistic random intercept; residual variance pi^2/3",
                   "treatment_model": "conditional treatment probability = min(control probability + absolute effect, 1)",
                   "data_policy": "planning assumptions only; no candidate/test/model outputs read"},
        "cells": cells,
    }


def markdown_report(result: dict) -> str:
    design = result["design"]
    lines = ["# HandoffBench confirmatory power simulation", "",
             "This is a pre-freeze planning simulation, not experimental evidence. The independent sample ",
             "unit is the task family. Model and seed repetitions are averaged within family and never ",
             "counted as independent samples.", "", "## Assumptions", "",
             f"- Analysis: {design['analysis']}.",
             f"- Baseline success planning value: {design['baseline_rate']:.3f}.",
             f"- Models per family: {design['n_models']}; seeds per model/family: {design['n_seeds']}.",
             f"- Two-sided alpha: {design['alpha_two_sided']}; RNG seed: {design['random_seed']}.",
             f"- ICC: {design['latent_icc_convention']}.",
             f"- DGP: {design['treatment_model']}.",
             "- The baseline rate/effect/ICC grid must be justified from development data and locked before test.",
             "", "## Estimated power", "",
             "| N families | ICC | Target Δ | Simulated Δ | Discordance | Power | MC SE |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for cell in result["cells"]:
        lines.append(f"| {cell['n_families']} | {cell['icc']:.2f} | "
                     f"{cell['target_absolute_effect']:.2f} | {cell['estimated_effect']:.3f} | "
                     f"{cell['mean_discordance']:.3f} | {cell['power']:.3f} | "
                     f"{cell['power_mc_se']:.3f} |")
    lines += ["", "## Interpretation constraints", "",
              "Power depends on the assumed baseline, discordance, effect model, ICC, and model heterogeneity. ",
              "Seeds reduce Monte Carlo noise but cannot replace independent families. This simulation does not ",
              "authorize optional stopping or sample-size changes after inspecting confirmatory outcomes.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-sizes", default="80,120,160,200")
    parser.add_argument("--iccs", default=".05,.10,.20")
    parser.add_argument("--effects", default=".05,.08,.10")
    parser.add_argument("--baseline-rate", type=float, default=.55)
    parser.add_argument("--models", type=int, default=2)
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--replications", type=int, default=1000)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    parser.add_argument("--alpha", type=float, default=.05)
    parser.add_argument("--random-seed", type=int, default=270127)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    result = simulate_grid(sample_sizes=_csv_numbers(args.sample_sizes, int),
                           iccs=_csv_numbers(args.iccs), effects=_csv_numbers(args.effects),
                           baseline_rate=args.baseline_rate, n_models=args.models, n_seeds=args.seeds,
                           replications=args.replications, bootstrap_draws=args.bootstrap_draws,
                           alpha=args.alpha, random_seed=args.random_seed)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    args.output_prefix.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    args.output_prefix.with_suffix(".md").write_text(markdown_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
