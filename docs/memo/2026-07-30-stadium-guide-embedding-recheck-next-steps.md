# Stadium Guide RAG Embedding/Recheck Next Steps

> 작성일: 2026-07-30  
> 목적: 다른 세션에서 구장 가이드 RAG 임베딩 재생성/검수 작업을 바로 이어가기 위한 메모  
> 현재 기준 커밋: `1bf197a data: add changwon stadium guide sources`

## 1. 현재 상태

정규 홈구장 기준 초기 수집은 완료됐다.

```text
SAJIK    5 docs
GOCHEOK  5 docs
MUNHAK   5 docs
GWANGJU  5 docs
DAEGU    5 docs
SUWON    5 docs
DAEJEON  5 docs
JAMSIL   5 docs
CHANGWON 5 docs
```

총 `45개` normalized JSON이 있다.

위치:

```text
data/stadium_guide/normalized/{STADIUM_ID}/*.json
data/stadium_guide/sources.json
data/stadium_guide/collection_summary.md
```

포항은 삼성 보조구장이므로 초기 RAG 수집 대상에서 제외한다.

## 2. 현재 임베딩 입력 상태

현재 임베딩 입력 파일은 아직 예전 SAJIK 중심 결과다.

```text
data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
```

현재 라인 수:

```text
5 lines
```

즉, 새로 수집한 9개 구장/45개 문서를 아직 chunk JSONL과 pgvector에 반영하지 않았다.

## 3. 다음 작업 순서

### 3.1 chunk 생성 스크립트 수정

현재 스크립트:

```text
backend/scripts/generate_stadium_guide_chunks.py
```

주의:

- 현재 기본값은 `--stadium-id SAJIK`라서 한 구장만 출력한다.
- 다음 작업에서는 전체 구장을 한 번에 처리하도록 수정하는 것이 좋다.
- 선택지는 두 가지다.

```text
A. --stadium-id all 옵션 추가
B. --stadium-id를 여러 번 받거나, normalized 하위 모든 구장을 순회
```

추천은 `A`다.

생성 목표:

```text
data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
```

기대 결과:

```text
45 lines
```

각 normalized 문서가 아직 짧기 때문에 문서 1개 = chunk 1개 방식 유지가 적당하다.

### 3.2 dry-run 또는 파일 검증

수정 후 먼저 chunk 파일 라인 수와 필수 metadata를 확인한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/generate_stadium_guide_chunks.py --stadium-id all
cd /Users/hong/Desktop/baseball-agent-v2
wc -l data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl
```

추가 확인 포인트:

```text
stadium_id가 9개 구장 모두 포함되는가
source_urls가 비어 있지 않은가
embedding_model이 text-embedding-3-small인가
embedding_dimensions가 1536인가
metadata.source_file은 chunk 생성용에는 있어도 DB 저장 시 제거되는가
```

## 4. 임베딩/upsert

현재 임베딩 스크립트:

```text
backend/scripts/embed_stadium_guide_chunks.py
```

실행 전 확인:

```text
backend/.env
OPENAI_API_KEY
DATABASE_URL
```

로컬 Supabase가 켜져 있어야 한다.

```bash
supabase status
```

pgvector 확인:

```sql
select extname
from pg_extension
where extname = 'vector';
```

임베딩 dry-run:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/embed_stadium_guide_chunks.py --dry-run
```

실제 임베딩/upsert:

```bash
uv run python scripts/embed_stadium_guide_chunks.py
```

주의:

- OpenAI embedding 비용이 발생한다.
- 현재 모델은 `text-embedding-3-small`이다.
- 기존 `rag_documents`, `rag_chunks`에 같은 `document_id`, `chunk_id`가 있으면 upsert된다.
- 이미 SAJIK 5개가 들어가 있으므로, 전체 45개 재실행 시 SAJIK은 갱신되고 나머지 구장이 추가되는 흐름이 맞다.

## 5. 검색 평가셋 확장

현재 평가셋은 SAJIK 중심이다.

```text
data/stadium_guide/evaluation/cases/sajik_search_cases.jsonl
```

현재 평가 스크립트:

```text
backend/scripts/evaluate_stadium_guide_retrieval.py
```

현재 특징:

- query를 같은 embedding 모델로 임베딩한다.
- `stadium_id` metadata filter를 사용한다.
- 기본 `top_k = 3`
- 결과를 `data/stadium_guide/evaluation/runs/*.json`에 저장한다.

다음에는 전체 구장 평가셋을 새로 만드는 것이 좋다.

추천 파일:

```text
data/stadium_guide/evaluation/cases/stadium_guide_search_cases.jsonl
```

구성 추천:

```text
구장별 positive 5개
구장별 negative 2개
총 9개 구장 기준 약 63개 케이스
```

단, 처음부터 63개를 다 만들기 부담스러우면 구장별 3개 positive + 1개 negative로 시작해도 된다.

## 6. 평가 시 확인할 것

필수 확인:

```text
1. stadium_id filter가 정확히 동작하는가
2. 같은 질문이라도 stadium_id가 다르면 해당 구장 문서만 검색되는가
3. top1/top3가 기대 document_type을 맞추는가
4. negative case에서 엉뚱한 구장 문서를 자신 있게 반환하지 않는가
5. 거리 threshold 0.65가 전체 구장에도 적절한가
```

예시 질문:

```text
사직구장 지하철로 어떻게 가?
잠실야구장 주차요금 얼마야?
창원NC파크 예매는 어디서 해?
대전 한화생명 볼파크 좌석 알려줘
고척돔 주차 가능해?
문학구장 주차장 있어?
수원 위즈파크 주차 예약해야 해?
광주 챔피언스필드 좌석 알려줘
대구 라이온즈파크 예매 취소 어떻게 해?
```

negative 예시:

```text
잠실야구장 질문인데 stadium_id=SAJIK으로 검색
고척돔 질문인데 stadium_id=CHANGWON으로 검색
포항야구장 질문
해외 야구장 질문
```

## 7. 중요한 설계 판단

현재 방향:

```text
정형 DB에는 최소 필수 정보만 둔다.
구장별 세부 안내는 RAG 문서로 관리한다.
metadata filter는 stadium_id를 필수로 사용한다.
Hybrid Search와 Re-ranking은 나중에 데이터가 더 커지고 Top-K 노이즈가 커질 때 도입한다.
```

현재는 top-k를 무작정 키우기보다:

```text
stadium_id filter
문서 타입별 chunk 품질
질문 평가셋
거리 threshold
```

이 네 가지를 먼저 다듬는 것이 우선이다.

## 8. 다음 세션 시작 체크리스트

```text
1. git status --short 확인
2. collection_summary.md에서 9개 구장/45개 문서 상태 확인
3. generate_stadium_guide_chunks.py 전체 구장 지원 수정
4. chunk JSONL 45 lines 생성
5. embed_stadium_guide_chunks.py --dry-run
6. 로컬 Supabase/pgvector 확인
7. 실제 임베딩/upsert 실행
8. 전체 구장 평가셋 생성
9. evaluate_stadium_guide_retrieval.py로 Top-1/Top-3 확인
10. 결과 JSON을 evaluation/runs에 저장
```
