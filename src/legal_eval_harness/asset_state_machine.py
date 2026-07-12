from __future__ import annotations

from .asset_schemas import AssetStatus


ALLOWED_ASSET_TRANSITIONS: dict[AssetStatus, set[AssetStatus]] = {
    AssetStatus.PROPOSED: {AssetStatus.CORRECTION_DRAFTING, AssetStatus.REJECTED},
    AssetStatus.CORRECTION_DRAFTING: {AssetStatus.AI_REVIEW_PENDING, AssetStatus.REWORK_REQUIRED},
    AssetStatus.AI_REVIEW_PENDING: {
        AssetStatus.ADJUDICATION_PENDING,
        AssetStatus.QA_PENDING,
        AssetStatus.REWORK_REQUIRED,
        AssetStatus.REJECTED,
    },
    AssetStatus.ADJUDICATION_PENDING: {
        AssetStatus.QA_PENDING,
        AssetStatus.REWORK_REQUIRED,
        AssetStatus.REJECTED,
    },
    AssetStatus.QA_PENDING: {AssetStatus.EXPERT_REVIEW_PENDING, AssetStatus.REWORK_REQUIRED},
    AssetStatus.EXPERT_REVIEW_PENDING: {
        AssetStatus.ACCEPTED,
        AssetStatus.REWORK_REQUIRED,
        AssetStatus.REJECTED,
    },
    AssetStatus.REWORK_REQUIRED: {AssetStatus.CORRECTION_DRAFTING, AssetStatus.REJECTED},
    AssetStatus.ACCEPTED: set(),
    AssetStatus.REJECTED: set(),
}


def validate_asset_transition(current: AssetStatus, target: AssetStatus) -> None:
    if target not in ALLOWED_ASSET_TRANSITIONS[current]:
        raise ValueError(f"illegal asset status transition: {current.value} -> {target.value}")
