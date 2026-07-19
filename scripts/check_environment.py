#!/usr/bin/env python3
"""Fail early with actionable diagnostics when the project environment is wrong."""

from __future__ import annotations

import importlib.metadata
import sys


def main() -> int:
    failures = []
    if sys.version_info < (3, 11):
        failures.append(f"Python >=3.11 required; found {sys.version.split()[0]} at {sys.executable}")
    required = {"jsonschema": (4, 23), "pydantic": (2, 10), "PyYAML": (6, 0), "pytest": (8, 3)}
    for package, minimum in required.items():
        try:
            raw = importlib.metadata.version(package)
            numeric = tuple(int(part) for part in raw.split(".")[:2])
            if numeric < minimum:
                failures.append(f"{package}>={'.'.join(map(str, minimum))} required; found {raw}")
        except (importlib.metadata.PackageNotFoundError, ValueError):
            failures.append(f"{package}>={'.'.join(map(str, minimum))} is not installed")
    if failures:
        print("Invalid HandoffBench environment:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        print("Activate/install the project environment, then rerun make with PYTHON=/path/to/python.",
              file=sys.stderr)
        return 2
    print(f"environment ok: {sys.executable} ({sys.version.split()[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
