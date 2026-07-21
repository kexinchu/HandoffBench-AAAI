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
ADVISORY_FACTORIAL = tuple(
    f"{typing}__{provenance}__{checks}__advisory"
    for typing in ("free_form", "typed")
    for provenance in ("absent", "trace_linked")
    for checks in ("absent", "executable")
)
ENFORCED_CONDITION = "typed__trace_linked__executable__enforced"
STRUCTURED_CONDITION = "typed__absent__absent__advisory"
EXPECTED_CONDITIONS = ("full_history", "gold_oracle", *ADVISORY_FACTORIAL,
                       ENFORCED_CONDITION)
EXPECTED_MATRIX_CONDITIONS = EXPECTED_CONDITIONS
EXPECTED_SEEDS = (101, 202)
RUN_CONFIG_KEYS = {
    "model", "transfer_kind", "temperature", "seed", "protocol_version",
    "max_turns", "max_output_tokens", "enforce_action_gates", "factorial_cell",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def _raw_tree_inventory(root: Path) -> dict[str, Any]:
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
        for path in sorted(root.rglob("*.json"))
    ]
    return {
        "algorithm": "sha256-canonical-json-relative-path-file-sha256-v1",
        "file_count": len(entries),
        "sha256": canonical_hash(entries),
    }


def _sealed_path_tree_sha256(root: Path, base: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    paths = sorted(root.rglob("*.json"), key=lambda path: path.relative_to(base).as_posix())
    for path in paths:
        relative = path.relative_to(base).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(sha256(path).encode("ascii") + b"\n")
    return len(paths), digest.hexdigest()


def _validate_replacement_inputs(
    manifest: dict[str, Any], base: Path, run_dirs: list[str | Path],
) -> dict[str, str] | None:
    """Bind final analysis to retained Ministral plus fresh v3.4 Qwen only."""
    attempt = manifest.get("execution_attempt")
    if attempt is None:
        return None
    retained = attempt.get("retained_arms", {}).get("ministral3-14b-2512", {})
    retained_root = _resolve(base, retained.get("raw_root", ""))
    qwen_root = _resolve(
        base, str(Path(attempt["fresh_output_root"]) / "qwen2.5-14b" / "runs")
    )
    supplied = [Path(value).resolve() for value in run_dirs]
    if len(supplied) != 2 or set(supplied) != {retained_root, qwen_root}:
        raise ValueError(
            "v3.4 analysis requires exactly the retained Ministral and fresh Qwen raw roots"
        )
    forbidden = {_resolve(base, value) for value in attempt["forbidden_raw_roots"]}
    if forbidden & set(supplied):
        raise ValueError("invalidated v3.3 Qwen raw root is forbidden")
    ledger_path = _resolve(base, retained["ledger"])
    if sha256(ledger_path) != retained["ledger_sha256"]:
        raise ValueError("retained Ministral ledger hash drift")
    count, tree_hash = _sealed_path_tree_sha256(retained_root, base)
    if count != retained["raw_file_count"] or tree_hash != retained["raw_tree_sha256"]:
        raise ValueError("retained Ministral raw inventory drift")

    replacement_ledger_path = qwen_root.parent / "execution_ledger.json"
    replacement_ledger = json.loads(replacement_ledger_path.read_text(encoding="utf-8"))
    expected_hashes = {
        "canonical_dataset_sha256": manifest["canonical_dataset_sha256"],
        "design_matrix_sha256": manifest["design_matrix_sha256"],
        "confirmatory_config_design_sha256": manifest["confirmatory_config_design_sha256"],
    }
    if (replacement_ledger.get("seal_id") != manifest.get("seal_id")
            or replacement_ledger.get("attempt_id") != attempt.get("attempt_id")
            or replacement_ledger.get("model") != "qwen2.5-14b"
            or replacement_ledger.get("scheduled_rows_for_model") != 4400
            or replacement_ledger.get("persisted_rows_for_model") != 4400
            or replacement_ledger.get("resumed_rows") != 0
            or replacement_ledger.get("written_rows") != 4400
            or any(replacement_ledger.get("hashes", {}).get(key) != value
                   for key, value in expected_hashes.items())
            or replacement_ledger.get("raw_run_inventory") != _raw_tree_inventory(qwen_root)):
        raise ValueError("fresh Qwen execution ledger/inventory does not satisfy v3.4")
    return {
        "ministral_raw_root": str(retained_root),
        "qwen_raw_root": str(qwen_root),
        "qwen_execution_ledger": str(replacement_ledger_path),
        "qwen_execution_ledger_sha256": sha256(replacement_ledger_path),
    }


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def _manifest_base(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    """Resolve repository-relative manifest paths without assuming seal location."""
    candidate_files = manifest.get("candidate_files")
    if (not isinstance(candidate_files, list) or not candidate_files
            or any(not isinstance(value, str) or not value for value in candidate_files)):
        raise ValueError("sealed manifest requires a non-empty candidate_files list")
    path_base = manifest.get("path_base")
    if path_base is not None:
        if not isinstance(path_base, str) or not path_base:
            raise ValueError("manifest path_base must be a non-empty string")
        base = _resolve(manifest_path.parent, path_base)
        if not base.is_dir():
            raise ValueError(f"manifest path_base is not a directory: {base}")
        return base

    relative = [value for value in candidate_files if not Path(value).is_absolute()]
    if not relative:
        return manifest_path.parent
    roots = (manifest_path.parent, *manifest_path.parent.parents)
    matches = [root for root in roots if all(_resolve(root, value).is_file()
                                             for value in relative)]
    if len(matches) != 1:
        raise ValueError(
            "cannot resolve repository-relative candidate_files unambiguously; "
            "set manifest path_base"
        )
    return matches[0]


def _validated_tasks(manifest_path: Path, manifest: dict[str, Any]) -> tuple[
        Path, list[Path], list[dict], list[str], dict[str, str], dict[str, str]]:
    base = _manifest_base(manifest_path, manifest)
    names = manifest["candidate_files"]
    if len(names) != len(set(names)):
        raise ValueError("sealed manifest contains duplicate candidate_files")
    expected_file_hashes = manifest.get("candidate_file_hashes")
    if not isinstance(expected_file_hashes, dict) or set(expected_file_hashes) != set(names):
        raise ValueError("candidate_file_hashes must exactly cover candidate_files")
    paths, file_hashes, tasks = [], {}, []
    for name in names:
        path = _resolve(base, name)
        if not path.is_file():
            raise ValueError(f"sealed candidate file is missing: {path}")
        actual = sha256(path)
        if actual != expected_file_hashes[name]:
            raise ValueError(f"sealed candidate file hash drift: {name}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or not value:
            raise ValueError(f"sealed candidate file must contain a non-empty array: {name}")
        paths.append(path); file_hashes[name] = actual; tasks.extend(value)

    try:
        task_ids = [item["episode"]["task_id"] for item in tasks]
        families = {item["episode"]["task_id"]:
                    item["episode"]["split_meta"]["template_family"] for item in tasks}
    except (KeyError, TypeError) as error:
        raise ValueError("sealed task lacks task_id or template_family") from error
    if len(task_ids) != 200 or len(set(task_ids)) != 200 or len(families) != 200:
        raise ValueError("sealed tasks are not exactly 200 unique task IDs")
    if len(set(families.values())) != 200:
        raise ValueError("sealed tasks are not 200 independent families")
    if manifest.get("n_independent_families", 200) != 200:
        raise ValueError("sealed manifest must declare 200 independent families")
    if "task_ids" in manifest and manifest["task_ids"] != sorted(task_ids):
        raise ValueError("sealed manifest task_ids drift")
    expected_task_hashes = manifest.get("task_hashes")
    if not isinstance(expected_task_hashes, dict) or set(expected_task_hashes) != set(task_ids):
        raise ValueError("task_hashes must exactly cover all sealed tasks")
    for item in tasks:
        task_id = item["episode"]["task_id"]
        if canonical_hash(item) != expected_task_hashes[task_id]:
            raise ValueError(f"sealed task hash drift: {task_id}")
    expected_dataset_hash = manifest.get("canonical_dataset_sha256")
    if expected_dataset_hash is not None and canonical_hash(tasks) != expected_dataset_hash:
        raise ValueError("sealed canonical dataset hash drift")
    return base, paths, tasks, task_ids, families, file_hashes


def _validate_design(design: Any, *, require_config_hashes: bool) -> dict[str, Any]:
    if not isinstance(design, dict):
        raise ValueError("sealed manifest lacks a valid confirmatory design")
    models, seeds, conditions = (design.get("models"), design.get("seeds"),
                                  design.get("conditions"))
    if (not isinstance(models, list) or len(models) != 2
            or any(not isinstance(model, str) or not model for model in models)
            or len(set(models)) != 2):
        raise ValueError("confirmatory design requires exactly two distinct models")
    if seeds != list(EXPECTED_SEEDS):
        raise ValueError(f"confirmatory design seeds must be {list(EXPECTED_SEEDS)}")
    if conditions != list(EXPECTED_CONDITIONS):
        raise ValueError("confirmatory design conditions do not match the v3 11-condition matrix")
    hashes = design.get("config_hashes")
    expected_keys = {
        f"{model}|{seed}|{condition}"
        for model, seed, condition in itertools.product(models, EXPECTED_SEEDS,
                                                        EXPECTED_CONDITIONS)
    }
    if require_config_hashes:
        if not isinstance(hashes, dict) or set(hashes) != expected_keys:
            raise ValueError("confirmatory design config_hashes do not exactly cover the schedule")
        if any(not isinstance(value, str) or len(value) != 64 for value in hashes.values()):
            raise ValueError("confirmatory design contains an invalid config hash")
    elif hashes not in (None, {}):
        raise ValueError("derived confirmatory design cannot contain unbound config hashes")
    return {"models": models, "seeds": list(EXPECTED_SEEDS),
            "conditions": list(EXPECTED_CONDITIONS), "config_hashes": hashes or {}}


def _derived_design(base: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Derive only from artifacts whose hashes are bound into the sealed manifest."""
    for field in ("design_matrix", "design_matrix_sha256", "model_snapshot_manifest",
                  "model_snapshot_manifest_sha256"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ValueError(f"sealed manifest lacks {field} for design derivation")
    matrix_path = _resolve(base, manifest["design_matrix"])
    snapshot_path = _resolve(base, manifest["model_snapshot_manifest"])
    if sha256(matrix_path) != manifest["design_matrix_sha256"]:
        raise ValueError("sealed design matrix hash drift")
    if sha256(snapshot_path) != manifest["model_snapshot_manifest_sha256"]:
        raise ValueError("sealed model snapshot manifest hash drift")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    if matrix.get("conditions") != list(EXPECTED_MATRIX_CONDITIONS):
        raise ValueError("bound design matrix does not match the v3 11-condition schedule")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    entries = snapshot.get("models")
    if not isinstance(entries, list):
        raise ValueError("bound model snapshot manifest lacks models")
    models = [item.get("served_model_name") for item in entries if isinstance(item, dict)]
    return _validate_design({"models": models, "seeds": list(EXPECTED_SEEDS),
                             "conditions": list(EXPECTED_CONDITIONS),
                             "config_hashes": {}}, require_config_hashes=False)


def _run_seed(run: dict[str, Any]) -> int:
    value = run.get("seed")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("run seed must be an integer")
    return value


def _validate_run_config(run: dict[str, Any], key: tuple[str, str, int, str]) -> None:
    config = run.get("config")
    if not isinstance(config, dict) or set(config) != RUN_CONFIG_KEYS:
        raise ValueError(f"run config does not match the v3 schema: {key}")
    if canonical_hash(config) != run.get("config_hash"):
        raise ValueError(f"run config content/hash mismatch: {key}")
    model, seed, method = key[1], key[2], key[3]
    if (config["model"] != model or config["seed"] != seed
            or config["protocol_version"] != "handoffbench-confirmatory-v3"
            or config["temperature"] != 0.7 or config["max_turns"] != 4
            or config["max_output_tokens"] != 1600):
        raise ValueError(f"run config drifts from the v3 frozen generation design: {key}")
    if method in {"full_history", "gold_oracle"}:
        valid = (config["transfer_kind"] == method and config["factorial_cell"] is None
                 and config["enforce_action_gates"] is False)
    else:
        parts = method.split("__")
        enforcement = parts[-1]
        valid = (
            len(parts) == 4
            and config["transfer_kind"] == "factorial"
            and config["enforce_action_gates"] is (enforcement == "enforced")
            and config["factorial_cell"] == {
                "typing": parts[0], "provenance": parts[1], "checks": parts[2],
                # RunConfig stores the base representation cell here. The
                # separate enforce_action_gates flag promotes only the runtime
                # transfer_config/method label to ``enforced``.
                "enforcement": "advisory",
            }
        )
    if not valid:
        raise ValueError(f"run config condition semantics mismatch: {key}")


def load_and_validate(manifest_path: str | Path, run_dirs: list[str | Path]) -> tuple[dict, list[dict], dict]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sealed") is not True or manifest.get("n_tasks") != 200:
        raise ValueError("confirmatory manifest must be sealed and contain exactly 200 tasks")
    base, task_files, tasks, task_ids, families, task_file_hashes = _validated_tasks(
        manifest_path, manifest
    )
    protocol_hashes = manifest.get("protocol_file_hashes", {})
    if not isinstance(protocol_hashes, dict):
        raise ValueError("sealed protocol_file_hashes must be an object")
    for value, expected in protocol_hashes.items():
        path = _resolve(base, value)
        if sha256(path) != expected:
            raise ValueError(f"sealed protocol hash drift: {path}")
    embedded = manifest.get("confirmatory_design")
    design = (_validate_design(embedded, require_config_hashes=True)
              if embedded is not None else _derived_design(base, manifest))
    manifest = dict(manifest); manifest["confirmatory_design"] = design
    factorial = list(ADVISORY_FACTORIAL)

    replacement_provenance = _validate_replacement_inputs(manifest, base, run_dirs)
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
        key = (run.get("task_id"), run.get("model"), _run_seed(run), run.get("method"))
        if key not in scheduled:
            raise ValueError(f"unscheduled/dev/foreign run contaminates confirmatory input: {key}")
        if key in observed:
            raise ValueError(f"duplicate scheduled run: {key}")
        observed[key] = run
        config_key = f"{key[1]}|{key[2]}|{key[3]}"
        expected_hash = design["config_hashes"].get(config_key)
        if expected_hash is not None and run.get("config_hash") != expected_hash:
            raise ValueError(f"config hash drift: {key}")
        _validate_run_config(run, key)
        if replacement_provenance is not None and run.get("model") == "qwen2.5-14b":
            error = run.get("error") if isinstance(run.get("error"), dict) else {}
            error_type = str(error.get("type", ""))
            message = str(error.get("message", "")).lower()
            infrastructure_error = (
                error_type in {"URLError", "TimeoutError", "ConnectionError"}
                or "connection refused" in message or "connection reset" in message
                or "enginecore" in message or "http 5" in message
                or "out of memory" in message or "cuda oom" in message
            )
            if infrastructure_error:
                raise ValueError(f"v3.4 Qwen infrastructure failure invalidates attempt: {key}")
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
                  "path_base": str(base),
                  "candidate_files": [str(path) for path in task_files],
                  "candidate_file_hashes": task_file_hashes,
                  "canonical_dataset_sha256": canonical_hash(tasks),
                  "raw_run_files": run_files, "n_raw_runs": len(ordered)}
    if replacement_provenance is not None:
        provenance["execution_replacement"] = replacement_provenance
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
        if run["method"] in {*factorial, ENFORCED_CONDITION}:
            groups[(run["task_id"], run["model"], int(run["seed"]))].append(run)
    for block, items in groups.items():
        if len(items) != 9 or {item["method"] for item in items} != {
                *factorial, ENFORCED_CONDITION}:
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
        if len(signatures) != 1 or any(value is None for value in next(iter(signatures))):
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
        # Evaluate in log space: direct int-to-float conversion overflows for
        # the preregistered 200 x 2 x 2 repeated-measures schedule.
        log_p = math.log(2.0) + math.log(tail) - discordant * math.log(2.0)
        pvalue = min(1.0, math.exp(log_p)) if log_p > -745 else 0.0
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
        structured = _metric(indexed[(task, model, run_seed, STRUCTURED_CONDITION)],
                             "strict_success")
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
    protocol = manifest.get("protocol")
    if protocol != "handoffbench-confirmatory-v3":
        raise ValueError("analysis requires the handoffbench-confirmatory-v3 protocol")
    return {"analysis_contract": "preregistration-v3",
            "protocol": protocol, "itt": True,
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
