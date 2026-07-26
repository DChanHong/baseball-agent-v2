# ADR-001: Vector Store로 Supabase PostgreSQL + pgvector 사용

- 상태: 채택
- 결정일: 2026-07-26
- 적용 범위: RAG 문서 저장, embedding 저장, 유사도 검색, 검색 metadata filter

## 1. 배경

기존 프로젝트는 로컬 FAISS index 파일을 생성하고 애플리케이션 실행 시 이를 로드했다. 새 프로젝트에서는 일반 관계형 데이터와 RAG 데이터를 하나의 관리형 PostgreSQL에서 운영하고, 배포 환경에서도 인덱스를 공유하기 위해 Supabase PostgreSQL의 `pgvector` 확장을 사용한다.

이 변경은 FAISS 호출부만 교체하는 작업이 아니다. 다음 항목을 프로젝트 시작 전에 고정해야 한다.

- embedding model과 vector 차원
- 유사도 기준과 vector index
- 문서·청크 schema
- metadata filter 방식
- 검색 SQL 함수 계약
- migration과 seed 관리 방식
- FastAPI와 Supabase의 연결 방식
- RLS와 secret 관리
- 재색인 및 embedding model 교체 전략

## 2. 결정

### 2.1 저장소

- RAG Vector Store는 Supabase PostgreSQL의 `pgvector`를 사용한다.
- FAISS는 production 및 기본 개발 경로에서 사용하지 않는다.
- 단위 테스트에서는 실제 Supabase 대신 Fake Retriever를 사용할 수 있다.
- 통합 테스트에서는 Supabase CLI로 실행한 local PostgreSQL + pgvector를 사용한다.

### 2.2 Embedding

- 초기 모델: OpenAI `text-embedding-3-small`
- 초기 차원: `1536`
- embedding column: `extensions.vector(1536)`
- 유사도: cosine distance
- 거리 연산자: `<=>`
- index operator class: `vector_cosine_ops`

기존 프로젝트와 같은 embedding model을 사용해 데이터 비교와 이전 경험 활용이 쉽다. 서로 다른 embedding model의 vector는 의미 있게 비교할 수 없으므로, 각 청크에 `embedding_model`과 `embedding_dimensions`를 저장한다.

모델 또는 차원을 변경할 때 기존 column에 혼합 저장하지 않는다. 새 embedding version을 생성하고 전체 재색인한 뒤 검색 대상을 전환한다.

### 2.3 Vector index

- 초기 데이터가 적을 때는 exact search로 검색 품질 baseline을 먼저 측정한다.
- 데이터 증가 후 HNSW index를 적용한다.
- HNSW를 기본으로 선택하고 IVFFlat은 초기 범위에서 사용하지 않는다.
- index와 검색 함수는 모두 cosine 기준을 사용한다.

```sql
create index rag_chunks_embedding_hnsw_idx
on public.rag_chunks
using hnsw (embedding vector_cosine_ops);
```

HNSW 적용 전후에 Recall@k와 latency를 비교한다. index가 사용하는 operator class와 검색 SQL의 연산자가 다르면 index가 사용되지 않을 수 있으므로 둘을 함께 변경한다.

## 3. Database schema

### 3.1 `rag_documents`

원본 문서 단위의 출처와 수명 주기를 관리한다.

| column | type | 설명 |
|---|---|---|
| `id` | uuid PK | 문서 ID |
| `document_type` | text | `stadium_seat`, `ticketing_guide`, `logistics_guide` |
| `title` | text | 문서 제목 |
| `source_type` | text | official, crawled, curated 등 |
| `source_url` | text nullable | 원문 URL |
| `source_file` | text nullable | 로컬 원본 경로 |
| `stadium_id` | text nullable | 구장 filter |
| `team_id` | text nullable | 팀 filter |
| `as_of` | timestamptz | 정보 기준 시점 |
| `trust_level` | text | 출처 신뢰 등급 |
| `content_hash` | text unique | 중복 및 변경 탐지 |
| `metadata` | jsonb | 비핵심 확장 metadata |
| `created_at` | timestamptz | 생성 시각 |
| `updated_at` | timestamptz | 변경 시각 |

