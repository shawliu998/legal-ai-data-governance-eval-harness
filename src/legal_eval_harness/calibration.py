from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import json_loads_or_none, safe_text


CRITICAL_TAGS = {"fabricated_citation", "unsafe_action_suggestion", "needs_human_review"}


def _coarse_tags(value: Any) -> list[str]:
    parsed = json_loads_or_none(value) or []
    tags: list[str] = []
    for item in parsed:
        if isinstance(item, dict):
            tag = safe_text(item.get("coarse_error_tag"))
        else:
            tag = safe_text(item)
        if tag:
            tags.append(tag)
    return tags


def _is_critical(row: pd.Series) -> bool:
    tags = set(_coarse_tags(row.get("error_tags")))
    return (
        safe_text(row.get("risk_level")) == "high"
        or safe_text(row.get("judge_confidence")) == "low"
        or bool(row.get("needs_human_review"))
        or bool(tags.intersection(CRITICAL_TAGS))
    )


def build_human_review_sample(
    *,
    runs: pd.DataFrame,
    scores: pd.DataFrame,
    routing: pd.DataFrame,
    output_path: str | Path,
    sample_rate: float = 0.2,
    min_samples: int = 20,
    random_state: int = 7,
) -> pd.DataFrame:
    if not 0 < sample_rate <= 1:
        raise ValueError("sample_rate must be in (0, 1]")

    run_subset = runs.copy()
    if "workflow_condition" not in run_subset.columns:
        run_subset["workflow_condition"] = run_subset.get("version", "")
        run_subset["workflow_name"] = run_subset.get("version", "")
    for col in ["model_vendor", "model_family", "latency_ms", "estimated_cost"]:
        if col not in run_subset.columns:
            run_subset[col] = 0 if col in {"latency_ms", "estimated_cost"} else ""
    merged = scores.merge(
        routing[
            [
                "run_id",
                "data_route",
                "main_error_type",
                "route_reason",
                "priority",
            ]
        ],
        on="run_id",
        how="left",
    ).merge(
        run_subset[
            [
                "run_id",
                "model_vendor",
                "model_family",
                "workflow_condition",
                "workflow_name",
                "output_text",
                "latency_ms",
                "estimated_cost",
            ]
        ],
        on="run_id",
        how="left",
    )

    merged["critical_for_review"] = merged.apply(_is_critical, axis=1)
    target = min(len(merged), max(min_samples, math.ceil(len(merged) * sample_rate)))

    selected = merged[merged["critical_for_review"]].copy()
    if len(selected) < target:
        remaining = merged[~merged["run_id"].isin(selected["run_id"])].copy()
        strata = [col for col in ["task_category", "model_alias", "workflow_condition", "risk_level"] if col in remaining]
        sampled_parts = []
        if strata and not remaining.empty:
            per_stratum = max(1, math.ceil((target - len(selected)) / max(1, remaining.groupby(strata).ngroups)))
            for _, group in remaining.groupby(strata, dropna=False):
                sampled_parts.append(
                    group.sample(n=min(per_stratum, len(group)), random_state=random_state)
                )
            sampled = pd.concat(sampled_parts, ignore_index=False) if sampled_parts else remaining.head(0)
            sampled = sampled.drop_duplicates("run_id")
            if len(sampled) > target - len(selected):
                sampled = sampled.sample(n=target - len(selected), random_state=random_state)
        else:
            sampled = remaining.sample(n=min(target - len(selected), len(remaining)), random_state=random_state)
        selected = pd.concat([selected, sampled], ignore_index=False)

    if len(selected) > target and not selected["critical_for_review"].all():
        critical = selected[selected["critical_for_review"]]
        non_critical = selected[~selected["critical_for_review"]]
        keep_non_critical = max(0, target - len(critical))
        if keep_non_critical:
            non_critical = non_critical.sample(n=keep_non_critical, random_state=random_state)
        else:
            non_critical = non_critical.head(0)
        selected = pd.concat([critical, non_critical], ignore_index=False)

    selected = selected.sort_values(
        ["critical_for_review", "task_category", "risk_level", "sample_id", "model_alias", "version"],
        ascending=[False, True, True, True, True, True],
    ).copy()
    selected["human_pass_fail"] = ""
    selected["human_corrected_score_rate"] = ""
    selected["human_critical_failure"] = ""
    selected["human_notes"] = ""
    selected["judge_human_agreement"] = ""

    columns = [
        "run_id",
        "sample_id",
        "source_dataset",
        "task_category",
        "model_alias",
        "model_vendor",
        "model_family",
        "version",
        "workflow_condition",
        "workflow_name",
        "score_rate",
        "risk_level",
        "judge_confidence",
        "needs_human_review",
        "data_route",
        "main_error_type",
        "priority",
        "critical_for_review",
        "latency_ms",
        "estimated_cost",
        "judge_reason",
        "output_text",
        "human_pass_fail",
        "human_corrected_score_rate",
        "human_critical_failure",
        "human_notes",
        "judge_human_agreement",
    ]
    for col in columns:
        if col not in selected.columns:
            selected[col] = ""
    result = selected[columns].reset_index(drop=True)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result
