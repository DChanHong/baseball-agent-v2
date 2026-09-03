# MVP2 Backend Upgrade Plan

> 라벨: `MVP2`  
> 상태: 계획 유지
> 작성일: 2026-08-03
> 최근 업데이트: 2026-09-03
> 목적: MVP 채팅/Tool 기본 틀 이후 운영 데이터 최신성, 실사용 QA, 관측성, 평가, RAG, 보안, Agent orchestration을 단계적으로 개선하기 위한 계획

## 1. 배경

MVP1 기획 문서는 `find_kbo_game` 단일 Tool과 로그인 사용자 온보딩을 중심으로 시작했다.

현재 구현 흐름은 그보다 넓어졌다.

```text
POST /api/v1/chat
SSE streaming
로그인 사용자 `user_profile_id` 기반 conversation
Tool 실행 이벤트
Tool 결과 card layout
find_kbo_game
get_stadium_info
get_weather_context
search_ticketing_guide
search_stadium_guide
search_baseball_knowledge
```

따라서 MVP2는 새 기능을 무작정 늘리는 단계가 아니라, 이미 만든 Tool 기반 채팅 흐름을 실제 사용 기준으로 점검하고, 운영 데이터와 Agent 품질을 단계적으로 개선하는 단계로 둔다.

특히 MVP1은 구현상 1차 완료로 볼 수 있지만, 아직 사용자가 실제 서비스처럼 충분히 흔들어 본 상태는 아니다. 그러므로 MVP2의 첫 단계는 평가 baseline 고정이 아니라, 운영에 필요한 빈칸을 먼저 메우고 실사용 QA로 실패 케이스를 수집하는 것이다.

## 2. MVP2 목표

MVP2의 목표는 "Tool을 더 많이 붙이는 것"이 아니다.

핵심 목표:

```text
1. KBO 경기 일정/상태 데이터를 주기적으로 갱신해 find_kbo_game Tool의 신뢰도를 유지한다.
2. 실제 사용 QA로 잘 되는 질문, 애매한 질문, 실패 질문을 수집하고 실패 유형을 분류한다.
3. LangChain/LangGraph 구조를 현재 코드와 비교하며 필요한 부분만 깊게 검토한다.
4. 관측 로그를 남겨 Tool 선택, latency, 실패 원인, 검색 품질을 추적한다.
5. 대표 질문에 대해 Tool 선택, 검색 결과, 최종 답변 품질을 재현 가능하게 평가한다.
6. RAG Tool의 semantic-only 검색 한계를 확인하고 hybrid search, query rewrite, fallback, reranking을 실험한다.
7. 최종 답변이 Tool 결과와 RAG source에 근거하도록 Citation / Grounded Answer 구조를 만든다.
8. Prompt Injection, Tool Abuse, 데이터 유출, RAG source trust를 포함한 LLM Agent Security 기준을 세운다.
9. 충분한 관측과 평가 기반이 생긴 뒤 제한된 multi-step Agent orchestration을 도입한다.
```

## 3. 우선순위

### 3.1 운영 데이터 파이프라인 먼저

검색 품질이나 Agent 구조를 개선하기 전에, 정형 Tool이 의존하는 운영 데이터가 낡지 않도록 만든다.

우선 대상은 `find_kbo_game`의 기반 데이터인 KBO 경기 일정과 상태다.

처리 흐름:

```text
KBO 공식 일정 API 수집
→ raw 응답 확인 또는 저장
→ normalized game 변환
→ kbo_games upsert
→ 상태/스코어 변경 시 kbo_game_status_history 기록
→ find_kbo_game Tool이 최신 DB 조회
```

1차 구현 범위:

```text
특정 season_year/month 수동 sync
오늘 경기만 sync
dry-run
inserted / updated / unchanged / status_history count 출력
source_collected_at 갱신
Render Cron Job 또는 동등한 스케줄러 연결
```