자주 filter하는 `document_type`, `stadium_id`, `team_id`, `as_of`, `trust_level`은 JSONB 안에만 넣지 않고 일반 column으로 둔다.

### 3.2 `rag_chunks`

검색 단위와 embedding을 관리한다.

| column | type | 설명 |
|---|---|---|
| `id` | uuid PK | 청크 ID |
| `document_id` | uuid FK | `rag_documents.id` |
| `chunk_index` | integer | 문서 내 순번 |
| `content` | text | 검색 및 인용할 본문 |
| `token_count` | integer nullable | 청크 크기 |
| `content_hash` | text | 청크 변경 탐지 |
| `embedding` | vector(1536) | embedding |
| `embedding_model` | text | 생성 모델 |
| `embedding_dimensions` | integer | vector 차원 |
| `embedding_version` | integer | 재색인 버전 |
| `metadata` | jsonb | 청크 확장 metadata |
| `created_at` | timestamptz | 생성 시각 |

권장 제약:

- `unique(document_id, chunk_index, embedding_version)`
- `embedding_dimensions = 1536`
- 문서 삭제 시 청크 cascade 삭제
- `document_id`, `embedding_version` B-tree index

## 4. 검색 함수 계약

PostgREST는 pgvector 유사도 연산자를 직접 표현하는 용도에 적합하지 않으므로 검색 로직은 PostgreSQL 함수로 고정한다.

초기 함수:

```text
match_rag_chunks(
  query_embedding,
  match_count,
  match_threshold,
  filter_document_type,
  filter_stadium_id,
  filter_team_id,
  filter_embedding_version
)
```

반환 필드:

```text
chunk_id
document_id
content
similarity
document_type
stadium_id
team_id
source_type
source_url
source_file
as_of
trust_level
metadata
```

검색 규칙:

1. 구조화 filter를 먼저 적용한다.
2. `1 - (embedding <=> query_embedding)`을 similarity로 반환한다.
3. threshold와 top-k는 코드에 숨기지 않고 설정값으로 관리한다.
4. 정렬식은 계산된 alias가 아니라 vector distance 연산을 직접 사용한다.
5. `match_count`에는 SQL 함수 내부 상한을 둔다.
6. 오래된 문서는 필요 시 제외하거나 freshness penalty를 적용한다.

FastAPI의 `PgVectorRetriever` adapter가 이 함수를 호출하고, application/agent 계층에는 공통 `RetrievedChunk` 모델만 반환한다.

## 5. 애플리케이션 연결 방식

### 5.1 Backend

- FastAPI는 SQLAlchemy 2.x async + asyncpg로 Supabase PostgreSQL에 연결한다.
- similarity search는 parameterized SQL로 `match_rag_chunks` 함수를 호출한다.
- Repository와 Retriever Protocol을 두어 Supabase 세부 구현이 domain/application 계층으로 새지 않게 한다.
- 일반 KBO 데이터와 RAG 데이터는 같은 PostgreSQL을 사용하되 repository를 분리한다.

### 5.2 Frontend

- 프론트엔드는 vector table이나 검색 RPC를 직접 호출하지 않는다.
- 모든 RAG 검색은 FastAPI를 거친다.
- 브라우저에는 Supabase secret/service role key와 DB password를 절대 전달하지 않는다.
- 추후 Supabase Auth를 도입하더라도 사용자 JWT만 FastAPI에 전달한다.

## 6. Migration과 local development

스키마 변경의 단일 기준은 Supabase CLI SQL migration으로 한다.

```text
supabase/
├── config.toml
├── migrations/
└── seed.sql
```

원칙:

- Supabase schema에는 Alembic을 병행하지 않는다.
- Dashboard에서 production schema를 직접 수정하지 않는다.
- `supabase migration new`로 migration을 만든다.
- local에서 `supabase db reset`으로 전체 migration과 seed 재현을 검증한다.
- remote 반영 전 `supabase db push --dry-run`을 확인한다.
- production에는 개발 seed를 적용하지 않는다.

첫 migration 범위:

1. `vector` extension 활성화
2. 관계형 도메인 table
3. `rag_documents`, `rag_chunks`
4. 제약과 B-tree index
5. `match_rag_chunks` 함수
6. RLS와 권한
7. 데이터 증가 후 HNSW index

## 7. RLS와 보안

