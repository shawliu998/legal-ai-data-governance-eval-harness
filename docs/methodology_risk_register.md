# Methodology Risk Register

This file turns known evaluation limitations into explicit product and data-governance actions.

## Risk Register

### A5 Was Only A Smoke Test

Current status:

- Upgraded from 6 traces to a 24-trace real API pilot across 8 cases and 3 models.

Mitigation already added:

- Added `config.qianfan_a5_multiturn_pilot.yaml`, `outputs/a5_multiturn_intake_pilot_v1/`, A5
  rubric, redacted trace example, and human calibration template.

Remaining work:

- Human-review all 24 traces before claiming A5 readiness.

### RAG Corpus Is Controlled And Small

Current status:

- Still a controlled corpus, not a full legal knowledge base.

Mitigation already added:

- RAG V2 explicitly frames results as source-limited reliability testing, not legal coverage.

Remaining work:

- Expand to authoritative statute, case, contract, and policy sources.
- Add hard negatives and retrieval-source boundary labels.

### Claim Entailment Is Triage

Current status:

- Claim checks are deterministic release-risk signals, not final legal entailment judgments.

Mitigation already added:

- Results now describe the 88.1% citation-gate issue rate as a strict material-claim release gate,
  not model accuracy.

Remaining work:

- Add human labels for support/contradiction, evidence-span matching, and sampled LLM entailment
  review.

### Judge Bias And Self-Judge Risk

Current status:

- Full 300-output scoring uses Qwen3.5-27B as a stable structured judge baseline.

Mitigation already added:

- Added caveats, priority human review, and an ensemble-smoke design with self-eval exclusion.

Remaining work:

- Run non-Qwen judge sampling on a stratified subset and report judge-human agreement by slice.

### API Sample Size Is Pilot-Scale

Current status:

- Real API evidence is 300 product-boundary outputs, 72 RAG V2 outputs, and 72 A5 turns.

Mitigation already added:

- README and results avoid statistical superiority claims and frame outputs as product-decision
  evidence.

Remaining work:

- Treat conclusions as deployment-policy hypotheses until larger stratified evaluation is run.

## Release Interpretation

The project should not claim:

- full legal correctness,
- production-ready autonomous legal advice,
- statistically significant model superiority,
- release-safe RAG,
- final judge accuracy.

The project can claim:

- real API outputs were collected,
- model-agent-workflow behavior was converted into release gates,
- RAG failures were decomposed into retrieval, citation, claim, and source-boundary issues,
- A5 multi-turn intake is now evaluated at trace level,
- failures are routed into human review, badcase, SFT, preference, and regression-eval data assets.
