import pytest

from handoffbench.confirmatory_analysis import ADVISORY_FACTORIAL, STRUCTURED_CONDITION
from handoffbench.post_confirmatory_analysis import analyze_post_confirmatory


MODELS = ["model-a", "model-b"]
SEEDS = [101, 202]


def _run(task: str, model: str, seed: int, method: str, success: bool) -> dict:
    return {
        "task_id": task,
        "model": model,
        "seed": seed,
        "method": method,
        "status": "ok",
        "success": success,
    }


def _fixture() -> tuple[dict, list[dict], dict[str, str], dict[str, str]]:
    tasks = ["commerce-1", "commerce-2", "it-1", "it-2"]
    families = {task: f"family-{task}" for task in tasks}
    domains = {task: task.split("-")[0] for task in tasks}
    runs = []
    for task in tasks:
        for model in MODELS:
            for seed in SEEDS:
                runs.append(_run(task, model, seed, "gold_oracle", True))
                for method in ADVISORY_FACTORIAL:
                    checks_on = "__executable__advisory" in method
                    success = checks_on if model == "model-a" else True
                    if method == STRUCTURED_CONDITION:
                        success = model == "model-b"
                    runs.append(_run(task, model, seed, method, success))
    manifest = {"confirmatory_design": {"models": MODELS, "seeds": SEEDS}}
    return manifest, runs, families, domains


def test_exploratory_subgroups_and_paired_model_interaction() -> None:
    manifest, runs, families, domains = _fixture()
    report = analyze_post_confirmatory(
        manifest, runs, families, domains, draws=100, seed=2027
    )

    assert report["analysis_contract"] == "post_confirmatory_v1"
    assert report["analysis_status"] == "exploratory"
    assert report["confirmatory_inference"] is False
    assert report["multiplicity_correction"].startswith("none")
    checks = report["estimands"]["advisory_checks_main_effect"]
    assert checks["by_model"]["model-a"]["effect"] == pytest.approx(1.0)
    assert checks["by_model"]["model-b"]["effect"] == pytest.approx(0.0)
    assert checks["by_domain"]["commerce"]["effect"] == pytest.approx(0.5)
    assert checks["by_model_domain"]["model-a|it"]["effect"] == pytest.approx(1.0)

    structured = report["estimands"]["structured_vs_oracle"]
    assert structured["by_model"]["model-a"]["effect"] == pytest.approx(-1.0)
    assert structured["by_model"]["model-b"]["effect"] == pytest.approx(0.0)
    assert structured["by_domain"]["it"]["effect"] == pytest.approx(-0.5)

    interaction = report["estimands"]["checks_model_difference_interaction"]
    assert interaction["contrast"] == "model-a minus model-b"
    assert interaction["overall"]["effect"] == pytest.approx(1.0)
    assert interaction["by_domain"]["commerce"]["effect"] == pytest.approx(1.0)
    assert interaction["overall"]["n_families"] == 4
    assert interaction["overall"]["n_paired_units"] == 8


def test_post_confirmatory_analysis_fails_closed_on_domain_or_pairing_errors() -> None:
    manifest, runs, families, domains = _fixture()
    domains.pop("it-2")
    with pytest.raises(ValueError, match="domain mapping must exactly cover"):
        analyze_post_confirmatory(manifest, runs, families, domains, draws=100)

    manifest, runs, families, domains = _fixture()
    runs = [run for run in runs if not (
        run["task_id"] == "it-2"
        and run["model"] == "model-a"
        and run["seed"] == 101
        and run["method"] == "gold_oracle"
    )]
    with pytest.raises(ValueError, match="missing run needed"):
        analyze_post_confirmatory(manifest, runs, families, domains, draws=100)


def test_bootstrap_requires_at_least_one_hundred_draws() -> None:
    manifest, runs, families, domains = _fixture()
    with pytest.raises(ValueError, match="at least 100 bootstrap draws"):
        analyze_post_confirmatory(manifest, runs, families, domains, draws=99)
