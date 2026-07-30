# 구장 가이드 RAG 다음 작업 메모

> 작성일: 2026-07-29  
> 목적: 구장 가이드 비정형 데이터 수집을 다음 세션에서 이어갈 때 현재 위치와 남은 작업을 바로 파악하기 위함.

## 1. 현재 결정

구장 가이드 비정형 데이터는 Supabase DB에 바로 넣지 않고, 먼저 repo 내부 JSON/HTML snapshot으로 관리한다.

```text
data/stadium_guide/
```

현재 기준은 다음과 같다.

```text
공식 출처가 확인된 데이터만 유지한다.
출처가 약하거나 추론이 많이 섞인 문서는 제외한다.
블로그/커뮤니티는 초기 RAG citation에 사용하지 않는다.
```

## 2. 현재 데이터 위치

source registry:

```text
data/stadium_guide/sources.json
```

수집 요약 문서:

```text
data/stadium_guide/collection_summary.md
```

raw HTML snapshot:

```text
data/stadium_guide/raw/2026-07-29/{STADIUM_ID}/
```

normalized RAG 후보 문서:

```text
data/stadium_guide/normalized/{STADIUM_ID}/
```

구장별 raw metadata:

```text
data/stadium_guide/raw/2026-07-29/{STADIUM_ID}/metadata.json
```

## 3. 현재 유지 중인 구장

현재 normalized 문서가 유지되는 구장은 7개다.

```text
SAJIK
GOCHEOK
MUNHAK
GWANGJU
DAEGU
SUWON
DAEJEON
```

문서 수:

```text
총 35개 normalized JSON
```

대략적인 상태:

| stadium_id | 상태 |
|---|---|
| `SAJIK` | 가장 완성도 높은 vertical slice |
| `GOCHEOK` | 좌석/티켓/교통/반입/시설 출처가 비교적 좋음 |
| `MUNHAK` | 홈구장 안내 품질 좋음. 교통/주차는 제외 |
| `GWANGJU` | 구장/교통/티켓 중심으로 유지 |
| `DAEGU` | 좌석/티켓/환불 중심으로 유지 |
| `SUWON` | 주차예약/구장/티켓 출처가 비교적 좋음 |
| `DAEJEON` | 좌석/시설/주소 중심으로 유지. 티켓/교통 상세는 추가 검수 필요 |

자세한 현재 상태는 아래 파일을 먼저 확인한다.

```text
data/stadium_guide/collection_summary.md
```

## 4. 남은 구장 수집 작업

아래 구장은 아직 normalized 문서를 유지하지 않는다.

```text
JAMSIL
CHANGWON
```

### 4.1 JAMSIL

홈팀:

```text
LG
DOOSAN
```

보류 이유:

- LG/두산 공동 홈이라 홈팀별 정책 분리가 필요하다.
- 두산 상세 티켓/좌석 공식 출처가 부족하다.
- 잠실은 구장 공통 정보와 홈팀별 티켓/응원/입장 정보가 섞이면 답변 품질이 떨어진다.

다음에 찾아야 할 출처:

```text
서울시 체육시설관리사업소 잠실야구장 세부 안내
LG 트윈스 공식 티켓/좌석/입장 안내
두산 베어스 공식 티켓/좌석/입장 안내
홈팀별 원정석/응원석 안내
```

### 4.2 CHANGWON

홈팀:

```text
NC
```

보류 이유:

- NC 공식 구장/티켓/좌석 최신 페이지가 충분히 확보되지 않았다.
- 다이노스몰 후보 출처는 fetch timeout이 발생했다.
- 창원NC파크는 운영 상태/안전점검 관련 이슈가 있어 최신 공식 공지 확인이 중요하다.

다음에 찾아야 할 출처:

```text
NC 공식 티켓/좌석 안내
창원NC파크 공식 시설/교통/주차 안내
NC 공식 최신 운영 상태 공지
다이노스몰/매장 안내의 현재 운영 출처
```

### 4.3 DAEJEON

홈팀:

```text
HANWHA
```

수집 상태:

- 2026-07-30 기준 공식 출처 기반 normalized 5개 문서 생성 완료.
- 한화 공식 페이지는 브라우저 기준으로 좌석, 시설, 주소, 대표 전화 정보를 확인했다.
- 한화 공식 페이지 raw fetch는 일부 `{}`
  또는 `{"user":null}` 수준으로만 저장되어 raw snapshot 단독 재현성은 약하다.

추가 보강 후보:

```text
티켓/좌석 세부 수동 검수
입장/GATE/반입 세부 안내
버스, 지하철, 주차 가능 대수, 주차 요금 공식 출처
```

