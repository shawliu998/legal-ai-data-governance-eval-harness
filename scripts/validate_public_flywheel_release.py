from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = ROOT / "release/legal_flywheel_v0.1.0"
FORBIDDEN_PUBLIC_COLUMNS = {
    "output_text",
    "prompt_hash",
    "output_text_hash",
    "rerun_id",
    "baseline_run_id",
    "source_snapshot",
    "expert_override_reason",
}
PII_PATTERNS = [
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(release: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = release / "public_manifest.yaml"
    if not manifest_path.exists():
        return ["missing public_manifest.yaml"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    for name, metadata in (manifest.get("files") or {}).items():
        path = release / name
        if not path.exists():
            errors.append(f"missing {name}")
        elif sha256(path) != metadata.get("sha256"):
            errors.append(f"hash mismatch: {name}")
    samples_path = release / "public_redacted_samples.jsonl"
    samples = [
        json.loads(line)
        for line in samples_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if samples_path.exists() else []
    if len(samples) != 3:
        errors.append(f"expected 3 public samples; found {len(samples)}")
    public_text = json.dumps(samples, ensure_ascii=False)
    if any(pattern.search(public_text) for pattern in PII_PATTERNS):
        errors.append("public sample PII pattern detected")
    regression_path = release / "regression_summary.csv"
    if regression_path.exists():
        frame = pd.read_csv(regression_path)
        leaked = FORBIDDEN_PUBLIC_COLUMNS.intersection(frame.columns)
        if leaked:
            errors.append(f"restricted regression columns leaked: {sorted(leaked)}")
        if len(frame) != 5:
            errors.append(f"expected 5 regression summary rows; found {len(frame)}")
        if set(frame.get("prompt_version", [])) != {"V5"}:
            errors.append("public regression summary is not V5")
    else:
        errors.append("missing regression_summary.csv")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    args = parser.parse_args()
    errors = validate(args.release)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Public flywheel release validation passed.")


if __name__ == "__main__":
    main()
