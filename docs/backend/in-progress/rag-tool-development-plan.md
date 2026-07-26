# RAG 및 Tool 개발 진행 메모

> 상태: 진행 중
> 시작일: 2026-07-26
> 범위: pgvector 기반 설정, Tool 기획, 데이터 재수집, 임베딩, Tool별 검증

## 1. 작업 목적

RAG와 Agent 프레임워크를 한 번에 구현하지 않는다. Tool 하나의 목적과 계약을 먼저 정의하고, 그 Tool에 필요한 데이터를 다시 수집한 뒤, 검색 및 출력 품질을 개별적으로 검증한다.

검증을 통과한 Tool만 이후 Agent에 연결한다.

## 2. 확정된 전체 순서

```text
1. pgvector 기반 설정
2. 서비스 기획과 Tool 계약 재정의
3. Tool별 데이터 출처 선정
4. 크롤링 및 원본 데이터 재수집
5. 데이터 정규화와 청킹
6. Tool 목적에 맞는 embedding 생성
7. Retriever와 Tool 하나 구현
8. Tool 단위 실행 및 검색 품질 검증
9. 통과한 Tool만 Agent에 연결
```

각 단계를 완료하기 전에 다음 단계의 프레임워크를 미리 도입하지 않는다.

## 3. pgvector 초기 설정 범위

첫 번째 단계에서는 PostgreSQL의 `vector` extension만 활성화한다.

```text
지금 확정:
extensions.vector 활성화

Tool 기획 후 확정:
rag_documents schema
rag_chunks schema
metadata filter
검색 함수 입력과 출력
청킹 규칙
embedding version 정책
```

Tool 계약을 정하기 전에 RAG 테이블 전체를 만들지 않는다. 필요한 filter와 출처 필드가 확정되지 않은 상태에서 table을 만들면 불필요한 migration이 반복될 수 있기 때문이다.

첫 명령:

```bash
supabase migration new enable_pgvector
```

예정 SQL:

```sql
create extension if not exists vector
with schema extensions;
```

적용:

```bash
supabase migration up
```

확인 항목:

- migration 적용 성공
- `extensions.vector` 사용 가능
- local DB reset 후에도 extension 재현 가능

## 4. Tool 분류 원칙

모든 데이터를 embedding으로 처리하지 않는다.

### 4.1 정형 데이터 Tool

정확한 조건 조회와 계산이 필요한 데이터는 관계형 DB 또는 외부 API를 사용한다.

초기 후보:

```text
find_kbo_game
get_stadium_info
get_weather_context
score_seat_candidates
```

예:

- 경기 일정
- 팀과 구장 ID
- 경기 시작 시각
- 날씨 수치
- 좌석 가격
- 결정론적 좌석 점수

### 4.2 RAG Tool

문서의 설명과 근거가 필요한 정보만 embedding 검색을 사용한다.

초기 후보:

```text
search_stadium_seat_knowledge
get_ticketing_guide
get_logistics_guide
```

예:

- 좌석 시야와 응원 분위기
- 구역별 장단점
- 예매 방법과 주의사항
- 입장과 현장 발권 안내
- 원정 이동과 편의시설 안내

## 5. Tool 계약 작성 항목

각 Tool은 구현 전에 다음 내용을 문서로 확정한다.

| 항목 | 설명 |
|---|---|
| 이름 | Agent와 코드에서 사용할 고정 Tool 이름 |
| 책임 | Tool이 해결하는 단일 문제 |
| 호출 조건 | 어떤 사용자 질문에서 호출하는지 |
| 입력 Schema | 필수값, 선택값, 타입, 제약조건 |
| 출력 Schema | 성공 데이터, 출처, 한계, 상태 |
| 데이터 출처 | 공식 사이트, 공공 데이터, curated 문서 |
| 신뢰 등급 | 공식, 검증된 수집, 수동 작성 등 |
| metadata filter | team, stadium, document type, 기준 시점 등 |
| 결과 없음 | no-result 처리와 사용자 안내 |
| 오류 정책 | timeout, retry, 오류 코드, fallback |
| citation | 답변에 표시할 출처 필드 |
| 테스트 사례 | 정상, 입력 부족, 결과 없음, 오래된 정보 |
| 완료 조건 | 다음 Tool로 넘어갈 수 있는 기준 |

## 6. 데이터 수집 원칙

Tool 계약이 확정된 후 그 Tool에 필요한 데이터만 수집한다.

```text
출처 선정
→ 크롤링
→ raw 원본 보존
→ normalized 데이터 생성
→ content hash 계산
→ chunk 생성
→ embedding
→ DB 저장
→ 검증
```

### 6.1 Raw 데이터

```text
data/raw/
```

원본 응답이나 원문을 수정하지 않고 저장한다.

