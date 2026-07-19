"""Fail-closed confirmatory analysis over sealed tasks and immutable raw runs."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable


FACTOR_NAMES = ("typing", "provenance", "checks")
TERMS = (("typing",), ("provenance",), ("checks",), ("typing", "provenance"),
         ("typing", "checks"), ("provenance", "checks"), FACTOR_NAMES)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def load_and_validate(manifest_path: str | Path, run_dirs: list[str | Path]) -> tuple[dict, list[dict], dict]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sealed") is not True or manifest.get("n_tasks") != 200:
        raise ValueError("confirmatory manifest must be sealed and contain exactly 200 tasks")
    design = manifest.get("confirmatory_design")
    if not isinstance(design, dict) or not all(key in design for key in
                                               ("models", "seeds", "conditions", "config_hashes")):
        raise ValueError("sealed manifest lacks confirmatory_design")
    if len(design["models"]) < 2 or not design["seeds"]:
        raise ValueError("confirmatory design requires at least two models and one seed")
    factorial = [condition for condition in design["conditions"] if _factor_levels(condition)]
    if len(factorial) != 8 or any(not condition.endswith("__advisory") for condition in factorial):
        raise ValueError("confirmatory design requires the complete advisory 2x2x2 cube")
    if not {"structured_payload", "gold_oracle"} <= set(design["conditions"]):
        raise ValueError("confirmatory design lacks Structured or Gold Oracle")

    base = manifest_path.parent
    task_file = _resolve(base, manifest["task_file"])
    if sha256(task_file) != manifest["task_file_sha256"]:
        raise ValueError("sealed task file hash drift")
    tasks = json.loads(task_file.read_text(encoding="utf-8"))
    task_ids = [item["episode"]["task_id"] for item in tasks]
    families = {item["episode"]["task_id"]: item["episode"]["split_meta"]["template_family"]
                for item in tasks}
    if len(task_ids) != 200 or len(set(families.values())) != 200:
        raise ValueError("sealed tasks are not 200 independent families")
    for item in tasks:
        task_id = item["episode"]["task_id"]
        if canonical_hash(item) != manifest["task_hashes"].get(task_id):
            raise ValueError(f"sealed task hash drift: {task_id}")
    for value, expected in manifest.get("protocol_file_hashes", {}).items():
        path = _resolve(base, value)
        if sha256(path) != expected:
            raise ValueError(f"sealed protocol hash drift: {path}")

    paths: list[Path] = []
    for directory in map(Path, run_dirs):
        resolved = directory.resolve()
        if any(part.lower() == "dev" or "invalid_protocol" in part.lower() for part in resolved.parts):
            raise ValueError(f"contaminated run directory is forbidden: {resolved}")
        paths.extend(sorted(resolved.rglob("*.json")))
    if not paths:
        raise ValueError("no raw runs found")
    runs, run_files = [], {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = payload if isinstance(payload, list) else [payload]
        for index, run in enumerate(values):
            if not isinstance(run, dict):
                raise ValueError(f"invalid run record in {path}")
            run = dict(run); run["_source_file"] = f"{path}#{index}"
            runs.append(run)
        run_files[str(path)] = sha256(path)

    scheduled = set(itertools.product(task_ids, design["models"],
                                      [int(seed) for seed in design["seeds"]], design["conditions"]))
    observed: dict[tuple[str, str, int, str], dict] = {}
    for run in runs:
        key = (run.get("task_id"), run.get("model"), int(run.get("seed")), run.get("method"))
        if key not in scheduled:
            raise ValueError(f"unscheduled/dev/foreign run contaminates confirmatory input: {key}")
        if key in observed:
            raise ValueError(f"duplicate scheduled run: {key}")
        observed[key] = run
        config_key = f"{key[1]}|{key[2]}|{key[3]}"
        expected_hash = design["config_hashes"].get(config_key)
        if expected_hash is None or run.get("config_hash") != expected_hash:
            raise ValueError(f"config hash drift: {key}")
        config = run.get("config")
        if not isinstance(config, dict) or canonical_hash(config) != run["config_hash"]:
            raise ValueError(f"run config content/hash mismatch: {key}")
        metrics = run.get("metrics")
        validator_cost = metrics.get("validator_cost") if isinstance(metrics, dict) else None
        if (not isinstance(validator_cost, (int, float)) or isinstance(validator_cost, bool)
                or not math.isfinite(float(validator_cost)) or validator_cost < 0):
            raise ValueError(f"missing or invalid required validator_cost metric: {key}")
    missing = scheduled - set(observed)
    if missing:
        example = sorted(missing)[0]
        raise ValueError(f"incomplete confirmatory pairing: {len(missing)} missing; first={example}")
    _audit_shared_sources(list(observed.values()), factorial)
    ordered = [observed[key] for key in sorted(scheduled)]
    provenance = {"sealed_manifest": str(manifest_path), "sealed_manifest_sha256": sha256(manifest_path),
                  "task_file": str(task_file), "task_file_sha256": sha256(task_file),
                  "raw_run_files": run_files, "n_raw_runs": len(ordered)}
    return manifest, ordered, {"families": families, "provenance": provenance}


def _factor_levels(condition: str) -> dict[str, int] | None:
    parts = condition.split("__")
    if len(parts) != 4 or parts[0] not in {"free_form", "typed"} or \
            parts[1] not in {"absent", "trace_linked"} or \
            parts[2] not in {"absent", "executable"} or parts[3] != "advisory":
        return None
    return {"typing": 1 if parts[0] == "typed" else -1,
            "provenance": 1 if parts[1] == "trace_linked" else -1,
            "checks": 1 if parts[2] == "executable" else -1}


def _audit_shared_sources(runs: list[dict], factorial: list[str]) -> None:
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for run in runs:
        if run["method"] in factorial:
            groups[(run["task_id"], run["model"], int(run["seed"]))].append(run)
    for block, items in groups.items():
        if len(items) != 8:
            raise ValueError(f"incomplete factorial source block: {block}")
        signatures = set()
        for run in items:
            calls = run.get("calls") or []
            if not calls:
                raise ValueError(f"factorial run lacks source call: {block}")
            call = calls[0]
            signatures.add((run.get("source_hash") or call.get("source_output_hash"),
                            call.get("prompt_hash"), call.get("response_schema_hash"),
                            canonical_hash(call.get("usage"))))
        if len(signatures) != 1 or None in next(iter(signatures)):
            raise ValueError(f"factorial shared-source hash/config drift: {block}")


def _metric(run: dict, name: str) -> float:
    metrics = run.get("metrics") if isinstance(run.get("metrics"), dict) else {}
    if name == "strict_success": return float(run.get("status") == "ok" and bool(run.get("success")))
    if name == "macro_state_f1": return float(metrics.get(name, 0)) if run.get("status") == "ok" else 0.0
    if name == "critical_errors": return float(metrics.get(name, 0))
    if name in {"input_tokens", "output_tokens", "validator_cost"}:
        if name in metrics and metrics[name] is not None: return float(metrics[name])
        if name == "validator_cost":
            raise ValueError("missing required validator_cost metric")
        usage = run.get("usage") or []
        key = "prompt_tokens" if name == "input_tokens" else "completion_tokens"
        return float(sum(item.get(key, item.get(name, 0)) for item in usage))
    if name == "calls": return float(len(run.get("calls") or []))
    raise KeyError(name)


def _cluster_ci(values: dict[str, list[float]], statistic: Callable[[list[float]], float],
                rng: random.Random, draws: int) -> tuple[float, list[float]]:
    families = sorted(values)
    point = statistic([value for family in families for value in values[family]])
    boot = []
    for _ in range(draws):
        selected = [rng.choice(families) for _ in families]
        boot.append(statistic([value for family in selected for value in values[family]]))
    boot.sort()
    return point, [boot[int(.025 * draws)], boot[max(0, int(.975 * draws) - 1)]]


def _signflip_p(family_effects: list[float], seed: int = 2027, draws: int = 20000) -> float:
    observed = abs(mean(family_effects))
    if len(family_effects) <= 18:
        samples = (abs(mean([value * sign for value, sign in zip(family_effects, signs)]))
                   for signs in itertools.product((-1, 1), repeat=len(family_effects)))
        values = list(samples)
    else:
        rng = random.Random(seed)
        values = [abs(mean([value * rng.choice((-1, 1)) for value in family_effects]))
                  for _ in range(draws)]
    return (1 + sum(value >= observed - 1e-12 for value in values)) / (len(values) + 1)


def _holm(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues, key=pvalues.get); result = {}; running = 0.0; n = len(ordered)
    for index, key in enumerate(ordered):
        running = max(running, min(1.0, (n - index) * pvalues[key])); result[key] = running
    return result


def _exact_mcnemar_p(left: list[float], right: list[float]) -> dict[str, float | int]:
    """Two-sided exact McNemar sensitivity test for paired binary outcomes."""
    if len(left) != len(right):
        raise ValueError("McNemar inputs must have equal length")
    if any(value not in {0.0, 1.0} for value in left + right):
        raise ValueError("McNemar inputs must be binary")
    left_only = sum(a == 1 and b == 0 for a, b in zip(left, right))
    right_only = sum(a == 0 and b == 1 for a, b in zip(left, right))
    discordant = left_only + right_only
    if discordant == 0:
        pvalue = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(min(left_only, right_only) + 1))
        pvalue = min(1.0, 2.0 * tail / (2 ** discordant))
    return {"left_only": left_only, "right_only": right_only,
            "discordant": discordant, "two_sided_exact_p": pvalue}


def analyze(manifest: dict, runs: list[dict], families: dict[str, str], *, draws: int = 10000,
            seed: int = 2027) -> dict:
    if draws < 100:
        raise ValueError("at least 100 bootstrap draws are required")
    indexed = {(r["task_id"], r["model"], int(r["seed"]), r["method"]): r for r in runs}
    design = manifest["confirmatory_design"]
    blocks = list(itertools.product(families, design["models"], [int(s) for s in design["seeds"]]))
    rng = random.Random(seed)
    condition_summary = {}
    endpoints = ("strict_success", "macro_state_f1", "critical_errors", "input_tokens",
                 "output_tokens", "calls", "validator_cost")
    for condition in design["conditions"]:
        condition_summary[condition] = {}
        for endpoint in endpoints:
            grouped: dict[str, list[float]] = defaultdict(list)
            for task, model, run_seed in blocks:
                grouped[families[task]].append(_metric(indexed[(task, model, run_seed, condition)], endpoint))
            point, ci = _cluster_ci(grouped, mean, rng, draws)
            condition_summary[condition][endpoint] = {"mean": point, "cluster_bootstrap_ci": ci}

    paired_by_family: dict[str, list[float]] = defaultdict(list)
    hir_by_family: dict[str, list[float]] = defaultdict(list)
    structured_binary, oracle_binary = [], []
    hir_all: dict[str, dict[str, float]] = {}
    for task, model, run_seed in blocks:
        oracle = _metric(indexed[(task, model, run_seed, "gold_oracle")], "strict_success")
        structured = _metric(indexed[(task, model, run_seed, "structured_payload")], "strict_success")
        structured_binary.append(structured); oracle_binary.append(oracle)
        paired_by_family[families[task]].append(structured - oracle)
        hir_by_family[families[task]].append(float(oracle == 1 and structured == 0))
    contrast, contrast_ci = _cluster_ci(paired_by_family, mean, rng, draws)
    hir, hir_ci = _cluster_ci(hir_by_family, mean, rng, draws)
    for condition in design["conditions"]:
        if condition == "gold_oracle": continue
        grouped: dict[str, list[float]] = defaultdict(list)
        for task, model, run_seed in blocks:
            oracle = _metric(indexed[(task, model, run_seed, "gold_oracle")], "strict_success")
            target = _metric(indexed[(task, model, run_seed, condition)], "strict_success")
            grouped[families[task]].append(float(oracle == 1 and target == 0))
        point, ci = _cluster_ci(grouped, mean, rng, draws)
        hir_all[condition] = {"rate": point, "cluster_bootstrap_ci": ci}

    factorial_runs = [r for r in runs if _factor_levels(r["method"])]
    factorial = {}
    checks_family_effects = []
    checks_off_binary, checks_on_binary = [], []
    for task, model, run_seed in blocks:
        for typing in ("free_form", "typed"):
            for provenance in ("absent", "trace_linked"):
                checks_off_binary.append(_metric(
                    indexed[(task, model, run_seed, f"{typing}__{provenance}__absent__advisory")],
                    "strict_success"))
                checks_on_binary.append(_metric(
                    indexed[(task, model, run_seed, f"{typing}__{provenance}__executable__advisory")],
                    "strict_success"))
    for endpoint in endpoints:
        factorial[endpoint] = {}
        for term in TERMS:
            grouped: dict[str, list[float]] = defaultdict(list)
            for run in factorial_runs:
                levels = _factor_levels(run["method"]); sign = math.prod(levels[name] for name in term)
                grouped[families[run["task_id"]]].append(2 * sign * _metric(run, endpoint))
            point, ci = _cluster_ci(grouped, mean, rng, draws)
            factorial[endpoint][":".join(term)] = {"effect": point, "cluster_bootstrap_ci": ci}
            if endpoint == "strict_success" and term == ("checks",):
                checks_family_effects = [mean(grouped[family]) for family in sorted(grouped)]
    structured_family_effects = [mean(paired_by_family[family]) for family in sorted(paired_by_family)]
    raw_p = {"structured_vs_oracle": _signflip_p(structured_family_effects, seed),
             "advisory_checks_main_effect": _signflip_p(checks_family_effects, seed + 1)}
    adjusted = _holm(raw_p)
    tests = {key: {"two_sided_p": raw_p[key], "holm_adjusted_p": adjusted[key]}
             for key in raw_p}
    for item in tests.values():
        item["test"] = "family-level two-sided sign-flip"
    tests["structured_vs_oracle"].update(effect=contrast, cluster_bootstrap_ci=contrast_ci,
                                          hir=hir, hir_ci=hir_ci,
                                          mcnemar_sensitivity=_exact_mcnemar_p(
                                              structured_binary, oracle_binary))
    tests["advisory_checks_main_effect"].update(
        factorial["strict_success"]["checks"])
    tests["advisory_checks_main_effect"]["mcnemar_sensitivity"] = _exact_mcnemar_p(
        checks_on_binary, checks_off_binary)
    return {"analysis_contract": "preregistration-v2", "itt": True,
            "bootstrap_seed": seed, "bootstrap_draws": draws,
            "n_tasks": len(families), "n_models": len(design["models"]),
            "n_seeds": len(design["seeds"]), "n_runs": len(runs),
            "confirmatory_tests": tests, "condition_summary": condition_summary,
            "hir_by_condition": hir_all, "factorial_effects": factorial}


def latex_tables(report: dict) -> str:
    tests = report["confirmatory_tests"]
    row_end = " " + "\\" * 2
    lines = ["% Generated by analyze_confirmatory.py; do not edit.",
             "\\begin{table}[t]", "\\centering", "\\small",
             "\\caption{Preregistered confirmatory tests (ITT; family-clustered 95\\% CIs).}",
             "\\begin{tabular}{lrrrr}", "\\toprule",
             "Contrast & Effect & CI low & CI high & Holm $p$" + row_end, "\\midrule"]
    for key, label in (("structured_vs_oracle", "Structured $-$ Oracle"),
                       ("advisory_checks_main_effect", "Advisory checks")):
        item = tests[key]; ci = item["cluster_bootstrap_ci"]
        lines.append(f"{label} & {item.get('effect', 0):.3f} & {ci[0]:.3f} & {ci[1]:.3f} & {item['holm_adjusted_p']:.3f}" + row_end)
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", "",
              "\\begin{table}[t]", "\\centering", "\\small",
              "\\caption{Representation factorial effects on strict success.}",
              "\\begin{tabular}{lrrr}", "\\toprule", "Term & Effect & CI low & CI high" + row_end, "\\midrule"]
    for term, item in report["factorial_effects"]["strict_success"].items():
        ci = item["cluster_bootstrap_ci"]
        term_label = term.replace(":", "$\\times$")
        lines.append(f"{term_label} & {item['effect']:.3f} & {ci[0]:.3f} & {ci[1]:.3f}" + row_end)
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", "",
              "\\begin{table*}[t]", "\\centering", "\\small",
              "\\caption{ITT endpoints by scheduled condition. HIR is oracle-conditional regression.}",
              "\\begin{tabular}{lrrrrrrrr}", "\\toprule",
              "Condition & Success & HIR & State $F_1$ & Critical & In tok. & Out tok. & Calls & Val. cost" + row_end,
              "\\midrule"]
    for condition, endpoints in report["condition_summary"].items():
        hir = report["hir_by_condition"].get(condition, {}).get("rate", 0.0)
        label = condition.replace("_", "\\_")
        lines.append(
            f"{label} & {endpoints['strict_success']['mean']:.3f} & {hir:.3f} & "
            f"{endpoints['macro_state_f1']['mean']:.3f} & {endpoints['critical_errors']['mean']:.3f} & "
            f"{endpoints['input_tokens']['mean']:.1f} & {endpoints['output_tokens']['mean']:.1f} & "
            f"{endpoints['calls']['mean']:.1f} & {endpoints['validator_cost']['mean']:.3f}" + row_end
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""]
    return "\n".join(lines)
