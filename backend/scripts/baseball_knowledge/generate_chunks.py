from __future__ import annotations

# 추출된 KBO PDF page JSONL을 search_baseball_knowledge용 RAG chunk JSONL로 변환한다.
# 초기 버전은 topic별 source page slice를 묶어 임베딩한다.
import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536
DEFAULT_AS_OF = "2026-07-31"
MAX_CONTENT_CHARS = 6500


@dataclass(frozen=True)
class TopicSource:
    source_id: str
    pages: tuple[int, ...]


@dataclass(frozen=True)
class Topic:
    topic_id: str
    title: str
    document_type: str
    knowledge_type: str
    summary: str
    keywords: tuple[str, ...]
    example_questions: tuple[str, ...]
    sources: tuple[TopicSource, ...]


TOPICS = [
    Topic(
        topic_id="basic_rule_game_objective",
        title="야구 경기의 목적",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="야구의 기본 구조, 공격팀과 수비팀의 목적, 득점의 의미.",
        keywords=("야구의 목적", "공격", "수비", "득점", "초보 규칙"),
        example_questions=("야구는 어떻게 이기는 거야?", "공격팀은 뭘 해야 해?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (25,)),),
    ),
    Topic(
        topic_id="basic_rule_scoring",
        title="득점 조건",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="타자 또는 주자가 베이스를 돌아 득점하는 기본 조건.",
        keywords=("득점", "홈인", "주자", "베이스", "점수"),
        example_questions=("야구는 언제 점수가 나?", "주자가 어떻게 들어오면 득점이야?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (25, 45, 47)),),
    ),
    Topic(
        topic_id="basic_rule_strike_ball",
        title="볼과 스트라이크",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="투구가 볼 또는 스트라이크로 판정되는 기본 맥락과 카운트.",
        keywords=("볼", "스트라이크", "삼진", "볼넷", "ABS", "카운트"),
        example_questions=("볼이랑 스트라이크가 뭐야?", "왜 저 공이 스트라이크야?"),
        sources=(
            TopicSource("kbo_2026_official_baseball_rules", (49, 50, 51, 52)),
            TopicSource("kbo_2026_league_rules", (67, 68, 69)),
        ),
    ),
    Topic(
        topic_id="basic_rule_fair_foul",
        title="페어와 파울",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="타구가 페어 또는 파울로 판단되는 기준.",
        keywords=("페어", "파울", "파울라인", "타구", "인플레이"),
        example_questions=("페어랑 파울은 어떻게 구분해?", "파울인데 왜 계속 쳐?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (26, 27, 37)),),
    ),
    Topic(
        topic_id="basic_rule_out_count",
        title="아웃카운트",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="공격이 끝나는 기준인 아웃과 이닝 전환의 기본 맥락.",
        keywords=("아웃", "아웃카운트", "삼자범퇴", "이닝", "공수교대"),
        example_questions=("아웃카운트가 뭐야?", "왜 3아웃이면 공격이 끝나?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (37, 45, 46, 47)),),
    ),
    Topic(
        topic_id="basic_rule_runner_advance",
        title="주자 진루와 귀루",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="주자가 다음 베이스로 가거나 원래 베이스로 돌아가야 하는 상황.",
        keywords=("주자", "진루", "귀루", "베이스", "태그업"),
        example_questions=("주자는 언제 뛰어야 해?", "왜 주자가 다시 돌아가?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65)),),
    ),
    Topic(
        topic_id="basic_rule_live_dead_ball",
        title="볼 인플레이와 볼 데드",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="플레이가 계속되는 상태와 중단되는 상태의 구분.",
        keywords=("볼 인플레이", "볼 데드", "플레이 중단", "타임"),
        example_questions=("볼 데드가 뭐야?", "왜 갑자기 플레이가 멈춰?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (45, 46, 47, 48)),),
    ),
    Topic(
        topic_id="basic_rule_regular_game",
        title="정식경기와 노게임",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="경기가 공식 경기로 성립하는 기준과 노게임 맥락.",
        keywords=("정식경기", "노게임", "강우", "우천", "경기 성립"),
        example_questions=("우천 노게임이 뭐야?", "몇 회부터 경기가 성립돼?"),
        sources=(
            TopicSource("kbo_2026_official_baseball_rules", (136, 137, 138, 139)),
            TopicSource("kbo_2026_league_rules", (44, 45, 46, 61)),
        ),
    ),
    Topic(
        topic_id="basic_rule_suspended_game",
        title="서스펜디드 게임",
        document_type="baseball_rule",
        knowledge_type="basic_rule",
        summary="일시정지 경기와 KBO 리그 적용 맥락.",
        keywords=("서스펜디드", "일시정지 경기", "경기 중단", "재개"),
        example_questions=("서스펜디드 게임이 뭐야?", "중단된 경기는 다시 해?"),
        sources=(
            TopicSource("kbo_2026_official_baseball_rules", (208,)),
            TopicSource("kbo_2026_league_rules", (45, 47, 49, 51, 52)),
        ),
    ),
    Topic(
        topic_id="common_play_balk",
        title="보크",
        document_type="common_play",
        knowledge_type="common_play",
        summary="투수의 반칙행위로 주자에게 진루권이 주어지는 상황.",
        keywords=("보크", "투수 반칙", "견제", "투구 동작"),
        example_questions=("보크가 뭐야?", "왜 주자가 그냥 한 베이스 갔어?"),
        sources=(
            TopicSource("kbo_2026_official_baseball_rules", (50, 57, 64, 66, 67)),
            TopicSource("kbo_2026_league_rules", (79, 82)),
        ),
    ),
    Topic(
        topic_id="common_play_infield_fly",
        title="인필드 플라이",
        document_type="common_play",
        knowledge_type="common_play",
        summary="내야 뜬공 상황에서 고의 낙구로 병살을 유도하지 못하게 하는 규칙.",
        keywords=("인필드 플라이", "내야 뜬공", "고의낙구", "병살 방지"),
        example_questions=("인필드 플라이가 왜 선언돼?", "공을 안 잡았는데 왜 아웃이야?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (75, 77, 83, 84)),),
    ),
    Topic(
        topic_id="common_play_tag_out_force_out",
        title="태그아웃과 포스아웃",
        document_type="common_play",
        knowledge_type="common_play",
        summary="주자를 직접 태그해야 하는 아웃과 베이스 터치만으로 되는 아웃의 차이.",
        keywords=("태그아웃", "포스아웃", "포스 플레이", "베이스 터치"),
        example_questions=("포스아웃이랑 태그아웃 차이가 뭐야?", "왜 베이스만 밟아도 아웃이야?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (53, 56, 58, 62, 70, 73, 80, 81, 82, 83)),),
    ),
    Topic(
        topic_id="common_play_steal_pickoff",
        title="도루와 견제",
        document_type="common_play",
        knowledge_type="common_play",
        summary="주자가 다음 베이스를 노리는 도루와 투수가 주자를 묶어두는 견제.",
        keywords=("도루", "견제", "주자", "투수", "베이스"),
        example_questions=("도루랑 견제는 뭐가 달라?", "투수는 왜 계속 1루로 던져?"),
        sources=(
            TopicSource("kbo_2026_official_baseball_rules", (55, 58, 64, 82, 113)),
            TopicSource("kbo_2026_league_rules", (70, 75, 76, 78)),
        ),
    ),
    Topic(
        topic_id="common_play_sacrifice",
        title="희생번트와 희생플라이",
        document_type="common_play",
        knowledge_type="common_play",
        summary="타자가 아웃을 감수하고 주자 진루나 득점에 기여하는 플레이.",
        keywords=("희생번트", "희생플라이", "번트", "플라이", "타점"),
        example_questions=("희생플라이가 뭐야?", "왜 일부러 번트를 대?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (151, 153, 155, 156)),),
    ),
    Topic(
        topic_id="common_play_double_play",
        title="병살과 더블플레이",
        document_type="common_play",
        knowledge_type="common_play",
        summary="하나의 연속된 플레이에서 두 개의 아웃이 잡히는 상황.",
        keywords=("병살", "더블플레이", "트리플플레이", "아웃"),
        example_questions=("병살은 왜 2아웃이야?", "더블플레이가 뭐야?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (147,)),),
    ),
    Topic(
        topic_id="common_play_wild_pitch_passed_ball",
        title="폭투와 포일",
        document_type="common_play",
        knowledge_type="common_play",
        summary="투구가 포수에게 제대로 처리되지 않아 주자가 진루하는 상황의 기록 구분.",
        keywords=("폭투", "포일", "와일드 피치", "패스트볼", "포수"),
        example_questions=("폭투랑 포일 차이가 뭐야?", "공 빠졌는데 왜 주자가 뛰어?"),
        sources=(TopicSource("kbo_2026_official_baseball_rules", (129, 131, 153)),),
    ),
    Topic(
        topic_id="latest_rule_video_review",
        title="비디오 판독",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="KBO 리그 비디오 판독 대상과 신청 절차의 기본 맥락.",
        keywords=("비디오 판독", "판독", "챌린지", "번복", "심판"),
        example_questions=("비디오 판독은 아무거나 신청할 수 있어?", "판독 기회는 어떻게 써?"),
        sources=(TopicSource("kbo_2026_league_rules", (29, 30, 31, 32)),),
    ),
    Topic(
        topic_id="latest_rule_check_swing_review",
        title="체크스윙 판독",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="체크스윙 비디오 판독의 KBO 리그 적용 방식.",
        keywords=("체크스윙", "스윙 판정", "비디오 판독", "노스윙"),
        example_questions=("체크스윙도 비디오 판독 돼?", "스윙인지 아닌지는 어떻게 봐?"),
        sources=(TopicSource("kbo_2026_league_rules", (12, 29, 30, 31, 32)),),
    ),
    Topic(
        topic_id="latest_rule_abs",
        title="ABS",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="KBO 자동 볼-스트라이크 판정 시스템의 적용 맥락.",
        keywords=("ABS", "자동 볼 판정", "자동 스트라이크", "스트라이크존"),
        example_questions=("ABS가 뭐야?", "볼 스트라이크를 기계가 봐?"),
        sources=(TopicSource("kbo_2026_league_rules", (67, 68, 69)),),
    ),
    Topic(
        topic_id="latest_rule_pitch_clock",
        title="피치클락",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="투구 간 시간 제한과 위반 시 적용되는 KBO 리그 규정.",
        keywords=("피치클락", "투구 시간", "시간 제한", "위반"),
        example_questions=("피치클락 위반하면 어떻게 돼?", "투수가 왜 빨리 던져야 해?"),
        sources=(TopicSource("kbo_2026_league_rules", (70, 75, 76, 77, 78)),),
    ),
    Topic(
        topic_id="latest_rule_weather_cancel",
        title="기상 상황 경기취소",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="기상 상황으로 경기가 취소될 수 있는 경우와 결정 권한.",
        keywords=("우천취소", "기상", "경기취소", "취소 여부"),
        example_questions=("비 오면 누가 경기 취소를 결정해?", "우천 취소는 언제 정해져?"),
        sources=(TopicSource("kbo_2026_league_rules", (44, 45, 46)),),
    ),
    Topic(
        topic_id="latest_rule_no_game_suspended",
        title="노게임과 서스펜디드",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="KBO 리그에서 노게임과 서스펜디드가 적용되는 맥락.",
        keywords=("노게임", "서스펜디드", "강우콜드", "경기 중단"),
        example_questions=("노게임이랑 서스펜디드는 뭐가 달라?", "비 때문에 중단되면 어떻게 돼?"),
        sources=(
            TopicSource("kbo_2026_league_rules", (24, 45, 46, 47, 48, 49, 50, 51, 52, 61)),
            TopicSource("kbo_2026_official_baseball_rules", (136, 137, 138, 139, 208)),
        ),
    ),
    Topic(
        topic_id="latest_rule_game_authority",
        title="경기 거행 여부 결정 권한",
        document_type="latest_kbo_rule",
        knowledge_type="latest_kbo_rule",
        summary="경기 전후로 경기 거행 여부와 중단을 결정하는 권한의 흐름.",
        keywords=("경기 거행", "경기 중지", "주심", "경기관리", "결정 권한"),
        example_questions=("경기 취소는 누가 결정해?", "시작한 뒤에는 누가 중단시켜?"),
        sources=(TopicSource("kbo_2026_league_rules", (44, 45, 46, 48, 49)),),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate baseball knowledge RAG chunk JSONL from extracted KBO PDF pages."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Project root directory. Defaults to the repository root.",
    )
    parser.add_argument(
        "--extracted-root",
        type=Path,
        default=None,
        help="Extracted PDF root. Defaults to data/baseball_knowledge/raw/extracted_pdf.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path. Defaults to data/baseball_knowledge/embedded_input/baseball_knowledge_chunks.jsonl.",
    )
    parser.add_argument(
        "--as-of",
        default=DEFAULT_AS_OF,
        help="As-of date for generated chunks.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when a topic source page is missing.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def source_path(extracted_root: Path, source_id: str) -> Path:
    parts = source_id.split("_")
    season_year = parts[1]
    if source_id.endswith("official_baseball_rules"):
        slug = "official_baseball_rules"
    elif source_id.endswith("league_rules"):
        slug = "league_rules"
    else:
        raise ValueError(f"Unsupported source_id: {source_id}")
    return extracted_root / season_year / f"{slug}_pages.jsonl"


def build_page_index(extracted_root: Path) -> dict[tuple[str, int], dict[str, Any]]:
    index: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted(extracted_root.glob("*/*_pages.jsonl")):
        for record in load_jsonl(path):
            index[(record["source_id"], int(record["page_number"]))] = record
    return index


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_urls(records: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for record in records:
        url = record.get("source_url")
        if url and url not in urls:
            urls.append(url)
    return urls


def source_page_metadata(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages_by_source: dict[str, list[int]] = {}
    for record in records:
        pages_by_source.setdefault(record["source_id"], []).append(
            int(record["page_number"])
        )

    return [
        {
            "source_id": source_id,
            "pages": sorted(set(pages)),
        }
        for source_id, pages in pages_by_source.items()
    ]


def collect_topic_records(
    topic: Topic,
    page_index: dict[tuple[str, int], dict[str, Any]],
    *,
    strict: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for source in topic.sources:
        for page_number in source.pages:
            record = page_index.get((source.source_id, page_number))
            if record is None:
                missing.append(f"{source.source_id}:p{page_number}")
                continue
            if record.get("text"):
                records.append(record)

    if strict and missing:
        raise ValueError(f"{topic.topic_id} missing source pages: {missing}")

    return records


def build_content(topic: Topic, records: list[dict[str, Any]]) -> str:
    source_blocks = []
    for record in records:
        source_blocks.append(
            "\n".join(
                [
                    f"[{record['document_title']} p.{record['page_number']}]",
                    record["text"],
                ]
            )
        )

    return "\n\n".join(
        [
            f"주제: {topic.title}",
            f"요약: {topic.summary}",
            "출처 발췌:",
            "\n\n".join(source_blocks),
        ]
    )


def build_embedding_text(topic: Topic, content: str) -> str:
    return "\n".join(
        [
            f"제목: {topic.title}",
            f"문서유형: {topic.document_type}",
            f"지식유형: {topic.knowledge_type}",
            f"topic_id: {topic.topic_id}",
            f"핵심주제: {topic.summary}",
            f"검색키워드: {', '.join(topic.keywords)}",
            f"초보자 질문 예시: {', '.join(topic.example_questions)}",
            "본문:",
            content,
        ]
    )


def split_topic_records(
    topic: Topic,
    records: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []

    for record in records:
        candidate_group = [*current_group, record]
        candidate_content = build_content(topic, candidate_group)
        if current_group and len(candidate_content) > MAX_CONTENT_CHARS:
            groups.append(current_group)
            current_group = [record]
        else:
            current_group = candidate_group

    if current_group:
        groups.append(current_group)

    return groups


def build_chunk(
    topic: Topic,
    records: list[dict[str, Any]],
    *,
    as_of: str,
    chunk_index: int,
) -> dict[str, Any]:
    content = build_content(topic, records)
    embedding_text = build_embedding_text(topic, content)
    source_ids = list(dict.fromkeys(record["source_id"] for record in records))
    years = sorted({int(record["season_year"]) for record in records})

    return {
        "schema_version": "1.0.0",
        "chunk_id": (
            f"baseball_knowledge_{topic.topic_id}_2026_chunk_{chunk_index:03d}"
        ),
        "document_id": f"baseball_knowledge_{topic.topic_id}_2026",
        "chunk_index": chunk_index,
        "document_type": topic.document_type,
        "stadium_id": None,
        "team_id": None,
        "title": topic.title,
        "as_of": as_of,
        "trust_level": "official",
        "review_status": "needs_review",
        "source_ids": source_ids,
        "source_urls": source_urls(records),
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "embedding_dimensions": DEFAULT_EMBEDDING_DIMENSIONS,
        "embedding_text": embedding_text,
        "content": content,
        "content_hash": sha256_text(embedding_text),
        "metadata": {
            "language": "ko",
            "audience": "beginner",
            "knowledge_type": topic.knowledge_type,
            "topic_id": topic.topic_id,
            "topic_summary": topic.summary,
            "search_keywords": list(topic.keywords),
            "example_questions": list(topic.example_questions),
            "season_years": years,
            "is_latest": 2026 in years,
            "source_pages": source_page_metadata(records),
            "limitations": [
                "PDF 원문 page slice 기반 초기 chunk이며, 초보자용 curated 설명문은 후속 단계에서 보강한다."
            ],
        },
    }


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    extracted_root = args.extracted_root or (
        project_root / "data" / "baseball_knowledge" / "raw" / "extracted_pdf"
    )
    output_path = args.output or (
        project_root
        / "data"
        / "baseball_knowledge"
        / "embedded_input"
        / "baseball_knowledge_chunks.jsonl"
    )

    date.fromisoformat(args.as_of)
    page_index = build_page_index(extracted_root)
    chunks: list[dict[str, Any]] = []
    skipped: list[str] = []
    for topic in TOPICS:
        records = collect_topic_records(topic, page_index, strict=args.strict)
        if not records:
            skipped.append(topic.topic_id)
            continue
        for chunk_index, record_group in enumerate(split_topic_records(topic, records)):
            chunks.append(
                build_chunk(
                    topic,
                    record_group,
                    as_of=args.as_of,
                    chunk_index=chunk_index,
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True))
            file.write("\n")

    print(f"Wrote {len(chunks)} chunks to {output_path}")
    if skipped:
        print(f"Skipped topics without text: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