보완 가능한 V2 역량:

```text
운영 데이터 최신성: 높음
Structured DB Tool 신뢰도: 높음
상태 변경 이력: 높음
데이터 파이프라인 관측성: 중간~높음
find_kbo_game 회귀 테스트: 중간
```

이 단계만으로 Advanced RAG, Citation, Security, Agentic Loop 전체를 해결하지는 못한다. 다만 운영형 Agent 프로젝트의 기반 작업으로 먼저 처리한다.

### 3.2 실사용 QA와 실패 케이스 수집

MVP1은 구현 완료 상태지만 실제 사용 관점의 충분한 검증은 아직 부족하다.

평가셋을 먼저 고정하기 전에 직접 사용하면서 실패 케이스 후보를 수집한다.

분류 기준:

```text
Tool routing 문제
Tool input 추출 문제
정형 데이터 최신성 문제
RAG 검색 실패
RAG 근거 부족
최종 답변 품질 문제
출처/한계 표시 문제
UI/SSE 표시 문제
보안/정책 위험
```

결과는 바로 정식 evaluation case로 넣지 않고, 먼저 사람이 읽을 수 있는 QA log 또는 candidate로 남긴다.

### 3.3 LangChain / LangGraph 구조 검토

LangChain/LangGraph는 전체 구조를 갈아엎기 위한 목적이 아니다.

이미 LangGraph StateGraph를 사용하고 있으므로, V2에서는 "라이브러리를 붙였다"가 아니라 "왜 이 구조가 필요한지 설명할 수 있다"를 목표로 한다.

검토 항목:

```text
State schema
node 책임 분리
conditional edge
tool calling abstraction
recursion_limit
checkpoint / memory
streaming event 연결
LangSmith trace 연동 가능성
```

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
2. 검증된 Tool만 LangChain Structured Tool로 감싸는 실험을 한다.
3. 동일 QA/evaluation case로 직접 orchestration과 LangChain adapter를 비교한다.
4. latency, 실패율, 디버깅 난이도를 보고 계속 사용할지 결정한다.
```

### 3.4 Observability

실사용 QA 이후에는 "왜 느렸고, 왜 틀렸고, 어떤 Tool을 선택했는지" 추적할 수 있어야 한다.

초기에는 운영용 dashboard보다 구조화 로그 또는 local run 파일을 우선한다.

기록할 지표:

```text
request_id
conversation_id
message_id
selected_tool
expected_tool 또는 manual_label
tool_input
tool status
tool latency_ms
retrieval query
retrieved_chunk_ids
top_k distance/score
answerable
limitations
assistant_response
LLM model
token usage 가능 시 기록
error_code
```

최소 완료 기준:

```text
한 chat 요청의 route → tool → retrieval → answer 흐름을 하나의 ID로 추적할 수 있다.
```

LangSmith, OpenTelemetry, 자체 DB/JSON trace는 비교 후보로 둔다. 처음부터 외부 관측 도구를 강제하지 않는다.

### 3.5 Evaluation Baseline

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

단, 이 단계는 실사용 QA 이후에 진행한다. 실제로 깨진 질문을 evaluation case 후보로 승격해야 평가셋이 프로젝트 문제를 잘 반영한다.

### 3.6 RAG 검색 baseline 고정

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

### 3.7 하이브리드 서치

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

### 3.8 Query Rewrite / Retrieval Fallback

짧거나 생략된 follow-up 질문은 현재 대화 context를 검색 query에 반영해야 한다.

예:

```text
사용자: 오늘 롯데 경기 있어?
Agent context: selected_game, selected_stadium_id=SAJIK

