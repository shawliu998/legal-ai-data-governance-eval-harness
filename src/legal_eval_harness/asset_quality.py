from __future__ import annotations

import hashlib
import re

from .asset_schemas import AssetStatus, AssetType, QualityCheck
from .asset_service import AssetService
from .utils import utc_now_iso


PII_PATTERNS = [
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
]


def run_asset_qa(service: AssetService, asset_id: str) -> QualityCheck:
    candidate = service.candidates.get(asset_id)
    correction = service.latest_correction(asset_id)
    if candidate is None or correction is None:
        raise ValueError("candidate and correction are required")
    findings: list[str] = []
    pii_ok = not any(pattern.search(correction.corrected_answer) for pattern in PII_PATTERNS)
    if not pii_ok:
        findings.append("possible PII in corrected answer")
    answer_hash = hashlib.sha256(correction.corrected_answer.strip().encode()).hexdigest()
    other_hashes = {
        hashlib.sha256(row.corrected_answer.strip().encode()).hexdigest()
        for row in service.corrections.all()
        if row.asset_id != asset_id
    }
    duplicate_ok = answer_hash not in other_hashes
    if not duplicate_ok:
        findings.append("duplicate corrected answer")
    trace_ok = bool(candidate.source_case_id and candidate.source_run_id and candidate.source_snapshot_id)
    law_date_ok = bool(candidate.source_snapshot.get("law_snapshot_date"))
    contamination_ok = candidate.source_snapshot_id not in {
        row.source_snapshot_id
        for row in service.candidates.all()
        if row.asset_id != asset_id and row.asset_type == candidate.asset_type
    }
    if candidate.asset_type == AssetType.PREFERENCE:
        type_ok = bool(
            correction.chosen_answer
            and correction.rejected_answer
            and correction.chosen_answer.strip() != correction.rejected_answer.strip()
        )
    elif candidate.asset_type == AssetType.REGRESSION:
        type_ok = service.assertion_for(asset_id) is not None and not candidate.training_eligible
    else:
        type_ok = bool(correction.corrected_answer) and candidate.training_eligible
    sequence = 1 + sum(row.asset_id == asset_id for row in service.quality_checks.all())
    check = QualityCheck(
        quality_check_id=f"QA-{asset_id}-{sequence:02d}",
        asset_id=asset_id,
        pii_check="passed" if pii_ok else "failed",
        duplicate_check="passed" if duplicate_ok else "failed",
        source_traceability="passed" if trace_ok else "failed",
        contamination_check="passed" if contamination_ok else "failed",
        law_effective_date_check="passed" if law_date_ok else "failed",
        type_specific_check="passed" if type_ok else "failed",
        findings=findings + ([] if type_ok else ["asset type-specific validation failed"]),
        created_at=utc_now_iso(),
    )
    service.quality_checks.append(check)
    if check.passed:
        service.transition(asset_id, AssetStatus.EXPERT_REVIEW_PENDING, reason="automated QA passed")
    else:
        service.transition(asset_id, AssetStatus.REWORK_REQUIRED, reason="automated QA failed")
    return check
