# Experiment Design

## Positioning

This is a two-day portfolio prototype for legal AI data-loop governance.
It is designed to show data product thinking, not to reproduce a public benchmark.

The prototype references common legal evaluation task taxonomy and rubric-based judging ideas, then implements a lightweight data loop:

1. Normalize legal samples.
2. Prevent gold label leakage.
3. Run multiple prompt versions across multiple model aliases.
4. Judge outputs with task-specific rubrics.
5. Route failures into data-use buckets.
6. Generate a dashboard for data production decisions.

No RAG, Web UI, database, or automatic legal citation verification is included.

## Dataset Layers

`Eval_Input` is visible to V0, V1, V2, and V3:

- `sample_id`
- `source_dataset`
- `task_category`
- `user_question`
- `known_facts`
- `legal_concepts`
- `jurisdiction`
- `law_snapshot_date`
- `task_type`
- `legal_advice_boundary`

`Gold_Labels` is visible only to Judge and Human Review:

- `key_missing_facts`
- `expected_clarification_questions`
- `expected_answer_points`
- `risk_points`
- `expected_behavior`
- `human_review_note`

`Rubric_Items` is visible only to Judge and Human Review.

This separation is the primary leakage-control design.

## Dataset Scale

The current portfolio dataset contains 85 samples:

- `self_authored_core_40`: 40 high-quality core samples.
- `reference_style_extended`: 45 synthetic reference-style samples.

Task categories:

- `consultation`
- `case_analysis`
- `document_drafting`

The extended samples are for taxonomy coverage and scale testing, not external benchmark replication.

## Agent Versions

V0 Direct Answer:
Baseline direct response using only `Eval_Input`.

V1 Answer Protocol:
Structured legal-information response using only `Eval_Input`.

V2 Blind Review Agent:
Reviews V0 output using only `Eval_Input` plus V0 output. It cannot see gold labels.

V3 Workflow Agent:
Runs intake, clarification, legal analysis, risk review, rewrite, and logger using only `Eval_Input`.

## Experiment Matrix

Full diagnostic run:

- 85 samples
- 3 model aliases
- V0 and V3
- 510 runs

Deep supplement:

- 6 selected badcases from the upgraded core workbook
- 3 model aliases
- V1 and V2 only
- 36 additional runs

Total mock/full run count:

- 546 normalized runs

## Task-Specific Judge

Judge can see `Eval_Input`, `Gold_Labels`, and `Rubric_Items`.

Consultation judge focuses on:

- missing facts
- clarification quality
- risk warning
- overclaim control

Case analysis judge focuses on:

- conclusion framing
- fact organization
- reasoning
- legal grounding
- claim/defense and procedure risks

Document drafting judge focuses on:

- document structure
- claims or defenses
- fact organization
- missing attachments/evidence
- risk omissions

The unified score dimensions remain stable across tasks:

- `missing_facts_awareness`
- `clarification_quality`
- `legal_grounding`
- `fact_rule_application`
- `conditional_reasoning`
- `risk_coverage`
- `overclaim_control`
- `hallucination_control`
- `data_tag_usability`

`score_rate = total_score / max_score`.

## Data Routing

Allowed `data_route` values:

- `eval`
- `sft`
- `preference`
- `badcase`
- `human_review`

Examples:

- fabricated citation, high risk, low judge confidence -> `human_review`
- overclaim -> `preference` or `badcase`
- missing facts -> `eval` or `sft`
- missing evidence warning -> `sft`
- weak fact-rule application -> `eval`

The dashboard is a data production panel. It should answer what data to build next, not which model is best.
