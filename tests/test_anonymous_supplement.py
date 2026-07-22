import json
import zipfile
from pathlib import Path

import pytest

from scripts.build_anonymous_supplement import (
    ARCHIVE_FORMAT,
    FIXED_ZIP_TIME,
    _zip_write,
    audit_archive,
    anonymous_execution_manifest,
    build_archive,
    collect_supplement_files,
)


ROOT = Path(__file__).parents[1]


def test_collects_complete_confirmatory_inventory_without_building_large_archive():
    files = collect_supplement_files(ROOT, include_raw_runs=True)
    assert "data/splits/confirmatory_v3.4.1.execution.sealed.json" in files
    assert "outputs/confirmatory_v3.4.1/analysis_v3.4.1/provenance_manifest.public.json" in files
    assert "outputs/confirmatory_v3.4.1/analysis_v3.4.1/provenance_manifest.json" not in files
    assert "scripts/build_anonymous_supplement.py" in files
    assert "scripts/audit_confirmatory_non_ok.py" in files
    assert "outputs/confirmatory_v3.4.1/post_confirmatory_v1/non_ok_descriptive_audit_v1.json" in files
    assert "tests/test_confirmatory_analysis.py" in files
    for name in ("LICENSE", "DATA_LICENSE.md", "NOTICE", "THIRD_PARTY_NOTICES.md"):
        assert name in files
    assert sum(name.startswith("outputs/confirmatory_v3/ministral3-14b-2512/runs/")
               for name in files) == 4400
    assert sum(name.startswith("outputs/confirmatory_v3.4.1/qwen2.5-14b/runs/")
               for name in files) == 4400
    assert not any(name.startswith(".git/") for name in files)
    anonymous = json.loads(anonymous_execution_manifest(ROOT))
    assert anonymous["protocol_file_hashes"] == {}
    assert anonymous["anonymous_analysis_derivative"]["source_sealed_manifest_sha256"]


def test_lightweight_archive_is_deterministic_and_auditable(tmp_path):
    first = build_archive(ROOT, tmp_path / "first.zip", include_raw_runs=False)
    second = build_archive(ROOT, tmp_path / "second.zip", include_raw_runs=False)
    assert first.read_bytes() == second.read_bytes()
    report = audit_archive(first, require_raw_runs=False)
    assert report["includes_raw_runs"] is False
    assert report["raw_run_members_present"] is False
    assert report["raw_run_inventory"] is None
    with zipfile.ZipFile(first) as archive:
        manifest = json.loads(archive.read("MANIFEST.json"))
        assert manifest["format"] == ARCHIVE_FORMAT
        assert manifest["includes_raw_runs"] is False
        assert all(info.date_time == FIXED_ZIP_TIME for info in archive.infolist())


def test_audit_rejects_identity_bearing_content(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    manifest = {
        "format": ARCHIVE_FORMAT,
        "anonymous_review": True,
        "includes_raw_runs": False,
        "member_count": 1,
        "members": [{"path": "note.txt", "sha256": "0" * 64, "bytes": 0}],
    }
    with zipfile.ZipFile(archive_path, "w") as archive:
        _zip_write(archive, "MANIFEST.json", json.dumps(manifest).encode())
        # Split the marker so this self-test can itself be included in an
        # anonymous archive without carrying the forbidden literal in source.
        _zip_write(archive, "note.txt", b"path=/" b"home/example")
    with pytest.raises(ValueError, match="identity-bearing"):
        audit_archive(archive_path, require_raw_runs=False)
