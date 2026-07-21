import hashlib
import json
from pathlib import Path

import pytest

from handoffbench.confirmatory_analysis import (
    ADVISORY_FACTORIAL,
    ENFORCED_CONDITION,
    EXPECTED_CONDITIONS,
    STRUCTURED_CONDITION,
    analyze,
    canonical_hash,
    latex_tables,
    load_and_validate,
)


FACTORIAL = list(ADVISORY_FACTORIAL)
CONDITIONS = list(EXPECTED_CONDITIONS)
MODELS = ["model-a", "model-b"]
SEEDS = [101, 202]


def _config(model: str, seed: int, condition: str) -> dict:
    if condition in {"full_history", "gold_oracle"}:
        transfer_kind = condition
        factorial_cell = None
        enforced = False
    else:
        typing, provenance, checks, enforcement = condition.split("__")
        transfer_kind = "factorial"
        factorial_cell = {
            "typing": typing,
            "provenance": provenance,
            "checks": checks,
            "enforcement": "advisory",
        }
        enforced = enforcement == "enforced"
    return {
        "model": model,
        "transfer_kind": transfer_kind,
        "temperature": 0.7,
        "seed": seed,
        "protocol_version": "handoffbench-confirmatory-v3",
        "max_turns": 4,
        "max_output_tokens": 1600,
        "enforce_action_gates": enforced,
        "factorial_cell": factorial_cell,
    }


