# [AI Agent] 야구 지식 RAG: 공식 규칙 PDF를 질문으로 검증하기

## 개요

KBO Mate에서는 경기 일정, 날씨, 구장 정보뿐 아니라 야구 규칙과 플레이 상황도 설명할 수 있어야 했습니다.
다만 야구 규칙은 단순한 정형 데이터가 아니라, 공식 규칙 PDF와 리그 규정처럼 문서 기반 근거가 중요한 영역이었습니다.

이번 글에서는 `search_baseball_knowledge` Tool을 만들기 위해 공식 문서를 RAG 데이터로 준비하고, 실제 질문으로 검색 품질을 확인한 과정을 정리해보겠습니다.

## 1. 작업 목표

이번 작업의 목표는 야구 지식 전체를 완벽하게 답변하는 것이 아니었습니다.

먼저 공식 문서 기반 chunk를 만들고, `search_baseball_knowledge` Tool이 실제 질문에서 기대한 topic을 찾는지 확인하는 것이 목표였습니다.

당시 기준으로 작업 범위는 다음과 같이 잡았습니다.

```text
KBO 공식 야구규칙과 리그 규정을 원천 문서로 사용한다.

PDF 원본은 repo에 포함하지 않는다.

pdfplumber 기반으로 page-level text를 추출한다.

야구 지식 topic별 chunk를 생성한다.

text-embedding-3-small 모델을 사용한다.

embedding dimension은 1536으로 맞춘다.

생성한 embedding은 기존 rag_documents / rag_chunks 테이블에 저장한다.

검색 평가는 대표 질문으로 top-1 ranking을 확인한다.
```

여기서 중요하게 본 것은 "공식 문서를 넣었다"가 아니었습니다.

사용자가 실제로 물어볼 법한 표현으로 질문했을 때, 공식 문서 기반 근거가 제대로 검색되는지를 확인하는 것이 더 중요했습니다.

## 2. 데이터 관리 기준

야구 지식 RAG 데이터는 다음 위치에서 관리했습니다.

```text
data/baseball_knowledge/
├── README.md
├── sources.json
├── raw/
│   └── extracted_pdf/
├── normalized/
├── embedded_input/
│   └── baseball_knowledge_chunks.jsonl
└── evaluation/
    ├── cases/
    └── runs/
```

다만 모든 파일을 git에 올리지는 않았습니다.

`data/baseball_knowledge/.gitignore` 기준으로 다음 산출물은 commit 대상에서 제외했습니다.

```text
raw/              // PDF에서 추출한 page-level text 산출물
embedded_input/   // embedding 입력으로 재생성되는 chunk JSONL
evaluation/runs/  // 평가 실행 결과 산출물
```

이렇게 둔 이유는 PDF 원본과 추출 산출물은 용량과 재배포 이슈가 있고, embedding input과 평가 실행 결과는 스크립트로 다시 만들 수 있는 생성물에 가깝기 때문입니다.

대신 repo에는 `sources.json`, 평가 케이스, 스크립트, Tool 구현 코드를 남겼습니다. 즉, 원천 파일 자체보다 재생성 가능한 파이프라인과 검증 기준을 남기는 방향으로 정리했습니다.

## 3. 원본 Source 정리

야구 지식 RAG에서 사용한 원천은 `data/baseball_knowledge/sources.json`에 정리했습니다.

관리한 source는 다음과 같습니다.

```text
2024 공식야구규칙
2025 공식야구규칙
2026 공식야구규칙
2024 KBO 리그 규정
2025 KBO 리그 규정
2026 KBO 리그 규정
2026 주요 규정 및 규칙
```

각 source에서 핵심적으로 관리한 값은 다음과 같습니다.

```text
source_id       // 원천 문서를 식별하기 위한 내부 ID
document_type   // 공식야구규칙, 리그규정, 최신 규정 페이지 등 문서 종류
source_kind     // PDF인지 web page인지 구분하는 값
source_url      // 근거 확인을 위한 원본 URL
season_year     // 어느 시즌 기준 문서인지 나타내는 값
extractor       // PDF 추출에 사용한 방식
repo_tracked    // repo에 원본 파일을 포함하는지 여부
```

이 값을 따로 둔 이유는 야구 규칙이 시즌별로 달라질 수 있기 때문입니다.

특히 피치클락, ABS, 체크스윙 판독처럼 최신 규정과 관련된 질문은 "어느 시즌 기준인가"가 중요합니다. 그래서 chunk를 만들기 전에 source 단계에서부터 문서의 기준 연도와 출처를 분리해두었습니다.

