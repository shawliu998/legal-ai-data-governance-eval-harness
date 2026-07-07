from pathlib import Path

from legal_eval_harness.config import load_config
from legal_eval_harness.io_excel import load_dataset
from legal_eval_harness.runner import build_run_plan


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset_manifest.yaml"


def test_run_plan_supports_multi_model_multi_version_without_duplicates():
    config = load_config(ROOT / "config.yaml")
    bundle = load_dataset(DATA)
    specs = build_run_plan(bundle, config)
    run_ids = [spec.run_id for spec in specs]

    assert len(specs) == 546
    assert len(run_ids) == len(set(run_ids))
    assert "RUN-L-001-Model_A-V0" in run_ids
    assert "RUN-L-001-Model_A-V1" in run_ids
    assert "RUN-L-001-Model_A-V2" in run_ids
    assert "RUN-L-001-Model_A-V3" in run_ids
    assert "RUN-L-040-Model_A-V2" in run_ids
