import importlib.util
from collections import Counter
from pathlib import Path

import pytest

from handoffbench.dataset import load_tasks


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_action_name_leakage", ROOT / "scripts" / "audit_action_name_leakage.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def records():
    return sum((load_tasks(path) for path in MODULE.TASK_FILES), [])


def test_observed_chance_majority_and_intervals_are_reproducible() -> None:
    report = MODULE.audit(records(), draws=1000, seed=2027)
    assert report["n"] == 200
    assert report["observed"]["successes"] == 69
    assert report["observed"]["rate"] == 0.345
    assert report["observed"]["wilson_95"] == pytest.approx(
        [0.2825968690139029, 0.41324539282077655]
    )
    assert report["uniform_argument_random"]["expected_successes"] == pytest.approx(
        27.753086419753085
    )
    assert report["uniform_argument_random"]["expected_rate"] == pytest.approx(
        0.13876543209876543
    )
    assert report["uniform_argument_random"]["poisson_binomial_tail_p"] < 1e-12
    assert report["global_enum_position_majority"] == {
        "position_counts": {0: 194, 1: 107, 2: 101},
        "majority_position": 0,
        "successes": 69,
        "rate": 0.345,
    }


def test_strata_and_successful_family_list_expose_enum_position_mechanism() -> None:
    report = MODULE.audit(records(), draws=100, seed=7)
    assert Counter(item["stratum"] for item in report["strata"]["domain"]) == {
        "travel": 1, "commerce": 1, "procurement": 1, "it": 1, "scheduling": 1
    }
    assert all(item["n"] == 40 for item in report["strata"]["domain"])
    assert len(report["successful_families"]) == 69
    assert len({item["template_family"] for item in report["successful_families"]}) == 69
    for row in report["rows"]:
        assert row["name_first_success"] == bool(
            row["enum_positions"] and all(position == 0 for position in row["enum_positions"])
        )
    assert "not a pure action-name-only learner" in report["probe_definition"]
    assert "combined" in report["recommended_paper_wording"]


def test_report_renderer_lists_all_successful_families() -> None:
    report = MODULE.audit(records(), draws=50)
    text = MODULE.markdown(report)
    assert "Successful families (69)" in text
    assert sum(f"`{item['task_id']}`" in text for item in report["successful_families"]) == 69
