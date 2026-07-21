from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from handoffbench.dataset import load_tasks


ROOT = Path(__file__).parents[1]


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BUILD = _module("build_confirmatory_v3", "scripts/build_confirmatory_v3.py")
AUDIT = _module("audit_confirmatory_v3", "scripts/audit_confirmatory_v3.py")
TASK_FILES = tuple(
    ROOT / "data/tasks/confirmatory_v3" / f"{domain}.json"
    for domain in BUILD.DOMAINS
)


def test_confirmatory_v3_is_exactly_137_plus_63_and_five_by_40() -> None:
    by_domain, annotations, lineage = BUILD.build_payloads()
    assert {domain: len(items) for domain, items in by_domain.items()} == {
        domain: 40 for domain in BUILD.DOMAINS
    }
    assert annotations["task_count"] == 200
    assert annotations["composition"] == {
        "retained_original": 137,
        "replacement_adjudicated": 47,
        "replacement_protocol_exact_agreement": 16,
    }
    assert lineage["composition"]["rejection_union"] == 63
    assert len(lineage["excluded_original_task_ids"]) == 63
    records = sum((load_tasks(path) for path in TASK_FILES), [])
    assert len(records) == 200
    assert Counter(record.episode.domain for record in records) == Counter(
        {domain: 40 for domain in BUILD.DOMAINS}
    )
    assert len({record.episode.task_id for record in records}) == 200
    assert len({record.episode.split_meta.template_family for record in records}) == 200


def test_agreement_only_tasks_are_protocol_exact_and_absent_from_queue() -> None:
    left = BUILD._index(BUILD._load(BUILD.REPLACEMENT_A)["annotations"])
    right = BUILD._index(BUILD._load(BUILD.REPLACEMENT_B)["annotations"])
    queue_ids = {
        item["task_id"] for item in BUILD._load(BUILD.REPLACEMENT_QUEUE)["queue"]
    }
    agreement_only = set(left) - queue_ids
    assert len(queue_ids) == 47
    assert len(agreement_only) == 16
    assert all(BUILD._protocol_view(left[item]) == BUILD._protocol_view(right[item])
               for item in agreement_only)


def test_final_audit_recomputes_and_all_hard_gates_pass() -> None:
    expected = AUDIT.audit(TASK_FILES)
    stored = json.loads(BUILD.FINAL_AUDIT.read_text(encoding="utf-8"))
    assert stored == expected
    assert stored["status"] == "pass_unsealed"
    assert all(stored["hard_checks"].values())
    assert stored["summary"]["unique_legal_terminal_without_phi"] == 200
    # These are recomputed diagnostics, not copied from the v2 reports.
    assert stored["summary"]["development_normalized_topology_flags"] == 69
    assert stored["summary"]["leakage_successes"]["name_only"] == 61
    assert stored["summary"]["leakage_successes"]["exact_copy"] == 200


def test_ready_agreement_binds_chain_but_does_not_seal_or_authorize() -> None:
    agreement = json.loads(BUILD.AGREEMENT.read_text(encoding="utf-8"))
    assert agreement["status"] == "ready_to_seal"
    assert agreement["protocol"] == "handoffbench-confirmatory-v3"
    assert agreement["seal_id"] is None
    assert agreement["accepted_task_ids"] == sorted(agreement["accepted_task_ids"])
    assert len(agreement["accepted_task_ids"]) == 200
    assert agreement["double_annotated_tasks"] == 200
    assert agreement["annotators_per_task"] == 2
    assert agreement["adjudication_complete"] is True
    assert agreement["agreement_gate_passed"] is True
    assert agreement["execution_authorized"] is False
    for item in agreement["artifact_chain"].values():
        path = ROOT / item["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_v3_config_is_sealed_and_execution_authorized_after_tagged_freeze() -> None:
    config = yaml.safe_load((ROOT / "configs/confirmatory_v3.yaml").read_text(encoding="utf-8"))
    assert config["protocol"] == "handoffbench-confirmatory-v3"
    assert config["status"] == "sealed_execution_authorized"
    assert config["execution_authorized"] is True
    assert config["annotation_agreement"] == "annotations/confirmatory_v3/agreement.final.v2.json"
    assert len(config["candidate_files"]) == 5
    manifest_path = ROOT / config["sealed_manifest"]
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    agreement = json.loads((ROOT / config["annotation_agreement"]).read_text(encoding="utf-8"))
    assert manifest["status"] == "sealed" and manifest["sealed"] is True
    assert agreement["status"] == "complete"
    # Human agreement remains bound to the original immutable dataset seal;
    # the execution seal independently binds the corrected runner/design.
    assert agreement["seal_id"] == manifest["dataset_seal_id"]
    assert manifest["seal_id"].startswith("hb-v3.2-exec-")
    assert manifest["supersedes_manifest"]["path"] == \
        "data/splits/confirmatory_v3.1.sealed.json"
    assert manifest["canonical_dataset_sha256"] == agreement["canonical_dataset_sha256"]
    assert agreement["execution_authorized"] is False
    assert config["model_snapshot_manifest"] == "configs/confirmatory_v3_model_snapshots.v2.json"


def test_builder_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "existing.json"
    path.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        BUILD._write(path, {"replacement": True})
    assert path.read_text(encoding="utf-8") == "keep"