def fixture(tmp_path: Path, *, explicit_path_base: bool = False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    task_root = tmp_path / "data" / "tasks" / "confirmatory_v3"
    task_root.mkdir(parents=True)
    tasks = [{"episode": {"task_id": f"sealed_{index:03d}", "domain": "it",
                           "split_meta": {"template_family": f"family_{index:03d}"}}}
             for index in range(200)]
    candidate_files, candidate_hashes = [], {}
    for file_index in range(5):
        relative = f"data/tasks/confirmatory_v3/part-{file_index}.json"
        path = tmp_path / relative
        path.write_text(json.dumps(tasks[file_index * 40:(file_index + 1) * 40]))
        candidate_files.append(relative)
        candidate_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()

    config_hashes, runs = {}, []
    for model in MODELS:
        for seed in SEEDS:
            for condition in CONDITIONS:
                config = _config(model, seed, condition)
                config_hashes[f"{model}|{seed}|{condition}"] = canonical_hash(config)
    for index, task in enumerate(tasks):
        task_id = task["episode"]["task_id"]
        for model in MODELS:
            for seed in SEEDS:
                shared_hash = hashlib.sha256(f"{task_id}|{model}|{seed}".encode()).hexdigest()
                for condition in CONDITIONS:
                    config = _config(model, seed, condition)
                    checks_on = "__executable__" in condition
                    success = True if condition == "gold_oracle" else (index % 2 == 0 or checks_on)
                    run = {"task_id": task_id, "model": model, "seed": seed,
                           "method": condition, "status": "ok", "success": success,
                           "config": config, "config_hash": canonical_hash(config),
                           "metrics": {"macro_state_f1": .9 if success else .2,
                                       "critical_errors": 0 if success else 1,
                                       "input_tokens": 100, "output_tokens": 20,
                                       "validator_cost": .01},
                           "usage": [{"prompt_tokens": 100, "completion_tokens": 20}],
                           "calls": []}
                    if condition in FACTORIAL or condition == ENFORCED_CONDITION:
                        run.update(source_hash=shared_hash)
                        run["calls"] = [{"source_output_hash": shared_hash,
                                         "prompt_hash": "shared-prompt",
                                         "response_schema_hash": "shared-schema",
                                         "usage": {"prompt_tokens": 30,
                                                   "completion_tokens": 10}}]
                    runs.append(run)
    run_dir = tmp_path / "confirmatory_raw"; run_dir.mkdir()
    run_path = run_dir / "runs.json"; run_path.write_text(json.dumps(runs))
    manifest = {
        "sealed": True,
        "status": "sealed",
        "protocol": "handoffbench-confirmatory-v3",
        "manifest_version": "test",
        "n_tasks": 200,
        "n_independent_families": 200,
        "candidate_files": candidate_files,
        "candidate_file_hashes": candidate_hashes,
        "canonical_dataset_sha256": canonical_hash(tasks),
        "task_ids": sorted(item["episode"]["task_id"] for item in tasks),
        "task_hashes": {item["episode"]["task_id"]: canonical_hash(item) for item in tasks},
        "protocol_file_hashes": {},
        "confirmatory_design": {"models": MODELS, "seeds": SEEDS,
                                 "conditions": CONDITIONS,
                                 "config_hashes": config_hashes},
    }
    manifest_dir = tmp_path / "data" / "splits"; manifest_dir.mkdir(parents=True)
    if explicit_path_base:
        manifest["path_base"] = "../.."
    manifest_path = manifest_dir / "sealed_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, run_dir, run_path, runs


def test_complete_pipeline_computes_v3_itt_hir_holm_factorial_and_tables(tmp_path):
    manifest_path, run_dir, _, _ = fixture(tmp_path)
    manifest, runs, context = load_and_validate(manifest_path, [run_dir])
    enforced = next(run for run in runs if run["method"] == ENFORCED_CONDITION)
    assert enforced["config"]["factorial_cell"]["enforcement"] == "advisory"
    assert enforced["config"]["enforce_action_gates"] is True
    report = analyze(manifest, runs, context["families"], draws=100)
    assert report["analysis_contract"] == "preregistration-v3"
    assert report["protocol"] == "handoffbench-confirmatory-v3"
    assert report["n_tasks"] == 200 and report["n_models"] == 2
    assert report["n_seeds"] == 2
    assert report["n_runs"] == 200 * 2 * 2 * 11
    assert set(report["condition_summary"]) == set(CONDITIONS)
    assert "structured_payload" not in report["condition_summary"]
    assert set(report["confirmatory_tests"]) == {
        "structured_vs_oracle", "advisory_checks_main_effect"
    }
    assert report["confirmatory_tests"]["structured_vs_oracle"]["hir"] == pytest.approx(.5)
    assert report["factorial_effects"]["strict_success"]["checks"]["effect"] == pytest.approx(.5)
    assert all(0 <= item["holm_adjusted_p"] <= 1
               for item in report["confirmatory_tests"].values())
    structured_mcnemar = report["confirmatory_tests"]["structured_vs_oracle"]["mcnemar_sensitivity"]
    assert structured_mcnemar == {
        "left_only": 0, "right_only": 400, "discordant": 400,
        "two_sided_exact_p": pytest.approx(2 / 2**400),
    }
    checks_mcnemar = report["confirmatory_tests"]["advisory_checks_main_effect"]["mcnemar_sensitivity"]
    assert checks_mcnemar["left_only"] == 1600
    assert checks_mcnemar["right_only"] == 0
    assert checks_mcnemar["discordant"] == 1600
    tables = latex_tables(report)
    assert "Preregistered confirmatory tests" in tables and "Advisory checks" in tables
    assert context["provenance"]["n_raw_runs"] == report["n_runs"]
    assert len(context["provenance"]["candidate_files"]) == 5


def test_structured_contrast_is_typed_absent_absent_advisory(tmp_path):
    manifest_path, run_dir, run_path, runs = fixture(tmp_path)
    target = next(run for run in runs
                  if run["method"] == STRUCTURED_CONDITION and not run["success"])
    target["success"] = True
    run_path.write_text(json.dumps(runs))
    manifest, validated, context = load_and_validate(manifest_path, [run_dir])
    report = analyze(manifest, validated, context["families"], draws=100)
    assert report["confirmatory_tests"]["structured_vs_oracle"]["hir"] < .5


def test_candidate_files_resolve_from_ancestor_or_explicit_path_base(tmp_path):
    for name, explicit in (("ancestor", False), ("explicit", True)):
        manifest_path, run_dir, _, _ = fixture(tmp_path / name,
                                                explicit_path_base=explicit)
        _, _, context = load_and_validate(manifest_path, [run_dir])
        assert Path(context["provenance"]["path_base"]) == (tmp_path / name).resolve()


def test_task_and_candidate_file_hash_drift_are_rejected(tmp_path):
    manifest_path, run_dir, _, _ = fixture(tmp_path / "task")
    manifest = json.loads(manifest_path.read_text())
    manifest["task_hashes"]["sealed_000"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="sealed task hash drift"):
        load_and_validate(manifest_path, [run_dir])

    manifest_path, run_dir, _, _ = fixture(tmp_path / "file")
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_file_hashes"][manifest["candidate_files"][0]] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="candidate file hash drift"):
        load_and_validate(manifest_path, [run_dir])


@pytest.mark.parametrize("replacement", ["structured_payload", None])
def test_non_v3_condition_matrix_is_rejected(tmp_path, replacement):
    manifest_path, run_dir, _, _ = fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    conditions = manifest["confirmatory_design"]["conditions"]
    if replacement is None:
        conditions.remove(ENFORCED_CONDITION)
    else:
        conditions[0] = replacement
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="11-condition matrix"):
        load_and_validate(manifest_path, [run_dir])


