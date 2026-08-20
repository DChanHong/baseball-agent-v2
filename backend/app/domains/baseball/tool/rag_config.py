from __future__ import annotations

from dataclasses import dataclass

DEFAULT_RAG_EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass(frozen=True)
class RagRetrievalConfig:
    """Search quality knobs for one RAG-backed tool."""

    embedding_model: str
    default_top_k: int
    max_top_k: int
    relevance_threshold: float
    document_types: tuple[str, ...]

    def effective_top_k(self, requested_top_k: int | None) -> int:
        if requested_top_k is None:
            return self.default_top_k
        return min(requested_top_k, self.max_top_k)


STADIUM_GUIDE_RAG_CONFIG = RagRetrievalConfig(
    embedding_model=DEFAULT_RAG_EMBEDDING_MODEL,
    default_top_k=5,
    max_top_k=10,
    relevance_threshold=0.65,
    document_types=(
        "stadium_bag_policy",
        "stadium_facility_guide",
        "stadium_seat_guide",
        "stadium_transport_guide",
    ),
)

TICKETING_GUIDE_RAG_CONFIG = RagRetrievalConfig(
    embedding_model=DEFAULT_RAG_EMBEDDING_MODEL,
    default_top_k=5,
    max_top_k=10,
    relevance_threshold=0.65,
    document_types=("stadium_ticketing_guide",),
)

BASEBALL_KNOWLEDGE_RAG_CONFIG = RagRetrievalConfig(
    embedding_model=DEFAULT_RAG_EMBEDDING_MODEL,
    default_top_k=5,
    max_top_k=10,
    relevance_threshold=0.82,
    document_types=(
        "baseball_rule",
        "common_play",
        "latest_kbo_rule",
    ),
)
