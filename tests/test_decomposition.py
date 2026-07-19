import json
from pathlib import Path

from handoffbench.dataset import load_tasks
from handoffbench.decomposition import (
    analyze_paired_runs,
    analyze_run,
    exact_fidelity,
)
from handoffbench.transfer import _CATEGORY_FIELD, oracle_state, public_action_contract


ROOT = Path(__file__).parents[1]
TASKS = ROOT / "data" / "tasks" / "dev" / "counterfactual_travel.json"


def _run(record, method, source, receiver, success=True):
    return {
        "task_id": record.episode.task_id,
        "method": method,
        "model": "test-model",
        "seed": 7,
        "status": "ok",
        "source_raw": source,
        "boundary_receiver_state": receiver,
        "success": success,
    }


def test_exact_transport_is_one_to_one_and_duplicate_is_false_positive() -> None:
    record = load_tasks(TASKS)[0]
    source = oracle_state(record)
    receiver = json.loads(json.dumps(source))
    receiver["user_goal"].append(dict(receiver["user_goal"][0]))
    score = exact_fidelity(source, receiver)
    assert score["tp"] == 4
    assert score["fp"] == 1
    assert score["recall"] == 1
    assert score["precision"] == 0.8


def test_structured_source_scores_extraction_and_transport() -> None:
    record = load_tasks(TASKS)[0]
    state = oracle_state(record)
    row = analyze_run(record, _run(record, "structured_payload", json.dumps(state), state))
    assert row["source_state_na_reason"] is None
    assert row["extraction"]["f1"] == 1
    assert row["transport"]["f1"] == 1


def test_non_atomized_methods_are_na_not_zero() -> None:
    record = load_tasks(TASKS)[0]
    state = oracle_state(record)
    for method in ("free_summary", "full_history"):
        row = analyze_run(record, _run(record, method, "some prose", state))
        assert row["source_state_na_reason"] == "source_state_not_directly_atomized"
        assert row["extraction"] is None
        assert row["transport"] is None


def test_ehc_reconstruction_reports_retention_and_quarantine() -> None:
    record = load_tasks(TASKS)[0]
    state = oracle_state(record)
    provenance = []
    for claim in record.episode.gold_state:
        evidence = claim.provenance[0]
        provenance.append({
            "field": _CATEGORY_FIELD[claim.category.value],
            "key": claim.key,
            "trace_id": evidence.trace_id,
            "source_type": evidence.source_type,
        })
    # Corrupt one evidence pointer: checked_ehc must quarantine, not retain it.
    provenance[0]["trace_id"] = "absent"
    checks = [
        {"condition": condition, "status": "missing"}
        for contract in public_action_contract(record)
        for condition in contract["requires"]
    ]
    capsule = {"state": state, "provenance": provenance, "checks": checks}
    row = analyze_run(
        record, _run(record, "ehc", json.dumps(capsule), state),
        reconstruct_checked_ehc=True,
    )
    assert row["validation"]["reconstructed"] is True
    assert row["validation"]["quarantined"] == 1
    assert row["validation"]["retained"] == 3
    assert row["validation"]["retention_rate"] == 0.75
    assert row["checked_transport"]["recall"] == 1
    assert row["checked_transport"]["fp"] == 1


def test_paired_oracle_defines_ceiling_and_regret() -> None:
    record = load_tasks(TASKS)[0]
    state = oracle_state(record)
    method = _run(record, "structured_payload", json.dumps(state), state, success=False)
    oracle = _run(record, "gold_oracle", None, state, success=True)
    rows = analyze_paired_runs([record], [method, oracle])
    structured = next(row for row in rows if row["method"] == "structured_payload")
    assert structured["utilization_ceiling"] is True
    assert structured["handoff_regret"] is True
