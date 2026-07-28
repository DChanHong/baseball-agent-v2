# 구장 가이드 데이터 수집 다음 작업 메모

> 작성일: 2026-07-28  
> 목적: `find_stadium_guide` 계열 Tool로 넘어가기 전 필요한 구장 정보 수집 작업 정리

## 1. 현재 결정

구장 안내 Tool은 바로 하나의 RAG Tool로 만들지 않는다.

데이터 성격을 먼저 분리한다.

```text
get_stadium_info
```

- 정형 구장 프로필 조회
- 주소, 좌표, 홈팀, 공식 URL, 돔 여부, 수용 규모 등
- RAG를 사용하지 않는다.

```text
search_stadium_guide
```

- 설명형 구장 가이드 검색
- 입장, 반입, 편의시설, 주차, 대중교통, 초행 팁, 우천/돔 관람 팁
- RAG 후보

Agent에게 최종적으로 `find_stadium_guide` 하나로 노출할지, 내부 Tool을 둘로 나눌지는 evaluation 후 결정한다.

## 2. 참고 문서

```text
docs/planning/stadium-guide/001-data-collection.md
docs/backend/in-progress/rag-tool-development-plan.md
docs/planning/001-service-and-mvp.md
docs/backend/policy/conversation-entry-policy.md
```

## 3. 초기 수집 대상

전체 10개 구장을 한 번에 수집하지 않는다.

먼저 vertical slice로 2개 구장만 진행한다.

```text
1순위: SAJIK
2순위: JAMSIL
```

이유:

- 평가셋에 이미 “사직구장 처음 가는데 뭐 챙겨야 해?” 계열 질문이 있다.
- 잠실은 LG/DOOSAN 공동 홈이라 팀 context와 구장 context 분리를 검증하기 좋다.

## 4. 다음 작업 순서

### 4.1 source registry schema 정의

먼저 수집 대상 URL을 관리할 schema를 만든다.

추천 경로:

```text
data/raw/stadium_guide/source_registry.schema.json
data/raw/stadium_guide/source_registry.json
```

필수 필드 후보:

```text
source_id
source_type
title
url
stadium_id
team_id
document_types
collection_method
trust_level
refresh_policy
notes
```

### 4.2 SAJIK/JAMSIL 공식 출처 후보 조사

우선순위:

```text
official_league
official_team
official_venue_or_city
verified_partner
curated
```

`community_reference`는 아이디어 확인용으로만 사용하고 사용자 답변 citation에는 쓰지 않는다.

### 4.3 raw 저장 포맷 샘플 작성

추천 경로:

```text
data/raw/stadium_guide/
├── source_registry.json
└── YYYY-MM-DD/
    ├── SAJIK/
    │   ├── official_team_entry.html
    │   └── metadata.json
    └── JAMSIL/
        ├── official_team_entry.html
        └── metadata.json
```

raw metadata 필수 필드:

```text
source_id
source_url
source_type
stadium_id
team_id
collected_at
as_of
collector_version
http_status
content_hash
```

### 4.4 normalized 문서 schema 작성

추천 경로:

```text
data/processed/stadium_guide/stadium_guide_documents.schema.json
data/processed/stadium_guide/stadium_guide_documents.json
```

필수 필드 후보:

```text
document_id
document_type
title
stadium_id
team_id
source_type
source_url
source_file
as_of
trust_level
content
content_hash
metadata
```

### 4.5 RAG table migration 설계

정형 구장 프로필은 `kbo_stadiums` 확장을 검토한다.

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

설명형 문서는 `rag_documents`, `rag_chunks`에 저장한다.

## 5. 수집 제외

초기 구장 가이드 수집에서 제외한다.

```text
당일 티켓 잔여석
당일 이벤트
실시간 주차 가능 대수
실시간 교통 상황
날씨 예보
```

이 값들은 별도 Tool 또는 외부 API가 필요하다.

## 6. 완료 기준

첫 vertical slice 완료 조건:

- SAJIK, JAMSIL의 source registry가 있다.
- 각 구장에 최소 3개 `document_type`이 있다.
- raw와 normalized 문서가 모두 저장된다.
- chunk metadata에 `stadium_id`, `document_type`, `source_url`, `as_of`가 있다.
- “사직구장 처음 가는데 뭐 챙겨야 해?” 질문에서 사직 문서만 검색된다.
- “잠실 원정/입장/교통” 질문에서 잠실 문서만 검색된다.
- source URL과 기준 시점이 Tool 결과에 포함된다.
- 공식 출처가 부족한 항목은 `curated`로 표시하고 한계를 남긴다.
