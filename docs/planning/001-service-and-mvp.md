# 야구 직관 Agent 서비스 및 MVP 기획

> 상태: MVP1 기준 업데이트
> 작성일: 2026-07-27
> 최근 업데이트: 2026-08-20
> 참고 프로젝트: `my-baseball-agent`
> MVP1 구현 기준: 로그인 사용자 채팅, 단일 `/api/v1/chat` 스트리밍 엔드포인트, LangGraph 기반 Tool 실행, Tool 결과 카드 렌더링

## 1. 문서 목적

야구 팬의 직관 준비를 돕는 Agent가 어떤 문제를 해결할지 정의하고, 현재 MVP1에서 구현된 채팅/Tool/LangGraph 기본 틀과 1차 완료까지 남은 연결 작업을 정리한다.

이 문서는 기존 프로젝트의 기능을 그대로 이식하기 위한 문서가 아니다. `my-baseball-agent`의 데이터 출처, 수집 방식, 실패 사례와 구현 아이디어를 참고하되 데이터 수집과 Tool 계약을 처음부터 다시 검토한다.

## 2. 서비스 정의

### 2.1 한 문장 정의

야구 입문자가 응원할 팀과 직관할 경기를 찾고, 구장 기본 정보, 예매, 응원과 좌석 선택을 단계적으로 준비하도록 돕는 야구 직관 Agent다. 이동 경로 안내는 향후 지도 API를 연결한 뒤 확장한다.

첫 번째 제품의 중심은 `직관 정보 찾기`다. 경기장 밖의 일반 야구 정보도 이후 제공하지만, 초기 MVP의 Tool과 대화 흐름은 사용자가 실제 관람할 경기를 찾고 준비하는 경험을 우선한다.

### 2.2 대상 사용자

- 야구 규칙, 용어와 관람 방법 등 기본 지식이 필요한 입문자
- 아직 응원할 팀을 정하지 못해 팀의 특징을 알아보고 싶은 입문자
- 원하는 팀의 경기를 처음 직관하려는 팬
- 특정 날짜 또는 기간에 볼 수 있는 경기를 찾는 팬
- 익숙하지 않은 구장으로 원정 직관을 가는 팬
- 예매 방법, 응원 구역 또는 좌석 선택이 어려운 팬

### 2.3 해결할 사용자 문제

1. 야구 규칙, 용어, 포지션과 경기 관람 방법 등 기본 지식을 이해한다.
2. KBO 팀별 특징과 연고지 등을 살펴보고 처음 응원할 팀을 고른다.
3. 원하는 팀의 경기 일정과 경기 정보를 찾는다.
4. 경기와 구장의 기본 정보를 확인한다.
5. 팀과 경기별 예매 정보를 찾는다.
6. 응원 문화, 준비물과 관람 팁을 찾는다.
7. 예산과 관람 성향에 맞는 좌석을 추천받는다.

### 2.4 서비스가 지켜야 할 원칙

- 일정, 날짜, 장소, 가격처럼 정확해야 하는 값은 정형 데이터로 조회한다.
- 설명과 근거가 필요한 정보만 문서 검색 및 RAG를 사용한다.
- 정보의 출처와 기준 시점을 가능한 범위에서 표시한다.
- 정보가 없거나 오래되었으면 추측하지 않고 한계를 알린다.
- 사용자의 필수 조건이 부족하면 Tool을 호출하기 전에 질문한다.
- 처음부터 모든 기능을 만들지 않고, 하나의 사용자 흐름을 완성한 후 확장한다.

## 3. 핵심 사용자 여정

최종적으로 지원하려는 대표 흐름은 다음과 같다.

```text
야구 기본 지식 확인(선택)
→ 응원 팀 탐색 및 선택(선택)
→ 선택한 응원 팀을 사용자 프로필에 저장
→ 날짜 또는 기간 입력
→ 경기 일정 조회
→ 경기 선택
→ 구장 기본 정보 확인
→ 예매 정보 확인
→ 응원 및 관람 팁 확인
→ 좌석 후보 비교와 추천
```

이미 응원 팀이 있는 사용자는 기본 지식과 팀 탐색 단계를 건너뛸 수 있다.

