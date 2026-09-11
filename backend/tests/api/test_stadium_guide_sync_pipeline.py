from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from scripts.stadium_guide_sync.application import LocalCandidateApplier
from scripts.stadium_guide_sync.classifier import classify_change, classify_missing
from scripts.stadium_guide_sync.evaluation import EvaluationResult
from scripts.stadium_guide_sync.parser import parse_collected_source
from scripts.stadium_guide_sync.raw_storage import save_raw_snapshot, sha256_text
from scripts.stadium_guide_sync.registry import load_registry, select_sources
from scripts.stadium_guide_sync.schemas import (
    ActiveDocument,
    CandidateRecord,
    CandidateStatus,
    ChangeOperation,
    CollectedSource,
    ParsedSource,
    SourceDefinition,
    SourceRegistry,
)
from scripts.stadium_guide_sync.service import build_embedding_text, source_fingerprint
from scripts.sync_stadium_guides import is_local_database_url

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_collect_database_guard_accepts_only_local_hosts() -> None:
    assert is_local_database_url(
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
    assert not is_local_database_url(
        "postgresql://postgres:secret@pooler.supabase.com:6543/postgres"
    )


def test_registry_selects_only_enabled_gocheok_food_source() -> None:
    registry = load_registry(
        REPOSITORY_ROOT / "data" / "stadium_guide" / "sources.json"
    )

    selected = select_sources(
        registry,
        stadium_id="GOCHEOK",
        document_type="stadium_food_guide",
    )

    assert [source.source_id for source in selected] == ["heroes_gocheok_faq"]
    assert not [
        source.source_id
        for source in registry.sources
        if source.enabled
        and (
            source.source_id.endswith("_kbo_safe_campaign")
            or source.source_id.endswith("_kbo_ticket_map")
        )
    ]


def test_gocheok_faq_parser_keeps_food_and_reentry_evidence() -> None:
    source = SourceDefinition.model_validate(
        {
            "source_id": "heroes_gocheok_faq",
            "title": "고척 FAQ",
            "url": "https://example.com/faq",
            "source_type": "official_team",
            "stadium_ids": ["GOCHEOK"],
            "team_ids": ["KIWOOM"],
            "document_types": ["stadium_food_guide"],
            "parser_name": "heroes_gocheok_faq",
            "refresh_policy": "monthly",
            "trust_level": "official",
        }
    )
    body = """
    <html><body><script>음식물 fake</script>
    <h2>구장 내 음식물 섭취 가능한가요?</h2>
    <p>구장 내 음식물 섭취는 모두 가능합니다.</p>
    <p>최초 입장 시 음식물 반입 가능하며 병에만 담겨있지 않으면 됩니다.
    재입장 시에는 외부 음식 반입은 제한됩니다.</p>
    <h2>캔 반입 가능한가요?</h2><p>총 1L 이내입니다.</p>
    </body></html>
    """
    collected = CollectedSource(
        source=source,
        collected_at=datetime.now(UTC),
        body=body,
        status_code=200,
        collector_type="http",
    )

    parsed = parse_collected_source(collected)

    assert "음식물" in parsed
    assert "재입장" in parsed
    assert "fake" not in parsed


def test_classifier_distinguishes_create_update_unchanged_and_delete() -> None:
    active = ActiveDocument(
        document_id="GOCHEOK_stadium_food_guide_r0001",
        logical_document_id="GOCHEOK_stadium_food_guide",
        revision_number=1,
        content_hash="same",
        title="고척 음식물 안내",
    )

    assert classify_change(None, "new") == ChangeOperation.CREATE
    assert classify_change(active, "new") == ChangeOperation.UPDATE
    assert classify_change(active, "same") == ChangeOperation.UNCHANGED
    assert (
        classify_missing(active_exists=True, consecutive_missing_count=2)
        == ChangeOperation.DELETE_CANDIDATE
    )
    assert (
        classify_missing(active_exists=True, consecutive_missing_count=1)
        == ChangeOperation.MANUAL_REQUIRED
    )


def test_raw_snapshot_and_source_fingerprint_are_idempotent(tmp_path: Path) -> None:
    source = SourceDefinition.model_validate(
        {
            "source_id": "source",
            "title": "source",
            "url": "https://example.com",
            "source_type": "official_team",
            "stadium_ids": ["GOCHEOK"],
            "team_ids": ["KIWOOM"],
            "document_types": ["stadium_food_guide"],
            "refresh_policy": "monthly",
            "trust_level": "official",
        }
    )
    collected = CollectedSource(
        source=source,
        collected_at=datetime(2026, 9, 10, tzinfo=UTC),
        body="<html><body>same body</body></html>",
        status_code=200,
        collector_type="http",
    )
    parsed = ParsedSource(
        collected=collected,
        text="same normalized text",
        raw_hash=sha256_text(collected.body),
        text_hash=sha256_text("same normalized text"),
    )

    first = save_raw_snapshot(tmp_path, parsed)
    second = save_raw_snapshot(tmp_path, parsed)

    assert first.raw_file_path == second.raw_file_path
    assert len(list(tmp_path.rglob("*.html"))) == 1
    assert source_fingerprint([first]) == source_fingerprint([second])


@pytest.mark.asyncio
async def test_apply_local_embeds_only_the_approved_candidate(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "logical_document_id": "GOCHEOK_stadium_food_guide",
        "revision_id": "GOCHEOK_stadium_food_guide_r0001",
        "revision_number": 1,
        "document_type": "stadium_food_guide",
        "stadium_id": "GOCHEOK",
        "team_id": "KIWOOM",
        "title": "고척 음식물 안내",
        "as_of": "2026-09-10",
        "trust_level": "official",
        "review_status": "needs_review",
        "sources": ["heroes_gocheok_faq"],
        "content": "최초 입장 시 병에 담기지 않은 음식물을 반입할 수 있습니다.",
        "metadata": {
            "topic_summary": "고척 음식물 반입 안내",
            "search_keywords": ["고척돔", "음식물"],
            "limitations": [],
        },
    }
    payload["content_hash"] = sha256_text(build_embedding_text(payload))
    now = datetime.now(UTC)
    candidate = CandidateRecord(
        candidate_id="candidate-1",
        run_id="run-1",
        logical_document_id="GOCHEOK_stadium_food_guide",
        operation=ChangeOperation.CREATE,
        previous_revision_id=None,
        candidate_revision_id="GOCHEOK_stadium_food_guide_r0001",
        previous_content_hash=None,
        candidate_content_hash=str(payload["content_hash"]),
        candidate_payload=payload,
        diff_summary={},
        source_ids=["heroes_gocheok_faq"],
        status=CandidateStatus.APPROVED,
        reviewed_at=now,
        review_note=None,
        created_at=now,
        updated_at=now,
    )

    class FakeRepository:
        async def candidate(self, candidate_id: str) -> CandidateRecord:
            assert candidate_id == "candidate-1"
            return candidate

        async def apply_candidate_revision(self, **kwargs: object) -> tuple[str, bool]:
            assert kwargs["candidate_id"] == "candidate-1"
            assert kwargs["embedding_text"] == build_embedding_text(payload)
            assert str(kwargs["embedding_vector"]).startswith("[0.0,0.0")
            return "GOCHEOK_stadium_food_guide_r0001", False

        async def finalize_evaluation(self, **kwargs: object) -> CandidateRecord:
            return candidate.model_copy(
                update={"status": CandidateStatus.READY_FOR_PRODUCTION}
            )

    class FakeEmbedder:
        calls = 0

        async def embed(self, text: str) -> list[float]:
            self.calls += 1
            assert text == build_embedding_text(payload)
            return [0.0] * 1536

    class FakeEvaluator:
        async def evaluate(self, **kwargs: object) -> EvaluationResult:
            assert kwargs == {
                "stadium_id": "GOCHEOK",
                "document_type": "stadium_food_guide",
            }
            return EvaluationResult("eval-1", True, tmp_path / "eval.json", {})

    source = SourceDefinition(
        source_id="heroes_gocheok_faq",
        title="고척 FAQ",
        url="https://example.com/faq",
        source_type="official_team",
        stadium_ids=["GOCHEOK"],
        team_ids=["KIWOOM"],
        document_types=["stadium_food_guide"],
        refresh_policy="monthly",
        trust_level="official",
    )
    embedder = FakeEmbedder()
    result = await LocalCandidateApplier(
        repository=FakeRepository(),  # type: ignore[arg-type]
        registry=SourceRegistry(
            schema_version="2.0.0",
            as_of=date(2026, 9, 10),
            description="test",
            sources=[source],
        ),
        embedder=embedder,
        evaluator=FakeEvaluator(),
    ).apply("candidate-1")

    assert embedder.calls == 1
    assert result.status == CandidateStatus.READY_FOR_PRODUCTION
    assert result.evaluation is not None and result.evaluation.passed
