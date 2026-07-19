from handoffbench.dataset import load_tasks


def test_annotation_packet_excludes_all_evaluator_labels():
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    path = Path(__file__).parents[1] / "scripts/export_annotation_packets.py"
    spec = spec_from_file_location("annotation_export", path)
    module = module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    record = load_tasks(Path(__file__).parents[1] /
                        "data/tasks/candidate/scheduling.json")[0]
    value = module.packet(record)
    module.assert_blind(value)
    rendered = str(value)
    for forbidden in module.FORBIDDEN_KEYS:
        assert forbidden not in rendered
