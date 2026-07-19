import csv
import hashlib
import json

import pytest

from handoffbench.annotation_agreement import (
    analyze_agreement, load_locked_annotations, markdown_report,
)


def claim(key, category="verified_fact", status="known", value=1,
          criticality="terminal", trace="e1"):
    return {"key": key, "category": category, "status": status, "value": value,
            "criticality": criticality,
            "provenance": [{"trace_id": trace, "source_type": "tool",
                            "field_path": f"content.{key}"}]}


def payload(annotator, *, duplicate=False, missing_task=False):
    first_claims = [claim("x"), claim("open", "unresolved_slot", "unknown", None, "safety", "e2")]
    if duplicate:
        first_claims.append(claim("x"))
    tasks = [{"task_id": "t1", "template_family": "family_one", "claims": first_claims,
              "action_sequence": [{"name": "ask", "arguments": {"slot": "open"}}]},
             {"task_id": "t2", "template_family": "family_two",
              "claims": [claim("policy", "policy_check", value=True, criticality="safety")],
              "action_sequence": [{"name": "stop", "arguments": {}}]}]
    if missing_task:
        tasks.pop()
    return {"annotator_id": annotator, "annotations": tasks}


def write_locked(tmp_path, a_payload, b_payload):
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    for path, value in zip(paths, (a_payload, b_payload)):
        path.write_text(json.dumps(value), encoding="utf-8")
    manifest = {"locked": True, "expected_task_ids": ["t1", "t2"], "inputs": [
        {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
         "annotator_id": value.get("annotator_id", "missing")}
        for path, value in zip(paths, (a_payload, b_payload))
    ]}
    lock = tmp_path / "lock.json"; lock.write_text(json.dumps(manifest), encoding="utf-8")
    return paths, lock


def test_one_to_one_metrics_kappa_action_and_cluster_bootstrap(tmp_path):
    a, b = payload("ann-a"), payload("ann-b")
    b["annotations"][0]["claims"] = [claim("x"), claim("extra", value=9)]
    b["annotations"][0]["action_sequence"] = [{"name": "stop", "arguments": {}}]
    paths, lock = write_locked(tmp_path, a, b)
    first, second = load_locked_annotations(*paths, lock)
    report = analyze_agreement(first, second, draws=200, seed=2027)
    metrics = report["metrics"]
    assert metrics["claim"]["tp"] == 2
    assert metrics["claim"]["annotator_a_denominator"] == 3
    assert metrics["claim"]["annotator_b_denominator"] == 3
    assert metrics["claim"]["f1"] == pytest.approx(2 / 3)
    assert metrics["category"]["denominator"] == 2
    assert metrics["category"]["cohen_kappa"] == 1
    assert metrics["status"]["cohen_kappa"] is None
    assert metrics["criticality"]["cohen_kappa"] == 1
    assert metrics["action_sequence"] == {
        "agree": 1, "denominator": 2, "rate": .5,
        "cluster_bootstrap_ci": [0.0, 1.0],
    }
    assert report["n_families"] == 2
    assert any(item["fields"] == ["action_sequence"] for item in report["adjudication_queue"])
    assert "Double-Annotation Agreement" in markdown_report(report)


def test_kappa_is_null_when_both_do_not_use_two_labels(tmp_path):
    a = payload("a"); b = payload("b")
    a["annotations"] = a["annotations"][:1]; b["annotations"] = b["annotations"][:1]
    a["annotations"][0]["claims"] = [claim("x")]; b["annotations"][0]["claims"] = [claim("x")]
    paths, lock = write_locked(tmp_path, a, b)
    manifest = json.loads(lock.read_text()); manifest["expected_task_ids"] = ["t1"]
    lock.write_text(json.dumps(manifest))
    first, second = load_locked_annotations(*paths, lock)
    assert analyze_agreement(first, second, draws=20)["metrics"]["category"]["cohen_kappa"] is None


@pytest.mark.parametrize("failure", ["duplicate", "coverage", "hash", "assignment"])
def test_rejects_invalid_or_unlocked_inputs(tmp_path, failure):
    a, b = payload("a", duplicate=failure == "duplicate"), payload("b", missing_task=failure == "coverage")
    if failure == "assignment":
        a = {"assignments": [{"task_id": "t1", "response": None}]}
    paths, lock = write_locked(tmp_path, a, b)
    if failure == "hash":
        paths[0].write_text(paths[0].read_text() + " ")
    with pytest.raises((ValueError, KeyError)):
        load_locked_annotations(*paths, lock)


def test_csv_annotations_are_supported_with_external_lock(tmp_path):
    fields = ["task_id", "annotator_id", "record_type", "claim_key", "category", "status",
              "value_json", "criticality", "trace_id", "source_type", "field_path",
              "action_sequence_json"]
    paths = [tmp_path / "a.csv", tmp_path / "b.csv"]
    for path, annotator in zip(paths, ("a", "b")):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            writer.writerow({"task_id": "t1", "annotator_id": annotator,
                             "record_type": "claim", "claim_key": "x",
                             "category": "verified_fact", "status": "known", "value_json": "1",
                             "criticality": "terminal", "trace_id": "e1", "source_type": "tool",
                             "field_path": "content.x",
                             "action_sequence_json": '[{"name":"act","arguments":{}}]'})
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"locked": True, "expected_task_ids": ["t1"], "inputs": [
        {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
         "annotator_id": annotator} for path, annotator in zip(paths, ("a", "b"))]}))
    first, second = load_locked_annotations(*paths, lock)
    assert analyze_agreement(first, second, draws=20)["metrics"]["claim"]["f1"] == 1
