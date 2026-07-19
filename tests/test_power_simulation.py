import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/simulate_power.py"


def module():
    spec = importlib.util.spec_from_file_location("simulate_power", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def test_power_grid_is_seeded_and_uses_family_as_inference_unit():
    sim = module()
    kwargs = dict(sample_sizes=(20,), iccs=(.1,), effects=(.08,), baseline_rate=.55,
                  n_models=2, n_seeds=3, replications=20, bootstrap_draws=50,
                  alpha=.05, random_seed=71)
    first, second = sim.simulate_grid(**kwargs), sim.simulate_grid(**kwargs)
    assert first == second
    assert first["design"]["inference_unit"] == "independent task family"
    assert "nested within family" in first["design"]["models_and_seeds"]
    assert len(first["cells"]) == 1
    assert first["cells"][0]["n_families"] == 20


def test_default_requested_design_grid_and_markdown_contract():
    sim = module()
    result = sim.simulate_grid(replications=2, bootstrap_draws=10, random_seed=9)
    assert len(result["cells"]) == 4 * 3 * 3
    assert {cell["n_families"] for cell in result["cells"]} == {80, 120, 160, 200}
    assert {cell["icc"] for cell in result["cells"]} == {.05, .10, .20}
    assert {cell["target_absolute_effect"] for cell in result["cells"]} == {.05, .08, .10}
    report = sim.markdown_report(result)
    assert "not experimental evidence" in report
    assert "cannot replace independent families" in report


def test_cli_writes_json_and_markdown_without_data_inputs(tmp_path, monkeypatch):
    sim = module()
    prefix = tmp_path / "planning_power"
    monkeypatch.setattr("sys.argv", [str(SCRIPT), "--sample-sizes", "12", "--iccs", ".05",
                                    "--effects", ".08", "--replications", "3",
                                    "--bootstrap-draws", "10", "--output-prefix", str(prefix)])
    assert sim.main() == 0
    payload = json.loads(prefix.with_suffix(".json").read_text())
    assert payload["cells"][0]["n_families"] == 12
    assert prefix.with_suffix(".md").exists()
