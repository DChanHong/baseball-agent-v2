from __future__ import annotations

from .schemas import ActiveDocument, ChangeOperation


def classify_change(
    active: ActiveDocument | None,
    candidate_content_hash: str,
    *,
    current_embedding_model: str = "text-embedding-3-small",
    target_embedding_model: str = "text-embedding-3-small",
) -> ChangeOperation:
    if active is None:
        return ChangeOperation.CREATE
    if active.content_hash != candidate_content_hash:
        return ChangeOperation.UPDATE
    active_model = active.metadata.get("embedding_model", current_embedding_model)
    if active_model != target_embedding_model:
        return ChangeOperation.RE_EMBED
    return ChangeOperation.UNCHANGED


def classify_missing(*, active_exists: bool, consecutive_missing_count: int) -> ChangeOperation:
    if active_exists and consecutive_missing_count >= 2:
        return ChangeOperation.DELETE_CANDIDATE
    return ChangeOperation.MANUAL_REQUIRED

