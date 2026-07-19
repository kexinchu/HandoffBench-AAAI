import hashlib
import json

import pytest

from handoffbench.confirmatory_analysis import (
    analyze, canonical_hash, latex_tables, load_and_validate,
)


FACTORIAL = [
    f"{typing}__{provenance}__{checks}__advisory"
    for typing in ("free_form", "typed")
    for provenance in ("absent", "trace_linked")
    for checks in ("absent", "executable")
]
CONDITIONS = ["structured_payload", "gold_oracle", *FACTORIAL]


def fixture(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    tasks = [{"episode": {"task_id": f"sealed_{index:03d}", "domain": "it",
                           "split_meta": {"template_family": f"family_{index:03d}"}}}
             for index in range(200)]
    task_path = tmp_path / "sealed_tasks.json"
    task_path.write_text(json.dumps(tasks))
    models, seeds = ["model-a", "model-b"], [11]
    config_hashes, runs = {}, []
    for model in models:
        for seed in seeds:
            for condition in CONDITIONS:
                config = {"model": model, "seed": seed, "condition": condition,
                          "protocol_version": "confirmatory-v2"}
                config_hashes[f"{model}|{seed}|{condition}"] = canonical_hash(config)
    for index, task in enumerate(tasks):
        task_id = task["episode"]["task_id"]
        for model in models:
            for seed in seeds:
                shared_hash = hashlib.sha256(f"{task_id}|{model}|{seed}".encode()).hexdigest()
                for condition in CONDITIONS:
                    config = {"model": model, "seed": seed, "condition": condition,
                              "protocol_version": "confirmatory-v2"}
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
                    if condition in FACTORIAL:
                        run.update(source_hash=shared_hash)
                        run["calls"] = [{"source_output_hash": shared_hash,
                                         "prompt_hash": "shared-prompt",
                                         "response_schema_hash": "shared-schema",
                                         "usage": {"prompt_tokens": 30, "completion_tokens": 10}}]
                    runs.append(run)
    run_dir = tmp_path / "confirmatory_raw"; run_dir.mkdir()
    run_path = run_dir / "runs.json"; run_path.write_text(json.dumps(runs))
    manifest = {"sealed": True, "manifest_version": "test", "n_tasks": 200,
                "task_file": str(task_path),
                "task_file_sha256": hashlib.sha256(task_path.read_bytes()).hexdigest(),
                "task_hashes": {item["episode"]["task_id"]: canonical_hash(item) for item in tasks},
                "protocol_file_hashes": {},
                "confirmatory_design": {"models": models, "seeds": seeds,
                                         "conditions": CONDITIONS,
                                         "config_hashes": config_hashes}}
    manifest_path = tmp_path / "sealed_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, run_dir, run_path, runs


def test_complete_pipeline_computes_itt_hir_holm_factorial_and_tables(tmp_path):
    manifest_path, run_dir, _, _ = fixture(tmp_path)
    manifest, runs, context = load_and_validate(manifest_path, [run_dir])
    report = analyze(manifest, runs, context["families"], draws=100)
    assert report["n_tasks"] == 200 and report["n_models"] == 2
    assert report["n_runs"] == 200 * 2 * len(CONDITIONS)
    assert set(report["confirmatory_tests"]) == {
        "structured_vs_oracle", "advisory_checks_main_effect"
    }
    assert report["confirmatory_tests"]["structured_vs_oracle"]["hir"] == pytest.approx(.5)
    assert report["factorial_effects"]["strict_success"]["checks"]["effect"] == pytest.approx(.5)
    assert all(0 <= item["holm_adjusted_p"] <= 1
               for item in report["confirmatory_tests"].values())
    structured_mcnemar = report["confirmatory_tests"]["structured_vs_oracle"]["mcnemar_sensitivity"]
    assert structured_mcnemar == {
        "left_only": 0, "right_only": 200, "discordant": 200,
        "two_sided_exact_p": pytest.approx(2 / 2**200),
    }
    checks_mcnemar = report["confirmatory_tests"]["advisory_checks_main_effect"]["mcnemar_sensitivity"]
    assert checks_mcnemar["left_only"] == 800
    assert checks_mcnemar["right_only"] == 0
    assert checks_mcnemar["discordant"] == 800
    tables = latex_tables(report)
    assert "Preregistered confirmatory tests" in tables and "Advisory checks" in tables
    assert context["provenance"]["n_raw_runs"] == report["n_runs"]


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

    _, run_dir, run_path, runs = fixture(tmp_path / "second")
    factorial = next(run for run in runs if run["method"] in FACTORIAL)
    factorial["source_hash"] = "drift"
    run_path.write_text(json.dumps(runs))
    with pytest.raises(ValueError, match="shared-source"):
        load_and_validate(tmp_path / "second/sealed_manifest.json", [run_dir])


def test_missing_validator_cost_fails_closed(tmp_path):
    manifest_path, run_dir, run_path, runs = fixture(tmp_path)
    del runs[0]["metrics"]["validator_cost"]
    run_path.write_text(json.dumps(runs))
    with pytest.raises(ValueError, match="missing or invalid required validator_cost"):
        load_and_validate(manifest_path, [run_dir])
