from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .schemas import COARSE_ERROR_TAGS, DATA_ROUTES
from .utils import json_dumps, json_loads_or_none, parse_bool, safe_text


def _parse_tags(value: Any) -> list[dict[str, str]]:
    parsed = json_loads_or_none(value) or []
    tags: list[dict[str, str]] = []
    for item in parsed:
        if isinstance(item, str):
            coarse = item if item in COARSE_ERROR_TAGS else "needs_human_review"
            tags.append({"coarse_error_tag": coarse, "error_subtype": ""})
        elif isinstance(item, dict):
            coarse = safe_text(item.get("coarse_error_tag"))
            subtype = safe_text(item.get("error_subtype"))
            if coarse not in COARSE_ERROR_TAGS:
                coarse = "needs_human_review"
                subtype = subtype or "non_standard_error_tag"
            tags.append({"coarse_error_tag": coarse, "error_subtype": subtype})
    return tags


def route_one(score_row: dict[str, Any]) -> dict[str, Any]:
    tags = _parse_tags(score_row.get("error_tags"))
    coarse_tags = [tag["coarse_error_tag"] for tag in tags]
    risk_level = safe_text(score_row.get("risk_level")) or "medium"
    judge_confidence = safe_text(score_row.get("judge_confidence")) or "medium"
    needs_review = parse_bool(score_row.get("needs_human_review"))
    score_rate = float(score_row.get("score_rate") or 0)

    if "fabricated_citation" in coarse_tags or risk_level == "high" or judge_confidence == "low" or needs_review:
        route = "human_review"
        main_error = "needs_human_review" if "fabricated_citation" not in coarse_tags else "fabricated_citation"
        reason = "High risk, low judge confidence, fabricated citation, or explicit review flag requires human calibration."
    elif "overclaim" in coarse_tags:
        route = "badcase" if score_rate < 0.66 else "preference"
        main_error = "overclaim"
        reason = "Overclaim behavior is useful for preference comparison or badcase regression."
    elif "missing_facts" in coarse_tags:
        route = "sft" if score_rate < 0.75 else "eval"
        main_error = "missing_facts"
        reason = "Missing-facts awareness can be converted into intake/checklist training or held-out eval."
    elif "missing_evidence_warning" in coarse_tags:
        route = "sft"
        main_error = "missing_evidence_warning"
        reason = "Evidence-risk warning should become risk-control SFT material."
    elif "weak_fact_rule_application" in coarse_tags:
        route = "eval"
        main_error = "weak_fact_rule_application"
        reason = "Weak fact-rule application should remain in targeted diagnostic eval."
    else:
        route = "eval"
        main_error = coarse_tags[0] if coarse_tags else "weak_fact_rule_application"
        reason = "Default route for diagnostic tracking."

    if route not in DATA_ROUTES:
        raise AssertionError(f"Non-standard route generated: {route}")

    priority = "P0" if route == "human_review" or risk_level == "high" else "P1" if risk_level == "medium" else "P2"
    subtype = next((tag["error_subtype"] for tag in tags if tag["coarse_error_tag"] == main_error), "")
    reusable = parse_bool(score_row.get("parsed_ok")) and route in {"eval", "sft", "preference", "badcase"}
    return {
        "sample_id": score_row["sample_id"],
        "run_id": score_row["run_id"],
        "source_dataset": score_row.get("source_dataset", ""),
        "task_category": score_row.get("task_category", ""),
        "model_alias": score_row.get("model_alias", ""),
        "version": score_row.get("version", ""),
        "main_error_type": main_error,
        "error_tags": json_dumps(tags),
        "risk_level": risk_level,
        "data_route": route,
        "route_reason": reason,
        "route_subtype": subtype,
        "priority": priority,
        "reusable_as_gold_sample": reusable,
    }


def route_scores(*, judge_scores: pd.DataFrame, output_path: str | Path) -> pd.DataFrame:
    rows = [route_one(row.to_dict()) for _, row in judge_scores.iterrows()]
    df = pd.DataFrame(rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df
