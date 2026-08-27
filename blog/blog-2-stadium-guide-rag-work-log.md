# 2026-07-30 작업 로그: 사직구장 RAG 임베딩 첫 실험

> 상태: 첫 vertical slice 기록, 현재 확장 상태 보강
> 최근 업데이트: 2026-08-27

## 오늘의 목표

사직구장(`SAJIK`) 구장 가이드 문서를 최소 단위로 임베딩하고, Supabase local PostgreSQL + pgvector에서 검색 품질을 확인할 수 있는 기반을 만든다.

## 왜 이 작업을 하는가

경기 일정 조회는 정형 DB로 처리할 수 있지만, 구장별 입장, 반입, 교통, 좌석, 티켓 안내는 출처와 형식이 제각각이다.

그래서 `kbo_stadiums` 같은 정형 테이블에는 최소 필드만 두고, 구장별 안내 문서는 RAG 대상으로 분리하기로 했다. 이번 작업은 그 첫 번째 실험으로 `SAJIK`만 대상으로 삼았다.

현재는 이 첫 실험을 바탕으로 normalized 문서가 9개 구장 45개 문서까지 확장됐고, `stadium_guide_chunks.jsonl`도 45개 chunk 기준으로 생성되어 있다. 그래도 이 글은 의도적으로 SAJIK 5문서만 다룬 첫 폐루프 실험 기록으로 남긴다.

## 현재 결정

- 전체 구장을 한 번에 임베딩하지 않는다.
- 첫 실험은 `SAJIK` normalized 문서 5개만 대상으로 한다.
- `text-embedding-3-small`, 1536 dimensions를 사용한다.
- 문서 1개를 chunk 1개로 두는 baseline에서 시작한다.
- `source_urls`는 chunk JSONL과 DB에 저장한다.
- `metadata.source_file`은 JSONL에는 남기고, DB upsert 시에는 제외한다.
- Hybrid Search, Re-ranking, HNSW index, Agent 연결은 아직 하지 않는다.

## 데이터 구조 정리

`data/` 폴더를 도메인 중심으로 재구성했다.

```text
data/
├── kbo_schedule/
│   ├── raw/
│   ├── processed/
│   └── evaluation/
└── stadium_guide/
    ├── sources.json
    ├── collection_summary.md
    ├── raw/
    ├── normalized/
    ├── embedded_input/
    └── evaluation/
```

이제 구장 가이드 검색 평가셋은 아래에 있다.

```text
data/stadium_guide/evaluation/cases/sajik_search_cases.jsonl
```

## 만든 것

### pgvector extension migration

```text
supabase/migrations/20260730043500_enable_vector_extension.sql
```

역할:

```sql
create extension if not exists vector with schema extensions;
```

로컬 DB에서 `vector 0.8.2` 활성화를 확인했다.

### RAG 테이블 migration

```text
supabase/migrations/20260730044000_create_rag_document_chunk_tables.sql
```

생성 테이블:

```text
public.rag_documents
public.rag_chunks
```

핵심 컬럼:

```text
stadium_id
team_id
document_type
review_status
trust_level
as_of
source_ids
source_urls
embedding extensions.vector(1536)
```

### chunk JSONL 생성 스크립트

```text
backend/scripts/generate_stadium_guide_chunks.py
```

입력:

```text
data/stadium_guide/normalized/SAJIK/*.json
data/stadium_guide/sources.json
```

출력:

```text
data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
```

현재 생성된 chunk:

```text
SAJIK_stadium_bag_policy_20260729_chunk_000
SAJIK_stadium_facility_guide_20260729_chunk_000
SAJIK_stadium_seat_guide_20260729_chunk_000
SAJIK_stadium_ticketing_guide_20260729_chunk_000
SAJIK_stadium_transport_guide_20260729_chunk_000
```

### embedding + upsert 스크립트

```text
backend/scripts/embed_stadium_guide_chunks.py
```

역할:

```text
chunk JSONL 읽기
→ embedding_text를 OpenAI embedding으로 변환
→ rag_documents / rag_chunks에 upsert
```

실행 결과:

```text
Loaded 5 chunks
Upserted 5 chunks into rag_documents/rag_chunks
```

DB 확인:

```text
rag_documents: 5
rag_chunks: 5
embedding_model: text-embedding-3-small
embedding_dimensions: 1536
metadata.source_file: DB에서는 제외됨
```

### 검색 평가셋

```text
data/stadium_guide/evaluation/cases/sajik_search_cases.jsonl
```

구성:

```text
총 15개
positive 12개
negative 3개
```

positive 예:

```text
사직구장 지하철로 어떻게 가? → stadium_transport_guide
사직구장 반입 금지 물품 알려줘 → stadium_bag_policy
롯데 홈경기 예매는 어디서 해? → stadium_ticketing_guide
```

교통 검색 품질을 더 보기 위해 아래 질문을 추가했다.

```text
사직야구장 몇 호선 타고 가?
사직구장 가까운 지하철역 어디야?
사직구장 버스로 가는 법 알려줘
사직구장 주차 가능해?
사직야구장 대중교통 추천해줘
```

### 검색 평가 스크립트

```text
backend/scripts/evaluate_stadium_guide_retrieval.py
```

의도:

```text
평가 질문을 embedding
→ public.rag_chunks에서 stadium_id filter로 검색
→ Top-1 / Top-3 hit 계산
→ data/stadium_guide/evaluation/runs/에 결과 JSON 저장
```

실행 중 각 질문별 로그를 출력하도록 구성했다.

추가로 `relevance_threshold`를 기록하도록 했다. 검색 결과를 무조건 답변에 쓰기보다, 거리값이 너무 큰 경우에는 "관련 문서 없음"으로 판단할 후보 기준을 만들기 위해서다.

## 중간에 막힌 점

검색 평가 스크립트 실행 시 로컬 DB 연결에서 timeout이 발생했다. 처음에는 스크립트 문제처럼 보였지만, `docker ps`도 실패했기 때문에 원인은 Docker Desktop 또는 Supabase local container 상태 문제로 좁혀졌다.

```text
DB 연결 실패: 로컬 Supabase PostgreSQL 연결 시간이 초과되었습니다.
docker ps: request returned Internal Server Error ...
```

해결 방향은 코드 수정이 아니라 Docker Desktop 재시작이었다. 이후 PostgreSQL 포트가 다시 응답했고, 평가 스크립트가 정상 실행됐다.

그래도 스크립트에는 디버깅 로그를 추가했다.

```text
env 파일 로드
OPENAI_API_KEY 존재 확인
DATABASE_URL 마스킹 출력
OpenAI client 객체 생성 로그
DB 연결 시도/성공 로그
OpenAI embedding 요청/응답 로그
질문별 Top-K 검색 결과 로그
```

중요한 점은 OpenAI client 객체 생성은 네트워크 호출이 아니라는 것이다. 실제 API 호출은 `client.embeddings.create(...)`에서 발생한다.

## 첫 평가 결과

처음 10개 케이스로 돌린 baseline 결과는 다음과 같았다.

```text
positive_cases: 7
top1_accuracy: 0.8571
top3_accuracy: 1.0
failed_top1_case_ids: sajik_001
```

실패 케이스:

```text
질문: 사직구장 지하철로 어떻게 가?
기대 문서: stadium_transport_guide
실제 1등: stadium_facility_guide
실제 2등: stadium_transport_guide
```

정답 문서가 Top-3 안에는 있었지만, 시설 안내가 교통 안내보다 더 가깝게 잡혔다. 이 결과를 보고 "RAG 데이터는 embedding하고 끝"이 아니라, 실제 질문으로 검색 품질을 보며 문서를 다듬어야 한다는 점을 확인했다.

## 데이터 보강

교통 문서와 시설 문서의 경계를 정리했다.

교통 문서에는 이런 표현을 강화했다.