- exposed schema의 table에는 RLS를 활성화한다.
- RAG table은 브라우저에서 직접 읽지 못하게 한다.
- backend DB 자격 증명 또는 Supabase secret key는 server environment에만 둔다.
- 관리용 ingestion/reindex 권한과 검색 권한을 분리한다.
- 검색 함수에는 `search_path`를 명시하고 동적 SQL을 피한다.
- 사용자 입력을 SQL 문자열로 조립하지 않고 parameter binding한다.
- 원문에 prompt injection 문장이 있어도 metadata와 content로만 취급한다.
- 로그에는 DB URL, secret key, 원문 embedding을 기록하지 않는다.

## 8. Ingestion과 재색인

```text
원본 수집
→ 정규화
→ 문서 content_hash 계산
→ chunk 생성
→ chunk content_hash 계산
→ embedding batch 생성
→ transaction/upsert
→ 검증
→ embedding_version 활성화
```

정책:

- 변경되지 않은 `content_hash`는 embedding을 다시 만들지 않는다.
- 문서 단위 transaction으로 partial write를 줄인다.
- batch 크기와 retry는 설정으로 관리한다.
- 실패 row는 별도 리포트로 남기고 전체 성공으로 숨기지 않는다.
- 재색인 중 기존 version을 계속 검색하고, 새 version 검증 후 전환한다.
- 삭제된 원문은 soft delete 또는 명시적 cleanup 정책으로 처리한다.

필요 script:

- `scripts/import_documents.py`
- `scripts/chunk_documents.py`
- `scripts/embed_chunks.py`
- `scripts/evaluate_retrieval.py`
- `scripts/reindex.py`

## 9. 평가와 운영

초기 평가:

- exact search 기준 Recall@5, MRR
- HNSW 적용 후 Recall@5 변화
- query p50/p95 latency
- metadata filter별 결과 수
- threshold별 no-result 비율
- 문서 유형별 검색 품질

관측 metadata:

- query hash
- filter
- top-k와 threshold
- 반환 chunk ID
- similarity
- embedding model/version
- DB/RPC latency
- fallback 여부

사용자 원문 query와 검색 문서 전문은 기본 trace에 저장하지 않는다.

## 10. FAISS 방식과 달라지는 점

| 항목 | 기존 FAISS | 새 Supabase pgvector |
|---|---|---|
| 저장 위치 | 로컬 index 파일 | 관리형 PostgreSQL |
| 동시 접근 | 프로세스/파일 단위 | 여러 backend instance 공유 |
| metadata | Vector Store metadata | 관계형 column + JSONB |
| 변경 반영 | index 재생성/교체 | transaction, upsert, version 전환 |
| 검색 | Python retriever | PostgreSQL 함수/RPC |
| filter | 애플리케이션/FAISS 제약 | SQL 조건 |
| 배포 | index artifact 필요 | migration + ingestion 필요 |
| 보안 | 파일 접근 통제 | RLS, role, secret 관리 |
| 백업 | index 파일 관리 | Supabase DB 백업 정책 |
| 테스트 | 로컬 파일 | Fake unit + local Supabase integration |

## 11. 초기에는 하지 않을 것

- hybrid search
- reranker
- 자동 embedding trigger/queue
- Edge Function 기반 embedding
- 다중 embedding model 동시 검색
- 사용자별 private RAG
- IVFFlat tuning

이 항목들은 semantic search baseline과 평가 결과가 나온 뒤 도입한다. KBO 구장명, 좌석명처럼 정확한 키워드가 중요한 질의에서 semantic-only 한계가 측정되면 PostgreSQL full-text search와 RRF를 이용한 hybrid search를 다음 개선으로 검토한다.

## 12. 완료 조건

- local Supabase를 migration과 seed만으로 재구성할 수 있다.
- `vector(1536)` 차원과 embedding model이 일치한다.
- 문서 import를 반복해도 중복 청크가 생기지 않는다.
- metadata filter와 cosine search 통합 테스트가 통과한다.
- exact search baseline이 기록되어 있다.
- HNSW 적용 시 품질과 latency 변화가 기록되어 있다.
- FastAPI 외부에서 secret key가 노출되지 않는다.
- FAISS 파일 없이 개발·테스트·배포할 수 있다.

