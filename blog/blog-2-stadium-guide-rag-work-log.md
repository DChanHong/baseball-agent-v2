# [AI Agent] RAG 임베딩: 사직구장, 벡터 숫자보다 질문으로 검증하기

## 개요

KBO Mate에서는 구장별 안내 정보를 RAG로 다루기로 정리해두었습니다.  
경기 일정이나 날씨처럼 구조화된 정보는 DB/API 기반 Tool로 처리하고, 구장 이용 안내처럼 문서 기반 설명이 필요한 정보는 RAG 문서로 관리하는 방향이었습니다.

이번 글에서는 그 계획에 따라 사직구장 안내 문서를 먼저 임베딩한 과정을 정리해보겠습니다.

## 1. 작업 목표

이번 작업의 목표는 거창한 RAG 시스템을 한 번에 만드는 것이 아니었습니다.

먼저 사직구장 하나를 기준으로 RAG 문서를 만들고, 임베딩을 생성한 뒤, 실제 질문으로 검색 품질을 확인할 수 있는 최소 흐름을 만드는 것이었습니다.

당시 기준으로 작업 범위는 다음과 같이 잡았습니다.

```text
사직구장 normalized 문서 5개를 대상으로 한다.

문서 1개를 chunk 1개로 두는 baseline에서 시작한다.

text-embedding-3-small 모델을 사용한다.

embedding dimension은 1536으로 맞춘다.

생성한 embedding은 Supabase local PostgreSQL + pgvector에 저장한다.

검색 평가는 Top-1 / Top-3 hit 기준으로 확인한다.

Hybrid Search, Re-ranking, Agent 연결은 아직 하지 않는다.
```

여기서 중요하게 본 것은 기능을 많이 붙이는 것이 아니었습니다.

RAG 검색 결과가 틀렸을 때 왜 틀렸는지 추적할 수 있을 만큼 작게 시작하는 것이 더 중요했습니다. 처음부터 모든 구장을 넣고 chunk 전략까지 복잡하게 가져가면 실패 원인을 구분하기 어려워질 수 있기 때문입니다.

## 2. 데이터 구조 정리

먼저 RAG 데이터를 관리할 폴더 구조를 정리했습니다.

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

각 폴더의 역할은 다음과 같이 나눴습니다.

```text
raw
→ 수집한 원본 데이터를 보존한다.

normalized
→ 사람이 읽고 검수할 수 있는 문서 단위로 정리한다.

embedded_input
→ OpenAI embedding API에 넣기 전의 입력 산출물을 저장한다.

evaluation
→ 검색 품질을 확인할 평가 케이스와 실행 결과를 저장한다.
```

이 구조를 먼저 잡은 이유는 RAG 데이터가 한 번 만들고 끝나는 파일이 아니기 때문입니다.

원본, 정규화 문서, 임베딩 입력, 평가 케이스, 평가 실행 결과가 섞이면 나중에 검색 품질을 고치기 어려워집니다. 그래서 처음부터 데이터의 단계와 역할을 나누어두었습니다.

## 3. pgvector 저장 구조

로컬 Supabase PostgreSQL에서 벡터 검색을 하기 위해 pgvector extension을 활성화했습니다.

```sql
create extension if not exists vector with schema extensions;
```

이후 RAG 문서와 chunk를 저장하기 위해 두 개의 테이블을 만들었습니다.

```text
public.rag_documents
public.rag_chunks
```

핵심적으로 관리한 값은 다음과 같습니다.

```text
stadium_id     // 어떤 구장의 문서인지 구분하기 위한 값
team_id        // 어떤 팀과 연결된 문서인지 구분하기 위한 값
document_type  // 교통, 반입, 좌석, 예매 등 문서의 종류
review_status  // 검수 완료, 제외 등 문서 사용 가능 상태
trust_level    // 공식 출처 여부 등 문서 신뢰도 판단 기준
as_of          // 해당 문서가 언제 기준 정보인지 나타내는 값
source_ids     // 원본 출처를 내부적으로 추적하기 위한 ID
source_urls    // 사용자에게 근거로 보여줄 수 있는 출처 URL
embedding      // 의미 기반 검색에 사용할 벡터 값
```

이 값들은 단순히 문서를 저장하기 위한 컬럼이 아니라, 나중에 검색 결과를 신뢰할 수 있게 만들기 위한 기준이었습니다.

특히 `stadium_id`, `team_id`, `document_type`은 검색 범위를 좁히기 위한 값입니다. 예를 들어 사용자가 사직구장 교통을 물었는데 잠실이나 고척 문서가 함께 검색되면 답변이 쉽게 흔들릴 수 있습니다.

`source_ids`, `source_urls`, `as_of`, `trust_level`, `review_status`는 검색된 문서가 어디서 왔고, 언제 기준이며, 답변 근거로 사용해도 되는지를 판단하기 위한 값입니다.

