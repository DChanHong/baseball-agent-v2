# 구장 가이드 데이터 수집 전략

> 라벨: `REFERENCE`  
> 상태: 데이터 수집 기준 문서  
> 작성일: 2026-07-28  
> 목적: `find_stadium_guide` 계열 Tool 구현 전에 구장 정보의 수집 범위, 출처, 정형/RAG 분리 기준을 확정한다.

## 1. 배경

다음 Tool 후보는 구장 안내다. 다만 현재 `kbo_stadiums`에는 경기 일정 조회에 필요한 최소 식별 정보만 있다.

현재 seed가 제공하는 값:

```text
stadium_id
name_ko
short_name
aliases
city
home_team_id
is_active
```

이 정보만으로는 다음 질문에 답하기 어렵다.

```text
사직구장 처음 가는데 뭐 챙겨야 해?
잠실 원정 갈 때 어디로 들어가?
고척은 비 와도 경기해?
대전구장 주차 괜찮아?
```

구장 안내는 정확한 정형 필드와 설명형 문서 지식이 섞여 있으므로, 수집 단계에서 둘을 분리한다.

## 2. Tool 방향

초기 이름은 대화상 편의상 `find_stadium_guide`로 부르되, 구현은 내부적으로 두 성격을 분리한다.

```text
get_stadium_info
```

- 정형 구장 프로필 조회
- 주소, 좌표, 홈팀, 공식 URL, 돔 여부, 기본 수용 규모 같은 값
- RAG를 사용하지 않는다.

```text
search_stadium_guide
```

- 설명형 구장 가이드 검색
- 입장, 반입, 편의시설, 주차, 대중교통, 초행 팁, 날씨/돔 관람 팁
- RAG 후보로 둔다.

Agent에게 노출할 최종 Tool을 하나로 둘지 둘로 나눌지는 evaluation 후 결정한다. 데이터 수집과 저장은 처음부터 분리한다.

## 3. 수집 범위

### 3.1 정형 구장 프로필

필수 필드:

| 필드 | 설명 |
|---|---|
| `stadium_id` | 내부 고정 ID |
| `name_ko` | 공식 또는 관용 구장명 |
| `short_name` | 짧은 구장명 |
| `aliases` | 사용자 입력 매칭용 별칭 |
| `city` | 도시 |
| `region` | 광역 지역 |
| `address` | 공식 주소 |
| `latitude` | 위도 |
| `longitude` | 경도 |
| `home_team_ids` | 홈으로 쓰는 팀 목록. 잠실은 LG/DOOSAN |
| `is_dome` | 돔 구장 여부 |
| `is_active` | 현재 KBO 1군 경기 사용 여부 |
| `official_url` | 구장 또는 구단 공식 안내 URL |
| `as_of` | 정보 기준 시점 |

선택 필드:

| 필드 | 설명 |
|---|---|
| `capacity` | 수용 인원. 출처별 차이가 있으므로 optional |
| `opened_year` | 개장 연도 |
| `owner` | 지자체/운영 주체 |
| `parking_summary` | 정형 요약이 가능한 경우만 저장 |
| `nearest_transit_summary` | 대표 지하철/역/정류장 요약 |

정확성이 중요한 주소와 좌표는 임의 블로그나 커뮤니티에서 수집하지 않는다.

### 3.2 설명형 구장 가이드 문서

초기 우선 지원 문서 유형:

| `document_type` | 내용 |
|---|---|
| `stadium_bag_policy` | 반입 가능/금지 물품, 음식물, 병/캔, 보안 검색 |
| `stadium_facility_guide` | 화장실, 매점, 수유실, 물품보관, 흡연구역, 장애인 편의 |
| `stadium_seat_guide` | 좌석 구역, 좌석 종류, 휠체어석, 공식 좌석도 기준 안내 |
| `stadium_ticketing_guide` | 예매처, 예매 절차, 요금/할인/취소 안내 |
| `stadium_transport_guide` | 대중교통, 주차, 교통 혼잡, 귀가 팁 |

추후 보강 후보:

| `document_type` | 내용 |
|---|---|
| `stadium_entry_guide` | 입장 게이트, 매표소, 재입장, 현장 동선 |
| `stadium_first_visit_tip` | 초행 관람 준비물, 시간 여유, 계절별 주의점 |
| `stadium_weather_tip` | 돔/야외 구장 차이, 우천 시 일반 안내 |

