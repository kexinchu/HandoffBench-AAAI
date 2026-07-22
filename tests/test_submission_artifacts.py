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
    assert len(hashes) == 33 and all(len(digest) == 64 for digest in hashes.values())
    assert "paper/figures/handoffbench_overview.tex" in hashes
    assert tables["confirmatory"]["development_only"] is False
    assert tables["confirmatory"]["n_runs"] == 8800
    assert tables["confirmatory"]["n_tasks"] == 200
    assert tables["confirmatory"]["tests"]["structured_vs_oracle"]["effect"] == -.195
    assert tables["confirmatory"]["tests"]["advisory_checks_main_effect"]["effect"] == .03625
    assert tables["post_confirmatory_exploratory"]["confirmatory_inference"] is False
    assert tables["post_confirmatory_exploratory"]["checks_by_model"]["qwen2.5-14b"]["effect"] == .001875
    assert tables["post_confirmatory_exploratory"]["non_ok_descriptive"]["overall"]["non_ok_rows"] == 178
    rows = (output / "development_table_rows.tex").read_text()
    assert "Full History & 44/48 & 91.7\\%" in rows
    assert "typing: 0.0260416666667" in rows
    assert "checks: 0.0677083333333" in rows
    assert "structured_vs_oracle: -0.195" in rows
    assert "advisory_checks_main_effect: 0.03625" in rows
    evidence = (ROOT / "paper/sections/evidence.tex").read_text()
    for paper_value in ("scheduled 384 cells", "381 completed", "$+2.60$ pp",
                        "$-6.77$ pp", "$+6.77$ pp", "$-4.69$ pp"):
        assert paper_value in evidence
    for paper_value in ("8,800 scheduled ITT cells", "$-19.50$ percentage points",
                        "improved strict success by 3.63 points",
                        "71.63 / 91.13", "70.19 / 73.81"):
        assert paper_value in evidence


def test_checklist_draft_has_no_unanswered_question_placeholders():
    checklist = (ROOT / "paper/ReproducibilityChecklist_draft.tex").read_text()
    question_section = checklist.split("% The questions start here", 1)[1]
    assert "Type your response here" not in question_section
    assert question_section.count("\\question{") == 31
