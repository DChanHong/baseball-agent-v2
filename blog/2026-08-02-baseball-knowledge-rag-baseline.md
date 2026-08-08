# 2026-08-02 작업 로그: 야구 지식 RAG Tool 초기 세팅과 개선 전 baseline

## 오늘의 목표

`search_baseball_knowledge` Tool의 초기 구현 상태를 기록한다.

이후 검색 품질 개선 작업을 진행하기 전에, 현재 데이터 구성, embedding 방식, Tool 연결 상태, 대표 질문 검색 결과를 baseline으로 남겨둔다.

## 왜 이 기록을 남기는가

야구 지식 RAG는 단순히 "검색이 된다"와 "좋은 답변 근거를 찾는다" 사이의 차이가 크다.

현재 Tool은 공식 PDF 기반 chunk를 pgvector에 넣고 실제 검색까지 동작하지만, 일부 질문에서 top-1 ranking이 기대와 다르게 나온다. 개선 전 상태를 남겨두면, 이후 chunk 구성이나 embedding text를 바꿨을 때 품질이 실제로 좋아졌는지 비교할 수 있다.

## 작업 전후 맥락

야구 지식 RAG의 원본 PDF는 repo에 포함하지 않고, 로컬 디렉터리에서 재생성했다.

```text
/Users/root1/desktop/야구지식-RAG용
```

사용한 PDF:

```text
2024_야구규칙.pdf
2025_야구규칙.pdf
2026_야구규칙.pdf
2024_리그규정.pdf
2025_리그규정.pdf
2026_리그규정.pdf
```

실행한 파이프라인:

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/backend
uv run python scripts/baseball_knowledge/extract_pdf_pages.py --pdf-dir /Users/root1/desktop/야구지식-RAG용 --strict
uv run python scripts/baseball_knowledge/generate_chunks.py --strict
uv run python scripts/baseball_knowledge/embed_chunks.py --dry-run
uv run python scripts/baseball_knowledge/embed_chunks.py --env-file .env
```

## 현재 DB 상태

새 테이블은 추가하지 않았다.

기존 RAG 공용 테이블을 사용한다.

```text
public.rag_documents
public.rag_chunks
```

embedding vector는 `rag_chunks.embedding`에 저장된다.

upsert 결과:

```text
baseball_rule 10
common_play 9
latest_kbo_rule 8
total 27
```

embedding 설정:

```text
model: text-embedding-3-small
dimensions: 1536
```

## 현재 Tool 구현 상태

추가한 Tool:

```text
search_baseball_knowledge
```

파일:

```text
backend/app/domains/baseball/tool/search_baseball_knowledge/
  __init__.py
  schemas.py
  retriever.py
  handler.py
```

Agent 연결:

```text
backend/app/agent/routing_schemas.py
backend/app/agent/tool_cards.py
backend/app/agent/prompts.py
backend/app/agent/tool_executor.py
backend/app/api/dependencies.py
```

입력 schema:

```json
{
  "query": "보크가 뭐야?",
  "knowledge_types": ["common_play"],
  "top_k": 5
}
```

지원 `knowledge_types`:

```text
baseball_rule
common_play
latest_kbo_rule
```

검색 대상:

```sql
document_type in ('baseball_rule', 'common_play', 'latest_kbo_rule')
stadium_id is null
team_id is null
review_status != 'rejected'
embedding is not null
```

현재 relevance threshold:

```text
0.82
```

구장 가이드 RAG에서 쓰던 `0.65`로는 야구 지식 PDF chunk가 대부분 걸러졌다. 예를 들어 "보크가 뭐야?"의 정답 chunk distance가 약 `0.7444`라서, 야구 지식 Tool 전용 threshold를 더 넉넉하게 잡았다.

## Routing 연결 확인

기존 routing 평가셋에 `search_baseball_knowledge` 케이스를 추가했다.

```text
data/kbo_schedule/evaluation/cases/find_kbo_game_cases.jsonl
```

평가 실행 결과:

```text
data/kbo_schedule/evaluation/runs/tool_routing/find_kbo_game/2026-08-02_032830_gpt-5-mini_baseball-knowledge-v1.json
```

결과:

```text
total=32
exact_match_accuracy=0.9688
failed_case_ids=fg_012
```

새로 추가한 야구 지식 routing 케이스는 모두 통과했다.

```text
보크가 뭐야? -> search_baseball_knowledge / common_play
피치클락 위반하면 어떻게 돼? -> search_baseball_knowledge / latest_kbo_rule
볼이랑 스트라이크가 뭐야? -> search_baseball_knowledge / baseball_rule
비 오면 누가 경기 취소를 결정해? -> search_baseball_knowledge / latest_kbo_rule
```

실패한 `fg_012`는 기존 "8월 첫째 주" 날짜 해석 케이스라 이번 Tool과 직접 관련은 없다.

## 개선 전 검색 테스트 결과

아래 결과는 실제 OpenAI query embedding과 로컬 Supabase pgvector 검색으로 확인했다.

### 보크가 뭐야?

```text
answerable: true
limitations: []