즉, 처음부터 이런 metadata를 함께 저장한 이유는 답변 문장보다 근거 관리가 먼저라고 봤기 때문입니다. RAG는 문서를 검색해 답변을 만드는 구조이기 때문에, 검색된 문서의 출처와 신뢰도를 함께 관리해야 한다고 판단했습니다.

## 4. Chunk 생성

사직구장 normalized 문서 5개를 chunk JSONL로 변환했습니다.

당시 생성된 chunk는 다음과 같습니다.

```text
SAJIK_stadium_bag_policy_20260729_chunk_000
SAJIK_stadium_facility_guide_20260729_chunk_000
SAJIK_stadium_seat_guide_20260729_chunk_000
SAJIK_stadium_ticketing_guide_20260729_chunk_000
SAJIK_stadium_transport_guide_20260729_chunk_000
```

실제 chunk JSONL은 아래와 같은 형태였습니다. 글에서는 전체 본문과 출처 URL을 모두 넣기보다, 어떤 값이 embedding 입력에 들어갔는지만 볼 수 있게 줄였습니다.

```json
{
  "chunk_id": "SAJIK_stadium_transport_guide_20260729_chunk_000",
  "document_id": "SAJIK_stadium_transport_guide_20260729",
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "document_type": "stadium_transport_guide",
  "title": "사직야구장 지하철 버스 주차 교통 안내 초안",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimensions": 1536,
  "embedding_text": "제목: 사직야구장 지하철 버스 주차 교통 안내 초안\n문서유형: stadium_transport_guide\n구장: SAJIK\n팀: LOTTE\n핵심주제: 사직야구장 지하철, 도시철도, 버스, 자가용, 주차 관련 교통 안내\n검색키워드: 사직구장 가는 법, 사직야구장 지하철, 사직야구장 몇 호선, 가까운 지하철역, 사직역, 종합운동장역, 사직구장 주차\n본문:\n...",
  "metadata": {
    "topic_summary": "사직야구장 지하철, 도시철도, 버스, 자가용, 주차 관련 교통 안내",
    "search_keywords": [
      "사직구장 가는 법",
      "사직야구장 지하철",
      "사직야구장 몇 호선",
      "가까운 지하철역",
      "사직역",
      "종합운동장역",
      "사직구장 주차"
    ]
  },
  "as_of": "2026-07-29",
  "trust_level": "official",
  "review_status": "needs_review",
  "source_ids": ["lotte_sajik_stadium", "lotte_stadium_shop"],
  "source_urls": ["..."]
}
```

여기서 핵심은 원문 본문만 embedding하지 않았다는 점입니다. 제목, 문서유형, 구장, 팀, 핵심주제, 검색키워드, 본문을 조합해 `embedding_text`를 만들었습니다.

문서 1개를 chunk 1개로 둔 것은 의도적인 baseline이었습니다.

사직구장 문서가 아직 짧았고, 첫 실험에서는 chunking 알고리즘보다 "검색이 의도한 문서로 가는지"를 먼저 확인하고 싶었습니다.

문서가 길어지면 섹션 기반 chunking이 필요합니다. 하지만 첫 작업부터 chunk 전략을 복잡하게 가져가면 문제가 생겼을 때 원인을 좁히기 어려워집니다.

```text
문서 내용이 부족한 문제인지

chunk가 잘못 나뉜 문제인지

embedding text가 부족한 문제인지

threshold나 top-k 설정 문제인지
```

이런 원인을 분리해서 보기 위해 첫 실험은 단순한 구조로 시작했습니다.

## 5. Embedding 생성과 Upsert

다음으로 chunk JSONL을 읽어 embedding을 생성하고 DB에 저장하는 흐름을 만들었습니다.

전체 흐름은 다음과 같습니다.

```text
chunk JSONL 읽기
→ embedding_text 생성
→ OpenAI embedding API 호출
→ rag_documents / rag_chunks upsert
```

실행 결과는 다음과 같이 확인했습니다.

```text
Loaded 5 chunks
Upserted 5 chunks into rag_documents/rag_chunks
```

DB에서도 같은 내용을 확인했습니다.

```text
rag_documents: 5
rag_chunks: 5
embedding_model: text-embedding-3-small
embedding_dimensions: 1536
```

여기서 한 가지 의도적으로 정리한 부분이 있었습니다.

`metadata.source_file`은 chunk JSONL에는 남겼지만, DB upsert 시에는 제외했습니다. 로컬 파일 경로는 재현과 디버깅에는 유용하지만, 서비스 DB에서 사용자 답변의 근거로 쓰기에는 적합하지 않다고 판단했기 때문입니다.

DB에는 답변 근거로 사용할 수 있는 출처 URL과 문서 메타데이터를 남기는 방향으로 정리했습니다.

