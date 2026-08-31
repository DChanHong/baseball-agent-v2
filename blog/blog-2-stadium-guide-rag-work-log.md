# 사직구장 RAG 임베딩 첫 실험: 벡터 숫자보다 질문으로 검증하기

> 이 글은 2026-07-30에 진행한 사직구장 RAG 임베딩 첫 실험을 기준으로 정리한 작업 로그다.
> 이후 MVP1 구현 과정에서 Tool 구조와 데이터 범위는 더 확장됐지만, 이 글에서는 당시의 판단과 시행착오를 그대로 남기는 데 집중한다.

## 시작점

야구 직관 Agent를 만들면서 가장 먼저 나눈 기준은 단순했다.

경기 일정처럼 날짜, 팀, 구장, 상태가 명확한 정보는 정형 DB로 조회한다. 반대로 구장별 입장, 반입, 교통, 좌석, 예매 안내처럼 출처와 형식이 제각각인 정보는 문서 검색, 즉 RAG 대상으로 분리한다.

예를 들어 "오늘 롯데 경기 있어?"는 DB가 맞다. 하지만 "사직구장 처음 가는데 뭐 챙겨야 해?"는 다르다. 이 질문에는 반입 정책, 교통, 좌석, 예매, 초행자 관람 팁이 섞여 있다. 정보 출처도 KBO 공통 안내, 구단 공식 사이트, 구장 시설 안내로 나뉜다.

그래서 `kbo_stadiums` 같은 정형 테이블에는 구장 식별에 필요한 최소 필드만 두고, 구장별 안내 문서는 RAG 문서로 따로 관리하기로 했다. 이 날의 목표는 그 판단이 실제로 가능한지 사직구장 하나로 아주 작게 검증하는 것이었다.

## 목표

목표는 거창한 RAG 시스템을 한 번에 만드는 것이 아니었다.

사직구장(`SAJIK`) normalized 문서 5개를 chunk로 만들고, OpenAI embedding을 생성한 뒤, Supabase local PostgreSQL + pgvector에서 실제 질문으로 검색 품질을 확인할 수 있는 최소 폐루프를 만드는 것이었다.

당시 기준으로 결정한 것은 다음과 같았다.

```text
전체 구장을 한 번에 임베딩하지 않는다.
첫 실험은 SAJIK normalized 문서 5개만 대상으로 한다.
text-embedding-3-small, 1536 dimensions를 사용한다.
문서 1개를 chunk 1개로 두는 baseline에서 시작한다.
source_urls는 chunk JSONL과 DB에 저장한다.
metadata.source_file은 JSONL에는 남기고, DB upsert 시에는 제외한다.
Hybrid Search, Re-ranking, HNSW index, Agent 연결은 아직 하지 않는다.
```

이 결정에서 중요했던 점은 "일단 많이 넣자"가 아니었다. 검색 결과가 틀렸을 때 왜 틀렸는지 눈으로 추적할 수 있을 만큼 작게 시작하는 것이 더 중요했다.

## 데이터 구조

먼저 `data/` 폴더를 도메인 중심으로 재구성했다.

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

구장 가이드 검색 평가셋은 아래에 두었다.

```text
data/stadium_guide/evaluation/cases/sajik_search_cases.jsonl
```

`raw/`는 원본 보존용, `normalized/`는 사람이 검수 가능한 문서 단위, `embedded_input/`은 OpenAI embedding API 호출 전 입력 산출물로 역할을 나눴다.

이 구조를 먼저 잡은 이유는 RAG 데이터가 한 번 만들고 끝나는 파일이 아니기 때문이다. 원본, 정규화 문서, 임베딩 입력, 평가 케이스, 평가 실행 결과가 섞이면 나중에 검색 품질을 고치기가 어려워진다.

## pgvector 준비

로컬 Supabase PostgreSQL에서 pgvector를 쓰기 위해 migration을 추가했다.

```text
supabase/migrations/20260730043500_enable_vector_extension.sql
```

역할은 단순하다.

```sql
create extension if not exists vector with schema extensions;
```

이후 로컬 DB에서 `vector 0.8.2`가 활성화된 것을 확인했다.

RAG 문서와 chunk를 저장할 테이블도 만들었다.

```text
supabase/migrations/20260730044000_create_rag_document_chunk_tables.sql
```

생성한 테이블은 두 개다.

```text
public.rag_documents
public.rag_chunks
```

핵심 컬럼은 다음과 같다.

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

