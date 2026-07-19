import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_offline_submission_artifact_builder(tmp_path):
    output = tmp_path / "repro"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_submission_artifacts.py"),
         "--output-dir", str(output)],
        cwd=ROOT, check=True,
    )
    environment = json.loads((output / "environment.json").read_text())
    tables = json.loads((output / "table_sources.json").read_text())
    hashes = json.loads((output / "input_hashes.json").read_text())
    assert environment["packages"]["pydantic"]
    assert tables["development_only"] is True
    assert tables["legacy_success"]["ehc"] == {"n_expected": 48, "success_rate": .6875}
    assert tables["factorial"]["n_runs"] == 384
    assert tables["factorial"]["n_ok"] == 381
    assert tables["factorial"]["source_fairness"]["pass"] is True
    assert len(hashes) == 9 and all(len(digest) == 64 for digest in hashes.values())
    rows = (output / "development_table_rows.tex").read_text()
    assert "Full History & 44/48 & 91.7\\%" in rows
    assert "typing: 0.0260416666667" in rows
    assert "checks: 0.0677083333333" in rows
    evidence = (ROOT / "paper/sections/evidence.tex").read_text()
    for paper_value in ("scheduled 384 cells", "381 completed", "+2.60 pp",
                        "$-6.77$ pp", "+6.77 pp", "$-4.69$ pp"):
        assert paper_value in evidence


def test_checklist_draft_has_no_unanswered_question_placeholders():
    checklist = (ROOT / "paper/ReproducibilityChecklist_draft.tex").read_text()
    question_section = checklist.split("% The questions start here", 1)[1]
    assert "Type your response here" not in question_section
    assert question_section.count("\\question{") == 31
