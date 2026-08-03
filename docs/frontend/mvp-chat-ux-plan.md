# MVP Chat UX Plan

> 상태: 초안  
> 목적: 로그인 전 1차 MVP에서 사용할 채팅 화면 레이아웃, 세션 흐름, API 계약을 정한다.  
> 범위: 프론트엔드 UX/상태/API 사용 방식. 백엔드 구현 상세는 별도 문서에서 다룬다.

## 1. MVP 목표

1차 MVP는 사용자가 한 화면에서 KBO 직관 관련 질문을 입력하고, Agent가 필요한 Tool을 사용해 답변하는 채팅 경험을 완성하는 것이다.

이번 단계에서는 Tool을 더 늘리지 않고, 이미 구현한 Tool을 실제 화면과 API 흐름에 연결한다.

MVP에서 지원할 대표 질문:

```text
오늘 롯데 경기 있어?
사직구장 주소 알려줘
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

## 2. 세션 정책

로그인은 아직 붙이지 않는다.

대신 브라우저 기준 guest session을 사용한다.

```text
browser localStorage
  -> guest_id
  -> current_conversation_id
  -> is_session_sidebar_collapsed
```

원칙:

- 첫 방문 시 frontend가 UUID `guest_id`를 생성해 `localStorage`에 저장한다.
- 새 채팅을 시작하면 `conversation_id=null`로 `/api/v1/chat`을 호출할 수 있다.
- 서버가 새 conversation을 만들고 `conversation_id`를 응답한다.
- 이후 같은 채팅창에서는 응답받은 `conversation_id`를 계속 보낸다.
- conversation 목록은 같은 `guest_id`에 묶어 보여준다.
- 로그인 도입 후에는 기존 `guest_id` conversation을 user account에 연결할 수 있게 남겨둔다.

## 3. Chat API 계약

1차 MVP는 단일 endpoint를 우선 사용한다.

```text
POST /api/v1/chat
```

요청:

```json
{
  "guest_id": "0f3cf263-cc8b-4f19-b6c0-675d34d7122b",
  "conversation_id": "4af9c95a-9580-4380-88bd-cf548c3ca932",
  "message": "오늘 사직 비 와?"
}
```

새 대화 시작 시:

```json
{
  "guest_id": "0f3cf263-cc8b-4f19-b6c0-675d34d7122b",
  "conversation_id": null,
  "message": "오늘 롯데 경기 있어?"
}
```

응답 초안:

```json
{
  "conversation_id": "4af9c95a-9580-4380-88bd-cf548c3ca932",
  "user_message": {
    "id": "7dd08fd5-8d7a-49f1-9f52-3569ff4ecbef",
    "role": "user",
    "content": "오늘 사직 비 와?",
    "sequence_no": 1,
    "created_at": "2026-08-03T10:20:00+09:00"
  },
  "assistant_message": {
    "id": "accc6762-7c13-46da-a75d-69ecb919fb91",
    "role": "assistant",
    "content": "사직 기준으로 현재 비는 오지 않는 것으로 조회됐어요...",
    "sequence_no": 2,
    "created_at": "2026-08-03T10:20:03+09:00"
  },
  "tool": {
    "name": "get_weather_context",
    "status": "completed",
    "result": {}
  },
  "sources": [],
  "limitations": [
    "weather_forecast_not_game_cancellation_decision"
  ]
}
```

MVP에서는 streaming을 붙이지 않는다. 답변 생성 완료 후 한 번에 응답한다.

## 4. 화면 레이아웃

1차 화면은 채팅 작업에 집중한다.

```text
┌──────────────────────────────────────────────────────────────┐
│ Header                                                       │
│ Baseball Agent                    새 채팅  사이드바  프로필 │
├───────────────┬──────────────────────────────────────────────┤
│ Session       │ Chat Workspace                               │
│ Sidebar       │                                              │
│               │  ┌────────────────────────────────────────┐  │
│ - 새 채팅     │  │ Message List                           │  │
│ - 오늘 사직.. │  │ - user message                         │  │
│ - 예매 방법.. │  │ - assistant answer                     │  │
│ - 보크 설명.. │  │ - tool result compact cards            │  │
│               │  └────────────────────────────────────────┘  │
│               │                                              │
│               │  ┌────────────────────────────────────────┐  │
│               │  │ Composer                               │  │
│               │  │ [질문 입력...]                  [send] │  │
│               │  └────────────────────────────────────────┘  │
└───────────────┴──────────────────────────────────────────────┘
```

Session Sidebar는 접을 수 있다.

```text
expanded width: 260px
collapsed width: 56px
mobile: overlay drawer
```

접힌 상태에서는 아이콘 버튼만 표시한다.

```text
┌────┬──────────────────────────────────────────────┐
│ +  │ Chat Workspace                               │
│ ≡  │                                              │
│ 1  │                                              │
│ 2  │                                              │
└────┴──────────────────────────────────────────────┘
```

데스크톱에서는 출처/근거 패널을 오른쪽 drawer로 열 수 있다. Source Drawer는 Session Sidebar와 별개다.

```text
┌──────────────────────────────┬───────────────┐
│ Chat                         │ Source Drawer │
│                              │ - source URL  │
│                              │ - as_of       │
│                              │ - limitations │
└──────────────────────────────┴───────────────┘
```

모바일에서는 drawer가 bottom sheet 또는 full-screen overlay로 열린다.

## 5. 첫 화면 상태

아직 메시지가 없을 때는 landing hero보다 실제 채팅 시작을 우선한다.

표시 요소:

- 짧은 서비스 제목
- 입력창
- 4~6개 예시 질문 chip
- 왼쪽 session sidebar의 최근 대화 목록
- 최근 대화가 있으면 sidebar에서 이어가기

예시 질문:

```text
오늘 롯데 경기 있어?
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

