# MVP2 Backend Upgrade Plan

> 상태: 초안
> 작성일: 2026-08-03
> 목적: MVP 채팅/Tool 기본 틀 이후 RAG, 검색 품질, 프롬프트, 관측성을 단계적으로 개선하기 위한 계획

## 1. 배경

MVP1 기획 문서는 `find_kbo_game` 단일 Tool과 로그인 사용자 온보딩을 중심으로 시작했다.

현재 구현 흐름은 그보다 넓어졌다.

```text
POST /api/v1/chat
SSE streaming
guest_id 기반 conversation
Tool 실행 이벤트
Tool 결과 card layout
find_kbo_game
get_stadium_info
get_weather_context
search_ticketing_guide
search_stadium_guide
search_baseball_knowledge
```

따라서 MVP2는 새 기능을 무작정 늘리는 단계가 아니라, 이미 만든 Tool 기반 채팅 흐름의 품질을 측정하고 개선하는 단계로 둔다.

## 2. MVP2 목표

MVP2의 목표는 "Tool을 더 많이 붙이는 것"이 아니다.

핵심 목표:

```text
1. 대표 질문에 대해 Tool 선택, 검색 결과, 최종 답변 품질을 재현 가능하게 평가한다.
2. RAG Tool의 semantic-only 검색 한계를 확인하고 hybrid search로 개선한다.
3. 검색 후보가 늘어난 뒤 lightweight re-rank 또는 reranker 도입 여부를 판단한다.
4. 프롬프트를 Tool 결과 기반 답변 생성에 맞게 정리한다.
5. LangChain/LangGraph는 필요한 부분만 비교 도입한다.
6. 관측 로그를 남겨 latency, 실패 원인, 검색 품질을 추적한다.
```

## 3. 우선순위

### 3.1 평가와 관측 먼저

검색 품질 개선 전에 기준 질문과 로그 구조를 먼저 만든다.

필요한 평가셋:

```text
tool routing 평가셋
search_baseball_knowledge 검색 평가셋
search_stadium_guide 검색 평가셋
search_ticketing_guide 검색 평가셋
chat end-to-end 수동 시나리오
```

기록할 지표:

```text
selected_tool
expected_tool
tool_input
retrieved_chunk_ids
expected_chunk_ids 또는 expected_topic_ids
top_k distance/score
answerable
limitations
assistant_response
latency_ms
error_code
```

초기에는 운영용 observability보다 로컬 평가 run 파일을 우선한다.

### 3.2 RAG 검색 baseline 고정

각 RAG Tool마다 현재 검색 상태를 baseline으로 저장한다.

대상 Tool:

```text
search_baseball_knowledge
search_stadium_guide
search_ticketing_guide
```

완료 조건:

```text
대표 질문 15~30개
top1_accuracy 또는 top3_accuracy 기록
실패 케이스 목록 저장
동일 평가셋으로 재실행 가능
```

### 3.3 하이브리드 서치

semantic vector search만으로는 고유명사와 짧은 키워드 질의에서 흔들릴 수 있다.

MVP2에서는 PostgreSQL full-text search 또는 별도 lexical score를 vector search와 섞는 방식을 검토한다.

후보 방식:

```text
vector search top_k
keyword/full-text search top_k
RRF 또는 weighted score로 merge
metadata filter는 기존처럼 Tool별로 유지
```

우선 적용 후보:

```text
구장명
팀명
좌석명
예매처
야구 용어
topic_id
search_keywords
example_questions
```

### 3.4 Re-rank

re-rank는 검색 후보가 충분히 좋아진 뒤 적용한다.

초기 후보:

```text
metadata keyword match 기반 lightweight re-rank
topic_id exact match boost
source trust boost
document_type priority
```

외부 reranker API나 LLM 기반 re-rank는 비용과 latency가 생기므로, 평가셋에서 필요성이 확인된 뒤 도입한다.

### 3.5 프롬프트 개선

프롬프트는 Tool routing과 최종 답변 생성을 분리해서 개선한다.

개선 방향:

```text
Tool을 호출해야 하는 질문과 일반 답변 질문 구분
Tool 결과에 없는 내용은 추측하지 않기
출처와 한계 표시
날짜, 구장, 팀이 애매하면 한 번에 하나만 되묻기
Tool card용 구조화 결과와 assistant 자연어 답변 분리
```

현재 `/api/v1/chat`은 Tool 결과 요약을 `assistant.delta`로 보내는 기본 흐름이다. MVP2에서는 Tool 결과를 바탕으로 LLM이 자연어 답변을 생성하는 단계를 붙이되, 원문 chunk와 Tool result를 그대로 노출하지 않도록 안전한 prompt contract를 둔다.