응원 팀 선택은 강제하지 않는다. 초기 문서는 guest-first 채팅을 기준으로 했지만, 2026-08-20 현재 구현은 로그인 사용자 기준으로 전환되어 있다. MVP1은 로그인 세션이 있는 사용자가 채팅을 시작하고, 사용자 프로필의 `favorite_team_id`를 라우팅 context로 활용하는 기준으로 정리한다.

MVP1에서는 이 중 `로그인 사용자 채팅 시작 → Tool 라우팅 → LangGraph Tool 실행 이벤트 스트리밍 → Tool 결과 카드 렌더링 → 기본 assistant 응답 저장 → 단일 경기 follow-up context 처리`까지의 틀을 마련했다. 선택형 응원 팀 온보딩, guest conversation 귀속, 좌석 최종 추천은 후속 MVP에서 별도 범위와 Tool을 정의한다.

### 3.1 MVP1 로그인 사용자 채팅 시작

현재 MVP1은 로그인된 사용자가 첫 채팅을 시작하는 흐름을 기준으로 한다. 로그인하지 않은 사용자가 메시지를 보내면 프론트엔드는 로그인 모달을 열고 채팅 요청을 보내지 않는다.

```text
직관할 경기를 함께 찾아볼게요.
원하는 날짜, 지역, 팀, 구장이나 궁금한 야구 정보를 바로 입력해도 돼요.

예시: “다음 주말 서울에서 볼 수 있는 경기 찾아줘”
```

처리 원칙:

- 새 채팅은 `conversation_id = null`로 `/api/v1/chat`을 호출한다.
- 백엔드는 쿠키 기반 인증으로 현재 `user_profile_id`를 확인한다.
- 백엔드는 conversation을 생성하고 SSE로 `conversation.created` 이벤트를 보낸다.
- 이후 같은 대화는 `conversation_id`를 포함해 이어서 호출한다.
- 로그인/프로필 API는 이미 존재하므로 MVP1 채팅은 authenticated-first로 둔다.
- guest-first 채팅과 guest conversation의 계정 귀속은 MVP1 완료 후 별도 확장으로 둔다.
- 사용자가 질문에 팀, 날짜, 구장, 목적을 명시하면 해당 값을 현재 요청의 context로 사용한다.
- 사용자 프로필에 `favorite_team_id`가 있으면 라우팅 context의 보조 기본값으로 사용한다.
- 조건이 부족하면 Tool을 억지로 호출하지 않고 필요한 조건을 묻는다.

예시:

```text
사용자: 다음 주 롯데 경기 알려줘
→ find_kbo_game

사용자: 잠실야구장 위치 알려줘
→ get_stadium_info

사용자: 보크가 뭐야?
→ search_baseball_knowledge
```

MVP1 시작 흐름:

| 시작 상태 | 사용자 행동 | 다음 행동 |
|---|---|---|
| 미로그인 | 메시지 입력 | frontend가 로그인 모달을 열고 채팅 요청을 중단 |
| 로그인 후 첫 방문 | 메시지 입력 | `conversation_id = null`로 `/api/v1/chat` 호출 |
| 새 대화 | 메시지 입력 | `conversation_id = null`로 conversation 생성 |
| 기존 대화 | 메시지 입력 | 기존 `conversation_id`로 메시지 추가 |
| Tool 실행 필요 | 질문 라우팅 성공 | `tool.started`와 `tool.completed` 이벤트 전송 |
| Tool 결과 표시 | 이벤트 수신 | 채팅창 안에 Tool card 렌더링 |
| 답변 생성 | Tool 결과 요약 | `assistant.delta`와 `assistant.completed` 이벤트 전송 |

guest-first를 다시 도입한다면 `guest_id` 기반 conversation 생성과 로그인 후 계정 귀속 흐름을 별도 설계한다.

### 3.2 직관 정보 찾기 대화 흐름

MVP1에서는 온보딩 단계 없이 사용자의 첫 메시지에서 바로 직관 정보를 찾는 흐름으로 연결한다.

