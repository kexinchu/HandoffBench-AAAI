import json
from dataclasses import replace

from handoffbench.dataset import load_tasks
from handoffbench.models import ClaimCategory
from handoffbench.pilot_analysis import aggregate_runs, score_boundary_transfer, score_receiver_state
from handoffbench.transfer import oracle_state


def test_receiver_state_oracle_scores_perfect_and_missing_critical_fails():
    record = load_tasks()[0]
    perfect = score_receiver_state(record, oracle_state(record))
    assert perfect["macro_state_f1"] == 1
    assert perfect["critical_errors"] == 0
    empty = score_receiver_state(record, {})
    assert empty["macro_state_f1"] < 1
    assert empty["critical_errors"] == len(record.episode.scoring.critical_keys)


def test_macro_ignores_empty_empty_categories():
    record = load_tasks()[0]
    state = {field: [] for field in oracle_state(record)}
    scored = score_receiver_state(record, state)
    assert scored["macro_state_f1"] == 0


def test_headline_state_score_explicitly_ignores_non_primary_gold_claims():
    record = load_tasks()[0]
    excluded = record.episode.gold_state[0].model_copy(update={
        "category": ClaimCategory.PRECONDITION,
        "key": "evaluator_only_precondition",
        "normalizer": "derived:action_rule",
    })
    episode = record.episode.model_copy(update={
        "gold_state": [*record.episode.gold_state, excluded],
    })
    with_non_primary = replace(record, episode=episode)
    scored = score_receiver_state(with_non_primary, oracle_state(record))
    assert scored["macro_state_f1"] == 1
    assert "evaluator_only_precondition" not in json.dumps(scored)


def test_receiver_duplicate_prediction_is_a_false_positive():
    record = load_tasks()[0]
    state = oracle_state(record)
    populated = next(field for field, claims in state.items() if claims)
    state[populated].append(dict(state[populated][0]))
    scored = score_receiver_state(record, state)
    assert scored["field_scores"][populated]["precision"] < 1
    assert scored["state_fp"] >= 1


def test_boundary_transfer_scores_first_probe_not_post_reply_state():
    record = load_tasks()[0]
    empty = {field: [] for field in oracle_state(record)}
    scored = score_boundary_transfer(record, [oracle_state(record), empty])
    assert scored["macro_state_f1"] == 1


def test_paired_table_aligns_methods_on_task_model_seed():
    base = {"task_id": "t", "model": "m", "seed": 1, "status": "ok"}
    runs = [base | {"method": method, "metrics": {"strict_success": success,
             "macro_state_f1": success, "critical_errors": 1 - success, "input_tokens": 10}}
            for method, success in (("full_history", 1), ("ehc", 0))]
    _, paired = aggregate_runs(runs)
    assert len(paired) == 1
    assert paired[0]["full_history.strict_success"] == 1
    assert paired[0]["ehc.strict_success"] == 0
