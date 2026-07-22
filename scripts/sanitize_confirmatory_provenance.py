#!/usr/bin/env python3
"""Create an anonymous, repo-relative derivative of a sealed provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(value, repo_root: Path):
    prefix = str(repo_root.resolve()) + "/"
    if isinstance(value, str):
        if value == str(repo_root.resolve()):
            return "${REPO_ROOT}"
        if value.startswith(prefix):
            return value[len(prefix):]
        return value
    if isinstance(value, list):
        return [sanitize(item, repo_root) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            clean_key = sanitize(key, repo_root)
            if clean_key in result:
                raise ValueError(f"path sanitization collision: {clean_key}")
            result[clean_key] = sanitize(item, repo_root)
        return result
    return value


def build_public_manifest(source: Path, repo_root: Path) -> dict:
    private = json.loads(source.read_text(encoding="utf-8"))
    public = sanitize(private, repo_root)
    public["public_derivative"] = {
        "anonymized_paths": True,
        "source_private_manifest_sha256": sha256(source),
        "transformation_script": "scripts/sanitize_confirmatory_provenance.py",
        "transformation_script_sha256": sha256(Path(__file__)),
    }
    raw = public.get("raw_run_files", {})
    if len(raw) != private.get("n_raw_runs"):
        raise ValueError("public raw hash inventory count does not match n_raw_runs")
    if sorted(raw.values()) != sorted(private.get("raw_run_files", {}).values()):
        raise ValueError("raw file hash values changed during sanitization")
    encoded = json.dumps(public, sort_keys=True)
    forbidden = ("/home/", "kec23008")
    if any(token in encoded for token in forbidden):
        raise ValueError("identity-bearing absolute path remains in public manifest")
    return public


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    public = build_public_manifest(args.source.resolve(), args.repo_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