## 4. Chunk 생성

원본 PDF는 repo 밖의 로컬 경로에 두고, 필요할 때 extraction과 chunk 생성을 다시 실행하는 방식으로 정리했습니다.

실행 흐름은 다음과 같았습니다.

```text
로컬 PDF 준비
→ pdfplumber로 page-level text 추출
→ topic 기준 chunk 생성
→ embedding_text 생성
→ OpenAI embedding 생성
→ rag_documents / rag_chunks upsert
```

사용한 스크립트 흐름은 다음과 같습니다.

```bash
uv run python scripts/baseball_knowledge/extract_pdf_pages.py --pdf-dir "/Users/hong/Desktop/야구지식-RAG용" --strict
uv run python scripts/baseball_knowledge/generate_chunks.py --strict
uv run python scripts/baseball_knowledge/embed_chunks.py --dry-run
uv run python scripts/baseball_knowledge/embed_chunks.py
```

생성된 chunk는 세 종류의 지식으로 나누었습니다.

```text
baseball_rule      // 기본 야구 규칙
common_play        // 직관 중 자주 만나는 플레이 상황
latest_kbo_rule    // 최신 KBO 규정
```

DB에 저장된 chunk 수는 다음과 같았습니다.

```text
baseball_rule 10
common_play 9
latest_kbo_rule 8
total 27
```

처음부터 모든 문장을 그대로 검색 대상으로만 쓰기보다, topic 단위로 묶어서 사용자가 물어볼 질문과 공식 문서 표현 사이의 간극을 줄이는 쪽을 선택했습니다.

## 5. Tool 구현

추가한 Tool 이름은 다음과 같습니다.

```text
search_baseball_knowledge
```

Tool은 야구 규칙, 플레이 설명, 최신 KBO 규정 질문을 처리합니다.

입력 schema는 다음 형태였습니다.

```json
{
  "query": "보크가 뭐야?",
  "knowledge_types": ["common_play"],
  "top_k": 5
}
```

지원하는 `knowledge_types`는 다음 세 가지로 제한했습니다.

```text
baseball_rule
common_play
latest_kbo_rule
```

검색 대상 조건도 명확히 제한했습니다.

```sql
document_type in ('baseball_rule', 'common_play', 'latest_kbo_rule')
stadium_id is null
team_id is null
review_status != 'rejected'
embedding is not null
```

야구 지식은 특정 구장이나 특정 팀에 묶이는 정보가 아니기 때문에 `stadium_id`, `team_id`가 없는 chunk만 검색 대상으로 두었습니다.

## 6. Threshold 설정

야구 지식 Tool의 relevance threshold는 다음과 같이 잡았습니다.

```text
0.82
```

구장 가이드 RAG에서 사용하던 `0.65`를 그대로 쓰지 않았습니다.

야구 지식 PDF chunk는 공식 문서 표현이 많고, 사용자의 질문은 대부분 짧고 구어체입니다. 예를 들어 "보크가 뭐야?" 같은 질문은 공식 규칙 문서의 표현과 거리가 있습니다.

실제 초기 검색에서 "보크가 뭐야?"의 정답 chunk distance가 약 `0.7444` 수준으로 나왔기 때문에, 구장 안내와 같은 threshold를 쓰면 정답 문서가 걸러질 수 있었습니다.

그래서 야구 지식 Tool은 별도 threshold를 두었습니다.

## 7. Routing 연결

`search_baseball_knowledge`는 Agent routing에도 연결했습니다.

추가한 routing 예시는 다음과 같습니다.

```text
보크가 뭐야?
→ search_baseball_knowledge / common_play

피치클락 위반하면 어떻게 돼?
→ search_baseball_knowledge / latest_kbo_rule

볼이랑 스트라이크가 뭐야?
→ search_baseball_knowledge / baseball_rule

비 오면 누가 경기 취소를 결정해?
→ search_baseball_knowledge / latest_kbo_rule
```

기존 routing 평가 결과는 다음과 같았습니다.

```text
total: 32
exact_match_accuracy: 0.9688
failed_case_ids: fg_012
```

새로 추가한 야구 지식 routing 케이스는 모두 통과했습니다.

실패한 `fg_012`는 "키움 8월 첫째 주 경기 일정 알려줘"의 날짜 범위 해석 케이스였고, 야구 지식 Tool 자체와 직접 관련된 실패는 아니었습니다.

## 8. 검색 평가 케이스

야구 지식 검색 평가는 실제 질문 형태로 만들었습니다.