```text
지하철
부산 도시철도 3호선
사직역
종합운동장역
버스
대중교통
주차
자가용
```

시설 문서는 아래 주제로 좁혔다.

```text
자이언츠샵
프로페셔널샵
유니폼샵
구장 내부 시설
편의시설
```

그리고 `metadata.topic_summary`, `metadata.search_keywords`를 embedding text에 포함하도록 chunk 생성 스크립트를 수정했다. 이 값들은 DB에서 검색 필터로 쓰기 위한 값이라기보다, 지금 단계에서는 embedding이 문서의 의도를 더 잘 잡도록 돕는 힌트에 가깝다.

## 최종 평가 결과

보강 후 chunk를 다시 생성하고, OpenAI embedding을 다시 만들고, pgvector에 upsert한 뒤 평가를 다시 실행했다.

최종 결과 파일:

```text
data/stadium_guide/evaluation/runs/2026-07-30_072430_SAJIK_text-embedding-3-small_transport-boost-v3.json
```

요약:

```text
positive_cases: 12
top1_accuracy: 0.9167
top3_accuracy: 1.0
failed_top1_case_ids: sajik_011
failed_top3_case_ids: 없음
```

남은 실패 케이스:

```text
질문: 사직야구장 몇 호선 타고 가?
기대 문서: stadium_transport_guide
실제 1등: stadium_facility_guide
실제 3등: stadium_transport_guide
```

정답이 Top-3 안에는 들어왔기 때문에 현재 `top_k=3` 설정으로는 답변 생성 실험을 진행해도 된다. 다만 이 케이스는 짧은 키워드형 질문에서 vector search만 쓰는 한계를 보여준다.

## Top-K에 대한 판단

현재 SAJIK은 chunk가 5개뿐이다. 이 상황에서 `top_k=5`로 높이면 사실상 SAJIK 문서 전체를 가져오는 것과 비슷하다.

그래서 현재 판단은 다음과 같다.

```text
SAJIK 최소 실험: top_k=3 유지
구장/문서 수 증가 후: top_k=5~10 후보 검색 + threshold + re-ranking 검토
```

Top-K를 무작정 높이면 정답 포함 가능성은 올라가지만, 관련 없는 chunk도 같이 들어와서 답변 품질을 흐릴 수 있다. 지금은 Top-3로 충분히 진행 가능하다.

## 다음 작업 후보

1. [완료] `search_stadium_guide` Tool을 backend routing/chat stream에 연결한다.
2. [완료] SAJIK 외 구장 normalized 문서와 chunk를 확장한다.
3. [진행 후보] 출처 URL과 limitation을 답변/Source Drawer에 함께 노출하는 방식을 정한다.
4. [진행 후보] negative case는 검색 전에 stadium/team 추출 또는 clarification으로 막는다.
5. [진행 후보] `잠실 주차`처럼 구장 context가 충돌하는 질문을 처리한다.
6. [MVP2 후보] 짧은 키워드형 질문은 Hybrid Search 또는 keyword boost 후보로 남긴다.

## 블로그에 살릴 포인트

처음에는 "임베딩이 잘 됐는지 숫자를 보면 알 수 있나?"라는 질문이 있었다.

결론은 숫자 벡터 자체를 사람이 검수하는 것이 아니라, 실제 질문을 던졌을 때 기대한 chunk가 검색되는지로 검증해야 한다는 것이다.

이번 실험은 사직구장 5개 문서만으로 RAG 검색의 가장 작은 폐루프를 만드는 과정이다.

이번 작업에서 가장 중요한 결론은 이것이다.

```text
RAG는 데이터를 넣는 작업이 아니라, 질문을 던지고 실패를 보며 데이터를 고치는 반복 작업이다.
```

처음에는 임베딩 숫자를 보고 잘 됐는지 확인할 수 있을 것 같았지만, 실제로는 평가 질문과 Top-K 결과가 훨씬 좋은 검증 도구였다.
