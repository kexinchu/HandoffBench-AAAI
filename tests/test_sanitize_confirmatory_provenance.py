import hashlib
import json
from pathlib import Path

import pytest

from scripts.sanitize_confirmatory_provenance import build_public_manifest


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_public_manifest_rewrites_paths_and_preserves_hash_inventory(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "private.json"
    private = {
        "path_base": str(root),
        "n_raw_runs": 2,
        "candidate_files": [str(root / "data/tasks/a.json")],
        "raw_run_files": {
            str(root / "outputs/runs/a.json"): digest(b"a"),
            str(root / "outputs/runs/b.json"): digest(b"b"),
        },
    }
    source.write_text(json.dumps(private))
    public = build_public_manifest(source, root)
    assert public["path_base"] == "${REPO_ROOT}"
    assert public["candidate_files"] == ["data/tasks/a.json"]
    assert set(public["raw_run_files"]) == {
        "outputs/runs/a.json", "outputs/runs/b.json"
    }
    assert sorted(public["raw_run_files"].values()) == sorted(private["raw_run_files"].values())
    assert public["public_derivative"]["source_private_manifest_sha256"] == digest(source.read_bytes())


def test_public_manifest_rejects_remaining_home_path(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "private.json"
    source.write_text(json.dumps({
        "path_base": str(root), "n_raw_runs": 0, "raw_run_files": {},
        "outside": "/home/another/private",
    }))
    with pytest.raises(ValueError, match="absolute path"):
        build_public_manifest(source, root)