현재 repo에 남아 있는 평가 케이스는 `data/baseball_knowledge/evaluation/cases/search_baseball_knowledge_cases.jsonl` 기준 총 20개입니다.

대표 케이스는 다음과 같습니다.

```json
{
  "id": "bk_001",
  "input": {
    "query": "보크가 뭐야?",
    "knowledge_types": ["common_play"],
    "top_k": 5
  },
  "expected": {
    "answerable": true,
    "top1_topic_ids": ["common_play_balk"],
    "top3_topic_ids": ["common_play_balk"],
    "top1_document_type": "common_play",
    "required_source_urls": true
  },
  "note": "보크 대표 질문은 보크 topic이 top1이어야 한다."
}
```

평가 케이스에서 본 것은 단순히 answerable 여부만이 아니었습니다.

```text
top1_topic_ids       // 가장 먼저 검색되어야 하는 topic
top3_topic_ids       // top3 안에는 들어와야 하는 topic
top1_document_type   // 기대한 문서 유형
required_source_urls // 출처 URL 포함 여부
```

이 기준을 둔 이유는 RAG 검색에서 "무언가 검색됐다"와 "답변에 쓸 수 있는 근거가 검색됐다"는 다르기 때문입니다.

## 9. 개선 전 검색 결과

초기 검색은 실제 OpenAI query embedding과 로컬 Supabase pgvector 검색으로 확인했습니다.

대표 질문 결과는 다음과 같았습니다.

```text
보크가 뭐야?
→ top1: 보크
→ distance: 0.7444
→ 판단: 정상

피치클락 위반하면 어떻게 돼?
→ top1: 피치클락
→ distance: 0.6927
→ 판단: 정상

비 오면 누가 경기 취소를 결정해?
→ top1: 기상 상황 경기취소
→ top2: 경기 거행 여부 결정 권한
→ top3: 체크스윙 판독
→ 판단: top1/top2는 좋지만 top3에 관련이 약한 topic이 섞임

볼이랑 스트라이크가 뭐야?
→ top1: 주자 진루와 귀루
→ top2: 볼과 스트라이크
→ 판단: 기대 topic이 top2로 밀림

인필드 플라이가 왜 선언돼?
→ top1: 병살과 더블플레이
→ top2: 인필드 플라이
→ 판단: 기대 topic이 top2로 밀림
```

이 결과를 보고 처음 확인한 문제는 chunk 본문 자체보다 `embedding_text` 구성이었습니다.

공식 PDF 문장은 정확하지만, 초보자 질문 표현과는 거리가 있습니다. 사용자는 "공을 안 잡았는데 왜 아웃이야?"처럼 묻지만, 공식 문서는 규칙 조항 중심으로 설명합니다.

그래서 검색 입력에는 공식 근거만이 아니라, 검색용 요약과 질문 표현을 더 강하게 넣을 필요가 있었습니다.

## 10. Embedding Text 개선

1차 개선에서는 chunk 수나 threshold를 바꾸지 않았습니다.

먼저 `embedding_text` 구성을 바꿨습니다.

변경 전 구조는 다음과 같았습니다.

```text
제목
문서유형
지식유형
topic_id
핵심주제
검색키워드
초보자 질문 예시
본문 전체
```

변경 후 구조는 다음과 같았습니다.

```text
검색문서명
핵심주제
주제반복
topic_id
문서유형
지식유형
핵심 답변 요약
검색 키워드와 동의어
이 문서가 답해야 하는 질문
공식 근거 짧은 발췌
```

핵심 변화는 다음과 같습니다.

```text
title, summary, keywords, example_questions를 embedding_text 앞쪽에 배치했습니다.

"{title}가 뭐야?", "{title} 뜻 알려줘", "{title} 규칙 설명해줘" 같은 검색 패턴을 추가했습니다.

긴 PDF 원문 전체를 embedding_text에 넣지 않고, 공식 근거 발췌를 2500자까지만 넣었습니다.

답변과 citation에 사용할 content는 기존처럼 source page slice를 유지했습니다.
```

이렇게 한 이유는 검색용 텍스트와 답변 근거용 텍스트의 역할이 다르다고 봤기 때문입니다.

검색에는 사용자의 질문 표현과 가까운 문장이 필요하고, 답변에는 공식 문서 기반 근거가 필요합니다. 두 목적을 하나의 긴 원문에만 맡기면 ranking이 흔들릴 수 있다고 판단했습니다.

## 11. 개선 후 검색 결과

`embedding_text`가 바뀌었기 때문에 같은 `chunk_id`로 재임베딩 후 upsert했습니다.