```text
일반 메시지 입력
→ 직관 희망 날짜나 기간 확인
→ 경기 일정 조회
→ 경기 후보 제시
→ 사용자가 경기 선택
→ 구장 기본 정보
→ 예매 안내
→ 응원 및 관람 팁
→ 좌석 정보와 추천
→ 직관 준비 요약
```

이 순서는 안내를 위한 기본 경로이며 강제된 설문 단계가 아니다. 사용자는 중간 단계를 건너뛰거나 원하는 정보부터 질문할 수 있다.

예시:

```text
“다음 주 롯데 경기 있어?”
→ 일정 조회부터 시작

“잠실 원정석은 어디야?”
→ 구장과 팀을 확인한 뒤 좌석·응원 안내

“야구에서 병살이 뭐야?”
→ 직관 흐름을 강제하지 않고 일반 야구 지식으로 답변
```

Agent는 대화에서 확인된 값을 conversation metadata의 `agent_context`로 유지한다. MVP1에서는 `find_kbo_game` 단일 결과를 `selected_game`으로 승격하고, 장소/시간/상대/홈원정/상태 follow-up 질문에 재사용한다.

| context | 설명 |
|---|---|
| `favorite_team_id` | 사용자 프로필에 저장된 응원 팀. 라우팅 context의 보조 기본값으로 사용 |
| `selected_team_id` | 현재 질문이나 직전 Tool 결과에서 다루는 팀 |
| `selected_game` | 단일 경기 조회 결과에서 승격한 compact game context |
| `selected_stadium_id` | 선택한 경기 또는 질문의 구장 |
| `selected_stadium_name` | 선택한 경기 또는 질문의 구장명 |
| `last_tool_name` | 직전 실행 Tool 이름 |

로그인 이후에는 프로필의 응원 팀과 현재 대화의 팀을 구분한다. 사용자가 다른 팀의 경기나 구장을 물어도 프로필의 응원 팀을 자동 변경하지 않는다.

#### 직관 탐색에 필요한 조건

경기 후보를 찾기 위해 모든 조건을 한 번에 요구하지 않는다. 사용자가 제공한 조건으로 조회가 가능하면 먼저 결과를 제시하고, 결과가 너무 많거나 조회할 수 없을 때만 추가 질문한다.

사용할 수 있는 탐색 조건:

```text
team_id
date 또는 date range
region
stadium_id
home_or_away
```

추가 질문 원칙:

- 한 번에 하나의 핵심 조건만 질문한다.
- 로그인 이후 저장된 응원 팀은 기본값으로 사용할 수 있지만 질문에 명시된 조건이 우선한다.
- 팀이 없어도 날짜와 지역 또는 구장으로 경기 후보를 찾을 수 있다.
- 날짜가 없으면 “언제 보러 갈 예정인가요?”처럼 기간을 확인한다.
- 조건이 충분하면 불필요한 확인 질문 없이 Tool을 호출한다.
- 여러 경기 결과가 나오면 사용자가 선택할 수 있는 경기 카드를 제공한다.

두 시작 경로는 경기 선택 단계에서 합쳐진다.

```text
팀 선택 경로:
응원 팀 → 날짜 확인 → 경기 후보 → 경기 선택

자유 입력 경로:
사용자 질문 → 날짜·지역·팀·구장 조건 추출 → 경기 후보 → 경기 선택

공통 후속 경로:
경기 선택 → 구장 → 예매 → 응원 → 좌석 → 직관 준비 요약
```

### 3.3 후속 서비스 확장

직관 정보 흐름을 MVP로 완성한 후 일반 야구 정보 영역을 단계적으로 추가한다.

후속 후보:

- 야구 규칙과 용어 설명
- KBO 팀, 구단 역사와 응원 문화
- 선수 프로필과 기록
- 경기 결과와 순위
- 라인업과 주요 관전 포인트
- 야구 뉴스와 이슈

일반 야구 정보를 하나의 범용 RAG에 모두 넣지는 않는다. 정확한 기록과 순위는 정형 데이터/API로 조회하고, 규칙 설명이나 역사처럼 문서 근거가 필요한 정보만 RAG 대상으로 검토한다.

