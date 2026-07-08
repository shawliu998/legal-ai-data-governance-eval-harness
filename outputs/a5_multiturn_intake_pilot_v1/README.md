# A5 Multi-Turn Intake Evidence Package

This directory contains a lightweight evidence package for an A5 multi-turn legal intake run.

The run evaluates trace-level behavior: material-fact elicitation, bad-premise challenge, safe redirection, human-review routing, and release decision.

## Scope

- Traces: 24
- Turns: 72
- Cases: 8
- Models: 3
- Trace pass rate: 0.75
- Average material fact coverage: 0.7708

## Included

- `trace_metrics_summary.csv`: high-level trace metrics.
- `turn_level_summary.csv`: redacted turn-level latency, token, status, and hash summary.
- `risk_route_summary.csv`: release decision counts by user behavior and legal domain.
- `redacted_trace_samples.csv`: one row per trace with output hashes only.
- `redacted_trace_example.md`: one redacted trace summary for reviewer inspection.
- `human_trace_calibration_template.csv`: row-level human review template for A5 trace rubric scoring.
- `artifact_manifest.yaml`: machine-readable manifest and caveats.

## Caveats

- This is a limited API smoke/pilot run, not a full benchmark.
- The pass rate is a deterministic triage signal, not human-validated product readiness.
- Deterministic trace checks are triage signals and need human calibration before production release.
- Full raw model outputs remain local/ignored.