top1: 보크
distance: 0.7444
topic_id: common_play_balk

top2: 태그아웃과 포스아웃
distance: 0.7666

top3: 병살과 더블플레이
distance: 0.7726
```

판단:

```text
정상. top1이 기대한 topic이다.
```

### 피치클락 위반하면 어떻게 돼?

```text
answerable: true
limitations: []

top1: 피치클락
distance: 0.6927
topic_id: latest_rule_pitch_clock

top2: ABS
distance: 0.7314

top3: 체크스윙 판독
distance: 0.7866
```

판단:

```text
정상. top1이 기대한 topic이다.
```

### 비 오면 누가 경기 취소를 결정해?

```text
answerable: true
limitations:
- not_official_game_cancellation_decision

top1: 기상 상황 경기취소
distance: 0.5443
topic_id: latest_rule_weather_cancel

top2: 경기 거행 여부 결정 권한
distance: 0.5551

top3: 체크스윙 판독
distance: 0.5752
```

판단:

```text
대체로 정상. top1/top2가 기대한 topic이다.
다만 top3에 체크스윙 판독이 섞이는 것은 개선 여지가 있다.
```

### 볼이랑 스트라이크가 뭐야?

```text
answerable: true
limitations: []

top1: 주자 진루와 귀루
distance: 0.7653
topic_id: basic_rule_runner_advance

top2: 볼과 스트라이크
distance: 0.7704
topic_id: basic_rule_strike_ball

top3: 볼 인플레이와 볼 데드
distance: 0.7760
```

판단:

```text
검색은 되지만 ranking 품질이 아쉽다.
기대 topic인 "볼과 스트라이크"가 top2로 밀렸다.
```

### 인필드 플라이가 왜 선언돼?

```text
answerable: true
limitations: []

top1: 병살과 더블플레이
distance: 0.7620
topic_id: common_play_double_play

top2: 인필드 플라이
distance: 0.7645
topic_id: common_play_infield_fly

top3: 태그아웃과 포스아웃
distance: 0.7882
```

판단:

```text
검색은 되지만 ranking 품질이 아쉽다.
기대 topic인 "인필드 플라이"가 top2로 밀렸다.
```

## 현재 품질 이슈

초기 chunk는 PDF 원문 page slice 중심이다.

장점:

```text
공식 출처 기반이다.
source page citation을 만들기 쉽다.
topic별로 최소 검색은 가능하다.
```

문제:

```text
chunk 본문이 길다.
PDF 원문에는 질문 의도와 직접 관련 없는 주변 조항이 많이 섞인다.
초보자 질문 표현과 공식 문서 표현 사이의 간극이 있다.
embedding distance가 전반적으로 높다.
top1 ranking이 일부 질문에서 흔들린다.
```

현재 징후:

```text
"보크가 뭐야?" -> top1 성공
"피치클락 위반하면 어떻게 돼?" -> top1 성공
"볼이랑 스트라이크가 뭐야?" -> 기대 topic top2
"인필드 플라이가 왜 선언돼?" -> 기대 topic top2
```

## 개선 후보

다음 개선 작업에서 비교할 후보:

```text
1. embedding_text 앞쪽에 topic title, summary, keywords, example_questions를 더 강하게 배치한다.
2. PDF 원문 전체보다 curated beginner explanation을 별도 chunk로 추가한다.
3. topic_id, search_keywords, example_questions 기반 lexical boost를 추가한다.
4. top_k 후보를 가져온 뒤 metadata keyword match로 re-rank한다.
5. 긴 PDF page slice를 section 단위로 더 작게 나눈다.
```

우선순위는 `embedding_text` 개선과 lightweight re-ranking이다.

## 개선 후에 추가할 내용

아래 항목은 개선 작업 이후에 채운다.

```text
변경한 chunk 생성 방식:
재임베딩 여부:
변경 후 DB chunk 수:
변경 후 threshold:
동일 질문 재테스트 결과:
top1 개선 여부:
남은 실패 케이스:
```

## 1차 개선 후 결과

### 변경한 chunk 생성 방식

`embedding_text`를 PDF 원문 전체 중심에서 검색용 요약 중심으로 바꿨다.

변경 전:

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

변경 후:

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

핵심 변화:

```text
title, summary, keywords, example_questions를 embedding_text 앞쪽에 더 강하게 배치했다.
example_questions 외에 "{title}가 뭐야?", "{title} 뜻 알려줘", "{title} 규칙 설명해줘" 같은 검색 패턴을 추가했다.
긴 PDF 원문 전체를 embedding_text에 넣지 않고, 공식 근거 발췌를 2500자까지만 넣었다.
답변/citation용 content는 기존처럼 전체 source page slice를 유지했다.
```

### 재임베딩 여부

`embedding_text`가 바뀌었으므로 OpenAI embedding을 다시 생성하고 같은 `chunk_id`로 upsert했다.

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/backend
uv run python scripts/baseball_knowledge/generate_chunks.py --strict
uv run python scripts/baseball_knowledge/embed_chunks.py --dry-run
uv run python scripts/baseball_knowledge/embed_chunks.py --env-file .env
```