초기 직관 Tool의 계약을 일반 야구 정보까지 미리 확장하지 않는다. 새로운 사용자 문제를 선택할 때마다 필요한 Tool, 데이터 출처, 갱신 주기와 검증 기준을 별도로 정의한다.

## 4. MVP 1: 로그인 채팅과 Tool 실행 기반 직관 도우미

### 4.1 목표

사용자가 로그인 후 채팅창에 KBO 직관 관련 질문을 입력하면, 백엔드가 필요한 Tool을 선택해 LangGraph 흐름으로 실행하고, 프론트엔드가 SSE 이벤트를 받아 Tool 실행 결과와 assistant 답변을 채팅창 안에 렌더링하는 기본 경험을 완성한다.

예시:

```text
사용자: 2026년 5월 23일 롯데 경기 일정 알려줘

SSE 이벤트 흐름:
conversation.created
message.created
tool.started
tool.completed
assistant.delta
assistant.completed
conversation.updated
done
```

MVP1은 완성된 최종 Agent가 아니라, 이후 RAG 품질 개선과 프롬프트 개선을 반복할 수 있는 제품 골격이다.

### 4.2 MVP1 Tool 범위

MVP1에서는 다음 Tool들을 backend routing과 chat stream에 연결했다.

```text
find_kbo_game
get_stadium_info
get_weather_context
search_ticketing_guide
search_stadium_guide
search_baseball_knowledge
```

Tool 책임:

| Tool | 책임 | 데이터 성격 |
|---|---|---|
| `find_kbo_game` | 팀, 날짜, 기간 조건으로 KBO 경기 일정 조회 | 정형 DB |
| `get_stadium_info` | 구장 기본 정보 조회 | 정형 DB |
| `get_weather_context` | 구장/경기 기준 날씨와 직관 컨디션 조회 | 외부 API/정형 계산 |
| `search_ticketing_guide` | 예매 절차와 주의사항 검색 | RAG |
| `search_stadium_guide` | 구장별 안내, 반입, 교통, 시설 등 검색 | RAG |
| `search_baseball_knowledge` | 야구 규칙, 용어, 플레이 설명 검색 | RAG |

### 4.3 Chat API 입력

| 필드 | 필수 여부 | 설명 |
|---|---|---|
| `conversation_id` | 선택 | 기존 대화를 이어갈 때 사용하는 id. 새 대화는 `null` |
| `message` | 필수 | 사용자 자연어 메시지 |

Endpoint:

```text
POST /api/v1/chat
```

인증:

```text
현재 구현은 쿠키 기반 로그인 세션을 요구한다.
백엔드는 `get_current_auth_user`로 현재 사용자 프로필을 확인한다.
```

MVP1에서는 `/api/v1/conversations` 목록 API와 `/api/v1/chat` SSE API를 함께 사용한다. 실제 메시지 전송은 `/api/v1/chat` 하나로 모으는 방향을 기준으로 한다.

### 4.4 Chat stream 출력

응답은 `text/event-stream` SSE로 전송한다.

주요 이벤트:

```text
conversation.created
message.created
tool.started
tool.completed
tool.failed
assistant.delta
assistant.completed
conversation.updated
stream.failed
done
```

Tool event의 공통 목적:

| 이벤트 | 프론트엔드 역할 |
|---|---|
| `tool.started` | 실행 중 상태의 Tool card를 만든다 |
| `tool.completed` | 같은 `tool_call_id`의 card를 완료 상태와 result로 갱신한다 |
| `tool.failed` | 같은 `tool_call_id`의 card를 실패 상태와 error로 갱신한다 |
| `assistant.delta` | assistant 말풍선 텍스트를 스트리밍으로 이어 붙인다 |
| `assistant.completed` | assistant 메시지를 완료 처리한다 |

MVP1의 assistant 답변은 아직 최종 LLM 답변 품질을 목표로 하지 않는다. 현재는 Tool 결과 요약을 스트리밍하는 기본 흐름이며, 프롬프트 개선과 Tool 결과 기반 자연어 답변 생성은 MVP2에서 다룬다.

### 4.5 MVP1에서 제외한 기능