처음부터 `source_urls`, `as_of`, `trust_level`, `review_status`를 넣은 이유는 답변 문장보다 근거 관리가 먼저라고 봤기 때문이다. 사용자가 구장 정보를 물었을 때, "어디 기준인지", "얼마나 신뢰할 수 있는지", "검수 상태가 어떤지"를 나중에 답변 흐름에 붙일 수 있어야 했다.

## Chunk 만들기

사직구장 normalized 문서 5개를 chunk JSONL로 바꾸는 스크립트를 만들었다.

```text
backend/scripts/generate_stadium_guide_chunks.py
```

입력은 사직구장 normalized JSON과 출처 매핑 파일이다.

```text
data/stadium_guide/normalized/SAJIK/*.json
data/stadium_guide/sources.json
```

출력은 하나의 JSONL 파일이다.

```text
data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
```

당시 생성된 chunk는 5개였다.

```text
SAJIK_stadium_bag_policy_20260729_chunk_000
SAJIK_stadium_facility_guide_20260729_chunk_000
SAJIK_stadium_seat_guide_20260729_chunk_000
SAJIK_stadium_ticketing_guide_20260729_chunk_000
SAJIK_stadium_transport_guide_20260729_chunk_000
```

문서 1개를 chunk 1개로 둔 것은 일부러 단순하게 잡은 baseline이었다. 사직구장 문서가 아직 짧았고, 첫 실험에서는 chunking 알고리즘보다 "검색이 의도한 문서로 가는지"를 먼저 보고 싶었다.

문서가 길어지면 섹션 기반 chunking이 필요하겠지만, 첫날부터 그 문제를 같이 풀면 실패 원인이 너무 많아진다. 문서가 틀린 건지, chunk가 잘못 잘린 건지, embedding text가 부족한 건지, threshold가 문제인지 구분하기 어려워지기 때문이다.

## Embedding과 Upsert

다음으로 embedding 생성과 DB upsert 스크립트를 만들었다.

```text
backend/scripts/embed_stadium_guide_chunks.py
```

역할은 다음 흐름이다.

```text
chunk JSONL 읽기
→ embedding_text를 OpenAI embedding으로 변환
→ rag_documents / rag_chunks에 upsert
```

실행 결과는 작고 명확했다.

```text
Loaded 5 chunks
Upserted 5 chunks into rag_documents/rag_chunks
```

DB에서도 같은 내용을 확인했다.

```text
rag_documents: 5
rag_chunks: 5
embedding_model: text-embedding-3-small
embedding_dimensions: 1536
metadata.source_file: DB에서는 제외됨
```

여기서 `metadata.source_file`을 DB에 넣지 않은 것도 의도적인 결정이었다. 로컬 파일 경로는 재현이나 디버깅에는 유용하지만, 서비스 DB에 남길 정보는 아니다. DB에는 답변 근거로 쓸 수 있는 출처 URL과 문서 메타데이터만 유지하는 쪽으로 잡았다.

## 평가셋 만들기

임베딩을 만들고 나서 가장 먼저 든 질문은 이것이었다.

```text
이 벡터가 잘 만들어졌는지 어떻게 알 수 있지?
```

처음에는 embedding 숫자 자체를 보면 뭔가 판단할 수 있을 것처럼 느껴졌다. 하지만 1536차원 숫자 배열을 사람이 보고 "좋은 임베딩이다"라고 말할 수는 없다.

그래서 평가 기준을 바꿨다. 벡터를 직접 보는 것이 아니라, 실제 사용자가 물어볼 법한 질문을 던지고 기대한 문서가 검색되는지 확인하기로 했다.

평가셋은 아래 파일에 저장했다.

```text
data/stadium_guide/evaluation/cases/sajik_search_cases.jsonl
```

구성은 다음과 같았다.

```text
총 15개
positive 12개
negative 3개
```

positive case 예시는 이런 식이었다.

```text
사직구장 지하철로 어떻게 가? → stadium_transport_guide
사직구장 반입 금지 물품 알려줘 → stadium_bag_policy
롯데 홈경기 예매는 어디서 해? → stadium_ticketing_guide
```

교통 검색 품질을 더 보기 위해 짧은 표현의 질문도 추가했다.

```text
사직야구장 몇 호선 타고 가?
사직구장 가까운 지하철역 어디야?
사직구장 버스로 가는 법 알려줘
사직구장 주차 가능해?
사직야구장 대중교통 추천해줘
```

이 질문들이 중요했다. 사용자는 "부산 도시철도 3호선 사직역 및 종합운동장역 기준 교통 안내를 알려줘"처럼 문서 제목에 가까운 문장으로 묻지 않는다. "몇 호선?", "가까운 역?", "주차 돼?"처럼 짧게 묻는다.