## 6. 평가셋 만들기

임베딩을 만들고 나서 가장 먼저 든 질문은 이것이었습니다.

```text
이 벡터가 잘 만들어졌는지 어떻게 알 수 있을까?
```

처음에는 embedding 숫자 자체를 보면 품질을 판단할 수 있을 것처럼 느껴졌습니다. 하지만 1536차원 숫자 배열을 사람이 직접 보고 좋은 임베딩인지 판단하기는 어렵습니다.

그래서 기준을 바꿨습니다.

벡터 숫자를 직접 보는 것이 아니라, 실제 사용자가 물어볼 법한 질문을 던지고 기대한 문서가 검색되는지 확인하기로 했습니다.

평가셋은 다음과 같이 구성했습니다.

```text
총 15개
positive 12개
negative 3개
```

positive case는 이런 식이었습니다.

```text
사직구장 지하철로 어떻게 가?
→ stadium_transport_guide

사직구장 반입 금지 물품 알려줘
→ stadium_bag_policy

롯데 홈경기 예매는 어디서 해?
→ stadium_ticketing_guide
```

교통 검색 품질을 확인하기 위해 짧은 표현의 질문도 추가했습니다.

```text
사직야구장 몇 호선 타고 가?
사직구장 가까운 지하철역 어디야?
사직구장 버스로 가는 법 알려줘
사직구장 주차 가능해?
사직야구장 대중교통 추천해줘
```

이 질문들이 중요했습니다.

사용자는 문서 제목처럼 질문하지 않습니다. "부산 도시철도 3호선 사직역 기준 교통 안내를 알려줘"라고 묻기보다, "몇 호선?", "가까운 역?", "주차 돼?"처럼 짧게 묻습니다.

RAG가 실제 서비스에서 쓸 수 있으려면 이런 질문에서도 기대한 문서를 찾아야 했습니다.

## 7. 검색 평가 방식

검색 평가 스크립트는 다음 흐름으로 만들었습니다.

```text
평가 질문을 embedding한다.

stadium_id filter를 적용해 public.rag_chunks에서 검색한다.

Top-1 / Top-3 hit를 계산한다.

평가 결과를 JSON으로 저장한다.
```

평가에서 중요하게 본 것은 두 가지였습니다.

```text
Top-1
→ 사용자의 질문에 가장 먼저 선택된 문서가 기대 문서인가?

Top-3
→ 답변 생성에 넘길 후보 안에는 기대 문서가 들어오는가?
```

Top-1은 검색 품질을 직접적으로 보여줍니다.  
Top-3는 이후 LLM 답변 생성 단계에서 정답 근거를 사용할 수 있는지 확인하기 위한 기준입니다.

추가로 `relevance_threshold`도 기록했습니다. 검색 결과를 무조건 답변에 쓰기보다, 관련성이 낮은 경우에는 "관련 문서 없음"으로 판단할 기준이 필요했기 때문입니다.

## 8. 첫 평가 결과

처음 10개 케이스로 baseline 평가를 실행했습니다.

결과는 다음과 같았습니다.

```text
positive_cases: 7
top1_accuracy: 0.8571
top3_accuracy: 1.0
failed_top1_case_ids: sajik_001
```

실패 케이스는 이 질문이었습니다.

```text
질문: 사직구장 지하철로 어떻게 가?
기대 문서: stadium_transport_guide
실제 1등: stadium_facility_guide
실제 2등: stadium_transport_guide
```

평가 결과 JSON에는 질문별로 기대 문서와 실제 Top-K 결과를 함께 남겼습니다. 실패한 `sajik_001` 케이스를 줄이면 아래와 같습니다.

```json
{
  "id": "sajik_001",
  "query": "사직구장 지하철로 어떻게 가?",
  "case_type": "positive",
  "stadium_id": "SAJIK",
  "expected_document_type": "stadium_transport_guide",
  "top1_hit": false,
  "top3_hit": true,
  "retrieved_document_types": [
    "stadium_facility_guide",
    "stadium_transport_guide",
    "stadium_seat_guide"
  ],
  "results": [
    {
      "rank": 1,
      "document_type": "stadium_facility_guide",
      "title": "사직야구장 시설 안내 초안",
      "distance": 0.5743523667945026
    },
    {
      "rank": 2,
      "document_type": "stadium_transport_guide",
      "title": "사직야구장 교통 안내 초안",
      "distance": 0.5796893185459618
    }
  ]
}
```

이렇게 저장해두면 단순히 정확도 숫자만 보는 것이 아니라, 어떤 질문에서 어떤 문서가 잘못 올라왔는지 바로 확인할 수 있었습니다.

정답 문서가 Top-3 안에는 있었지만, Top-1은 아니었습니다.