- 지도, 대중교통, 자동차 경로와 현장 동선
- 좌석 검색과 추천
- guest-first 채팅
- guest conversation의 user account 귀속
- 외부 reranker
- 하이브리드 서치
- LangChain routing/answer generation 전면 이전
- 운영용 observability dashboard
- LLM이 여러 Tool을 반복 호출하며 계획을 수정하는 Agent loop
- 대화 이름 변경/삭제/검색 같은 대화 관리 고급 기능

### 4.6 MVP1 완료/진행 상태

완료된 항목:

```text
POST /api/v1/chat SSE endpoint 추가
로그인 사용자 기준 conversation_id, message request schema 정의
conversation/message 저장 흐름 연결
Tool routing과 Tool executor 연결
LangGraph route -> tool_execute -> state_update -> answer_generate skeleton 연결
find_kbo_game 단일 결과 기반 selected_game follow-up context 처리
tool.started / tool.completed / tool.failed 이벤트 정의
assistant.delta / assistant.completed 이벤트 정의
backend SSE contract 테스트 추가
프론트엔드 Tool 결과 타입을 backend 이벤트 계약에 맞게 정리
Tool별 card component 분리
frontend POST /api/v1/chat fetch stream 연결
실제 SSE 이벤트를 message state와 Tool card state에 반영
conversation 목록 API와 sidebar 목록 조회 연결
```

남은 MVP1 연결 항목:

```text
관련 문서의 MVP1 인증 정책을 authenticated-first 기준으로 정렬
sidebar conversation 선택과 ChatPanel conversation_id/messages 상태 연결
GET /api/v1/conversations/{conversation_id}/messages API 또는 동등한 메시지 복원 경로 추가
새 채팅 버튼이 ChatPanel의 현재 conversation/message state를 초기화하도록 연결
Source Drawer에 실제 sources/limitations 또는 Tool result 근거 연결
수동 MVP 시나리오 검증
```

## 5. 데이터 수집 전략

### 5.1 기본 원칙

Tool 계약을 먼저 정하고 계약을 만족하는 데이터만 수집한다.

```text
Tool 계약
→ 후보 출처 조사
→ 소량 샘플 수집
→ 원본 보존
→ 정규화 규칙 작성
→ 검증
→ 전체 범위 수집
```

### 5.2 MVP1에 사용한 데이터 범위

정형 Tool:

- KBO 경기 일정
- KBO 팀 식별자와 별칭
- KBO 구장 기본 정보
- 구장별 기상청 격자 정보

RAG Tool:

- 구장 안내 문서
- 예매 안내 문서
- 야구 기본 규칙과 자주 묻는 플레이 지식

### 5.3 수집 방법 후보

- 공식 또는 신뢰 가능한 일정 페이지 크롤링
- 공개 API가 있다면 API 사용
- MVP 검증용 소량 데이터를 수동 작성
- 기존 `my-baseball-agent`의 출처와 크롤러를 분석한 후 새 계약에 맞게 재구현

수동 데이터는 채팅과 Tool 계약을 검증하기 위한 임시 수단으로 사용할 수 있다. 실제 MVP 완료 판정에는 선택한 출처에서 재현 가능한 수집 절차가 필요하다.

### 5.4 아직 결정할 사항

- 일정 데이터의 갱신 주기와 stale 판단 기준
- 지원할 시즌과 기간 확장 기준
- 크롤링 주기와 재수집 정책
- 우천 취소, 연기, 더블헤더 상태 표현
- 데이터 중복과 변경 감지 방법
- RAG 문서별 최신성 기준과 재임베딩 정책
- 날씨 API 실패 시 fallback 응답 정책

## 6. RAG 적용 범위

### 6.1 RAG 판단 기준

다음 조건을 만족할 때 RAG 후보로 분류한다.

- 답이 단일 필드가 아니라 설명형 문서에 있다.
- 사용자 표현과 원문 표현이 달라 의미 검색이 유용하다.
- 답변에 근거 문단과 출처를 제시해야 한다.
- 구장, 팀, 문서 종류 등의 metadata로 검색 범위를 제한할 수 있다.

