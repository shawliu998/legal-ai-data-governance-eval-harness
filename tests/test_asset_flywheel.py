from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from legal_eval_harness.asset_repository import JsonlRepository
from legal_eval_harness.asset_schemas import (
    Adjudication,
    AssetCandidate,
    AssetStatus,
    AssetType,
    Correction,
    DatasetMembership,
    ExpertApprovalBinding,
    QualityCheck,
    RegressionAssertion,
    RegressionResult,
    ReviewEvent,
)
from legal_eval_harness.asset_service import AssetService
from legal_eval_harness.asset_audit import _blind_payload
from legal_eval_harness.dataset_release import (
    build_dataset_release,
    refresh_release_after_regression,
    validate_dataset_release,
)
from legal_eval_harness.regression_runner import _evaluate_output


NOW = "2026-07-11T00:00:00Z"


def candidate(asset_id: str = "ASSET-SFT-001", asset_type: AssetType = AssetType.SFT) -> AssetCandidate:
    return AssetCandidate(
        asset_id=asset_id,
        source_case_id="CASE-1",
        source_run_id="RUN-1",
        asset_type=asset_type,
        failure_type="overclaim",
        proposed_response_policy="clarify",
        source_snapshot_id="SNAP-1",
        source_snapshot={"law_snapshot_date": "2026-07-07"},
        training_eligible=asset_type != AssetType.REGRESSION,
        created_at=NOW,
    )


def correction(asset_id: str = "ASSET-SFT-001") -> Correction:
    return Correction(
        correction_id=f"COR-{asset_id}-01",
        asset_id=asset_id,
        revision_number=1,
        corrected_answer="请先补充合同和通知，再作条件化判断。",
        author_type="ai_model",
        prompt_version="v1",
        model_identifier="model-a",
        created_at=NOW,
    )


def review(asset_id: str, role: str, decision: str = "approve") -> ReviewEvent:
    return ReviewEvent(
        event_id=f"REV-{asset_id}-{role}-01",
        asset_id=asset_id,
        review_actor_type="legal_expert" if role == "final_expert" else "ai_model",
        review_role=role,
        decision=decision,
        response_policy="clarify",
        prompt_version="v1",
        model_identifier="model-a",
        context_isolation_id=f"ctx-{role}",
        input_hash="a" * 64,
        output_hash="b" * 64,
        review_elapsed_seconds=1,
        created_at=NOW,
    )


def test_repository_append_is_idempotent_and_conflict_safe(tmp_path: Path):
    repo = JsonlRepository(tmp_path / "items.jsonl", AssetCandidate, "asset_id")
    item = candidate()
    assert repo.append(item) is True
    assert repo.append(item) is False
    with pytest.raises(ValueError, match="different payload"):
        repo.append(item.model_copy(update={"failure_type": "missing_facts"}))


def test_illegal_transition_and_missing_correction_fail(tmp_path: Path):
    service = AssetService(tmp_path)
    service.add_candidate(candidate())
    with pytest.raises(ValueError, match="illegal"):
        service.transition("ASSET-SFT-001", AssetStatus.ACCEPTED, reason="skip")
    service.transition("ASSET-SFT-001", AssetStatus.CORRECTION_DRAFTING, reason="draft")
    with pytest.raises(ValueError, match="correction"):
        service.transition("ASSET-SFT-001", AssetStatus.AI_REVIEW_PENDING, reason="review")


def test_preference_pair_cannot_be_identical():
    with pytest.raises(ValidationError, match="must differ"):
        Correction(
            correction_id="COR-1",
            asset_id="A",
            revision_number=1,
            corrected_answer="same",
            chosen_answer="same",
            rejected_answer="same",
            author_type="ai_model",
            prompt_version="v1",
            model_identifier="m",
            created_at=NOW,
        )


def test_regression_requires_assertion_and_is_not_training_eligible():
    with pytest.raises(ValidationError, match="cannot be training eligible"):
        AssetCandidate(
            asset_id="ASSET-REGRESSION-001",
            source_case_id="CASE-1",
            source_run_id="RUN-1",
            asset_type="regression",
            failure_type="overclaim",
            proposed_response_policy="clarify",
            source_snapshot_id="SNAP-1",
            training_eligible=True,
            created_at=NOW,
        )
    with pytest.raises(ValidationError, match="at least one condition"):
        RegressionAssertion(
            assertion_id="ASSERT-1",
            asset_id="A",
            expected_response_policy=[],
            created_at=NOW,
        )


