import pandas as pd

from legal_eval_harness.calibration import build_human_review_sample
from legal_eval_harness.release_gate import build_release_gate
from legal_eval_harness.utils import json_dumps


def _frames():
    runs = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "S1",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "workflow_condition": "W0",
                "workflow_name": "closed-book answer",
                "output_text": "unsafe",
                "latency_ms": 100,
                "estimated_cost": 0.01,
            },
            {
                "run_id": "r2",
                "sample_id": "S2",
                "task_category": "case_analysis",
                "model_alias": "Model_A",
                "version": "V3",
                "workflow_condition": "W3",
                "workflow_name": "risk-control workflow agent",
                "output_text": "better",
                "latency_ms": 200,
                "estimated_cost": 0.02,
            },
            {
                "run_id": "r3",
                "sample_id": "S3",
                "task_category": "document_drafting",
                "model_alias": "Model_A",
                "version": "V3",
                "workflow_condition": "W3",
                "workflow_name": "risk-control workflow agent",
                "output_text": "ok",
                "latency_ms": 120,
                "estimated_cost": 0.01,
            },
        ]
    )
    scores = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "S1",
                "source_dataset": "pilot",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "score_rate": 0.2,
                "risk_level": "high",
                "judge_confidence": "low",
                "needs_human_review": True,
                "error_tags": json_dumps(
                    [{"coarse_error_tag": "unsafe_action_suggestion", "error_subtype": "stop_work"}]
                ),
                "judge_reason": "critical",
                "parsed_ok": True,
            },
            {
                "run_id": "r2",
                "sample_id": "S2",
                "source_dataset": "pilot",
                "task_category": "case_analysis",
                "model_alias": "Model_A",
                "version": "V3",
                "score_rate": 0.85,
                "risk_level": "low",
                "judge_confidence": "high",
                "needs_human_review": False,
                "error_tags": json_dumps([]),
                "judge_reason": "ok",
                "parsed_ok": True,
            },
            {
                "run_id": "r3",
                "sample_id": "S3",
                "source_dataset": "pilot",
                "task_category": "document_drafting",
                "model_alias": "Model_A",
                "version": "V3",
                "score_rate": 0.82,
                "risk_level": "low",
                "judge_confidence": "high",
                "needs_human_review": False,
                "error_tags": json_dumps([]),
                "judge_reason": "ok",
                "parsed_ok": True,
            },
        ]
    )
    routing = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "S1",
                "data_route": "human_review",
                "main_error_type": "unsafe_action_suggestion",
                "route_reason": "critical",
                "priority": "P0",
            },
            {
                "run_id": "r2",
                "sample_id": "S2",
                "data_route": "eval",
                "main_error_type": "none",
                "route_reason": "holdout",
                "priority": "P2",
            },
            {
                "run_id": "r3",
                "sample_id": "S3",
                "data_route": "eval",
                "main_error_type": "none",
                "route_reason": "holdout",
                "priority": "P2",
            },
        ]
    )
    return runs, scores, routing


def test_human_review_sample_includes_critical_rows(tmp_path):
    runs, scores, routing = _frames()
    sample = build_human_review_sample(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "human_review.csv",
        sample_rate=0.2,
        min_samples=1,
    )

    assert "r1" in set(sample["run_id"])
    assert sample.loc[sample["run_id"] == "r1", "critical_for_review"].item()
    assert "human_notes" in sample.columns


def test_release_gate_blocks_unsafe_action(tmp_path):
    runs, scores, routing = _frames()
    gate = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "release_gate.csv",
    )

    blocked = gate[gate["workflow_condition"] == "W0"].iloc[0]
    assert blocked["release_decision"] == "blocked"
    assert "unsafe action" in blocked["blockers"]

    candidate = gate[(gate["task_category"] == "case_analysis") & (gate["workflow_condition"] == "W3")].iloc[0]
    assert candidate["release_decision"] == "candidate_auto_answer"
