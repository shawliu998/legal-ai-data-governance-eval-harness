import pandas as pd

from legal_eval_harness.router import route_scores
from legal_eval_harness.schemas import DATA_ROUTES
from legal_eval_harness.utils import json_dumps


def test_router_uses_fixed_route_enum(tmp_path):
    scores = pd.DataFrame(
        [
            {
                "sample_id": "L-001",
                "run_id": "RUN-L-001-Model_A-V0",
                "error_tags": json_dumps(
                    [{"coarse_error_tag": "overclaim", "error_subtype": "premature_conclusion"}]
                ),
                "risk_level": "medium",
                "judge_confidence": "medium",
                "needs_human_review": False,
                "score_rate": 0.55,
                "parsed_ok": True,
            },
            {
                "sample_id": "L-002",
                "run_id": "RUN-L-002-Model_A-V0",
                "error_tags": json_dumps(
                    [{"coarse_error_tag": "fabricated_citation", "error_subtype": "fake_article"}]
                ),
                "risk_level": "high",
                "judge_confidence": "low",
                "needs_human_review": True,
                "score_rate": 0.2,
                "parsed_ok": True,
            },
        ]
    )

    routed = route_scores(judge_scores=scores, output_path=tmp_path / "routing.csv")
    assert set(routed["data_route"]).issubset(set(DATA_ROUTES))
    assert routed.loc[routed["sample_id"] == "L-002", "data_route"].item() == "human_review"


def test_router_does_not_treat_string_false_as_review_flag(tmp_path):
    scores = pd.DataFrame(
        [
            {
                "sample_id": "L-003",
                "run_id": "RUN-L-003-Model_A-V1",
                "error_tags": json_dumps([]),
                "risk_level": "low",
                "judge_confidence": "high",
                "needs_human_review": "False",
                "score_rate": 0.9,
                "parsed_ok": "False",
            },
        ]
    )

    routed = route_scores(judge_scores=scores, output_path=tmp_path / "routing.csv")

    row = routed.iloc[0]
    assert row["data_route"] == "eval"
    assert bool(row["reusable_as_gold_sample"]) is False