초기에는 모든 구장을 완벽히 채우지 않는다. 먼저 2개 구장만 vertical slice로 만든다.

```text
1순위: SAJIK
2순위: JAMSIL
```

이유:

- 평가 질문에 이미 사직 초행 질문이 있다.
- 잠실은 LG/DOOSAN 공동 홈이라 팀/구장 분리 정책을 검증하기 좋다.

## 4. 출처 우선순위

### 4.1 신뢰 등급

| 등급 | 출처 | 사용 용도 |
|---|---|---|
| `official_league` | KBO 공식 사이트 | 리그 공통 안전/관람 정책, 공지 |
| `official_team` | 구단 공식 사이트/앱/예매 안내 | 구장별 입장, 예매, 좌석, 반입, 이벤트 |
| `official_venue_or_city` | 구장 운영 주체 또는 지자체 | 주소, 시설, 주차, 교통 |
| `verified_partner` | 공식 예매처, 지도 API, 공공데이터 | 예매 경로, 위치/좌표 |
| `curated` | 사람이 직접 작성하고 출처를 단 가이드 | 초행 팁, 주의사항 요약 |
| `community_reference` | 블로그, 커뮤니티, 후기 | 초기 MVP에서는 원문 근거로 사용하지 않음 |

`community_reference`는 아이디어 확인용으로만 사용하고, 사용자 답변 citation에는 쓰지 않는다.

### 4.2 초기 source registry

수집 전 `data/raw/stadium_guide/source_registry.json`을 먼저 만든다.

필드:

```json
{
  "source_id": "kbo_safe_guide",
  "source_type": "official_league",
  "title": "KBO 경기장 안전 가이드",
  "url": "https://www.koreabaseball.com/Kbo/BusinessAndEvent/SafeGuide.aspx",
  "stadium_id": null,
  "team_id": null,
  "document_types": ["stadium_bag_policy", "stadium_first_visit_tip"],
  "collection_method": "manual_review",
  "trust_level": "official",
  "refresh_policy": "monthly_or_before_season",
  "notes": "공통 관람 안전 정책"
}
```

source registry는 crawler보다 먼저 관리한다. 어느 URL을 왜 수집했는지 추적할 수 있어야 한다.

## 5. 수집 방식

### 5.1 단계 1: 수동 source registry

먼저 각 구장별 공식 출처 후보를 사람이 확인해 registry에 등록한다.

필수 확인:

- URL이 현재 접근 가능한가
- 공식 출처인가
- 구장별 정보인지, 리그 공통 정보인지
- 수집 가능한 문서 유형이 무엇인가
- 갱신 주기가 빠른 정보인가

실시간성이 큰 값은 수집하지 않는다.

초기 제외:

- 당일 티켓 잔여석
- 당일 이벤트
- 실시간 주차 가능 대수
- 실시간 교통 상황
- 날씨 예보

### 5.2 단계 2: raw 저장

경로:

```text
data/raw/stadium_guide/
├── source_registry.json
└── YYYY-MM-DD/
    ├── SAJIK/
    │   ├── official_team_entry.html
    │   ├── official_team_facility.html
    │   └── metadata.json
    └── JAMSIL/
        ├── official_team_entry.html
        └── metadata.json
```

raw metadata 필수 필드:

```json
{
  "source_id": "lotte_sajik_entry",
  "source_url": "https://...",
  "source_type": "official_team",
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "collected_at": "2026-07-28T00:00:00+09:00",
  "as_of": "2026-07-28",
  "collector_version": "stadium-guide-v1",
  "http_status": 200,
  "content_hash": "sha256..."
}
```

원본 HTML/PDF/JSON은 수정하지 않는다.

### 5.3 단계 3: normalized 문서 생성

경로:

```text
data/processed/stadium_guide/
└── stadium_guide_documents.json
```

정규화 필드:

```json
{
  "document_id": "SAJIK_stadium_entry_guide_lotte_official_20260728",
  "document_type": "stadium_entry_guide",
  "title": "사직야구장 입장 안내",
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "source_type": "official_team",
  "source_url": "https://...",
  "source_file": "data/raw/stadium_guide/2026-07-28/SAJIK/official_team_entry.html",
  "as_of": "2026-07-28",
  "trust_level": "official",
  "content": "정규화된 본문...",
  "content_hash": "sha256...",
  "metadata": {
    "language": "ko",
    "collection_method": "manual_review"
  }
}
```