RAG가 실제 서비스에서 쓸 수 있으려면 이런 질문에서 버텨야 했다.

## 검색 평가 스크립트

검색 평가 스크립트도 만들었다.

```text
backend/scripts/evaluate_stadium_guide_retrieval.py
```

의도는 단순했다.

```text
평가 질문을 embedding
→ public.rag_chunks에서 stadium_id filter로 검색
→ Top-1 / Top-3 hit 계산
→ data/stadium_guide/evaluation/runs/에 결과 JSON 저장
```

실행 중에는 각 질문별 로그를 출력하도록 했다. 나중에 한 케이스가 실패했을 때 전체 결과 JSON만 뒤지는 것보다, 질문별 Top-K 결과를 바로 보는 편이 훨씬 빨랐다.

추가로 `relevance_threshold`도 기록했다. 검색 결과를 무조건 답변에 쓰기보다, 거리값이 너무 큰 경우에는 "관련 문서 없음"으로 판단할 기준이 필요했기 때문이다.

## 로컬 환경에서 막힌 점

검색 평가 스크립트를 실행하던 중 로컬 DB 연결 timeout이 발생했다.

처음에는 스크립트 문제처럼 보였다. 그런데 `docker ps`도 실패했다. 이때 원인은 코드가 아니라 Docker Desktop 또는 Supabase local container 상태 문제로 좁혀졌다.

```text
DB 연결 실패: 로컬 Supabase PostgreSQL 연결 시간이 초과되었습니다.
docker ps: request returned Internal Server Error ...
```

해결 방향은 코드 수정이 아니라 Docker Desktop 재시작이었다. 이후 PostgreSQL 포트가 다시 응답했고, 평가 스크립트도 정상 실행됐다.

다만 이 과정에서 스크립트에는 디버깅 로그를 추가했다.

```text
env 파일 로드
OPENAI_API_KEY 존재 확인
DATABASE_URL 마스킹 출력
OpenAI client 객체 생성 로그
DB 연결 시도/성공 로그
OpenAI embedding 요청/응답 로그
질문별 Top-K 검색 결과 로그
```

여기서 한 가지 정리한 점은 OpenAI client 객체 생성은 네트워크 호출이 아니라는 것이다. 실제 API 호출은 `client.embeddings.create(...)`에서 발생한다.

작게 보이는 차이지만, timeout 원인을 찾을 때 이런 구분이 중요했다. 어디까지가 로컬 객체 생성이고, 어디부터가 외부 API 호출인지 알아야 로그를 믿고 따라갈 수 있다.

## 첫 평가 결과

처음 10개 케이스로 돌린 baseline 결과는 다음과 같았다.

```text
positive_cases: 7
top1_accuracy: 0.8571
top3_accuracy: 1.0
failed_top1_case_ids: sajik_001
```

실패 케이스는 이 질문이었다.

```text
질문: 사직구장 지하철로 어떻게 가?
기대 문서: stadium_transport_guide
실제 1등: stadium_facility_guide
실제 2등: stadium_transport_guide
```

정답 문서가 Top-3 안에는 있었지만, 시설 안내가 교통 안내보다 더 가깝게 잡혔다.

이 결과가 꽤 좋았다. 성공해서 좋았다는 뜻이 아니라, 고칠 곳을 정확히 보여줬기 때문이다. "RAG 데이터는 embedding하고 끝"이 아니라, 실제 질문으로 검색 품질을 보면서 문서의 경계와 표현을 다듬어야 한다는 점이 드러났다.

## 데이터 보강

실패 원인을 보고 교통 문서와 시설 문서의 경계를 정리했다.

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

그리고 `metadata.topic_summary`, `metadata.search_keywords`를 embedding text에 포함하도록 chunk 생성 스크립트를 수정했다.

이 값들은 DB에서 검색 필터로 쓰기 위한 값이라기보다, 당시에는 embedding이 문서의 의도를 더 잘 잡도록 돕는 힌트에 가까웠다. 특히 "몇 호선", "가까운 지하철역", "주차 가능해?"처럼 짧은 질문은 본문에 같은 표현이 없으면 의도한 문서로 잘 붙지 않을 수 있었다.

## 최종 평가 결과

보강 후 chunk를 다시 생성하고, OpenAI embedding을 다시 만들고, pgvector에 upsert한 뒤 평가를 다시 실행했다.

최종 결과 파일은 아래였다.

