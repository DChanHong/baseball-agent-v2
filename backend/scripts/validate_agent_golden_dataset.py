"""Validate the 50-case draft without database, network or model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "data/chat/evaluation/cases/agent_golden_candidates_v1.json"
SCHEMA_PATH = ROOT / "data/chat/evaluation/schemas/agent_golden_candidate.schema.json"
Category = Literal[
    "stadium_guide",
    "ticketing",
    "baseball_knowledge",
    "mixed_follow_up",
    "insufficient_out_of_scope",
]
COUNTS = {
    "stadium_guide": (10, 5),
    "ticketing": (7, 3),
    "baseball_knowledge": (11, 4),
    "mixed_follow_up": (4, 1),
    "insufficient_out_of_scope": (3, 2),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotFile(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Snapshot(StrictModel):
    kind: Literal["repository_files_not_database"]
    files: list[SnapshotFile]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Source(StrictModel):
    source_id: str
    url: str | None
    locator: str
    checked_at: date
    source_as_of: str | None
    verification_status: Literal[
        "web_verified",
        "historical_raw_verified",
        "official_pdf_verified",
        "repository_verified",
        "unverified_dynamic_page",
        "unverified_empty_or_timeout",
        "browser_verified",
        "synthetic_fixture_verified",
    ]
    local_path: str | None
    content_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    hash_note: str
    verification_notes: list[str] = Field(default_factory=list)
    page_text_sha256: dict[str, str] = Field(default_factory=dict)


class Turn(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class CaseInput(StrictModel):
    question: str = Field(min_length=1)
    today: date
    timezone: Literal["Asia/Seoul"]
    auth_status: Literal["authenticated"]
    favorite_team_id: str | None
    history: list[Turn]
    conversation_context: dict[str, Any]
    context_mode: Literal["fixed_synthetic_fixture", "fresh_conversation"]
    event_scope: str


class Expected(StrictModel):
    in_scope: bool
    tool_name: (
        Literal[
            "search_stadium_guide",
            "search_ticketing_guide",
            "search_baseball_knowledge",
        ]
        | None
    )
    filter_constraints: dict[str, Any]
    top_k: int | None
    query_policy: str | None
    allowed_behaviors: list[str] = Field(min_length=1)
    answerability: Literal["source_answerable", "policy_only", "pending_source_review"]
    reference_answer: str | None
    required_facts: list[str] = Field(min_length=1)
    forbidden_claims: list[str] = Field(min_length=1)
    conditions_and_exceptions: list[str]


class Evidence(StrictModel):
    source_id: str
    locator: str
    supports_fact_indexes: list[int] = Field(min_length=1)
    pdf_pages: list[int]


class ChunkSpan(StrictModel):
    fact_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)
    support: Literal["full", "partial"]


class ChunkCandidate(StrictModel):
    document_id: str
    chunk_id: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    logical_document_id: None
    revision_id: None
    relevance_grade: Literal[0, 1, 2] | None
    label_status: Literal["agent_reviewed_local", "source_review_pending"]
    reason: str
    evidence_spans: list[ChunkSpan]
    passes_expected_filter: bool


class FactLabel(StrictModel):
    fact_index: int = Field(ge=0)
    status: Literal[
        "supported",
        "partial",
        "missing",
        "not_retrieval_fact",
        "unverified_corpus",
        "source_review_pending",
    ]
    supporting_chunk_ids: list[str]
    reason: str


class PoolScope(StrictModel):
    kind: Literal[
        "policy_or_context_only",
        "knowledge_chunk_file_unavailable",
        "all_local_stadium_document_types",
    ]
    chunk_ids: list[str]
    exhaustive_for_scope: bool


class HistoricalRevisionHint(StrictModel):
    document_id: str
    chunk_id: str
    record_path: str
    body_verified: Literal[False]
    active_in_current_db: bool | None
    note: str


class DbValidation(StrictModel):
    environment: Literal["local_supabase"]
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checked_at: date
    status: Literal[
        "not_applicable", "corpus_empty", "source_review_pending_corpus_empty"
    ]
    actual_matching_chunk_ids: list[str]
    missing_retrieval_fact_indexes: list[int]
    unresolved_source_fact_indexes: list[int]
    note: str


class RuntimeCorpusSnapshot(StrictModel):
    environment: Literal["local_supabase"]
    project_id: Literal["new-baseball"]
    checked_at: date
    transaction_read_only: Literal[True]
    document_count: Literal[0]
    chunk_count: Literal[0]
    active_document_count: Literal[0]
    embedded_chunk_count: Literal[0]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hash_scope: str
    query_scope: list[str]
    status: Literal["verified_empty"]
    content_manifest: dict[str, list[Any]]
    limitations: list[str]


class ProductionCandidatePool(StrictModel):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal[
        "not_applicable",
        "pending_fact_level_review",
        "agent_reviewed_metadata_and_facts",
        "source_review_pending",
    ]
    chunk_ids: list[str]
    scope: str
    note: str


class ProductionCorpusSnapshot(StrictModel):
    environment: Literal["production_supabase"]
    checked_at: date
    read_method: Literal["PostgREST GET only"]
    consistency: Literal["two_identical_complete_reads_non_atomic"]
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    active_document_count: int = Field(ge=0)
    embedded_chunk_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest: dict[str, list[dict[str, Any]]]
    hash_scope: str
    limitations: list[str]


class ProductionFactSpan(StrictModel):
    fact_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    span_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    support: Literal["full", "partial"]
    reason: str


class ProductionChunkLabel(StrictModel):
    chunk_id: str
    document_id: str
    logical_document_id: str | None
    revision_number: int | None
    document_type: str
    observed_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    relevance_grade: Literal[0, 1, 2] | None
    passes_expected_filter: bool
    evidence_spans: list[ProductionFactSpan]
    reason: str


class ProductionFactLabel(FactLabel):
    filtered_status: Literal[
        "supported", "partial", "missing", "not_retrieval_fact", "source_review_pending"
    ]
    filtered_supporting_chunk_ids: list[str]


class ProductionRelevanceReview(StrictModel):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["agent_reviewed", "source_review_pending", "not_applicable"]
    pool_scope: Literal[
        "policy_or_fixed_context_only",
        "all_current_knowledge_chunks_across_document_types",
        "all_active_same_stadium_and_shared_guide_chunks",
    ]
    reviewed_chunk_ids: list[str]
    chunks: list[ProductionChunkLabel]
    fact_labels: list[ProductionFactLabel]
    corpus_coverage: Literal[
        "full", "partial", "missing", "source_review_pending", "not_applicable"
    ]
    filtered_coverage: Literal[
        "full", "partial", "missing", "source_review_pending", "not_applicable"
    ]
    risk_notes: list[str]
    human_reviewed: Literal[False]


class Retrieval(StrictModel):
    status: Literal[
        "not_applicable",
        "local_corpus_unavailable",
        "agent_reviewed_local_pending_db",
        "agent_reviewed_local_db_corpus_empty",
    ]
    local_candidate_chunks: list[ChunkCandidate]
    expected_topic_ids: list[str]
    local_coverage: str
    db_corpus_verified: bool
    corpus_gap_note: str
    fact_labels: list[FactLabel]
    pool_scope: PoolScope
    historical_revision_hints: list[HistoricalRevisionHint]
    db_validation: DbValidation
    production_candidate_pool: ProductionCandidatePool
    production_relevance_review: ProductionRelevanceReview


class Review(StrictModel):
    status: Literal["agent_reviewed_candidate", "needs_source_review"]
    reviewer_kind: Literal["agent"]
    reviewed_at: date | None
    human_reviewed: Literal[False]
    notes: list[str]


class Evaluation(StrictModel):
    run_status: Literal["not_run"]
    ragas_input_scope: str
    metric_policy: Literal[
        "conditional_rag", "agent_behavior_only", "pending_multi_tool_adapter"
    ]
    rank_metrics_ready: Literal[False]
    baseline_ready: Literal[False]


class FinalReview(StrictModel):
    status: Literal["agent_checked", "source_blocked"]
    reviewed_at: date
    reviewer_kind: Literal["agent"]
    human_reviewed: Literal[False]
    exploratory_candidate: bool
    corpus_gap_preserved: Literal[True]
    notes: list[str] = Field(min_length=1)


class Case(StrictModel):
    case_id: str = Field(pattern=r"^golden_(guide|ticket|knowledge|mixed|scope)_\d{3}$")
    dataset_version: str
    category: Category
    split: Literal["development", "held_out"]
    related_case_ids: list[str]
    fact_groups: list[str] = Field(min_length=1)
    input: CaseInput
    expected: Expected
    evidence: list[Evidence] = Field(min_length=1)
    retrieval_ground_truth: Retrieval
    review: Review
    evaluation: Evaluation
    final_review: FinalReview


class ProductionCorpusCheck(StrictModel):
    checked_at: date
    environment: Literal["production_supabase"]
    status: Literal["connection_failed", "read_complete"]
    document_count: int | None
    chunk_count: int | None
    snapshot_sha256: str | None
    diagnostics: list[str]
    read_completed: bool
    writes_performed: Literal[False]
    note: str


class Dataset(StrictModel):
    schema_version: Literal[1]
    dataset_version: str
    created_at: date
    status: Literal["candidate_draft"]
    human_reviewed: Literal[False]
    frozen: Literal[False]
    split_status: Literal["proposed_group_split_not_frozen"]
    case_count: Literal[50]
    category_counts: dict[str, int]
    split_counts: dict[str, int]
    code_revision: str
    scope: Literal[
        "synthetic_public_source_candidate_authoring_and_readonly_local_and_production_corpus_review"
    ]
    evaluation_executed: Literal[False]
    runtime_corpus_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_corpus_snapshot: RuntimeCorpusSnapshot
    production_corpus_check: ProductionCorpusCheck | None = None
    production_corpus_snapshot: ProductionCorpusSnapshot
    source_snapshot_status: str
    local_corpus_snapshot: Snapshot
    sources: list[Source]
    cases: list[Case] = Field(min_length=50, max_length=50)
    review_todo: list[str]
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any, *, ascii_only: bool = False) -> bytes:
    return json.dumps(
        value, ensure_ascii=ascii_only, sort_keys=True, separators=(",", ":")
    ).encode()


def validate_dataset(
    raw: dict[str, Any],
    *,
    check_files: bool = True,
    production_snapshot_path: Path | None = None,
) -> Dataset:
    dataset = Dataset.model_validate(raw)
    unhashed = {k: v for k, v in raw.items() if k != "content_sha256"}
    if sha(canonical(unhashed)) != dataset.content_sha256:
        raise ValueError("dataset content hash mismatch")
    runtime = dataset.runtime_corpus_snapshot
    if runtime.content_manifest != {"documents": [], "chunks": []}:
        raise ValueError("verified empty snapshot has content")
    if (
        sha(canonical(runtime.content_manifest, ascii_only=True)) != runtime.sha256
        or dataset.runtime_corpus_hash != runtime.sha256
    ):
        raise ValueError("runtime corpus snapshot hash mismatch")
    production = dataset.production_corpus_snapshot
    if sha(canonical(production.manifest)) != production.sha256:
        raise ValueError("production manifest hash mismatch")
    production_documents = production.manifest.get("documents", [])
    production_chunks = production.manifest.get("chunks", [])
    production_chunk_map = {c["chunk_id"]: c for c in production_chunks}
    production_doc_map = {c["document_id"]: c for c in production_documents}
    body_map = {}
    if production_snapshot_path is not None:
        body_snapshot = json.loads(production_snapshot_path.read_text())
        body_map = {c["chunk_id"]: c for c in body_snapshot["chunks"]}
        if set(body_map) != set(production_chunk_map):
            raise ValueError("production body snapshot IDs mismatch")
        for chunk_id, chunk in body_map.items():
            if (
                sha(chunk["content"].encode())
                != production_chunk_map[chunk_id]["observed_content_sha256"]
            ):
                raise ValueError("production body snapshot hash mismatch")
    production_chunk_ids = {c["chunk_id"] for c in production_chunks}
    if (
        len(production_documents) != production.document_count
        or len(production_chunks) != production.chunk_count
        or len(production_chunk_ids) != production.chunk_count
        or sum(d["is_active"] for d in production_documents)
        != production.active_document_count
        or sum(c["has_embedding"] for c in production_chunks)
        != production.embedded_chunk_count
    ):
        raise ValueError("production manifest count mismatch")
    check = dataset.production_corpus_check
    if check is None or not check.read_completed or check.status != "read_complete":
        raise ValueError("production snapshot requires completed read")
    if (
        check.snapshot_sha256 != production.sha256
        or check.document_count != production.document_count
        or check.chunk_count != production.chunk_count
    ):
        raise ValueError("production check snapshot mismatch")
    counts = Counter(c.category for c in dataset.cases)
    if dict(counts) != dataset.category_counts:
        raise ValueError("category summary mismatch")
    if dict(Counter(c.split for c in dataset.cases)) != dataset.split_counts:
        raise ValueError("split summary mismatch")
    for category, (dev, held) in COUNTS.items():
        if Counter(c.split for c in dataset.cases if c.category == category) != {
            "development": dev,
            "held_out": held,
        }:
            raise ValueError(f"category split mismatch: {category}")
    source_map = {s.source_id: s for s in dataset.sources}
    if len(source_map) != len(dataset.sources):
        raise ValueError("duplicate source ID")
    linked_ids = {
        json.loads(line)["case_id"]
        for line in (ROOT / "data/chat/evaluation/cases/chat_mvp_cases.jsonl")
        .read_text()
        .splitlines()
    }
    linked_ids |= {
        json.loads(line)["id"]
        for line in (
            ROOT
            / "data/baseball_knowledge/evaluation/cases/search_baseball_knowledge_cases.jsonl"
        )
        .read_text()
        .splitlines()
    }
    local_chunks = {
        c["chunk_id"]: c
        for c in map(
            json.loads,
            (ROOT / "data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl")
            .read_text()
            .splitlines(),
        )
    }
    ids: set[str] = set()
    questions: set[str] = set()
    groups: dict[str, str] = {}
    for case in dataset.cases:
        source_blocked = case.review.status == "needs_source_review"
        if (
            case.final_review.status
            != ("source_blocked" if source_blocked else "agent_checked")
            or case.final_review.exploratory_candidate == source_blocked
        ):
            raise ValueError("final review eligibility contradicts source review")
        if case.case_id in ids or case.input.question in questions:
            raise ValueError("duplicate case ID or question")
        ids.add(case.case_id)
        questions.add(case.input.question)
        if case.dataset_version != dataset.dataset_version:
            raise ValueError("case version mismatch")
        if set(case.related_case_ids) - linked_ids:
            raise ValueError(f"unknown linked case: {case.case_id}")
        for group in case.fact_groups:
            if group in groups and groups[group] != case.split:
                raise ValueError(f"fact group crosses splits: {group}")
            groups[group] = case.split
        covered: set[int] = set()
        for evidence in case.evidence:
            if evidence.source_id not in source_map:
                raise ValueError(f"unknown source: {case.case_id}")
            if any(
                i < 0 or i >= len(case.expected.required_facts)
                for i in evidence.supports_fact_indexes
            ):
                raise ValueError("invalid fact index")
            covered.update(evidence.supports_fact_indexes)
            source = source_map[evidence.source_id]
            if (
                source.verification_status.startswith("unverified")
                and case.expected.reference_answer is not None
            ):
                raise ValueError("unverified source has a factual reference")
            if any(str(n) not in source.page_text_sha256 for n in evidence.pdf_pages):
                raise ValueError("missing PDF page digest")
        if covered != set(range(len(case.expected.required_facts))):
            raise ValueError("required fact lacks evidence mapping")
        if (
            case.review.status == "needs_source_review"
            and case.expected.reference_answer is not None
        ):
            raise ValueError("unreviewed reference must be null")
        if (
            case.expected.answerability == "source_answerable"
            and not case.expected.reference_answer
        ):
            raise ValueError("answerable case requires reference")
        if case.expected.tool_name:
            filters = case.expected.filter_constraints
            if case.expected.top_k != 5:
                raise ValueError("unexpected top_k")
            if (
                case.expected.tool_name != "search_baseball_knowledge"
                and not filters.get("stadium_id")
            ):
                raise ValueError("RAG stadium filter missing")
        elif case.expected.top_k is not None or case.expected.filter_constraints:
            raise ValueError("non-tool case has tool arguments")
        for candidate in case.retrieval_ground_truth.local_candidate_chunks:
            chunk = local_chunks.get(candidate.chunk_id)
            if (
                not chunk
                or chunk["document_id"] != candidate.document_id
                or chunk["content_hash"] != candidate.content_sha256
            ):
                raise ValueError("local chunk identity mismatch")
            for span in candidate.evidence_spans:
                if (
                    span.fact_index >= len(case.expected.required_facts)
                    or span.end <= span.start
                    or chunk["content"][span.start : span.end] != span.text
                ):
                    raise ValueError("fact evidence span mismatch")
            if candidate.relevance_grade == 2 and not candidate.evidence_spans:
                raise ValueError("core evidence grade requires a fact span")
            if candidate.relevance_grade in {0, 1} and candidate.evidence_spans:
                raise ValueError("direct fact evidence must have core grade")
            if (candidate.label_status == "source_review_pending") != (
                candidate.relevance_grade is None
            ):
                raise ValueError("pending label must have null grade")
        retrieval = case.retrieval_ground_truth
        production_pool = retrieval.production_candidate_pool
        if production_pool.snapshot_sha256 != production.sha256:
            raise ValueError("case production snapshot mismatch")
        if set(production_pool.chunk_ids) - production_chunk_ids:
            raise ValueError("invented production chunk ID")
        if production_pool.status == "not_applicable" and production_pool.chunk_ids:
            raise ValueError("non-RAG case has production candidates")
        review = retrieval.production_relevance_review
        labels = {c.chunk_id: c for c in review.chunks}
        if (
            review.snapshot_sha256 != production.sha256
            or len(labels) != len(review.chunks)
            or set(labels) != set(review.reviewed_chunk_ids)
            or set(labels) - production_chunk_ids
        ):
            raise ValueError("production relevance pool identity mismatch")
        if set(production_pool.chunk_ids) != {
            c.chunk_id for c in review.chunks if c.passes_expected_filter
        }:
            raise ValueError("production eligible pool does not match labels")
        for label in review.chunks:
            actual = production_chunk_map[label.chunk_id]
            document = production_doc_map[label.document_id]
            if (
                label.document_id != actual["document_id"]
                or label.document_type != actual["document_type"]
                or label.observed_content_sha256 != actual["observed_content_sha256"]
                or label.logical_document_id != document["logical_document_id"]
                or label.revision_number != document["revision_number"]
            ):
                raise ValueError("production label revision/hash mismatch")
            if (label.relevance_grade == 2) != bool(label.evidence_spans):
                raise ValueError("production core grade requires fact spans")
            if (review.status == "source_review_pending") != (
                label.relevance_grade is None
            ):
                raise ValueError("source-pending production label must be null")
            for span in label.evidence_spans:
                if (
                    span.fact_index >= len(case.expected.required_facts)
                    or span.end <= span.start
                ):
                    raise ValueError("invalid production fact span")
                if body_map:
                    body = body_map[label.chunk_id]["content"]
                    if (
                        span.end > len(body)
                        or sha(body[span.start : span.end].encode()) != span.span_sha256
                    ):
                        raise ValueError("production span content/hash mismatch")
        if sorted(f.fact_index for f in review.fact_labels) != list(
            range(len(case.expected.required_facts))
        ):
            raise ValueError("production fact label completeness mismatch")
        for fact in review.fact_labels:
            for filtered in (False, True):
                state = fact.filtered_status if filtered else fact.status
                support_ids = (
                    fact.filtered_supporting_chunk_ids
                    if filtered
                    else fact.supporting_chunk_ids
                )
                strengths = []
                span_ids = {
                    chunk_id
                    for chunk_id, label in labels.items()
                    if (not filtered or label.passes_expected_filter)
                    and any(
                        s.fact_index == fact.fact_index for s in label.evidence_spans
                    )
                }
                if set(support_ids) != span_ids:
                    raise ValueError(
                        "production fact support/span completeness mismatch"
                    )
                for chunk_id in support_ids:
                    if chunk_id not in labels or (
                        filtered and not labels[chunk_id].passes_expected_filter
                    ):
                        raise ValueError(
                            "production fact support outside eligible pool"
                        )
                    spans = [
                        s
                        for s in labels[chunk_id].evidence_spans
                        if s.fact_index == fact.fact_index
                    ]
                    if not spans:
                        raise ValueError("production fact support lacks span")
                    strengths.extend(s.support for s in spans)
                if state in {"supported", "partial"} and not support_ids:
                    raise ValueError("production supported fact has no evidence")
                if state not in {"supported", "partial"} and support_ids:
                    raise ValueError("production non-supported fact claims evidence")
                if state == "supported" and "full" not in strengths:
                    raise ValueError("production supported fact lacks full span")
                if state == "partial" and "full" in strengths:
                    raise ValueError("production partial fact has full span")
        for field, stated in (
            ("status", review.corpus_coverage),
            ("filtered_status", review.filtered_coverage),
        ):
            states = [
                getattr(f, field)
                for f in review.fact_labels
                if getattr(f, field) != "not_retrieval_fact"
            ]
            expected_coverage = (
                "not_applicable"
                if review.status == "not_applicable"
                else "source_review_pending"
                if review.status == "source_review_pending"
                else "full"
                if states and all(s == "supported" for s in states)
                else "partial"
                if any(s in {"supported", "partial"} for s in states)
                else "missing"
            )
            if stated != expected_coverage:
                raise ValueError("production fact coverage mismatch")
        db_check = retrieval.db_validation
        if db_check.snapshot_sha256 != runtime.sha256:
            raise ValueError("case DB snapshot mismatch")
        if db_check.actual_matching_chunk_ids:
            raise ValueError("empty DB cannot have matching chunks")
        if retrieval.db_corpus_verified != (db_check.status != "not_applicable"):
            raise ValueError("case DB verification status mismatch")
        expected_missing = (
            [
                f.fact_index
                for f in retrieval.fact_labels
                if f.status not in {"not_retrieval_fact", "source_review_pending"}
            ]
            if db_check.status == "corpus_empty"
            else []
        )
        if db_check.missing_retrieval_fact_indexes != expected_missing:
            raise ValueError("DB missing fact indexes mismatch")
        candidates = {x.chunk_id: x for x in retrieval.local_candidate_chunks}
        if len(candidates) != len(retrieval.local_candidate_chunks):
            raise ValueError("duplicate local candidate chunk")
        if set(retrieval.pool_scope.chunk_ids) != set(candidates):
            raise ValueError("reviewed pool mismatch")
        if sorted(x.fact_index for x in retrieval.fact_labels) != list(
            range(len(case.expected.required_facts))
        ):
            raise ValueError("fact label completeness mismatch")
        for fact in retrieval.fact_labels:
            if (
                fact.status in {"supported", "partial"}
                and not fact.supporting_chunk_ids
            ):
                raise ValueError("supported fact requires evidence")
            if (
                fact.status not in {"supported", "partial"}
                and fact.supporting_chunk_ids
            ):
                raise ValueError("non-supported fact cannot claim evidence")
            supports = []
            for chunk_id in fact.supporting_chunk_ids:
                if chunk_id not in candidates:
                    raise ValueError("fact chunk outside reviewed pool")
                spans = [
                    s
                    for s in candidates[chunk_id].evidence_spans
                    if s.fact_index == fact.fact_index
                ]
                if not spans:
                    raise ValueError("fact chunk lacks matching span")
                supports.extend(s.support for s in spans)
            if fact.status == "supported" and "full" not in supports:
                raise ValueError("supported fact requires full support span")
            if fact.status == "partial" and "full" in supports:
                raise ValueError("partial fact has full support span")
    manifest = raw["local_corpus_snapshot"]["files"]
    if (
        sha(canonical(manifest, ascii_only=True))
        != dataset.local_corpus_snapshot.sha256
    ):
        raise ValueError("local corpus manifest hash mismatch")
    if check_files:
        checks = [(f.path, f.sha256) for f in dataset.local_corpus_snapshot.files]
        checks += [
            (s.local_path, s.content_sha256) for s in dataset.sources if s.local_path
        ]
        for path, expected_hash in checks:
            assert path is not None
            actual_path = (ROOT / path).resolve()
            if (
                not actual_path.is_relative_to(ROOT)
                or not actual_path.is_file()
                or sha(actual_path.read_bytes()) != expected_hash
            ):
                raise ValueError(f"local source snapshot mismatch: {path}")
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--write-schema", action="store_true")
    parser.add_argument(
        "--production-snapshot",
        type=Path,
        help="Optional temporary public body snapshot for exact span/hash verification",
    )
    args = parser.parse_args()
    dataset = validate_dataset(
        json.loads(args.path.read_text()),
        production_snapshot_path=args.production_snapshot,
    )
    if args.write_schema:
        schema = Dataset.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        SCHEMA_PATH.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n")
    pending = sum(c.review.status == "needs_source_review" for c in dataset.cases)
    print(
        f"Valid draft: {len(dataset.cases)} cases, development=35, held_out=15, source_review_pending={pending}; evaluation not run."
    )


if __name__ == "__main__":
    main()
