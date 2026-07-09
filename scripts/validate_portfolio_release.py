#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "FAIL: PyYAML is required. Install project dependencies with "
        '`python3 -m pip install ".[test]"` or run `.venv/bin/python`.'
    ) from exc


ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                fail(f"JSONL parse error in {path.relative_to(ROOT)}:{line_no}: {exc}")
    return rows


def iter_yaml_files() -> Iterable[Path]:
    yield from ROOT.glob("*.yaml")
    yield from (ROOT / "configs").rglob("*.yaml")
    yield from (ROOT / "outputs").rglob("*.yaml")


def check_yaml() -> None:
    for path in iter_yaml_files():
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"YAML parse error in {path.relative_to(ROOT)}: {exc}")


def check_jsonl() -> None:
    for path in (ROOT / "data").rglob("*.jsonl"):
        read_jsonl(path)

    for path in (ROOT / "outputs").rglob("*.jsonl"):
        read_jsonl(path)


def check_csv() -> None:
    for base in [ROOT / "data", ROOT / "outputs"]:
        for path in base.rglob("*.csv"):
            try:
                with path.open(encoding="utf-8", newline="") as handle:
                    reader = csv.reader(handle)
                    header = next(reader, None)
                    if header is None:
                        fail(f"Empty CSV file: {path.relative_to(ROOT)}")
                    expected_width = len(header)
                    for line_no, row in enumerate(reader, start=2):
                        if len(row) != expected_width:
                            fail(
                                f"CSV width mismatch in {path.relative_to(ROOT)}:{line_no}; "
                                f"expected {expected_width}, found {len(row)}"
                            )
            except UnicodeDecodeError:
                fail(f"CSV is not UTF-8 decodable: {path.relative_to(ROOT)}")
            except csv.Error as exc:
                fail(f"CSV parse error in {path.relative_to(ROOT)}: {exc}")


def check_case_bank() -> None:
    path = ROOT / "data/eval_sets/legal_product_boundary_pilot_v1.jsonl"
    rows = read_jsonl(path)
    if len(rows) != 50:
        fail(f"Expected 50 product-boundary cases, found {len(rows)}")

    ids = [row.get("case_id") for row in rows]
    if any(not case_id for case_id in ids):
        fail("Missing case_id in product-boundary case bank")
    if len(ids) != len(set(ids)):
        fail("Duplicate case_id in product-boundary case bank")


def check_a5_cases() -> None:
    path = ROOT / "data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl"
    rows = read_jsonl(path)
    allowed_profiles = {"cooperative", "dependent", "withdrawn", "adversarial"}

    for row in rows:
        case_id = row.get("case_id")
        raw_profile = row.get("simulator_profile") or row.get("user_behavior")
        profile = str(raw_profile or "").removesuffix("_client")
        if profile not in allowed_profiles:
            fail(f"Invalid simulator profile/user behavior in {case_id}: {raw_profile}")
        if not row.get("material_facts_to_elicit"):
            fail(f"Missing material_facts_to_elicit in {case_id}")


def check_focused_config() -> None:
    path = ROOT / "configs/experiments/legal_agent_product_eval_v2_focused.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    experiment = data.get("experiment", {})
    scope = data.get("scope", {})

    if experiment.get("status") != "planned":
        fail("Focused V2 config must remain status: planned")
    if int(scope.get("expected_model_outputs", 0)) != 450:
        fail("Focused V2 config must describe 450 planned model outputs")


def check_outputs() -> None:
    required = [
        "outputs/product_boundary_api_pilot_v1/artifact_manifest.yaml",
        "outputs/product_boundary_api_pilot_v1/metrics_summary.csv",
        "outputs/product_boundary_api_pilot_v1/release_gate_summary.csv",
        "outputs/rag_v2_focused_pilot_v1/artifact_manifest.yaml",
        "outputs/rag_v2_focused_pilot_v1/metrics_summary.csv",
        "outputs/a5_multiturn_intake_pilot_v1/artifact_manifest.yaml",
        "outputs/a5_multiturn_intake_pilot_v1/trace_metrics_summary.csv",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            fail(f"Missing evidence artifact: {rel}")


def check_markdown() -> None:
    targets = [
        "README.md",
        "docs/final_portfolio_findings.md",
        "docs/results_product_boundary_eval.md",
        "docs/model_boundary_memo.md",
        "docs/legal_agent_product_eval_v2_design.md",
        "docs/trace_level_eval_schema.md",
        "docs/a5_multiturn_pilot_results.md",
        "docs/rag_v2_focused_results.md",
        "docs/rag_v2_improvement_plan.md",
    ]
    for rel in targets:
        path = ROOT / rel
        if not path.exists():
            fail(f"Missing markdown file: {rel}")
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 20 and rel != "docs/final_portfolio_findings.md":
            fail(f"Markdown may be compressed into too few lines: {rel}")
        long_lines = [
            line_no
            for line_no, line in enumerate(lines, start=1)
            if len(line) > 350 and not line.lstrip().startswith("|")
        ]
        if long_lines:
            fail(f"Markdown has very long non-table lines in {rel}: {long_lines[:5]}")


def check_claim_boundaries() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = readme.lower()

    required_phrases = [
        "a0 baseline closed-book",
        "a5 multi-turn legal intake agent",
        "what not to claim",
    ]
    for phrase in required_phrases:
        if phrase not in lowered:
            fail(f"README is missing required release-boundary phrase: {phrase}")

    bad_phrases = [
        "450-output focused run completed",
        "450 output focused run completed",
        "full 1250 real api outputs",
        "production ready legal advice",
        "production-ready legal advice",
    ]
    for phrase in bad_phrases:
        if phrase in lowered:
            fail(f"Overclaim found in README: {phrase}")

    if "450-output focused run has already been completed" not in lowered:
        fail("README must state that the 450-output focused run is not completed")


def main() -> None:
    check_yaml()
    check_jsonl()
    check_csv()
    check_case_bank()
    check_a5_cases()
    check_focused_config()
    check_outputs()
    check_markdown()
    check_claim_boundaries()
    print("Portfolio release validation passed.")


if __name__ == "__main__":
    main()
