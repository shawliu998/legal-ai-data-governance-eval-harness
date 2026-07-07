from pathlib import Path

from legal_eval_harness.config import load_config
from legal_eval_harness.io_excel import find_eval_row, find_gold_row, load_dataset
from legal_eval_harness.schemas import PROTECTED_GOLD_FIELDS, VISIBLE_INPUT_FIELDS


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset_manifest.yaml"


def test_eval_input_has_no_gold_columns():
    load_config(ROOT / "config.yaml")
    bundle = load_dataset(DATA, jurisdiction="中国大陆", law_snapshot_date="2026-07-07")

    assert list(bundle.eval_input.columns) == VISIBLE_INPUT_FIELDS
    assert PROTECTED_GOLD_FIELDS.isdisjoint(set(bundle.eval_input.columns))
    assert len(bundle.eval_input) == 85
    assert len(bundle.gold_labels) == 85
    assert set(bundle.eval_input["task_category"]) == {"consultation", "case_analysis", "document_drafting"}


def test_gold_labels_are_separate_from_eval_input():
    bundle = load_dataset(DATA)
    eval_row = find_eval_row(bundle, "L-001")
    gold_row = find_gold_row(bundle, "L-001")

    assert "录用条件是否提前告知" not in eval_row["known_facts"]
    assert "录用条件是否提前告知" in gold_row["key_missing_facts"]