사용자: 거기 주차 돼?
검색 query 후보: 사직야구장 주차 안내
```

먼저 비교할 것:

```text
Raw Query
Context-enriched Query
LLM Rewritten Query
```

검색 실패 시에는 무조건 retry하지 않고 조건부 fallback을 둔다.

```text
Vector Search
→ No Result
→ Hybrid Search
→ Still No Result
→ answerable=false
```

또는

```text
Query Rewrite
→ Re-search
```

완료 기준:

```text
무조건 retry가 아닌 조건 기반 fallback
최대 검색 횟수 제한
fallback reason 기록
평가셋으로 효과 검증
```

### 3.9 Re-rank

re-rank는 검색 후보가 충분히 좋아진 뒤 적용한다.

초기 후보:

```text
metadata keyword match 기반 lightweight re-rank
topic_id exact match boost
source trust boost
document_type priority
```

외부 reranker API나 LLM 기반 re-rank는 비용과 latency가 생기므로, 평가셋에서 필요성이 확인된 뒤 도입한다.

### 3.10 Citation / Grounded Answer

현재 V1은 Tool Card 안에서 Evidence와 `source_urls`를 보여주지만, 최종 자연어 답변과 Source 연결은 약하다.

1차 목표:

```json
{
  "answer": "...",
  "sources": [
    {
      "chunk_id": "...",
      "title": "...",
      "source_urls": ["..."]
    }
  ],
  "limitations": []
}
```

2차 목표:

```text
사직야구장은 부산 도시철도 3호선 사직역에서 접근할 수 있습니다. [1]
```

구현 고려사항:

```text
동일 source 중복 제거
최종 답변에 실제 사용된 source만 노출
Tool Evidence와 Final Source 연결
Source 없는 claim 최소화
근거 문서에 없는 내용은 limitation으로 표시
```

평가 후보:

```text
Citation Correctness
Citation Coverage
Faithfulness
Groundedness
Forbidden claim 포함 여부
```

### 3.11 LLM Agent Security

V2에는 LLM Agent Security를 별도 축으로 포함한다.

대상 위협:

```text
Prompt Injection
RAG 문서 안의 악성 지시
Jailbreak성 사용자 입력
Tool Abuse
과도한 Tool 반복 호출
민감정보 유출
검증되지 않은 source trust
오래된 데이터 기반 확정 답변
```

1차 적용 범위:

```text
prompt에서 system instruction / user input / tool result / retrieved document 구분 명확화
RAG 문서는 명령이 아니라 참고 근거로만 취급
Tool input schema validation 강화
Tool execution policy 문서화
Tool별 timeout / max call / retry 가능 오류 구분
환경변수, cookie, token, 사용자 개인정보가 prompt/log/evaluation case에 들어가지 않도록 차단
source_url, trust_level, review_status, as_of, source_collected_at 기반 source trust 정책 정리
Prompt Injection / Tool Abuse / Data Leakage 평가 케이스 추가
```

KBO Mate에서 특히 중요한 답변 정책:

```text
날씨 정보만 보고 경기 취소를 확정하지 않는다.
KBO 일정 상태 또는 공식 공지 없이 취소/연기/지연을 확정하지 않는다.
예매/환불/반입 정책은 source와 기준 시점을 함께 표시한다.
사용자 요청이 있어도 시스템 프롬프트, secret, token, 내부 설정은 공개하지 않는다.
```

### 3.12 프롬프트 개선

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

### 3.13 제한된 Agentic Loop / Agent Orchestration

V2에서는 무조건 Autonomous Agent로 확장하지 않는다.

여러 Tool이 정말 필요한 질문에서만 제한된 multi-step 실행을 허용한다.

예:

```text
오늘 잠실 경기 있는데 비 올까?
```

필요한 정보:

```text
1. 경기 조회
2. 경기 구장 확인
3. 날씨 조회
4. 필요 시 공식 공지 확인
5. 최종 답변
```

반드시 함께 구현할 제어 장치:

```text
max_steps
max_tool_calls
recursion_limit
termination_reason
failure_reason
same_tool_repeat_limit
loop detection
tool timeout
LLM timeout
Graph/Turn timeout
retry_count
transient/permanent failure 구분
```

Human-in-the-loop은 KBO Mate에서 억지로 넣지 않는다. 실제 action tool이 생기는 별도 프로젝트 또는 후속 단계에서 다룬다.

## 4. 단계별 작업안

### Step 0. 경기 일정 갱신 파이프라인

KBO 일정/상태를 수집하고 `kbo_games`에 갱신하는 worker 또는 CLI를 만든다.

구현 범위:

```text
KBO 일정 API client
월별 schedule 수집
오늘 경기 필터
정규화 parser
기존 kbo_schedule_import upsert 로직 재사용
dry-run
sync 결과 요약 출력
Render Cron Job 또는 동등한 스케줄러 연결
```

검증:

```text
특정 월 dry-run
오늘 경기 dry-run
동일 데이터 재실행 시 unchanged 확인
상태 변경 시 kbo_game_status_history 기록 확인
find_kbo_game이 갱신된 데이터로 응답하는지 확인
```

### Step 1. 실사용 QA와 실패 케이스 후보 수집

사용자가 실제 서비스처럼 질문을 던지고 결과를 기록한다.

```text
30~50개 대표 질문
잘 됨 / 애매함 / 실패 분류
실패 유형 라벨링
평가셋 승격 후보 표시
```

### Step 2. LangChain / LangGraph Deep Dive

현재 StateGraph와 LangChain/LangGraph 문서를 비교하며 구조를 정리한다.

```text
현재 node/edge/state 구조 문서화
LangChain Structured Tool adapter 실험 후보 정리
LangSmith trace 도입 가능성 검토
전면 전환이 아니라 비교 도입 기준 작성
```

### Step 3. Agent trace / Observability

`POST /api/v1/chat` 실행 중 아래 이벤트와 지표를 하나의 trace로 묶어 남긴다.

```text
conversation_created
message_created
route_started
route_completed
tool_started
tool_completed
tool_failed
retrieval_completed
assistant_completed
stream_failed
```

운영 DB table을 바로 만들기보다, 우선 구조화 logging 또는 local run 파일로 시작한다.

### Step 4. 평가셋과 run 저장

```text
data/baseball_knowledge/evaluation/cases/search_baseball_knowledge_cases.jsonl
data/stadium_guide/evaluation/cases/search_stadium_guide_cases.jsonl
data/ticketing_guide/evaluation/cases/search_ticketing_guide_cases.jsonl
data/chat/evaluation/cases/chat_mvp_cases.jsonl
```

결과는 `data/**/evaluation/runs/` 아래에 timestamp와 model/search 설정을 포함해 저장한다.

### Step 5. RAG Tool별 baseline 측정

각 Tool의 현재 semantic search 결과를 저장한다.

완료 기준:

```text
평가셋이 git에 남아 있다.
baseline run 파일이 남아 있다.
실패 케이스가 사람이 읽을 수 있게 정리되어 있다.
```

### Step 6. Hybrid search 실험

검색 pipeline을 교체하기 전에 실험 스크립트로 비교한다.

비교 대상:

```text
semantic only
lexical only
semantic + lexical RRF
semantic + metadata boost
```

### Step 7. Query Rewrite / Retrieval Fallback 실험

실사용 QA와 retrieval baseline에서 확인된 짧은 질문과 실패 케이스를 대상으로 한다.

```text
raw query
context-enriched query
LLM rewritten query
no-result fallback
fallback reason
max search attempts
```

### Step 8. Re-rank 실험

하이브리드 검색 후에도 실패하는 케이스를 대상으로만 re-rank를 검토한다.

### Step 9. Citation / Grounded Answer

최종 답변과 source를 연결한다.

```text
answer
sources
limitations
forbidden_claims
required_sources
```

Tool card evidence와 assistant 답변 source가 같은 근거를 공유하도록 한다.

### Step 10. LLM Agent Security

보안 정책과 평가 케이스를 추가한다.

```text
prompt injection case
RAG injection case
tool abuse case
data leakage case
source trust case
```

### Step 11. Prompt와 답변 생성 개선

SSE event 흐름은 유지한다.

```text
tool.started
tool.completed
assistant.delta
assistant.completed
done
```

단, `assistant.delta`는 단순 Tool 요약이 아니라 Tool result와 retrieved source를 바탕으로 생성한 최종 답변 chunk가 되도록 개선한다.

### Step 12. 제한된 Multi-step Agent

관측과 평가 기반이 생긴 뒤 시작한다.

```text
find_kbo_game → get_weather_context
find_kbo_game → search_stadium_guide
find_kbo_game → search_ticketing_guide
find_kbo_game → official_notice 후보
```

반드시 max step, timeout, retry policy, termination reason을 함께 남긴다.

### Step 13. True Streaming / CI / Regression Automation

마지막에 운영 완성도를 보강한다.

```text
LLM astream 기반 assistant.delta
Time To First Token 측정
Backend ruff / pytest
Frontend lint / typecheck / build
PR smoke evaluation
Manual 또는 release full golden evaluation
```

## 5. MVP2에서 바로 하지 않을 것

```text
로그인 정책 재설계
사용자별 private RAG
좌석 최종 추천 엔진
지도/교통 API
실시간 티켓 잔여석
운영용 dashboard
LangChain 전면 전환
외부 reranker API 선도입
Human-in-the-loop action tool
사용자 채팅 전문 자동 학습
```

로그인은 MVP1에서 Google OAuth + HttpOnly cookie 기반으로 연결됐다. MVP2에서는 `user_profile_id`와 `conversation_id` 기반 소유권 검증을 유지하고, guest-first 채팅 재도입 여부는 별도 제품 판단으로 둔다.

## 6. 완료 조건

MVP2 완료 기준:

```text
KBO 경기 일정/상태 갱신 파이프라인이 수동 실행과 스케줄 실행 기준으로 동작한다.
find_kbo_game이 갱신된 DB 데이터와 source_collected_at을 기반으로 응답한다.
실사용 QA 결과와 실패 케이스 후보가 문서 또는 데이터 파일로 남아 있다.
한 chat 요청의 route → tool → retrieval → answer 흐름을 trace로 추적할 수 있다.
LangChain/LangGraph의 현재 사용 방식과 추가 도입 기준이 정리되어 있다.
대표 chat 시나리오가 SSE로 end-to-end 동작한다.
Tool card가 실제 Tool event로 렌더링된다.
RAG Tool별 baseline 평가셋과 run 결과가 있다.
하이브리드 서치 적용 전후 결과를 같은 평가셋으로 비교했다.
Query Rewrite / Retrieval Fallback / Reranking 도입 여부를 평가 결과로 판단했다.
최종 답변과 source를 연결하는 Citation / Grounded Answer 구조가 있다.
Prompt Injection, Tool Abuse, Data Leakage, Source Trust 관련 security case가 있다.
프롬프트가 Tool 결과 기반 답변 생성으로 분리되었다.
제한된 multi-step tool use에 max step, timeout, retry, termination reason이 포함되어 있다.
실패 케이스와 다음 개선 후보가 문서로 남아 있다.
```

## 7. 다음 작업

가장 먼저 할 일:

```text
1. KBO 경기 일정 갱신 파이프라인 구현 범위를 확정한다.
2. 현재 import_kbo_schedule.py와 kbo_schedule_import 모듈을 기준으로 수집→정규화→upsert 구조를 설계한다.
3. DB migration 추가 여부를 결정한다. raw snapshot table은 유용하지만 초기 sync CLI에서는 선택 사항으로 둔다.
4. Render Cron Job 또는 GitHub Actions schedule 중 1차 스케줄러를 결정한다.
5. dry-run, 오늘 경기 sync, 상태 변경 이력 검증 기준을 먼저 만든다.
```
