# 구장 가이드 데이터 범위 결정 메모

> 작성일: 2026-07-29  
> 목적: 구장 정보 수집을 이어갈 때 정형 테이블과 RAG 문서의 경계를 다시 확인하지 않도록 결정사항을 남긴다.

## 1. 현재 결정

구장별 정보는 구장마다 제공 방식과 상세도가 다르다.

따라서 `kbo_stadiums` 같은 정형 테이블에는 정말 필수적인 값만 넣고, 구장별 안내/정책/팁은 RAG 문서로 분리한다.

```text
정형 테이블
→ 구장 식별과 기본 위치 확인에 필요한 최소 정보

RAG 문서
→ 구장별로 내용 형식이 다르거나 설명이 필요한 정보
```

## 2. 정형 테이블에 남길 최소 후보

기존 `kbo_stadiums`에 이미 있는 값:

```text
id
name_ko
short_name
aliases
city
home_team_id
is_active
created_at
updated_at
```

추가를 검토할 최소 필드:

```text
region
address
latitude
longitude
is_dome
official_url
as_of
metadata jsonb
```

필드 기준:

| 필드 | 이유 |
|---|---|
| `region` | 도시보다 넓은 지역 구분이 필요할 수 있음 |
| `address` | 구장 위치 안내의 기본값 |
| `latitude` | 지도/거리/날씨 API 연결 시 필요 |
| `longitude` | 지도/거리/날씨 API 연결 시 필요 |
| `is_dome` | 우천/날씨 질문에서 결정론적으로 중요한 값 |
| `official_url` | 대표 공식 출처 링크 |
| `as_of` | 정형 정보 기준 시점 |
| `metadata jsonb` | 이후 확장용. 자주 filter할 값은 column으로 승격 |

## 3. 정형 테이블에서 제외할 후보

아래 값들은 당장은 정형 컬럼으로 만들지 않는다.

```text
capacity
opened_year
owner
parking_summary
nearest_transit_summary
entry_gate_summary
bag_policy_summary
facility_summary
food_or_store_summary
ticketing_summary
```

제외 이유:

- 출처마다 표현이 다르다.
- 구장마다 제공되는 정보 수준이 다르다.
- 시즌, 이벤트, 구단 정책에 따라 바뀔 수 있다.
- 사용자 답변에서는 출처와 기준 시점이 중요하다.
- 설명형 문서로 검색하는 편이 자연스럽다.

예외:

- `capacity`, `opened_year`, `owner`는 나중에 모든 구장에 공식 출처가 안정적으로 확보되면 정형 필드로 승격할 수 있다.
- 하지만 초기 vertical slice에서는 RAG 또는 `metadata` 후보로만 둔다.

## 4. RAG 문서로 분리할 정보

구장별 상세 안내는 RAG 문서로 관리한다.

초기 문서 유형 후보:

```text
stadium_entry_guide
stadium_bag_policy
stadium_facility_guide
stadium_transport_guide
stadium_first_visit_tip
stadium_weather_tip
stadium_ticketing_guide
stadium_seat_guide
```

RAG 문서가 가져야 할 핵심 metadata:

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
content_hash
metadata
```

검색 filter에서 중요한 값:

```text
stadium_id
team_id
document_type
source_type
as_of
trust_level
```

## 5. 출처 수집 방향

KBO 사이트 하나에서 구장별 상세 정보를 모두 가져오기는 어렵다.

출처는 다음처럼 역할별로 나눈다.

| 출처 유형 | 사용 정보 |
|---|---|
| `official_team` | 좌석, 티켓, 입장, 반입, 홈경기 운영 정책 |
| `official_venue_or_city` | 주소, 시설, 주차, 운영 주체 |
| `official_league` | 리그 공통 안전정책, 예매처 매핑 |
| `verified_partner` | 공식 예매처, 지도/공공 데이터 |
| `curated` | 공식 출처 기반 초행자 팁 요약 |
| `community_reference` | 아이디어 참고용. 사용자 답변 citation에는 사용하지 않음 |

## 6. 구장별 수집 방식

전체 구장을 한 번에 수집하지 않는다.

구장별 vertical slice로 진행한다.

```text
1. SAJIK 먼저 완료
2. SAJIK source registry 작성
3. SAJIK raw 저장
4. SAJIK normalized 문서 작성
5. SAJIK 기준으로 schema 문제 확인
6. 같은 패턴으로 JAMSIL 확장
```

초기 우선순위:

```text
1순위: SAJIK
2순위: JAMSIL
```

SAJIK에서 먼저 검증할 질문:

```text
사직구장 처음 가는데 뭐 챙겨야 해?
사직구장 가는 길과 주차는 어떻게 봐야 해?
사직구장 입장/반입 주의사항 알려줘
```

JAMSIL에서 나중에 검증할 질문:

```text
잠실 원정 가는데 어디로 들어가?
잠실 LG 경기와 두산 경기 안내가 달라?
잠실 교통/주차 정보 알려줘
```

## 7. 다음 작업

가장 먼저 할 일:

```text
data/raw/stadium_guide/source_registry.schema.json
data/raw/stadium_guide/source_registry.json
```

위 두 파일을 만들고, `SAJIK` 출처 후보부터 등록한다.

SAJIK 초기 출처 후보:

```text
롯데 자이언츠 공식 구장 안내
롯데 자이언츠 공식 좌석 안내
롯데 자이언츠 공식 요금/예매 안내
부산시 체육시설관리사업소 사직야구장 시설 안내
KBO 공통 안전정책
KBO 티켓/예매처 안내
```

이후 raw 저장:

```text
data/raw/stadium_guide/YYYY-MM-DD/SAJIK/
```

이후 normalized 저장:

```text
data/processed/stadium_guide/stadium_guide_documents.schema.json
data/processed/stadium_guide/stadium_guide_documents.json
```

## 8. 주의사항

- 구장별 정보 차이를 억지로 정형 컬럼에 맞추지 않는다.
- 공식 출처가 부족한 설명은 `curated`로 표시하고 한계를 남긴다.
- 실시간 값은 초기 수집 대상에서 제외한다.
- 좌석 잔여석, 당일 이벤트, 실시간 주차 가능 대수, 실시간 교통 상황, 날씨 예보는 별도 Tool 또는 외부 API 영역으로 둔다.