좌석 추천 예시는 이번 MVP에서 제외한다.

## 6. 세션 사이드바

세션 사이드바는 로그인 전부터 만든다. 로그인 도입 후에도 같은 UI를 사용하고, 데이터 소스만 guest conversation에서 user conversation으로 바꾼다.

표시 요소:

- 새 채팅 버튼
- 접기/펼치기 버튼
- 현재 conversation 강조
- 최근 대화 목록
- 각 대화의 제목 또는 첫 질문
- 마지막 메시지 시각
- 비어 있을 때 안내 문구

MVP 동작:

```text
새 채팅 클릭
→ current_conversation_id=null
→ message list 초기화
→ composer focus
```

```text
대화 항목 클릭
→ current_conversation_id 변경
→ 해당 conversation messages 조회
→ message list 표시
```

```text
사이드바 접기
→ is_session_sidebar_collapsed=true 저장
→ message workspace 폭 확장
```

API 후보:

```text
GET /api/v1/conversations?guest_id=...
GET /api/v1/conversations/{conversation_id}/messages?guest_id=...
```

단, 백엔드 MVP 속도를 위해 첫 구현에서는 conversation 목록 API가 준비되기 전까지 localStorage에 최근 conversation summary cache를 둘 수 있다.

프론트 로컬 캐시 초안:

```json
{
  "recent_conversations": [
    {
      "conversation_id": "4af9c95a-9580-4380-88bd-cf548c3ca932",
      "title": "오늘 사직 비 와?",
      "last_message_at": "2026-08-03T10:20:03+09:00"
    }
  ]
}
```

## 7. 메시지 UI

메시지 타입:

| 타입 | UI |
|---|---|
| user | 오른쪽 정렬 말풍선 |
| assistant | 왼쪽 정렬 답변 블록 |
| tool result | assistant 답변 아래 compact card |
| source | drawer 또는 접이식 source list |
| limitation | 답변 하단의 작은 안내 문구 |

Tool card는 길게 펼치지 않는다. MVP에서는 요약만 보여준다.

Tool별 compact card:

| Tool | 표시 정보 |
|---|---|
| `find_kbo_game` | 날짜, 팀, 구장, 경기 상태 |
| `get_stadium_info` | 구장명, 주소, 돔 여부, 홈팀 |
| `get_weather_context` | 기온, 강수, 습도, 바람, 직관 condition |
| `search_ticketing_guide` | 예매처/방법 요약, 공식 출처 |
| `search_stadium_guide` | 반입/교통/시설 요약, 출처 |
| `search_baseball_knowledge` | 근거 요약, 문서 출처 |

