# Stadium Guide RAG Collection And Embedding Status v1-1

> 작성일: 2026-07-31  
> 대상 Tool: `search_stadium_guide`  
> 목적: 이미 수집/임베딩한 구장 가이드 RAG 데이터의 범위, 구조, 운영 방법을 기록  
> 상태: 9개 정규 홈구장 수집 및 임베딩 완료

## 1. Tool 목표

`search_stadium_guide`는 KBO 홈구장의 예매, 좌석, 반입 정책, 교통, 주차, 편의시설 안내를 RAG 문서에서 검색하는 Tool이다.

Agent 답변 생성에 사용할 근거 chunk, 출처 URL, 기준 시점, 신뢰 등급을 반환한다.

## 2. 현재 데이터 범위

현재 유지 중인 normalized 문서는 9개 구장, 45개 문서다.

```text
SAJIK   5 docs
GOCHEOK 5 docs
MUNHAK  5 docs
GWANGJU 5 docs
DAEGU   5 docs
SUWON   5 docs
DAEJEON 5 docs
JAMSIL  5 docs
CHANGWON 5 docs
```

구장별 문서 유형:

```text
stadium_bag_policy
stadium_facility_guide
stadium_seat_guide
stadium_ticketing_guide
stadium_transport_guide
```

현재 embedded input:

```text
data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
45 chunks
```

평가 케이스:

```text
data/stadium_guide/evaluation/cases/search_stadium_guide_tool_cases.jsonl
10 cases

data/stadium_guide/evaluation/cases/stadium_guide_search_cases.jsonl
49 cases
```

## 3. 데이터 디렉터리 구조

```text
data/stadium_guide/
├── README.md
├── sources.json
├── collection_summary.md
├── raw/
├── normalized/
├── embedded_input/
│   └── stadium_guide_chunks.jsonl
└── evaluation/
    ├── cases/
    └── runs/
```

원칙:

```text
공식 출처가 확인된 데이터만 RAG 후보로 유지한다.
raw snapshot은 원본 보존용이며 직접 수정하지 않는다.
normalized 문서는 embedding 전 검수 가능한 문서 단위다.
embedded_input은 OpenAI embedding API 호출 전 입력 산출물이다.
```

## 4. 주요 출처

공통 공식 출처:

| source_id | 용도 |
|---|---|
| `kbo_safe_campaign` | 전 구장 공통 반입/보안 정책 기준 |
| `kbo_ticket_map` | KBO 공식 구단별 예매처 매핑 |

구장별 주요 출처는 `data/stadium_guide/sources.json`과 `data/stadium_guide/collection_summary.md`에 기록한다.

구장별 수집 품질 메모:

```text
SAJIK: 가장 완성도 높은 vertical slice.
GOCHEOK: 주차 제한과 대중교통 권장 안내가 공식 출처에 명확함.
MUNHAK: SSG 공식 홈구장 안내와 별도 주차 안내로 품질 양호.
GWANGJU: 좌석/요금 상세는 이미지 중심이라 추가 수동 검수 필요.
DAEGU: 좌석/티켓/환불 정보는 충분, 교통 세부는 추가 확인 필요.
SUWON: 사전 주차 예약제가 공식 출처에 명확함.
DAEJEON: 동적 페이지/raw 재현성이 약한 부분 있음.
JAMSIL: LG/두산 공동 홈구장 맥락 유지 필요.
CHANGWON: 안전점검/재개장 맥락은 최신 공지 확인 필요.
```

## 5. Normalized 문서 구조

각 normalized JSON은 하나의 구장/문서유형 단위다.

예상 필드:

```json
{
  "schema_version": "1.0.0",
  "document_id": "SAJIK_stadium_ticketing_guide_20260729",
  "document_type": "stadium_ticketing_guide",
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "title": "사직야구장 예매 안내 초안",
  "as_of": "2026-07-29",
  "trust_level": "official",
  "review_status": "needs_review",
  "sources": ["kbo_ticket_map"],
  "content": "...",
  "metadata": {
    "topic_summary": "...",
    "search_keywords": ["..."],
    "limitations": ["..."]
  }
}
```

## 6. Chunk 생성 방식

스크립트:

```text
backend/scripts/generate_stadium_guide_chunks.py
```