```text
data/stadium_guide/evaluation/runs/2026-07-30_072430_SAJIK_text-embedding-3-small_transport-boost-v3.json
```

요약은 다음과 같다.

```text
positive_cases: 12
top1_accuracy: 0.9167
top3_accuracy: 1.0
failed_top1_case_ids: sajik_011
failed_top3_case_ids: 없음
```

남은 실패 케이스는 이 질문이었다.

```text
질문: 사직야구장 몇 호선 타고 가?
기대 문서: stadium_transport_guide
실제 1등: stadium_facility_guide
실제 3등: stadium_transport_guide
```

정답이 Top-3 안에는 들어왔기 때문에, 당시 기준으로는 `top_k=3` 설정으로 답변 생성 실험을 진행해도 된다고 판단했다.

다만 이 케이스는 짧은 키워드형 질문에서 vector search만 쓰는 한계를 보여줬다. "몇 호선"이라는 짧은 표현은 사람이 보면 교통 질문이지만, embedding 검색에서는 시설 문서와도 가깝게 붙을 수 있었다.

## Top-K 판단

당시 SAJIK은 chunk가 5개뿐이었다. 이 상황에서 `top_k=5`로 높이면 사실상 사직구장 문서 전체를 가져오는 것과 비슷했다.

그래서 판단은 이렇게 정리했다.

```text
SAJIK 최소 실험: top_k=3 유지
구장/문서 수 증가 후: top_k=5~10 후보 검색 + threshold + re-ranking 검토
```

Top-K를 무작정 높이면 정답 포함 가능성은 올라간다. 하지만 관련 없는 chunk도 같이 들어와서 답변 품질을 흐릴 수 있다. 이 실험의 목적은 모든 문서를 가져오는 것이 아니라, 질문에 맞는 근거 문서가 상위에 오는지 확인하는 것이었다.

그래서 이 단계에서는 Top-3로 충분히 진행 가능하다고 봤다.

## 다음 작업 후보

당시 다음 작업 후보는 다음과 같았다.

1. `top_k=3` 검색 결과를 LLM 답변 생성 단계에 연결한다.
2. 출처 URL을 답변에 함께 노출하는 방식을 정한다.
3. negative case는 검색 전에 stadium/team 추출 또는 clarification으로 막는다.
4. `잠실 주차`처럼 다른 구장 질문이 SAJIK filter로 들어온 경우를 처리한다.
5. 짧은 키워드형 질문은 Hybrid Search 또는 keyword boost 후보로 남긴다.
6. SAJIK 답변 생성까지 검증한 뒤 나머지 구장으로 확장한다.

여기서 핵심은 "검색만 된다"를 완료로 보지 않았다는 점이다. RAG 검색 결과가 실제 답변 생성에 들어가고, 출처가 사용자에게 보이고, 엉뚱한 구장 질문이 들어왔을 때 잘 막는 흐름까지 가야 서비스 기능이 된다.

## 배운 점

이번 작업에서 가장 크게 배운 것은, 임베딩 품질은 벡터 숫자를 직접 보면서 판단하는 것이 아니라는 점이다.

처음에는 "임베딩이 잘 됐는지 숫자를 보면 알 수 있나?"라는 질문이 있었다. 하지만 실제로 도움이 된 것은 1536차원 숫자 배열이 아니라, 사람이 만든 평가 질문과 Top-K 결과였다.

이번 실험은 사직구장 5개 문서만으로 RAG 검색의 가장 작은 폐루프를 만든 과정이었다.

```text
normalized 문서 작성
→ chunk JSONL 생성
→ embedding 생성
→ pgvector upsert
→ 평가 질문 실행
→ 실패 케이스 확인
→ 문서 표현 보강
→ 다시 평가
```

이 과정을 거치면서 결론은 꽤 분명해졌다.

```text
RAG는 데이터를 넣는 작업이 아니라, 질문을 던지고 실패를 보며 데이터를 고치는 반복 작업이다.
```

구장 가이드 RAG의 첫 실험은 작았다. 사직구장 하나, 문서 5개, chunk 5개가 전부였다. 하지만 작게 시작했기 때문에 검색 실패를 이해할 수 있었고, 문서를 어떻게 고쳐야 하는지도 보였다.

나중에 더 많은 구장과 더 많은 문서로 확장하더라도 이 기준은 그대로 가져가야 한다. 먼저 질문을 만들고, 검색 결과를 보고, 실패를 기록하고, 데이터를 고친다. RAG에서 중요한 것은 "넣었다"가 아니라 "검증하면서 좋아지고 있다"는 증거다.