실행 결과는 다음과 같았습니다.

```text
Wrote 27 chunks
Loaded 27 chunks
Upserted 27 chunks into rag_documents/rag_chunks
```

chunk 수와 threshold는 그대로 유지했습니다.

```text
chunk 수: 27
threshold: 0.82
```

동일 질문을 다시 확인한 결과는 다음과 같았습니다.

```text
보크가 뭐야?
→ 개선 전 top1: 보크 / distance 0.7444
→ 개선 후 top1: 보크 / distance 0.6660
→ top1 유지, distance 개선

피치클락 위반하면 어떻게 돼?
→ 개선 전 top1: 피치클락 / distance 0.6927
→ 개선 후 top1: 피치클락 / distance 0.6862
→ top1 유지, distance 소폭 개선

비 오면 누가 경기 취소를 결정해?
→ 개선 전 top3: 체크스윙 판독 포함
→ 개선 후 top1: 기상 상황 경기취소
→ 개선 후 top2: 노게임과 서스펜디드
→ 개선 후 top3: 경기 거행 여부 결정 권한
→ 관련이 약한 체크스윙 판독이 빠짐

볼이랑 스트라이크가 뭐야?
→ 개선 전 top2: 볼과 스트라이크
→ 개선 후 top1: 볼과 스트라이크 / distance 0.7111
→ 기대 topic이 top1로 올라옴

인필드 플라이가 왜 선언돼?
→ 개선 전 top2: 인필드 플라이
→ 개선 후 top1: 인필드 플라이 / distance 0.7256
→ 기대 topic이 top1로 올라옴
```

대표 질문 5개 기준으로는 다음과 같이 정리할 수 있었습니다.

```text
개선 전 top1 성공: 3/5
개선 후 top1 성공: 5/5
```

## 12. Chunk 진단

1차 개선 후 바로 split이나 re-rank를 추가할지 판단하기 위해 chunk 상태도 확인했습니다.

전체 chunk 수는 다음과 같았습니다.

```text
total_chunks: 27
```

긴 chunk는 일부 있었습니다.

```text
보크                         content 6289 / embed 2750 / pages 7
주자 진루와 귀루 idx0         content 6262 / embed 2820 / pages 7
도루와 견제 idx0              content 6058 / embed 2805 / pages 7
노게임과 서스펜디드 idx0       content 5755 / embed 2847 / pages 11
볼과 스트라이크               content 5694 / embed 2816 / pages 7
태그아웃과 포스아웃 idx0       content 5581 / embed 2848 / pages 6
정식경기와 노게임             content 5504 / embed 2813 / pages 8
```

split된 topic도 있었습니다.

```text
주자 진루와 귀루: 2 chunks / total 11655 chars / 13 pages
도루와 견제: 2 chunks / total 7647 chars / 9 pages
태그아웃과 포스아웃: 2 chunks / total 9632 chars / 10 pages
노게임과 서스펜디드: 2 chunks / total 9260 chars / 15 pages
```

하지만 대표 질문 5개는 모두 기대 topic이 top1이었고, top2/top3에 섞이는 chunk도 대부분 같은 규칙 범주 안에서 약하게 관련된 topic이었습니다.

그래서 이 시점에서는 chunk split이나 re-rank를 즉시 넣기보다, `embedding_text` 개선만으로 baseline을 한 번 정리하는 쪽이 적절하다고 봤습니다.

## 13. 정리

이번 작업에서 확인한 것은 야구 지식 RAG의 핵심이 "공식 문서를 넣는 것"만은 아니라는 점이었습니다.

공식 PDF는 신뢰할 수 있는 근거지만, 사용자의 질문은 공식 문서처럼 들어오지 않습니다. 그래서 검색 품질을 보려면 embedding vector 숫자보다 실제 질문을 기준으로 봐야 했습니다.

이번 기준선에서는 다음 흐름을 확인했습니다.

```text
공식 문서 source 관리
→ PDF page-level extraction
→ topic 기반 chunk 생성
→ embedding_text 개선
→ pgvector 저장
→ 실제 질문 기반 검색 평가
```

그리고 `embedding_text`를 검색 목적에 맞게 조정하는 것만으로도 대표 질문의 top1 결과가 개선되는 것을 확인했습니다.

다음 단계에서 더 중요한 것은 단순히 chunk를 더 많이 만드는 것이 아니라, 평가 케이스를 기준으로 어떤 실패가 남아 있는지 확인하면서 split, re-rank, citation 노출을 차례로 판단하는 일이라고 봅니다.