실행 결과:

```text
Wrote 27 chunks
Loaded 27 chunks
Upserted 27 chunks into rag_documents/rag_chunks
```

변경 후 DB chunk 수:

```text
baseball_rule 10
common_play 9
latest_kbo_rule 8
total 27
```

변경 후 threshold:

```text
0.82
```

threshold는 아직 바꾸지 않았다. 이번 1차 개선은 embedding_text 구성 변경만으로 효과를 확인했다.

### 동일 질문 재테스트 결과

#### 보크가 뭐야?

개선 전:

```text
top1: 보크
distance: 0.7444
```

개선 후:

```text
top1: 보크
distance: 0.6660
```

판단:

```text
top1 유지.
distance 개선.
```

#### 피치클락 위반하면 어떻게 돼?

개선 전:

```text
top1: 피치클락
distance: 0.6927
```

개선 후:

```text
top1: 피치클락
distance: 0.6862
```

판단:

```text
top1 유지.
distance 소폭 개선.
```

#### 비 오면 누가 경기 취소를 결정해?

개선 전:

```text
top1: 기상 상황 경기취소
distance: 0.5443

top2: 경기 거행 여부 결정 권한
distance: 0.5551

top3: 체크스윙 판독
distance: 0.5752
```

개선 후:

```text
top1: 기상 상황 경기취소
distance: 0.5342

top2: 노게임과 서스펜디드
distance: 0.5588

top3: 경기 거행 여부 결정 권한
distance: 0.5629
```

판단:

```text
top1 유지.
top3에 섞였던 체크스윙 판독이 빠지고, 더 관련 있는 경기 중단/결정 권한 topic으로 바뀌었다.
```

#### 볼이랑 스트라이크가 뭐야?

개선 전:

```text
top1: 주자 진루와 귀루
distance: 0.7653

top2: 볼과 스트라이크
distance: 0.7704
```

개선 후:

```text
top1: 볼과 스트라이크
distance: 0.7111

top2: 득점 조건
distance: 0.7646

top3: 주자 진루와 귀루
distance: 0.7661
```

판단:

```text
기대 topic이 top2에서 top1로 올라왔다.
distance도 크게 개선됐다.
```

#### 인필드 플라이가 왜 선언돼?

개선 전:

```text
top1: 병살과 더블플레이
distance: 0.7620

top2: 인필드 플라이
distance: 0.7645
```

개선 후:

```text
top1: 인필드 플라이
distance: 0.7256

top2: 병살과 더블플레이
distance: 0.7457
```

판단:

```text
기대 topic이 top2에서 top1로 올라왔다.
distance도 개선됐다.
```

### 넓은 질문 확인

질문:

```text
야구 규칙 알려줘
```

개선 후 결과:

```text
answerable: true

top1: 야구 경기의 목적
distance: 0.5210

top2: 페어와 파울
distance: 0.5566

top3: 득점 조건
distance: 0.5621

top4: 아웃카운트
distance: 0.5714

top5: 볼 인플레이와 볼 데드
distance: 0.5765
```

판단:

```text
넓은 야구 규칙 질문도 계속 정상 검색된다.
```

### 1차 개선 요약

```text
대표 질문 5개 중 top1 성공: 3/5 -> 5/5
기존 top2 실패였던 "볼과 스트라이크", "인필드 플라이"가 top1로 개선됐다.
재임베딩 후 chunk 수는 27개로 유지됐다.
threshold는 0.82 그대로 유지했다.
```

남은 개선 후보:

```text
1. top2/top3에 남는 약한 관련 chunk를 줄이기 위해 threshold 재조정 검토
2. metadata keyword 기반 lightweight re-rank 검토
3. 초보자용 curated explanation chunk 추가 검토
4. 검색 평가셋 15~20개를 별도 파일로 만들고 자동 평가 지표 관리
```

## Chunk 진단

1차 개선 후 바로 추가 split이나 re-rank를 넣을지 판단하기 위해 현재 chunk 상태를 확인했다.

