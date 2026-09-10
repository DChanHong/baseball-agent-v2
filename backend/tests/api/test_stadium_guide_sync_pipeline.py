from datetime import UTC, datetime
from pathlib import Path

from scripts.stadium_guide_sync.classifier import classify_change, classify_missing
from scripts.stadium_guide_sync.parser import parse_collected_source
from scripts.stadium_guide_sync.raw_storage import save_raw_snapshot, sha256_text
from scripts.stadium_guide_sync.registry import load_registry, select_sources
from scripts.stadium_guide_sync.schemas import (
    ActiveDocument,
    ChangeOperation,
    CollectedSource,
    ParsedSource,
    SourceDefinition,
)
from scripts.stadium_guide_sync.service import source_fingerprint
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