이 결과는 오히려 도움이 됐습니다. 단순히 "검색이 된다"에서 끝나는 것이 아니라, 어떤 질문에서 문서의 경계와 표현이 흔들리는지 보여줬기 때문입니다.

## 9. 실패 원인과 데이터 보강

실패 원인은 검색 로직 자체보다 embedding text의 정보 부족에 가깝다고 봤습니다.

"사직구장 지하철로 어떻게 가?"라는 질문은 사람이 보면 교통 질문입니다. 하지만 embedding 검색에서는 시설 안내 문서가 교통 안내 문서보다 더 가깝게 잡혔습니다.

그래서 교통 문서와 시설 문서의 경계를 다시 정리했습니다.

교통 문서에는 다음 표현을 강화했습니다.

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

시설 문서는 아래 주제로 좁혔습니다.

```text
자이언츠샵
프로페셔널샵
유니폼샵
구장 내부 시설
편의시설
```

그리고 `metadata.topic_summary`, `metadata.search_keywords`를 embedding text에 포함하도록 chunk 생성 방식을 수정했습니다.

이 값들은 DB 검색 필터라기보다 embedding이 문서의 의도를 더 잘 잡도록 돕는 힌트에 가까웠습니다.

특히 "몇 호선", "가까운 지하철역", "주차 가능해?"처럼 짧은 질문은 본문에 같은 표현이 없으면 의도한 문서로 잘 붙지 않을 수 있었습니다.

## 10. 변경 후 평가 결과

데이터를 보강한 뒤 다시 평가했습니다.

흐름은 다음과 같았습니다.

```text
chunk 다시 생성
→ OpenAI embedding 다시 생성
→ pgvector upsert
→ 평가 재실행
```

최종 결과는 다음과 같았습니다.

```text
positive_cases: 12
top1_accuracy: 0.9167
top3_accuracy: 1.0
failed_top1_case_ids: sajik_011
failed_top3_case_ids: 없음
```

Top-1 정확도는 85.71%에서 91.67%로 올라갔고, Top-3는 계속 100%를 유지했습니다.

다만 완전히 해결된 것은 아니었습니다.

남은 실패 케이스는 다음 질문이었습니다.

```text
질문: 사직야구장 몇 호선 타고 가?
기대 문서: stadium_transport_guide
실제 1등: stadium_facility_guide
실제 3등: stadium_transport_guide
```

정답이 Top-3 안에는 들어왔기 때문에, 당시 기준으로는 `top_k=3` 설정으로 답변 생성 실험을 진행해도 된다고 판단했습니다.

하지만 이 케이스는 짧은 키워드형 질문에서 vector search만 사용하는 방식의 한계도 보여줬습니다.

## 11. Top-K 판단

당시 사직구장 문서는 chunk가 5개뿐이었습니다.

이 상황에서 `top_k=5`로 높이면 사실상 사직구장 문서 전체를 가져오는 것과 비슷했습니다.

그래서 당시 판단은 다음과 같이 정리했습니다.

```text
SAJIK 최소 실험
→ top_k=3 유지

구장/문서 수 증가 후
→ top_k=5~10 후보 검색 + threshold + re-ranking 검토
```

Top-K를 무작정 높이면 정답 포함 가능성은 올라갑니다.

하지만 관련 없는 chunk도 같이 들어와 답변 품질을 흐릴 수 있습니다. 이 실험의 목적은 모든 문서를 가져오는 것이 아니라, 질문에 맞는 근거 문서가 상위에 오는지 확인하는 것이었습니다.

## 12. 정리

이번 작업에서 가장 크게 배운 것은 임베딩 품질을 벡터 숫자만 보고 판단할 수 없다는 점이었습니다.

처음에는 "임베딩이 잘 됐는지 숫자를 보면 알 수 있나?"라는 질문이 있었습니다. 하지만 실제로 도움이 된 것은 1536차원 숫자 배열이 아니라, 사람이 만든 평가 질문과 Top-K 결과였습니다.

이번 실험의 흐름은 다음과 같이 정리할 수 있습니다.

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

결론은 명확했습니다.

```text
RAG는 데이터를 넣는 작업이 아니라,
질문을 던지고 실패를 보며 데이터를 고치는 반복 작업입니다.
```

사직구장 하나, 문서 5개, chunk 5개로 시작한 작은 실험이었지만, 작게 시작했기 때문에 검색 실패를 이해할 수 있었습니다.

나중에 더 많은 구장과 더 많은 문서로 확장하더라도 이 기준은 그대로 가져가야 합니다. 먼저 질문을 만들고, 검색 결과를 보고, 실패를 기록하고, 데이터를 고칩니다.

RAG에서 중요한 것은 "넣었다"가 아니라 "검증하면서 좋아지고 있다"는 증거라고 판단했습니다.