다음 정보에는 RAG를 사용하지 않는다.

- 경기 일정과 경기 상태
- 구장 공식 명칭, 주소와 좌표
- 날씨 수치와 예보
- 좌석 가격과 잔여석처럼 실시간성이 중요한 값
- 예산과 선호도에 따른 결정론적 점수 계산

### 6.2 RAG가 필요한 후속 서비스

| 서비스 영역 | RAG 여부 | 이유 |
|---|---|---|
| 야구 기본 지식 | 부분적으로 필요 | 고정된 핵심 규칙은 검증된 문서로 제공하고, 다양한 자연어 질문의 관련 근거 검색에는 RAG가 유용함 |
| KBO 팀 정보와 응원 팀 탐색 | 혼합 | 연고지와 구장 등은 정형 조회하고, 팀 역사·응원 문화·특징은 문서 근거 검색이 필요함 |
| 경기 일정 찾기 | 불필요 | 날짜와 팀 조건의 정확한 조회 |
| 구장 기본 정보 | 불필요 | 주소, 좌표, 홈팀 등의 정형 필드 |
| 구장 이동 경로 | 현재 제외 | 향후 지도·대중교통 API를 사용하는 별도 Tool로 설계해야 함 |
| 날씨와 직관 컨디션 | 불필요 | 날씨 수치와 예보는 기상 API 기반 정형 Tool로 조회하고, 비·더위·습도·바람에 따른 직관 주의 수준만 계산함 |
| 예매 안내 | 부분적으로 필요 | 절차와 주의사항은 문서 검색, 오픈 시각과 가격은 정형 정보 |
| 응원 팁 | 필요 | 응원 문화, 구역 분위기와 준비물 등 자연어 지식 |
| 좌석 특징 검색 | 필요 | 시야, 햇빛, 지붕, 분위기와 장단점 등 설명형 지식 |
| 좌석 최종 추천 | 혼합 | RAG 근거 검색 후 규칙 기반 점수 계산 |

### 6.3 RAG Tool 후보

MVP1에서 실제 연결한 RAG Tool:

```text
search_ticketing_guide
search_stadium_guide
search_baseball_knowledge
```

아직 분리하지 않은 후보:

```text
search_cheering_guide
search_stadium_seat_knowledge
search_stadium_facility_guide
```

MVP1에서는 구장 상세 안내를 `search_stadium_guide`로 묶어 시작했다. 이후 평가 결과에 따라 응원, 좌석, 시설을 별도 Tool로 분리한다.

예매, 응원, 좌석, 구장 시설은 하나의 통합 Tool로 합치지 않는다. 출처, 갱신 주기와 metadata filter가 다르므로 각각 독립적으로 구현하고 검증한다.

| RAG Tool | 단일 책임 | MVP 포함 여부 |
|---|---|---|
| `search_ticketing_guide` | 구단·경기별 예매 절차와 주의사항 검색 | MVP1 포함 |
| `search_stadium_guide` | 구장별 반입, 교통, 시설, 관람 안내 검색 | MVP1 포함 |
| `search_baseball_knowledge` | 야구 규칙, 용어, 플레이 설명 검색 | MVP1 포함 |
| `search_cheering_guide` | 팀 응원 문화, 응원 구역과 준비 팁 검색 | MVP 이후 분리 후보 |
| `search_stadium_seat_knowledge` | 구장 좌석 구역별 시야와 특징 검색 | MVP 이후 |
| `search_stadium_facility_guide` | 구장 내부 편의시설과 이용 안내 검색 | MVP 이후 |

동선 Tool은 이 RAG 목록에 포함하지 않는다. 지도 API를 도입할 시점에 출발지, 도착 구장, 이동 수단과 출발 시각을 입력받는 별도 정형/API Tool로 기획한다.

## 7. 단계별 확장안

### 단계 1: MVP1 채팅/Tool 기본 틀

```text
find_kbo_game
get_stadium_info
get_weather_context
search_ticketing_guide
search_stadium_guide
search_baseball_knowledge
POST /api/v1/chat SSE
Tool result card layout
LangGraph selected_game follow-up context
```