### 4.4 POHANG

홈팀:

```text
SAMSUNG 보조 구장
```

초기 수집 대상 제외 이유:

- 정규 홈구장 중심 RAG 초기 수집 범위에서 보조 구장은 제외한다.
- 삼성 공식 티켓 페이지에 포항경기 요금표는 있으나, 포항야구장 자체 시설/교통/주차 공식 출처가 부족하다.
- 보조 구장이라 경기 편성 시점의 삼성 공지가 중요하다.

향후 검토 조건:

```text
포항시 또는 포항시시설관리공단 포항야구장 전용 시설 안내
삼성 라이온즈 포항경기 운영 공지
포항경기 교통/주차/입장 안내
```

## 5. 수집 방식

새 구장을 추가할 때는 아래 순서로 진행한다.

```text
1. 공식 출처 URL 확인
2. data/stadium_guide/sources.json에 source 등록
3. raw HTML snapshot 저장
4. raw metadata.json에 source_url, local_file, content_hash 기록
5. normalized/{STADIUM_ID}/ 문서 작성
6. collection_summary.md 갱신
```

normalized 문서 유형은 초기에는 아래 5개를 우선 지원한다.

```text
stadium_bag_policy
stadium_facility_guide
stadium_seat_guide
stadium_ticketing_guide
stadium_transport_guide
```

아래 3개는 현재 normalized 문서로 만들지 않고, 추후 공식 출처와 질문 수요가 충분할 때 보강한다.

```text
stadium_entry_guide
stadium_first_visit_tip
stadium_weather_tip
```

단, 출처가 부족하면 문서를 만들지 않는다.

```text
없는 정보를 채우기 위해 추론하지 않는다.
공통 KBO 정책만으로 구장별 문서를 억지 생성하지 않는다.
```

## 6. 임베딩 전 해야 할 일

현재 normalized JSON은 RAG 후보 문서이지만, 아직 embedding 입력 포맷으로 확정된 것은 아니다.

임베딩 전에 필요한 작업:

```text
1. normalized document schema 확정
2. review_status 기준 정의
3. needs_review 문서 검수
4. approved 문서만 chunk 대상에 포함
5. chunk metadata 필드 확정
```

권장 normalized schema:

```text
document_id
document_type
stadium_id
team_id
title
as_of
trust_level
review_status
sources
content
metadata
```

권장 chunk metadata:

```text
chunk_id
document_id
document_type
stadium_id
team_id
source_ids
source_urls
as_of
trust_level
review_status
chunk_index
content_hash
```

## 7. 임베딩 방식 후보

초기에는 DB에 바로 넣기보다 로컬 JSONL을 먼저 만든다.

추천 경로:

```text
data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
```

흐름:

```text
normalized JSON
→ approved 문서 필터링
→ content chunking
→ chunk JSONL 생성
→ embedding 생성
→ Supabase pgvector 또는 별도 vector store에 upsert
```

chunking 기본안:

```text
문서 하나를 500~800 token 기준으로 분할
짧은 문서는 1 chunk 유지
chunk마다 stadium_id/document_type/source_urls 포함
```

검색 filter에서 중요한 값:

```text
stadium_id
team_id
document_type
trust_level
review_status
as_of
```

## 8. Supabase 반영 방향

Supabase 무료 티어 제약이 있으므로, 원본 HTML과 normalized JSON은 repo에 유지한다.

Supabase에는 최소한만 넣는 방향이 좋다.

```text
rag_documents
rag_chunks
```

저장 후보:

```text
rag_documents:
- document_id
- document_type
- stadium_id
- team_id
- title
- content_hash
- as_of
- trust_level
- review_status
- source_urls
- metadata

rag_chunks:
- chunk_id
- document_id
- stadium_id
- team_id
- document_type
- chunk_text
- embedding
- metadata
```

원본 raw HTML은 Supabase Storage에 올리지 않고 repo 파일로 유지한다.

## 9. 다음 세션 시작 체크리스트

다음에 이어서 작업할 때는 먼저 아래를 확인한다.

```text
git status --short
data/stadium_guide/collection_summary.md
data/stadium_guide/sources.json
find data/stadium_guide/normalized -mindepth 2 -maxdepth 2 -name '*.json'
```

그 다음 우선순위:

```text
1. 남은 구장 중 JAMSIL 공식 출처 재조사
2. JAMSIL을 LG/DOOSAN 홈팀별로 분리할지 결정
3. CHANGWON 최신 운영/티켓 공식 출처 확인
4. approved 문서 검수 기준 작성
5. chunk JSONL 생성 스크립트 작성
```
