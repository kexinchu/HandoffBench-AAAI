#!/usr/bin/env python3
"""Build and audit a deterministic, anonymous confirmatory supplement.

The archive is deliberately an *analysis reproduction* package: it contains
the frozen inputs, sealed raw run records, validation/analysis source, and
published aggregate outputs needed to independently regenerate the formal and
exploratory aggregates.  It is not a model-weight distribution or an
environment image.

No Git metadata, remote URL, private provenance manifest, or absolute local
path is eligible for the archive.  The audit is fail-closed for a small,
documented set of identity-bearing path markers; it is a mechanical safeguard,
not a claim that all synthetic task content is anonymous in every context.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import lzma
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path


ARCHIVE_FORMAT = "handoffbench-anonymous-supplement-v1"
DEFAULT_ARCHIVE = "build/anonymous_supplement/handoffbench_aaai27_anonymous_supplement.zip"
SEALED_MANIFEST = "data/splits/confirmatory_v3.4.1.execution.sealed.json"
RAW_ROOTS = (
    "outputs/confirmatory_v3/ministral3-14b-2512/runs",
    "outputs/confirmatory_v3.4.1/qwen2.5-14b/runs",
)
RAW_LEDGER_FILES = (
    "outputs/confirmatory_v3/ministral3-14b-2512/execution_ledger.json",
    "outputs/confirmatory_v3.4.1/qwen2.5-14b/execution_ledger.json",
)
RAW_RUN_BUNDLE = "raw_runs.tar.xz"
RAW_RUN_COUNT = 8_800
PUBLISHED_OUTPUTS = (
    "outputs/confirmatory_v3.4.1/analysis_v3.4.1/confirmatory_results.json",
    "outputs/confirmatory_v3.4.1/analysis_v3.4.1/main_tables.tex",
    "outputs/confirmatory_v3.4.1/analysis_v3.4.1/provenance_manifest.public.json",
    "outputs/confirmatory_v3.4.1/post_confirmatory_v1/exploratory_subgroup_results.json",
    "outputs/confirmatory_v3.4.1/post_confirmatory_v1/provenance_manifest.json",
    "outputs/confirmatory_v3.4.1/post_confirmatory_v1/non_ok_descriptive_audit_v1.json",
)
PUBLIC_CONTEXT = (
    "configs/confirmatory_v3_matrix.json",
    "annotations/confirmatory_v3/agreement.final.v2.json",
    "research/annotation_provenance_correction_v1.json",
    "research/annotation_provenance_correction_v1.md",
    "research/confirmatory_v3.4.1_execution_audit.md",
    "research/runtime_environment_snapshot_v3.4.1.md",
    "research/non_ok_descriptive_audit_v1.md",
    "research/human_spot_check_record_v1.md",
    "release/ANONYMOUS_SUPPLEMENT_README.md",
    "release/DATA_AND_MODEL_CARD.md",
    "release/RELEASE_SCOPE.md",
    "LICENSE",
    "DATA_LICENSE.md",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
)
SOURCE_SCRIPTS = (
    "scripts/analyze_confirmatory.py",
    "scripts/analyze_post_confirmatory_subgroups.py",
    "scripts/audit_confirmatory_non_ok.py",
    "scripts/build_anonymous_supplement.py",
)
PUBLIC_TESTS = (
    "tests/test_anonymous_supplement.py",
    "tests/test_confirmatory_analysis.py",
    "tests/test_non_ok_audit.py",
    "tests/test_post_confirmatory_analysis.py",
    "tests/test_submission_artifacts.py",
)
FORBIDDEN_PATH_PARTS = {".git", ".github", "__pycache__"}
# Keep the marker spellings split so this self-auditing script can itself be a
# supplement member without carrying a false-positive marker literal.
FORBIDDEN_TEXT_MARKERS = ("/" "home/", "kec" "23008", "git" "@", "github" ".com", "origin" "/")
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
FIXED_TAR_TIME = 1_577_836_800


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _require_file(root: Path, name: str) -> Path:
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(f"supplement input is missing: {name}")
    return path


def _add_file(files: dict[str, Path], root: Path, path: Path) -> None:
    name = _relative(path, root)
    if name in files and files[name] != path:
        raise ValueError(f"supplement path collision: {name}")
    files[name] = path


def _add_tree(files: dict[str, Path], root: Path, directory: str, pattern: str) -> None:
    tree = root / directory
    if not tree.is_dir():
        raise FileNotFoundError(f"supplement input directory is missing: {directory}")
    for path in sorted(tree.rglob(pattern)):
        if path.is_file():
            _add_file(files, root, path)


def anonymous_execution_manifest(root: Path) -> bytes:
    """Make an analysis-only manifest that drops path-bearing protocol metadata.

    The original byte-exact seal remains in the archive and its SHA-256 is
    recorded here.  The analysis code does not use the removed metadata to
    calculate any endpoint; retaining it would require shipping legacy files
    that expose absolute local paths.  This derivative must never replace or be
    described as the original execution seal.
    """
    source = _require_file(root, SEALED_MANIFEST)
    manifest = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("protocol_file_hashes"), dict):
        raise ValueError("sealed manifest lacks protocol_file_hashes")
    derivative = dict(manifest)
    derivative["protocol_file_hashes"] = {}
    derivative["anonymous_analysis_derivative"] = {
        "purpose": "recompute aggregates from supplied raw records",
        "source_sealed_manifest": SEALED_MANIFEST,
        "source_sealed_manifest_sha256": sha256_bytes(source.read_bytes()),
        "removed_field": "protocol_file_hashes",
        "reason": "some legacy protocol metadata contains absolute local paths",
        "transformation_script": "scripts/build_anonymous_supplement.py",
    }
    return (json.dumps(derivative, indent=2, sort_keys=True) + "\n").encode("utf-8")


def collect_supplement_files(root: Path, *, include_raw_runs: bool = True) -> dict[str, Path]:
    """Return the complete deterministic member inventory before archive creation."""
    files: dict[str, Path] = {}
    names = {
        SEALED_MANIFEST,
        *RAW_LEDGER_FILES,
        *PUBLISHED_OUTPUTS,
        *PUBLIC_CONTEXT,
        *SOURCE_SCRIPTS,
        *PUBLIC_TESTS,
    }
    manifest = json.loads(_require_file(root, SEALED_MANIFEST).read_text(encoding="utf-8"))
    candidates = manifest.get("candidate_files")
    if not isinstance(candidates, list) or not all(isinstance(value, str) for value in candidates):
        raise ValueError("sealed manifest lacks valid candidate_files")
    names.update(candidates)
    for name in sorted(names):
        _add_file(files, root, _require_file(root, name))
    _add_tree(files, root, "data/schemas", "*.json")
    _add_tree(files, root, "src/handoffbench", "*.py")
    if include_raw_runs:
        for raw_root in RAW_ROOTS:
            _add_tree(files, root, raw_root, "*.json")
    return dict(sorted(files.items()))


def _raw_run_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for raw_root in RAW_ROOTS:
        _add_tree(files, root, raw_root, "*.json")
    if len(files) != RAW_RUN_COUNT:
        raise ValueError(f"expected {RAW_RUN_COUNT} raw runs, found {len(files)}")
    return dict(sorted(files.items()))


def raw_run_bundle(root: Path) -> bytes:
    """Losslessly bundle raw JSON with cross-file compression.

    ZIP compresses each member independently and left the submission artifact
    perilously close to the upload cap. A deterministic inner tar.xz preserves
    every original path and byte while sharing compression context across runs.
    """
    files = _raw_run_files(root)
    with tempfile.TemporaryFile() as temporary:
        with lzma.LZMAFile(
            temporary, "wb", format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6,
        ) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for name, path in files.items():
                    data = path.read_bytes()
                    _assert_anonymous_member(name, data)
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mtime = FIXED_TAR_TIME
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(data))
        temporary.seek(0)
        return temporary.read()


def audit_raw_run_bundle(data: bytes) -> dict[str, object]:
    """Validate the nested raw-run inventory and its anonymous contents."""
    names: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tar:
        for info in tar:
            name = info.name
            if not info.isfile() or _unsafe_member_name(name):
                raise ValueError(f"unsafe raw-run bundle member: {name}")
            if info.mtime != FIXED_TAR_TIME or info.uid != 0 or info.gid != 0:
                raise ValueError(f"non-deterministic raw-run bundle metadata: {name}")
            extracted = tar.extractfile(info)
            if extracted is None:
                raise ValueError(f"unreadable raw-run bundle member: {name}")
            payload = extracted.read()
            if len(payload) != info.size:
                raise ValueError(f"truncated raw-run bundle member: {name}")
            _assert_anonymous_member(name, payload)
            names.append(name)
    if names != sorted(names) or len(names) != len(set(names)):
        raise ValueError("raw-run bundle paths must be unique and sorted")
    counts = {root: sum(name.startswith(root + "/") for name in names) for root in RAW_ROOTS}
    if len(names) != RAW_RUN_COUNT or any(count != 4_400 for count in counts.values()):
        raise ValueError(f"raw-run bundle inventory mismatch: {counts}")
    return {"member_count": len(names), "root_counts": counts}


def _unsafe_member_name(name: str) -> bool:
    path = Path(name)
    return (
        path.is_absolute()
        or ".." in path.parts
        or any(part in FORBIDDEN_PATH_PARTS for part in path.parts)
        or name == "MANIFEST.json"
    )


def _assert_anonymous_member(name: str, data: bytes) -> None:
    if _unsafe_member_name(name):
        raise ValueError(f"forbidden supplement member path: {name}")
    encoded_name = name.lower()
    if any(marker in encoded_name for marker in FORBIDDEN_TEXT_MARKERS):
        raise ValueError(f"identity-bearing supplement member name: {name}")
    text = data.decode("utf-8", errors="ignore").lower()
    if any(marker in text for marker in FORBIDDEN_TEXT_MARKERS):
        raise ValueError(f"identity-bearing text in supplement member: {name}")


def member_records(
    files: dict[str, Path], *, extra_payloads: dict[str, bytes] | None = None,
) -> tuple[list[dict[str, object]], dict[str, bytes]]:
    payloads = {name: path.read_bytes() for name, path in files.items()}
    for name, data in (extra_payloads or {}).items():
        if name in payloads:
            raise ValueError(f"supplement extra payload collision: {name}")
        payloads[name] = data
    for name, data in payloads.items():
        _assert_anonymous_member(name, data)
    records = [
        {"path": name, "sha256": sha256_bytes(data), "bytes": len(data)}
        for name, data in sorted(payloads.items())
    ]
    return records, payloads


def archive_manifest(records: list[dict[str, object]], *, includes_raw_runs: bool) -> bytes:
    document = {
        "format": ARCHIVE_FORMAT,
        "anonymous_review": True,
        "purpose": "reproduce frozen confirmatory aggregate analyses without model calls",
        "includes_raw_runs": includes_raw_runs,
        "raw_run_roots": list(RAW_ROOTS) if includes_raw_runs else [],
        "raw_run_storage": RAW_RUN_BUNDLE if includes_raw_runs else None,
        "raw_run_member_count": RAW_RUN_COUNT if includes_raw_runs else 0,
        "excludes": [
            ".git metadata and remotes",
            "private provenance manifests with absolute paths",
            "model weights, provider credentials, and service logs",
        ],
        "member_count": len(records),
        "members": records,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _zip_write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_archive(root: Path, output: Path, *, include_raw_runs: bool = True) -> Path:
    files = collect_supplement_files(root, include_raw_runs=False)
    extra_payloads = {
        "data/splits/confirmatory_v3.4.1.execution.anonymous.json":
            anonymous_execution_manifest(root),
    }
    if include_raw_runs:
        extra_payloads[RAW_RUN_BUNDLE] = raw_run_bundle(root)
    records, payloads = member_records(
        files,
        extra_payloads=extra_payloads,
    )
    manifest = archive_manifest(records, includes_raw_runs=include_raw_runs)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        _zip_write(archive, "MANIFEST.json", manifest)
        for name in sorted(payloads):
            _zip_write(archive, name, payloads[name])
    audit_archive(output, require_raw_runs=include_raw_runs)
    return output


def audit_archive(archive_path: Path, *, require_raw_runs: bool = True) -> dict[str, object]:
    """Fail closed if an archive is incomplete, non-deterministic in structure, or non-anonymous."""
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if (not names or names[0] != "MANIFEST.json"
                or names[1:] != sorted(names[1:])):
            raise ValueError("supplement archive members must be sorted with MANIFEST.json first")
        if len(names) != len(set(names)):
            raise ValueError("supplement archive has duplicate member names")
        if any(item.date_time != FIXED_ZIP_TIME for item in infos):
            raise ValueError("supplement archive has non-deterministic member timestamps")
        if any(_unsafe_member_name(name) for name in names if name != "MANIFEST.json"):
            raise ValueError("supplement archive has an unsafe member name")
        manifest = json.loads(archive.read("MANIFEST.json"))
        if manifest.get("format") != ARCHIVE_FORMAT or manifest.get("anonymous_review") is not True:
            raise ValueError("supplement archive has an invalid manifest")
        records = manifest.get("members")
        if not isinstance(records, list) or manifest.get("member_count") != len(records):
            raise ValueError("supplement archive has an invalid member inventory")
        expected = {record["path"]: record for record in records if isinstance(record, dict)}
        actual_names = set(names) - {"MANIFEST.json"}
        if set(expected) != actual_names or len(expected) != len(records):
            raise ValueError("supplement archive member inventory mismatch")
        for name in sorted(actual_names):
            data = archive.read(name)
            _assert_anonymous_member(name, data)
            record = expected[name]
            if record.get("sha256") != sha256_bytes(data) or record.get("bytes") != len(data):
                raise ValueError(f"supplement archive member hash mismatch: {name}")
        has_raw_runs = RAW_RUN_BUNDLE in actual_names
        raw_run_report = None
        if has_raw_runs:
            raw_run_report = audit_raw_run_bundle(archive.read(RAW_RUN_BUNDLE))
        if require_raw_runs and (not has_raw_runs or manifest.get("includes_raw_runs") is not True):
            raise ValueError("supplement archive is missing required raw confirmatory runs")
        if has_raw_runs and manifest.get("raw_run_member_count") != RAW_RUN_COUNT:
            raise ValueError("supplement manifest has an invalid raw-run count")
        return {
            "archive": str(archive_path),
            "member_count": len(actual_names),
            "includes_raw_runs": bool(manifest.get("includes_raw_runs")),
            "raw_run_members_present": has_raw_runs,
            "raw_run_inventory": raw_run_report,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_ARCHIVE))
    parser.add_argument("--audit", type=Path, help="audit an existing archive instead of building")
    parser.add_argument("--exclude-raw-runs", action="store_true",
                        help="build a lightweight structural test archive; not submission-ready")
    args = parser.parse_args()
    if args.audit:
        report = audit_archive(args.audit.resolve(), require_raw_runs=not args.exclude_raw_runs)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    root = args.repo_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    archive = build_archive(root, output.resolve(), include_raw_runs=not args.exclude_raw_runs)
    print(archive)


if __name__ == "__main__":
    main()