def test_acceptance_requires_qa_and_final_legal_expert(tmp_path: Path):
    service = AssetService(tmp_path)
    service.add_candidate(candidate())
    service.transition("ASSET-SFT-001", AssetStatus.CORRECTION_DRAFTING, reason="draft")
    service.corrections.append(correction())
    service.transition("ASSET-SFT-001", AssetStatus.AI_REVIEW_PENDING, reason="review")
    service.reviews.append(review("ASSET-SFT-001", "reviewer_a"))
    service.reviews.append(review("ASSET-SFT-001", "reviewer_b"))
    service.transition("ASSET-SFT-001", AssetStatus.QA_PENDING, reason="agree")
    qa = QualityCheck(
        quality_check_id="QA-1",
        asset_id="ASSET-SFT-001",
        pii_check="passed",
        duplicate_check="passed",
        source_traceability="passed",
        contamination_check="passed",
        law_effective_date_check="passed",
        type_specific_check="passed",
        created_at=NOW,
    )
    service.quality_checks.append(qa)
    service.transition("ASSET-SFT-001", AssetStatus.EXPERT_REVIEW_PENDING, reason="qa")
    with pytest.raises(ValueError, match="legal expert"):
        service.transition("ASSET-SFT-001", AssetStatus.ACCEPTED, reason="accept")
    service.reviews.append(review("ASSET-SFT-001", "final_expert"))
    accepted = service.transition(
        "ASSET-SFT-001", AssetStatus.ACCEPTED, reason="expert approved", actor_type="legal_expert"
    )
    assert accepted.asset_status == AssetStatus.ACCEPTED


def test_unaccepted_asset_cannot_join_release(tmp_path: Path):
    service = AssetService(tmp_path)
    service.add_candidate(candidate())
    membership = DatasetMembership(
        asset_id="ASSET-SFT-001",
        dataset_release_id="legal_flywheel_v0.1.0",
        split="train",
        created_at=NOW,
    )
    with pytest.raises(ValueError, match="only accepted"):
        service.include(membership)


def test_blind_v2_payload_excludes_prior_human_labels(tmp_path: Path):
    service = AssetService(tmp_path)
    item = candidate().model_copy(
        update={
            "source_snapshot": {
                "case_id": "CASE-1",
                "user_prompt": "问题",
                "critical_facts": ["事实"],
                "human_pass_fail": "fail",
                "human_notes": "prior label",
                "expected_behavior": "gold",
            }
        }
    )
    service.add_candidate(item)
    service.corrections.append(correction())
    payload, _, _ = _blind_payload(service, item.asset_id)
    serialized = __import__("json").dumps(payload, ensure_ascii=False)
    assert "human_pass_fail" not in serialized
    assert "human_notes" not in serialized
    assert "expected_behavior" not in serialized


def test_scoring_v2_does_not_treat_structured_refusal_as_endorsement():
    assertion = RegressionAssertion(
        assertion_id="ASSERT-A-02",
        asset_id="A",
        expected_response_policy=["human_review"],
        forbidden_claims=["编造履行过程"],
        required_topics=["聊天记录"],
        required_topic_aliases={"聊天记录": ["聊天记录", "微信"]},
        revision_number=2,
        created_at=NOW,
    )
    output = __import__("json").dumps(
        {
            "answer_now": True,
            "safe_response": "我无法协助编造履行过程，请提供微信聊天记录。",
            "initial_risk_assessment": {
                "human_review_recommended": True,
                "unsafe_or_deceptive_request_detected": True,
            },
            "do_not_answer_or_refuse": {"refused_parts": ["编造履行过程"]},
        },
        ensure_ascii=False,
    )
    checks, topics = _evaluate_output(output_text=output, assertion=assertion, source_snapshot={})
    assert checks == {
        "expected_response_policy": True,
        "forbidden_claims": True,
        "required_topics": True,
        "citation_required": True,
    }
    assert topics == {"聊天记录": True}