def test_missing_scheduled_cell_is_rejected(tmp_path):
    manifest_path, run_dir, run_path, runs = fixture(tmp_path)
    run_path.write_text(json.dumps(runs[:-1]))
    with pytest.raises(ValueError, match="incomplete confirmatory pairing"):
        load_and_validate(manifest_path, [run_dir])


def test_dev_or_invalid_protocol_directory_is_rejected(tmp_path):
    manifest_path, _, _, _ = fixture(tmp_path)
    polluted = tmp_path / "DEV"; polluted.mkdir(); (polluted / "run.json").write_text("{}")
    with pytest.raises(ValueError, match="contaminated"):
        load_and_validate(manifest_path, [polluted])
    invalid = tmp_path / "INVALID_PROTOCOL_old"; invalid.mkdir()
    with pytest.raises(ValueError, match="contaminated"):
        load_and_validate(manifest_path, [invalid])


def test_config_and_shared_source_hash_drift_are_rejected(tmp_path):
    manifest_path, run_dir, run_path, runs = fixture(tmp_path)
    runs[0]["config_hash"] = "0" * 64
    run_path.write_text(json.dumps(runs))
    with pytest.raises(ValueError, match="config hash drift"):
        load_and_validate(manifest_path, [run_dir])

    second_manifest, run_dir, run_path, runs = fixture(
        tmp_path / "second", explicit_path_base=True
    )
    factorial = next(run for run in runs if run["method"] in FACTORIAL)
    factorial["source_hash"] = "drift"
    run_path.write_text(json.dumps(runs))
    with pytest.raises(ValueError, match="shared-source"):
        load_and_validate(second_manifest, [run_dir])


def test_enforced_arm_must_reuse_factorial_source(tmp_path):
    manifest_path, run_dir, run_path, runs = fixture(tmp_path)
    enforced = next(run for run in runs if run["method"] == ENFORCED_CONDITION)
    enforced["source_hash"] = "independent-source"
    run_path.write_text(json.dumps(runs))
    with pytest.raises(ValueError, match="shared-source"):
        load_and_validate(manifest_path, [run_dir])


def test_missing_validator_cost_fails_closed(tmp_path):
    manifest_path, run_dir, run_path, runs = fixture(tmp_path)
    del runs[0]["metrics"]["validator_cost"]
    run_path.write_text(json.dumps(runs))
    with pytest.raises(ValueError, match="missing or invalid required validator_cost"):
        load_and_validate(manifest_path, [run_dir])