로그인 후 질문을 시작하고, 필요한 Tool을 실행해 채팅창 안에서 결과를 확인할 수 있는 기반을 만든다.

### 단계 2: MVP1 프론트 연결 마무리

```text
SSE fetch stream hook
message state reducer
tool.started / tool.completed 기반 card 갱신
conversation list sidebar
conversation 선택과 message 복원
source drawer 근거 표시
```

프론트엔드 임시 card preview는 제거했고, 실제 backend event로 card를 렌더링하는 연결은 완료됐다. 1차 완료 전에는 sidebar 선택과 대화 복원, source drawer 실제 데이터 연결이 남아 있다.

### 단계 3: MVP2 검색 품질 개선

```text
RAG 평가셋
semantic search baseline
hybrid search
lightweight re-rank
prompt 개선
observability
```

세부 계획은 `docs/planning/002-mvp2-backend-upgrade-plan.md`를 기준으로 한다.

### 단계 4: 로그인과 사용자 프로필

```text
회원가입/로그인
guest conversation 귀속
favorite_team_id
team_onboarding_seen_at
team_preference_updated_at
```

회원가입/로그인과 프로필 조회/수정은 MVP1 채팅 흐름에 이미 일부 포함되어 있다. 다만 guest conversation 귀속, 응원 팀 온보딩, 프로필 기반 추천 고도화는 이 단계에서 다시 다룬다.

### 단계 5: 응원 팀 탐색

```text
KBO 팀 특징 탐색
응원 문화 안내
응원 팀 선택 지원
```

팀 선택은 LLM의 주관만으로 결정하지 않는다. 연고지, 선호하는 응원 문화, 좋아하는 선수나 경기 스타일, 직관 접근성 등 사용자가 제공한 기준을 바탕으로 선택 이유를 설명해야 한다.

### 단계 6: 응원 안내 분리

```text
+ search_cheering_guide
```

현재 구장 안내/예매 안내와 겹치는 응원 정보를 별도 Tool로 분리할 필요가 있을 때 추가한다.

### 단계 7: 좌석 추천

```text
+ search_stadium_seat_knowledge
+ score_seat_candidates
```

좌석 설명 근거는 검색하고, 최종 순위는 예산과 선호 조건을 사용한 결정론적 계산으로 만든다.

### 후속 후보

```text
지도·교통 API 기반 동선 Tool
```

지도·교통 API 기반 동선 Tool은 MVP 이후 후보로 두고, API 제공 범위와 비용을 검토한 뒤 별도 기획한다.

## 8. 채팅과 기본 응답 정책

### 8.1 처리 흐름 초안

MVP1에서는 단일 `/api/v1/chat` endpoint와 SSE event stream을 사용한다.

```text
frontend가 로그인 세션 확인
→ POST /api/v1/chat
→ conversation 생성 또는 조회
→ user message 저장
→ BaseballAgentGraph 실행
→ ToolRoutingService가 Tool과 입력 또는 direct_answer_intent 결정
→ tool.started event
→ AgentToolExecutor가 Tool 실행
→ tool.completed 또는 tool.failed event
→ conversation metadata의 agent_context 갱신
→ assistant.delta event
→ assistant.completed event
→ conversation.updated event
→ done event
```

현재 Tool 선택 기준:

```text
1. 현재 사용자 메시지에 명시된 조건
2. 기존 conversation context에서 추론 가능한 조건
3. Tool별 필수 입력 충족 여부
4. 값이 없으면 필요한 경우에만 추가 질문
```

### 8.2 Chat request와 event 계약

```json
{
  "conversation_id": null,
  "message": "다음 주 롯데 경기 알려줘"
}
```

SSE event는 `event: <name>`과 JSON `data`로 보낸다. 프론트엔드는 event name을 기준으로 message state와 Tool card state를 갱신한다.

### 8.3 사용자 응답에 필요한 요소

- 조건을 어떻게 이해했는지 알 수 있는 문장
- Tool 결과 요약
- 경기 없음 또는 오류 안내
- 출처와 데이터 기준 시점
- 다음 행동을 돕는 짧은 질문