함께 기록할 정보:

- source URL
- 수집 시각
- 데이터 기준 시점
- 출처 유형
- 요청 조건
- 크롤러 버전
- 응답 상태

### 6.2 Normalized 데이터

```text
data/normalized/
```

애플리케이션과 Tool 계약에 맞는 표준 필드로 변환한다.

정규화 단계에서 처리할 항목:

- 팀과 구장 식별자 통일
- 날짜와 시간대 통일
- 중복 제거
- HTML과 불필요한 문구 제거
- 출처와 기준 시점 유지
- 필수 필드 누락 검증

## 7. Tool별 수직 개발 흐름

하나의 Tool을 다음 순서로 끝까지 완성한다.

```text
Tool 기획
→ 입력과 출력 계약
→ 출처 선정
→ 크롤링
→ 정규화
→ chunk 규칙
→ embedding
→ Retriever
→ Tool 구현
→ 대표 질문 실행
→ 검색 결과와 citation 검증
→ 완료 판정
```

여러 Tool의 크롤러나 embedding을 동시에 만들지 않는다.

## 8. RAG 문서 metadata 후보

Tool 계약을 작성하면서 다음 후보 중 실제 filter에 필요한 필드를 일반 column으로 확정한다.

```text
document_type
team_id
stadium_id
source_type
source_url
source_file
as_of
trust_level
embedding_model
embedding_dimensions
embedding_version
```

자주 filter하거나 정렬하는 값은 JSONB에만 넣지 않는다. 확장 정보만 `metadata jsonb`에 저장한다.

## 9. 초기 RAG 검색 정책

현재 결정:

```text
Vector Store: Supabase PostgreSQL + pgvector
Embedding model: text-embedding-3-small
Embedding dimensions: 1536
Similarity: cosine
Distance operator: <=>
초기 검색: exact search
```

초기 데이터가 적을 때는 HNSW index를 만들지 않는다. exact search로 품질 baseline을 먼저 측정한 후 데이터와 latency가 증가했을 때 HNSW를 적용한다.

## 10. Tool 검증 기준

Tool 하나를 완료했다고 판단하려면 다음 항목을 확인한다.

- 입력 Schema가 잘못된 값을 거부한다.
- 정상 질문에서 기대한 데이터 또는 chunk가 검색된다.
- 다른 팀이나 구장의 문서가 섞이지 않는다.
- 결과에 source URL과 기준 시점이 포함된다.
- 결과가 없을 때 빈 성공으로 숨기지 않는다.
- 오래된 정보는 기준 시점 또는 한계를 표시한다.
- 사용자 입력을 SQL 문자열로 직접 조립하지 않는다.
- Tool 출력만으로 답변 근거를 추적할 수 있다.
- 대표 질문과 실패 질문의 실행 결과를 기록한다.

RAG Tool에는 추가로 다음 검색 지표를 기록한다.

```text
Recall@k
MRR
검색 latency
threshold별 no-result 비율
metadata filter 정확성
```

## 11. 초기에는 하지 않을 작업

- LangChain 또는 LangGraph Agent 연결
- Hybrid search
- Reranker
- HNSW tuning
- 자동 embedding trigger
- 다중 embedding model 동시 검색
- 사용자별 private RAG
- 사용자 로그인과 RAG 권한 연결
- 모든 문서를 한 번에 수집하고 embedding

이 항목들은 Tool 단위 검색 품질이 검증된 후 검토한다.

## 12. 예상 Tool 개발 순서

기획 단계에서 변경할 수 있으며, 한 번에 하나만 선택한다.

```text
1. find_kbo_game
2. get_stadium_info
3. search_stadium_seat_knowledge
4. get_ticketing_guide
5. get_logistics_guide
6. get_weather_context
7. score_seat_candidates
```

정형 데이터 Tool과 RAG Tool을 명확히 분리하고, Agent는 검증된 Tool을 조율하는 역할만 담당한다.

## 13. 바로 다음 작업

1. `enable_pgvector` migration 생성
2. vector extension 활성화
3. local Supabase에 migration 적용
4. extension 확인
5. 코드 구현을 잠시 멈추고 Tool 기획 문서 작성
6. 첫 번째 Tool과 필요한 데이터 출처 확정

현재 바로 실행할 첫 명령:

```bash
supabase migration new enable_pgvector
```

## 14. 진행 기록

| 날짜 | 작업 | 상태 | 비고 |
|---|---|---|---|
| 2026-07-26 | RAG 및 Tool 개발 순서 합의 | 완료 | Tool별 수직 개발 방식 |
| 2026-07-26 | pgvector extension migration | 예정 | extension만 먼저 활성화 |
| 2026-07-26 | Tool 계약 재정의 | 예정 | pgvector 활성화 후 진행 |
