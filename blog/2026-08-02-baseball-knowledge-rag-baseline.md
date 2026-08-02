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