진단 대상:

```text
data/baseball_knowledge/embedded_input/baseball_knowledge_chunks.jsonl
```

전체 chunk 수:

```text
total_chunks: 27
```

content 길이 기준 상위 chunk:

```text
보크                         content 6289 / embed 2750 / pages 7
주자 진루와 귀루 idx0         content 6262 / embed 2820 / pages 7
도루와 견제 idx0              content 6058 / embed 2805 / pages 7
노게임과 서스펜디드 idx0       content 5755 / embed 2847 / pages 11
볼과 스트라이크               content 5694 / embed 2816 / pages 7
태그아웃과 포스아웃 idx0       content 5581 / embed 2848 / pages 6
정식경기와 노게임             content 5504 / embed 2813 / pages 8
```

split된 topic:

```text
주자 진루와 귀루: 2 chunks / total 11655 chars / 13 pages
도루와 견제: 2 chunks / total 7647 chars / 9 pages
태그아웃과 포스아웃: 2 chunks / total 9632 chars / 10 pages
노게임과 서스펜디드: 2 chunks / total 9260 chars / 15 pages
```

대표 질문별 top 후보도 함께 봤다.

```text
보크가 뭐야?
top1: 보크
top2: 태그아웃과 포스아웃
top3: 인필드 플라이

볼이랑 스트라이크가 뭐야?
top1: 볼과 스트라이크
top2: 득점 조건
top3: 주자 진루와 귀루

인필드 플라이가 왜 선언돼?
top1: 인필드 플라이
top2: 병살과 더블플레이

비 오면 누가 경기 취소를 결정해?
top1: 기상 상황 경기취소
top2: 노게임과 서스펜디드
top3: 경기 거행 여부 결정 권한
```

진단:

```text
긴 chunk는 일부 존재한다.
하지만 1차 개선 후 대표 질문 5개는 모두 기대 topic이 top1이다.
top2/top3에 섞이는 chunk도 대부분 같은 규칙 범주 안에서 약하게 관련된 topic이다.
현재 상태에서는 chunk split이나 re-rank를 즉시 넣을 정도의 큰 문제는 아니다.
```

이번에 하지 않기로 한 것:

```text
re-rank 도입
threshold 재조정
MAX_CONTENT_CHARS 하향
topic 추가 분할
curated explanation chunk 추가
```

보류 이유:

```text
대표 질문 기준 top1 품질이 이미 개선됐다.
추가 split은 DB chunk 수와 평가 복잡도를 늘린다.
re-rank는 외부 API나 수작업 boost 정책이 들어가므로 현재 단계에서는 과하다.
먼저 검색 평가셋을 만든 뒤, 실제 실패 케이스가 쌓이면 그때 적용하는 편이 안전하다.
```

## 현재 결론

`search_baseball_knowledge`는 초기 Tool로 사용할 수 있는 수준까지 왔다.

현재 기준:

```text
PDF 기반 공식 출처 chunk 27개
OpenAI embedding + Supabase pgvector upsert 완료
Agent routing 연결 완료
대표 검색 질문 5개 top1 성공
넓은 "야구 규칙 알려줘" 질문도 정상 검색
```

다음 우선순위는 chunk를 더 쪼개는 것이 아니라, 검색 품질을 지속적으로 볼 수 있는 평가셋과 평가 스크립트를 만드는 것이다.

후속 작업 후보:

```text
1. data/baseball_knowledge/evaluation/cases/search_baseball_knowledge_cases.jsonl 작성
2. backend/scripts/baseball_knowledge/evaluate_search_baseball_knowledge.py 작성
3. 현재 상태를 검색 품질 baseline run으로 저장
4. 실패 케이스가 명확해진 뒤 chunk split, threshold, re-rank, curated chunk 중 선택
```

## 다음 블로그 정리 후보

이번 글은 `search_baseball_knowledge`의 검색 품질 baseline과 1차 embedding_text 개선까지로 닫는다.

이후 별도 글로 정리할 만한 내용:

```text
1. POST /api/v1/chat SSE 스트리밍 엔드포인트 설계와 구현
2. tool.started / tool.completed / assistant.delta 이벤트 계약
3. 백엔드 Tool 결과 schema와 프론트 Tool 카드 layout 분리
4. guest_id 기반 MVP 채팅 세션 흐름
5. RAG 품질 개선 전에 평가셋과 관측 로그를 먼저 만드는 이유
```

아직 별도 글로 쓸 만큼 결과가 쌓인 것은 아니지만, 다음 개발 흐름은 "채팅 스트리밍 계약과 Tool 카드 렌더링" 또는 "RAG 검색 평가셋 자동화" 중 하나로 묶으면 좋다.
