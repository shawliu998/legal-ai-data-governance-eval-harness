from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .aggregator import build_executive_dashboard
from .config import get_project_default, load_config
from .dataset_builder import build_normalized_dataset
from .io_excel import find_eval_row, load_dataset
from .judge import run_judge
from .prompt_builder import PromptBuilder
from .runner import build_run_plan, run_models
from .router import route_scores
from .schemas import PROTECTED_GOLD_FIELDS, VISIBLE_INPUT_FIELDS


def _load_bundle(input_path: str, config: dict) -> object:
    return load_dataset(
        input_path,
        jurisdiction=get_project_default(config, "jurisdiction", "中国大陆"),
        law_snapshot_date=get_project_default(config, "law_snapshot_date", "2026-07-07"),
        legal_advice_boundary=get_project_default(
            config, "legal_advice_boundary", "仅用于诊断评测，不构成法律咨询。"
        ),
    )


def cmd_validate(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    run_count = len(build_run_plan(bundle, config))
    leaked = sorted(PROTECTED_GOLD_FIELDS.intersection(bundle.eval_input.columns))
    if leaked:
        raise SystemExit(f"Eval_Input leaked protected gold fields: {leaked}")
    print("Validation OK")
    print(f"Eval_Input columns: {list(bundle.eval_input.columns)}")
    print(f"Gold_Labels columns: {list(bundle.gold_labels.columns)}")
    print(f"Samples: {bundle.eval_input['sample_id'].nunique()}")
    print(f"Rubric rows: {len(bundle.rubric_items)}")
    if "task_category" in bundle.eval_input.columns:
        print(f"Task categories: {bundle.eval_input['task_category'].value_counts().to_dict()}")
    if "source_dataset" in bundle.eval_input.columns:
        print(f"Source datasets: {bundle.eval_input['source_dataset'].value_counts().to_dict()}")
    print(f"Planned normalized runs: {run_count}")


def cmd_prepare_data(args: argparse.Namespace) -> None:
    eval_input, gold_labels, rubric_items = build_normalized_dataset(
        input_workbook=args.input_workbook,
        output_dir=args.output_dir,
    )
    print(f"Wrote {len(eval_input)} Eval_Input rows to {Path(args.output_dir) / 'eval_input.csv'}")
    print(f"Wrote {len(gold_labels)} Gold_Labels rows to {Path(args.output_dir) / 'gold_labels.csv'}")
    print(f"Wrote {len(rubric_items)} Rubric_Items rows to {Path(args.output_dir) / 'rubric_items.csv'}")


def cmd_render_prompts(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    eval_row = find_eval_row(bundle, args.sample_id)
    builder = PromptBuilder(args.prompt_dir)
    prompt, visible = builder.render_agent_prompt(
        args.version, eval_row, v0_output=args.v0_output or "[V0 output placeholder for blind review]"
    )
    print(f"Visible fields: {visible}")
    print(prompt)


def cmd_run_models(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    df = run_models(bundle=bundle, config=config, mode=args.mode, output_path=args.output)
    print(f"Wrote {len(df)} normalized model runs to {args.output}")


def cmd_run_judge(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    runs = pd.read_csv(args.runs)
    df = run_judge(runs=runs, bundle=bundle, config=config, mode=args.mode, output_path=args.output)
    print(f"Wrote {len(df)} judge scores to {args.output}")


def cmd_route_data(args: argparse.Namespace) -> None:
    scores = pd.read_csv(args.scores)
    df = route_scores(judge_scores=scores, output_path=args.output)
    print(f"Wrote {len(df)} routing decisions to {args.output}")


def cmd_summarize(args: argparse.Namespace) -> None:
    runs = pd.read_csv(args.runs)
    scores = pd.read_csv(args.scores)
    routing = pd.read_csv(args.routing)
    dashboard = build_executive_dashboard(runs=runs, scores=scores, routing=routing, output_path=args.output)
    print(f"Wrote executive dashboard to {args.output}")
    print(dashboard)


def cmd_all(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    model_path = output_dir / "model_run_log.csv"
    judge_path = output_dir / "judge_scores.csv"
    routing_path = output_dir / "data_routing.csv"
    dashboard_path = output_dir / "executive_dashboard.xlsx"

    runs = run_models(bundle=bundle, config=config, mode=args.mode, output_path=model_path)
    scores = run_judge(runs=runs, bundle=bundle, config=config, mode=args.mode, output_path=judge_path)
    routing = route_scores(judge_scores=scores, output_path=routing_path)
    dashboard = build_executive_dashboard(runs=runs, scores=scores, routing=routing, output_path=dashboard_path)
    print("Pipeline complete")
    print(f"Samples: {scores['sample_id'].nunique()}")
    print(f"Runs: {len(runs)}")
    print(f"Scores: {len(scores)}")
    print(f"Human review queue size: {(routing['data_route'] == 'human_review').sum()}")
    print(f"Dashboard: {dashboard}")
    print(f"Outputs: {model_path}, {judge_path}, {routing_path}, {dashboard_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legal AI data-loop governance MVP")
    parser.set_defaults(func=None)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--prompt-dir", default="prompts")

    sub = parser.add_subparsers(dest="command")

    prepare = sub.add_parser("prepare-data")
    prepare.add_argument("--input-workbook", default="data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx")
    prepare.add_argument("--output-dir", default="data")
    prepare.set_defaults(func=cmd_prepare_data)

    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    validate.add_argument("--config", default="config.yaml")
    validate.set_defaults(func=cmd_validate)

    render = sub.add_parser("render-prompts")
    render.add_argument("--input", required=True)
    render.add_argument("--config", default="config.yaml")
    render.add_argument("--prompt-dir", default="prompts")
    render.add_argument("--sample-id", required=True)
    render.add_argument("--version", choices=["V0", "V1", "V2", "V3"], required=True)
    render.add_argument("--v0-output", default="")
    render.set_defaults(func=cmd_render_prompts)

    run_models_cmd = sub.add_parser("run-models")
    run_models_cmd.add_argument("--input", required=True)
    run_models_cmd.add_argument("--config", default="config.yaml")
    run_models_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    run_models_cmd.add_argument("--output", default="outputs/model_run_log.csv")
    run_models_cmd.set_defaults(func=cmd_run_models)

    judge_cmd = sub.add_parser("run-judge")
    judge_cmd.add_argument("--input", required=True)
    judge_cmd.add_argument("--config", default="config.yaml")
    judge_cmd.add_argument("--runs", required=True)
    judge_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    judge_cmd.add_argument("--output", default="outputs/judge_scores.csv")
    judge_cmd.set_defaults(func=cmd_run_judge)

    route_cmd = sub.add_parser("route-data")
    route_cmd.add_argument("--scores", required=True)
    route_cmd.add_argument("--output", default="outputs/data_routing.csv")
    route_cmd.set_defaults(func=cmd_route_data)

    summarize = sub.add_parser("summarize")
    summarize.add_argument("--runs", required=True)
    summarize.add_argument("--scores", required=True)
    summarize.add_argument("--routing", required=True)
    summarize.add_argument("--output", default="outputs/executive_dashboard.xlsx")
    summarize.set_defaults(func=cmd_summarize)

    all_cmd = sub.add_parser("all")
    all_cmd.add_argument("--input", required=True)
    all_cmd.add_argument("--config", default="config.yaml")
    all_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    all_cmd.add_argument("--output-dir", default="outputs")
    all_cmd.set_defaults(func=cmd_all)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        raise SystemExit(2)
    for field in VISIBLE_INPUT_FIELDS:
        if field in PROTECTED_GOLD_FIELDS:
            raise AssertionError(f"Visible field is also protected: {field}")
    args.func(args)


if __name__ == "__main__":
    main()
