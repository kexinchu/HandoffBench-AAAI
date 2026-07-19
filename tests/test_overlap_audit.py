import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/audit_candidate_dev_overlap.py"


def module():
    spec = importlib.util.spec_from_file_location("overlap_audit", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def record(task_id, family, pool, seed, trace, action="commit"):
    return {"set": "synthetic", "file": "memory", "task_id": task_id,
            "trace": trace, "episode": {"task_id": task_id,
                "split_meta": {"template_family": family, "entity_pool": pool, "seed": seed},
                "allowed_next_actions": [{"action": action, "expected_arguments": {"id": "X1"},
                                           "when": ["consent=known"], "irreversible": True}],
                "forbidden_next_actions": [],
                "success_predicate": {"predicate_id": "event_sequence", "args": {
                    "required_events": [{"name": action, "arguments": {"id": "X1"}}],
                    "forbidden_events": []}}}}


def test_audit_detects_deliberate_exact_and_normalized_overlap():
    audit = module()
    trace = [{"trace_id": "e1", "source_type": "user",
              "content": {"goal": "Book room R17 on 2027-01-02"}}]
    dev = record("dev_1", "same_family", "same_pool", 7, trace)
    candidate = record("cand_1", "same_family", "same_pool", 7, trace)
    result = audit.audit([candidate], [dev], lexical_threshold=.5)
    for signal in ("family_id", "entity_pool", "generator_seed", "exact_trace_hash",
                   "normalized_trace_hash", "exact_action_graph_hash",
                   "normalized_action_graph_hash"):
        assert result["collisions"][signal]
    assert result["lexical_near_duplicates"][0]["jaccard"] == 1


def test_normalization_catches_id_only_rewrites_but_exact_hash_does_not():
    audit = module()
    left = record("dev_1", "dev_family", "dev_pool", 1,
                  [{"trace_id": "d1", "source_type": "tool",
                    "content": {"verified_slot": "slot_A17", "date": "2027-01-02"}}])
    right = record("cand_1", "candidate_family", "candidate_pool", 2,
                   [{"trace_id": "c9", "source_type": "tool",
                     "content": {"verified_slot": "slot_B93", "date": "2028-04-09"}}])
    result = audit.audit([right], [left], lexical_threshold=.5)
    assert not result["collisions"]["exact_trace_hash"]
    assert result["collisions"]["normalized_trace_hash"]
