from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol

from openai import AsyncOpenAI

from .schemas import ActiveDocument, CandidateDraft, SourceDefinition


class CandidateGenerator(Protocol):
    async def generate(
        self,
        *,
        logical_document_id: str,
        document_type: str,
        stadium_id: str | None,
        team_id: str | None,
        sources: list[tuple[SourceDefinition, str]],
        active: ActiveDocument | None,
    ) -> CandidateDraft: ...


class OpenAICandidateGenerator:
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float = 60.0) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    async def generate(
        self,
        *,
        logical_document_id: str,
        document_type: str,
        stadium_id: str | None,
        team_id: str | None,
        sources: list[tuple[SourceDefinition, str]],
        active: ActiveDocument | None,
    ) -> CandidateDraft:
        source_payload = [
            {
                "source_id": source.source_id,
                "title": source.title,
                "url": source.url,
                "extracted_text": text,
            }
            for source, text in sources
        ]
        prompt = {
            "logical_document_id": logical_document_id,
            "document_type": document_type,
            "stadium_id": stadium_id,
            "team_id": team_id,
            "today": datetime.now(UTC).date().isoformat(),
            "active_document": active.model_dump(mode="json") if active else None,
            "official_sources": source_payload,
            "document_type_scope": {
                "stadium_food_guide": "음식물 반입·섭취와 구장 내 식음시설만 포함한다.",
                "stadium_bag_policy": "가방·용기·주류·금지 물품만 포함한다.",
                "stadium_entry_guide": "입장·재입장·티켓 확인 절차만 포함한다.",
                "stadium_accessibility_guide": (
                    "휠체어석·장애인 편의시설과 이동 지원만 포함한다."
                ),
            }.get(
                document_type,
                f"{document_type}에 직접 해당하는 정보만 포함한다.",
            ),
        }
        response = await self._client.responses.parse(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "공식 출처의 추출 본문만 사용해 KBO 구장 안내 후보를 작성한다. "
                        "출처에 없는 사실을 만들지 말고, 충돌하거나 불확실한 내용은 limitations에 둔다. "
                        "content는 한국어로 독립적으로 이해되는 안내문이어야 한다. "
                        "as_of는 출처를 확인한 오늘 날짜를 사용한다. "
                        "주소, 전화번호, 사이트 메뉴, 저작권 문구 등 문서 유형과 "
                        "직접 관계없는 페이지 공통 정보는 제외한다. "
                        "이번 시즌·현재 같은 상대 시점 표현은 기준일과 함께 제한하고 "
                        "지속 여부를 limitations에 남긴다."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            text_format=CandidateDraft,
        )
        if response.output_parsed is None:
            raise RuntimeError("LLM_SCHEMA_OUTPUT_MISSING")
        return response.output_parsed