### 3.6 LangChain 또는 LangGraph

LangChain/LangGraph는 전체 구조를 갈아엎기 위한 목적이 아니다.

도입 판단 기준:

```text
Tool 수가 늘어 orchestration 코드가 복잡해졌는가
retriever/reranker/tracing adapter를 쓰는 편이 단순한가
대화 상태와 step 실행을 그래프로 표현할 필요가 있는가
평가와 trace 연동에 이점이 있는가
```

도입 방식:

```text
1. 현재 직접 구현한 Tool contract와 service는 유지한다.
2. 검증된 Tool만 LangChain Structured Tool로 감싼다.
3. 동일 평가셋으로 직접 orchestration과 LangChain 버전을 비교한다.
4. latency, 실패율, 디버깅 난이도를 보고 계속 사용할지 결정한다.
```

## 4. 단계별 작업안

### Step 1. 평가셋과 run 저장

```text
data/baseball_knowledge/evaluation/cases/search_baseball_knowledge_cases.jsonl
data/stadium_guide/evaluation/cases/search_stadium_guide_cases.jsonl
data/ticketing_guide/evaluation/cases/search_ticketing_guide_cases.jsonl
data/chat/evaluation/cases/chat_mvp_cases.jsonl
```

결과는 `data/**/evaluation/runs/` 아래에 timestamp와 model/search 설정을 포함해 저장한다.

### Step 2. Chat event 관측 로그

`POST /api/v1/chat` 실행 중 아래 이벤트를 내부 로그로 남긴다.

```text
conversation_created
message_created
tool_started
tool_completed
tool_failed
assistant_completed
stream_failed
```

운영 DB table을 바로 만들기보다, 우선 구조화 logging 또는 local run 파일로 시작한다.

### Step 3. RAG Tool별 baseline 측정

각 Tool의 현재 semantic search 결과를 저장한다.

완료 기준:

```text
평가셋이 git에 남아 있다.
baseline run 파일이 남아 있다.
실패 케이스가 사람이 읽을 수 있게 정리되어 있다.
```

### Step 4. Hybrid search 실험

검색 pipeline을 교체하기 전에 실험 스크립트로 비교한다.

비교 대상:

```text
semantic only
lexical only
semantic + lexical RRF
semantic + metadata boost
```

### Step 5. Re-rank 실험

하이브리드 검색 후에도 실패하는 케이스를 대상으로만 re-rank를 검토한다.

### Step 6. Prompt와 답변 생성 개선

SSE event 흐름은 유지한다.

```text
tool.started
tool.completed
assistant.delta
assistant.completed
done
```

단, `assistant.delta`는 단순 Tool 요약이 아니라 Tool result와 retrieved source를 바탕으로 생성한 최종 답변 chunk가 되도록 개선한다.

### Step 7. LangChain/LangGraph 비교 도입

직접 구현한 orchestration이 충분히 안정된 뒤 실험 브랜치 또는 별도 adapter로 비교한다.

## 5. MVP2에서 바로 하지 않을 것

```text
로그인 필수화
사용자별 private RAG
좌석 최종 추천 엔진
지도/교통 API
실시간 티켓 잔여석
운영용 dashboard
LangChain 전면 전환
외부 reranker API 선도입
```

로그인은 나중에 붙이기 어렵지 않게 `guest_id`와 `conversation_id` 흐름을 유지하고, 로그인 후 guest conversation을 user account에 귀속할 수 있는 구조만 고려한다.

## 6. 완료 조건

MVP2 완료 기준:

```text
대표 chat 시나리오가 SSE로 end-to-end 동작한다.
Tool card가 실제 Tool event로 렌더링된다.
RAG Tool별 baseline 평가셋과 run 결과가 있다.
하이브리드 서치 적용 전후 결과를 같은 평가셋으로 비교했다.
프롬프트가 Tool 결과 기반 답변 생성으로 분리되었다.
실패 케이스와 다음 개선 후보가 문서로 남아 있다.
```

## 7. 다음 작업

가장 먼저 할 일:

```text
1. 프론트엔드에서 POST /api/v1/chat SSE stream을 연결한다.
2. 실제 tool.started/tool.completed 이벤트로 Tool card를 렌더링한다.
3. search_baseball_knowledge 평가셋과 평가 스크립트를 만든다.
4. 현재 semantic search baseline run을 저장한다.
```