MVP1에서는 Tool card의 구조화 데이터와 assistant 자연어 답변을 분리하는 기반을 마련한다. 최종 답변 품질 개선은 MVP2의 프롬프트 개선 단계에서 진행한다.

## 9. 테스트와 검증 방향

### 9.1 Tool 테스트 후보

- 특정 날짜에 한 경기가 있는 경우
- 해당 날짜에 경기가 없는 경우
- 기간 내 여러 경기가 있는 경우
- 팀 별칭으로 요청한 경우
- 존재하지 않는 팀인 경우
- 날짜 형식이 잘못된 경우
- 일정이 취소 또는 연기된 경우
- 데이터 출처 조회가 실패한 경우
- 구장 기본 정보가 있는 경우와 없는 경우
- 날씨 API가 성공하는 경우와 실패하는 경우
- RAG 검색 결과가 있는 경우와 없는 경우
- RAG 결과의 `answerable`과 `limitations`가 올바른 경우

### 9.2 채팅 흐름 테스트 후보

- 미로그인 사용자가 메시지를 보내면 로그인 모달 또는 401 흐름으로 처리되는 경우
- 로그인 사용자가 첫 메시지를 보내 conversation이 생성되는 경우
- 기존 conversation에 메시지를 이어 보내는 경우
- sidebar에서 기존 conversation을 선택해 메시지를 복원하는 경우
- 팀과 날짜가 모두 있는 요청
- 팀이 없어 추가 질문이 필요한 요청
- 날짜가 없어 추가 질문이 필요한 요청
- 구장 정보 요청
- 날씨 요청
- 예매 안내 RAG 요청
- 구장 안내 RAG 요청
- 야구 지식 RAG 요청
- `tool.started` 후 `tool.completed`가 같은 `tool_call_id`로 도착하는지 확인
- `tool.failed`를 카드 실패 상태로 표시하는지 확인
- `assistant.delta`를 하나의 assistant message로 이어 붙이는지 확인
- 단일 경기 조회 후 "어디서 해?", "몇 시야?", "상대가 누구야?" follow-up이 Tool 재호출 없이 답하는지 확인
- Tool의 `no_result`를 자연어로 안내하는 경우
- Tool 오류를 경기 없음으로 잘못 안내하지 않는지 확인

### 9.3 MVP 품질 기준

MVP1 품질 기준은 기능 연결과 계약 안정성에 둔다.

```text
backend tests 통과
frontend lint/typecheck/build 통과
POST /api/v1/chat route 등록 확인
SSE event contract 테스트 존재
Tool card component가 모든 MVP Tool name을 처리
sidebar에서 기존 conversation을 선택해 메시지를 복원
source/limitation 확인 경로 존재
실제 stream 연결 후 대표 질문 수동 검증
```

## 10. 결정이 필요한 항목

아래 항목을 순서대로 결정한다.

1. 프론트엔드 SSE stream parser 구현 방식
2. message state와 Tool card state의 최종 구조
3. conversation 메시지 조회 API와 프론트 상태 연결 방식
4. assistant 답변을 Tool 요약으로 둘지 LLM 답변 생성까지 붙일지
5. RAG 평가셋의 우선 Tool
6. 하이브리드 서치 실험 순서
7. guest-first 채팅을 MVP1 이후 어느 단계에서 다시 도입할지
8. guest conversation 귀속 방식
9. MVP2에서 LangChain routing/answer generation을 도입할 최소 범위

## 11. 바로 다음 작업

MVP1 문서 기준 바로 다음 작업은 채팅 화면의 대화 복원과 근거 표시를 마무리하는 것이다.

```text
관련 문서를 authenticated-first MVP 기준으로 정렬
→ conversation 선택 상태를 ChatPanel과 공유
→ conversation messages 조회 API 또는 동등한 복원 경로 추가
→ 새 채팅/기존 채팅 전환 시 message state 정리
→ Source Drawer에 sources/limitations 또는 Tool result 근거 연결
→ 대표 질문 및 follow-up 수동 검증
```

그 다음 작업은 `docs/planning/002-mvp2-backend-upgrade-plan.md`에 따라 RAG 평가셋과 baseline run을 만드는 것이다.
