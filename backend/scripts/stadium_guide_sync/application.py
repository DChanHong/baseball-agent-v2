from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .evaluation import CandidateEvaluator, EvaluationResult
from .raw_storage import sha256_text
from .repository import StadiumGuideSyncRepository
from .schemas import CandidatePayload, CandidateStatus, ChangeOperation, SourceRegistry
from .service import build_embedding_text


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True, slots=True)
class ApplyLocalResult:
    candidate_id: str
    revision_id: str
    status: CandidateStatus
    already_applied: bool
    evaluation: EvaluationResult | None


class OpenAIEmbedder:
    def __init__(self, client: object, model: str = "text-embedding-3-small") -> None:
        self._client = client
        self._model = model

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=[text])
        return list(response.data[0].embedding)


class LocalCandidateApplier:
    def __init__(
        self,
        *,
        repository: StadiumGuideSyncRepository,
        registry: SourceRegistry,
        embedder: Embedder,
        evaluator: CandidateEvaluator,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._embedder = embedder
        self._evaluator = evaluator

    async def apply(self, candidate_id: str) -> ApplyLocalResult:
        candidate = await self._repository.candidate(candidate_id)
        if not candidate:
            raise ValueError(f"candidate not found: {candidate_id}")
        if candidate.status in {
            CandidateStatus.READY_FOR_PRODUCTION,
            CandidateStatus.PROMOTED,
        }:
            revision_id = candidate.candidate_revision_id or candidate.previous_revision_id
            if not revision_id:
                raise ValueError("applied candidate has no revision id")
            return ApplyLocalResult(
                candidate_id=candidate_id,
                revision_id=revision_id,
                status=candidate.status,
                already_applied=True,
                evaluation=None,
            )
        if candidate.status not in {
            CandidateStatus.APPROVED,
            CandidateStatus.APPLIED_LOCAL,
            CandidateStatus.EVALUATION_FAILED,
        }:
            raise ValueError(
                f"candidate must be approved before apply-local: {candidate.status.value}"
            )

        operation = candidate.operation
        payload: CandidatePayload | None = None
        embedding_text: str | None = None
        embedding_vector: str | None = None
        if operation != ChangeOperation.DELETE_CANDIDATE:
            payload = CandidatePayload.model_validate(candidate.candidate_payload)
            embedding_text = build_embedding_text(candidate.candidate_payload)
            content_hash = sha256_text(embedding_text)
            if content_hash != candidate.candidate_content_hash:
                raise ValueError("candidate content hash does not match its payload")
            if candidate.status == CandidateStatus.APPROVED:
                values = await self._embedder.embed(embedding_text)
                if len(values) != 1536:
                    raise ValueError(f"expected 1536 embedding dimensions, got {len(values)}")
                embedding_vector = "[" + ",".join(str(value) for value in values) + "]"

        source_index = {source.source_id: source.url for source in self._registry.sources}
        source_urls = [source_index[source_id] for source_id in candidate.source_ids]
        revision_id, already_applied = await self._repository.apply_candidate_revision(
            candidate_id=candidate_id,
            embedding_text=embedding_text,
            embedding_vector=embedding_vector,
            source_urls=source_urls,
        )
        document_type = (
            payload.document_type
            if payload
            else candidate.logical_document_id.split("_", 1)[1]
        )
        stadium_id = payload.stadium_id if payload else None
        evaluation = await self._evaluator.evaluate(
            stadium_id=stadium_id,
            document_type=document_type,
        )
        reviewed = await self._repository.finalize_evaluation(
            candidate_id=candidate_id,
            revision_id=revision_id,
            evaluation_run_id=evaluation.run_id,
            passed=evaluation.passed,
            summary=evaluation.summary,
        )
        return ApplyLocalResult(
            candidate_id=candidate_id,
            revision_id=revision_id,
            status=reviewed.status,
            already_applied=already_applied,
            evaluation=evaluation,
        )