기본 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/generate_stadium_guide_chunks.py --stadium-id all
```

현재 chunk 전략:

```text
normalized 문서 1개 -> chunk 1개
45 normalized docs -> 45 chunks
```

`embedding_text` 구성:

```text
제목
문서유형
구장
팀
핵심주제
검색키워드
본문
```

이 방식은 짧은 구장 안내 문서에는 단순하고 안정적이다. 문서가 길어질 경우에는 섹션 기반 multi-chunk로 확장한다.

## 7. 임베딩 및 Upsert

스크립트:

```text
backend/scripts/embed_stadium_guide_chunks.py
```

기본 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/embed_stadium_guide_chunks.py
```

임베딩 설정:

```text
model: text-embedding-3-small
dimensions: 1536
batch_size: 32
```

저장 테이블:

```text
public.rag_documents
public.rag_chunks
```

Upsert 키:

```text
rag_documents.document_id
rag_chunks.chunk_id
```

DB 저장 정책:

```text
content_hash 기준으로 변경 추적
source_urls는 citation에 사용
metadata.source_file은 DB metadata에서 제외
review_status는 needs_review 또는 verified
```

주의:

```text
local Supabase에서 supabase db reset을 실행하면 임베딩 데이터는 사라진다.
현재 임베딩 데이터는 seed에 포함되어 있지 않으므로 reset 후 재생성이 필요하다.
```

재생성 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/generate_stadium_guide_chunks.py --stadium-id all
uv run python scripts/embed_stadium_guide_chunks.py
```

## 8. Retriever 및 Tool 연결

Tool 코드:

```text
backend/app/domains/baseball/tool/search_stadium_guide/
├── __init__.py
├── handler.py
├── retriever.py
└── schemas.py
```

연결 파일:

```text
backend/app/agent/routing_schemas.py
backend/app/agent/tool_cards.py
backend/app/agent/prompts.py
backend/app/agent/tool_executor.py
backend/app/api/dependencies.py
```

검색 필터:

```text
stadium_id 필수
guide_types 선택
team_id 선택
top_k 기본 5
review_status는 retriever 정책에 따라 필터링
```

라우팅 호출 대상:

```text
구장별 예매 방법
좌석 종류
반입 정책
교통/주차
편의시설
직관 준비
```

라우팅 제외 대상:

```text
특정 날짜 경기 일정/상태 -> find_kbo_game
구장 주소/돔 여부/홈팀 기본 정보 -> get_stadium_info
실시간 티켓 잔여석 -> 미지원
날씨/우천 취소 예측 -> get_weather_context 예정
야구 규칙/플레이 설명 -> search_baseball_knowledge 예정
```

## 9. 평가 현황

현재 평가 파일:

```text
data/stadium_guide/evaluation/cases/search_stadium_guide_tool_cases.jsonl
data/stadium_guide/evaluation/cases/stadium_guide_search_cases.jsonl
```

평가 스크립트:

```text
backend/scripts/evaluate_search_stadium_guide_tool.py
backend/scripts/evaluate_stadium_guide_retrieval.py
```

대표 Tool 케이스는 10/10 통과한 상태로 기록되어 있다.

평가 run 기록:

```text
data/stadium_guide/evaluation/runs/
```

특히 전체 구장 baseline:

```text
2026-07-30_121818_stadium_guide_search_cases_text-embedding-3-small_all-stadium-baseline.json
```

## 10. 향후 업데이트 후보

데이터 보강:

```text
좌석/요금이 이미지 중심인 구장의 수동 검수
구장별 반입 예외 정책 추가 확인
주차 대수, 요금, 예약 여부 최신화
층별 시설, 수유실, 흡연구역, 팬샵 위치 보강
동적 페이지 raw snapshot 재현성 개선
```

임베딩 개선:

```text
긴 normalized 문서의 section multi-chunk 분할
검색키워드 synonym 보강
guide_type별 top_k 튜닝
review_status=verified 데이터만 운영 검색에 노출하는 정책 검토
```

운영 개선:

```text
supabase db reset 후 자동 재임베딩 절차 문서화
source_url dead link 점검 스크립트
content_hash 변경분만 재임베딩
evaluation case를 구장별 균등하게 확장
```

## 11. 다음 버전 기록 방식

이 문서는 운영 중 업데이트될 수 있으므로 파일명에 버전을 유지한다.

```text
stadium-guide-rag-status-v1-1.md
stadium-guide-rag-status-v1-2.md
...
```