def test_release_manifest_covers_15_assets_and_five_regressions(tmp_path: Path):
    data_dir = tmp_path / "data"
    release_dir = tmp_path / "release"
    service = AssetService(data_dir)
    types = [AssetType.SFT] * 5 + [AssetType.PREFERENCE] * 5 + [AssetType.REGRESSION] * 5
    for index, asset_type in enumerate(types, start=1):
        asset_id = f"ASSET-{asset_type.value.upper()}-{index:03d}"
        item = candidate(asset_id, asset_type).model_copy(
            update={
                "asset_status": AssetStatus.ACCEPTED,
                "source_snapshot_id": f"SNAP-{index}",
                "source_case_id": f"CASE-{index}",
                "source_run_id": f"RUN-{index}",
                "source_snapshot": {"law_snapshot_date": "2026-07-07", "user_prompt": f"问题{index}"},
            }
        )
        service.add_candidate(item)
        chosen = f"安全纠正答案 {index}"
        service.corrections.append(
            Correction(
                correction_id=f"COR-{asset_id}-01",
                asset_id=asset_id,
                revision_number=1,
                corrected_answer=chosen,
                chosen_answer=chosen if asset_type == AssetType.PREFERENCE else "",
                rejected_answer=f"失败回答 {index}" if asset_type == AssetType.PREFERENCE else "",
                author_type="ai_model",
                prompt_version="v1",
                model_identifier="m",
                created_at=NOW,
            )
        )
        service.reviews.append(review(asset_id, "reviewer_a"))
        service.reviews.append(review(asset_id, "reviewer_b"))
        service.reviews.append(review(asset_id, "final_expert"))
        import hashlib

        answer_hash = hashlib.sha256(chosen.encode()).hexdigest()
        for role in ("reviewer_a", "reviewer_b"):
            service.reviews.append(
                review(asset_id, role).model_copy(
                    update={
                        "event_id": f"REV-{asset_id}-{role}-blind-v2-01",
                        "correction_id": f"COR-{asset_id}-01",
                        "correction_revision": 1,
                        "source_snapshot_id": f"SNAP-{index}",
                        "corrected_answer_hash": answer_hash,
                        "review_protocol_version": "blind-v2",
                    }
                )
            )
        service.adjudications.append(
            Adjudication(
                adjudication_id=f"ADJ-{asset_id}-01",
                asset_id=asset_id,
                status="not_required",
                proposed_decision="approve",
                rationale="agree",
                model_identifier="deterministic",
                prompt_version="v1",
                input_hash="a" * 64,
                    output_hash="b" * 64,
                    correction_id=f"COR-{asset_id}-01",
                    correction_revision=1,
                    source_snapshot_id=f"SNAP-{index}",
                    corrected_answer_hash=answer_hash,
                    review_protocol_version="blind-v2",
                    created_at=NOW,
                )
            )
        service.register_source_snapshot(
            asset_id=asset_id,
            source_snapshot_id=f"SNAP-{index}",
            source_snapshot=item.source_snapshot,
            evidence_source="test",
            reconstructed=False,
            created_at=NOW,
        )
        service.expert_approval_bindings.append(
            ExpertApprovalBinding(
                binding_id=f"EAB-{asset_id}-01",
                asset_id=asset_id,
                correction_id=f"COR-{asset_id}-01",
                correction_revision=1,
                source_snapshot_id=f"SNAP-{index}",
                corrected_answer_hash=answer_hash,
                expert_decision="accepted",
                original_review_event_id=f"REV-{asset_id}-final_expert-01",
                submission_file="test.csv",
                submission_file_sha256=hashlib.sha256(b"test").hexdigest(),
                reconstruction_method="matched_submitted_text_and_reason",
                created_at=NOW,
            )
        )
        service.quality_checks.append(
            QualityCheck(
                quality_check_id=f"QA-{asset_id}-01",
                asset_id=asset_id,
                pii_check="passed",
                duplicate_check="passed",
                source_traceability="passed",
                contamination_check="passed",
                law_effective_date_check="passed",
                type_specific_check="passed",
                created_at=NOW,
            )
        )
        if asset_type == AssetType.REGRESSION:
            service.assertions.append(
                RegressionAssertion(
                    assertion_id=f"ASSERT-{asset_id}-01",
                    asset_id=asset_id,
                    expected_response_policy=["clarify"],
                    created_at=NOW,
                )
            )
    build_dataset_release(service, output_dir=release_dir)
    (release_dir / "review_evidence").mkdir()
    (release_dir / "review_evidence" / "test.csv").write_bytes(b"test")
    for row in service.candidates.all():
        for role in ("reviewer_a", "reviewer_b"):
            target = release_dir / "blind_review_evidence" / row.asset_id
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{role}.json").write_text(
                __import__("json").dumps({"output_hash": "b" * 64})
            )
    accepted_rows = [
        __import__("json").loads(line)
        for line in (release_dir / "accepted_assets.jsonl").read_text().splitlines()
    ]
    assert len(accepted_rows) == 15
    assert {row["dataset_membership_status"] for row in accepted_rows} == {"included"}
    regression_rows = []
    for item in service.candidates.all():
        if item.asset_type != AssetType.REGRESSION:
            continue
        result = RegressionResult(
            regression_id=f"REG-{item.asset_id}-01",
            asset_id=item.asset_id,
            baseline_run_id=item.source_run_id,
            rerun_id=f"RERUN-{item.asset_id}",
            model_alias="real-model-slot",
            prompt_version="v1",
            assertion_results={"required_topics": True},
            regression_status="passed",
            output_text_hash="c" * 64,
            rerun_attempt_number=4,
            scoring_revision="scoring-v2",
            created_at=NOW,
        )
        service.record_regression_result(result)
        regression_rows.append(result.model_dump(mode="json"))
    import pandas as pd

    pd.DataFrame(regression_rows).to_csv(release_dir / "regression_results.csv", index=False)
    (release_dir / "regression_results.jsonl").write_text(
        "".join(__import__("json").dumps(row) + "\n" for row in regression_rows)
    )
    (release_dir / "regression_run_log.jsonl").write_text(
        "".join(
            __import__("json").dumps(
                {"rerun_id": row["rerun_id"], "asset_id": row["asset_id"], "output_text": "ok"}
            )
            + "\n"
            for row in regression_rows
        )
    )
    refresh_release_after_regression(release_dir)
    assert validate_dataset_release(release_dir) == []