## 8. 상태 모델

프론트엔드 상태는 세 층으로 나눈다.

### Local Storage

```text
guest_id
current_conversation_id
is_session_sidebar_collapsed
recent_conversations_cache
```

### Jotai

```text
chat_input
is_session_sidebar_open
is_session_sidebar_collapsed
is_source_drawer_open
selected_source_item
optimistic_pending_message
```

### React Query

```text
conversation messages
chat mutation result
conversation list
```

MVP에서는 conversation list API를 붙이는 것이 좋다. 단, 백엔드 일정상 늦어지면 `recent_conversations_cache`로 sidebar UI를 먼저 완성한다.

## 9. 전송 흐름

```text
사용자 입력
→ guest_id 확인 또는 생성
→ current_conversation_id 읽기
→ optimistic user message 표시
→ POST /api/v1/chat
→ 응답 conversation_id 저장
→ recent_conversations_cache 갱신
→ assistant message append
→ tool/source/limitation 표시
→ input focus 복구
```

실패 시:

```text
network error
→ user message는 유지
→ assistant error block 표시
→ 다시 시도 버튼 제공
```

## 10. MVP에서 제외

- 로그인
- SSE streaming
- 좌석 추천
- 실시간 티켓 잔여석
- 대화방 검색/삭제/이름 변경
- 프로필 저장
- 복수 Tool chain을 UI에서 복잡하게 보여주는 timeline

단, 백엔드가 tool 결과를 반환하면 카드로 요약 표시는 한다.

## 11. 구현 순서

1. `POST /api/v1/chat` 백엔드 계약 확정
2. frontend Zod schema 작성
3. `guest_id` localStorage helper 작성
4. session sidebar 상태와 레이아웃 구현
5. chat mutation hook 작성
6. 현재 conversation 상태 저장
7. message list UI 구현
8. composer 전송 연결
9. tool compact card 1차 구현
10. source drawer 최소 구현
11. conversation list API 또는 local cache 연결
12. MVP 시나리오 6개로 수동 검증

## 12. 파일 배치 초안

```text
frontend/src/
├── features/
│   ├── manage-session-sidebar/
│   │   ├── model/
│   │   │   └── session-sidebar.atom.ts
│   │   └── ui/
│   │       └── session-sidebar-toggle.tsx
│   └── send-message/
│       ├── api/
│       │   ├── send-chat-message.ts
│       │   └── use-send-chat-message.ts
│       ├── lib/
│       │   └── guest-session.ts
│       ├── model/
│       │   └── chat-input.atom.ts
│       └── ui/
│           └── chat-composer.tsx
├── entities/
│   ├── conversation/
│   │   └── model/
│   │       └── types.ts
│   ├── message/
│   │   ├── model/
│   │   │   └── types.ts
│   │   └── ui/
│   │       └── message-bubble.tsx
│   └── tool-result/
│       └── ui/
│           └── tool-result-card.tsx
└── widgets/
    ├── session-sidebar/
    │   ├── model/
    │   │   └── recent-conversations-cache.ts
    │   └── ui/
    │       └── session-sidebar.tsx
    ├── chat/
    │   └── ui/
    │       └── chat-panel.tsx
    └── source-drawer/
        └── ui/
            └── source-drawer.tsx
```

## 13. 결정 사항

- 1차 MVP는 단일 `POST /api/v1/chat`로 간다.
- 로그인 전 세션은 `guest_id + conversation_id`로 이어간다.
- 프론트는 `guest_id`, 현재 `conversation_id`, sidebar 접힘 상태를 `localStorage`에 저장한다.
- session sidebar는 로그인 전부터 만든다.
- sidebar는 데스크톱 고정 영역, 모바일 overlay drawer로 동작한다.
- 좌석 추천 UI는 MVP에서 제외한다.
- Tool 결과는 답변 아래 compact card로 표시한다.
- 출처와 기준 시점은 drawer 또는 접이식 영역으로 분리한다.