정규화 원칙:

- 광고, 메뉴, footer, 반복 navigation은 제거한다.
- 원문 의미를 바꾸는 요약을 하지 않는다.
- 표는 문장형 또는 markdown table로 보존한다.
- “현재”, “오늘”, “이번 시즌” 같은 표현은 `as_of`와 함께 유지한다.
- 출처별로 같은 내용이 충돌하면 공식 등급이 높은 문서를 우선한다.

### 5.4 단계 4: chunk 생성

초기 chunk 규칙:

```text
chunk 단위: 하나의 소제목 또는 500~900 Korean chars
overlap: 80~120 chars
metadata: document_type, stadium_id, team_id, source_type, as_of, trust_level
```

질문이 구장을 명시하면 `stadium_id` filter를 반드시 적용한다. 구장을 명시하지 않았지만 팀이 있으면 홈구장을 이용해 `stadium_id` 후보를 좁힌다.

## 6. DB 저장 방향

정형 구장 프로필은 기존 `kbo_stadiums`를 확장한다.

추가 후보:

```text
region
address
latitude
longitude
capacity
opened_year
is_dome
official_url
as_of
metadata jsonb
```

설명형 문서는 RAG 테이블에 저장한다.

```text
rag_documents
rag_chunks
```

`rag_documents.document_type`은 다음 5개 값을 우선 지원한다.

```text
stadium_bag_policy
stadium_facility_guide
stadium_seat_guide
stadium_ticketing_guide
stadium_transport_guide
```

다음 값은 현재 테이블 enum으로 강제하지 않고, 추후 공식 출처와 질문 수요가 충분할 때 보강한다.

```text
stadium_entry_guide
stadium_first_visit_tip
stadium_weather_tip
```

## 7. Tool 계약 초안

### 7.1 입력

```json
{
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "query": "처음 가는데 뭐 챙겨야 해?",
  "guide_types": ["stadium_first_visit_tip", "stadium_bag_policy"],
  "top_k": 5
}
```

필드:

| 필드 | 필수 | 설명 |
|---|---:|---|
| `stadium_id` | 조건부 | 구장 ID. 없으면 team_id나 selected_game_id로 추론 |
| `team_id` | 선택 | 팀 context. 홈/원정 응원 안내에서 사용 |
| `query` | 필수 | 사용자 질문 |
| `guide_types` | 선택 | 문서 유형 filter |
| `top_k` | 선택 | 검색 결과 수. 기본 5 |

### 7.2 출력

```json
{
  "stadium_id": "SAJIK",
  "stadium_name": "부산 사직 야구장",
  "answerable": true,
  "items": [
    {
      "document_type": "stadium_first_visit_tip",
      "content": "검색된 근거 문단...",
      "similarity": 0.82,
      "source_title": "사직야구장 관람 안내",
      "source_url": "https://...",
      "as_of": "2026-07-28",
      "trust_level": "official"
    }
  ],
  "limitations": []
}
```

결과가 없으면 빈 성공으로 숨기지 않는다.

```json
{
  "stadium_id": "SAJIK",
  "stadium_name": "부산 사직 야구장",
  "answerable": false,
  "items": [],
  "limitations": ["no_relevant_stadium_guide_found"]
}
```

## 8. 검증 기준

첫 vertical slice 완료 기준:

- SAJIK, JAMSIL의 source registry가 있다.
- 각 구장에 최소 3개 document_type이 있다.
- raw와 normalized 문서가 모두 저장된다.
- chunk에 `stadium_id`, `document_type`, `source_url`, `as_of`가 있다.
- “사직구장 처음 가는데 뭐 챙겨야 해?” 질문에서 사직 문서만 검색된다.
- “잠실 원정석/입장/교통” 질문에서 잠실 문서만 검색된다.
- source URL과 기준 시점이 tool 결과에 포함된다.
- 공식 출처가 부족한 항목은 `curated`로 표시하고 한계를 남긴다.

## 9. 다음 작업

1. `source_registry.json` schema 정의
2. SAJIK, JAMSIL 공식 출처 후보 조사
3. raw 저장 포맷 샘플 작성
4. normalized 문서 schema 작성
5. RAG table migration 설계
6. `find_stadium_guide` 또는 `search_stadium_guide` 최종 Tool 이름 확정
