# MVP Chat UX Plan

> 상태: 구현 완료 (2026-08-21 기준)
> 목적: 1차 MVP 채팅 화면 레이아웃, 세션 흐름, API 계약 기록.
> 범위: 프론트엔드 UX/상태/API 사용 방식. 백엔드 구현 상세는 별도 문서에서 다룬다.
> 주의: 이 문서는 초안 당시 guest-first 기준으로 작성됐으나, 실제 구현은 authenticated-first로 확정됐다. guest_id 관련 내용은 현재 구현과 다르다.

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

Supabase Auth 기반 로그인이 적용되어 있다. 비로그인 상태에서는 채팅을 사용할 수 없다.

```text
Supabase Auth
  → access_token / refresh_token (쿠키 저장)
  → FastAPI: Authorization: Bearer <token>
  → user_profile_id 기반 conversation 소유권 관리
```

원칙:

- 로그인한 사용자만 `/api/v1/chat` 및 대화 목록 API를 사용할 수 있다.
- 새 채팅은 `conversation_id=null`로 시작하고, 서버가 새 conversation을 생성해 SSE로 `conversation.created` 이벤트를 보낸다.
- 이후 같은 채팅창에서는 생성된 `conversation_id`를 계속 사용한다.
- conversation 목록은 로그인한 사용자의 `user_profile_id`에 묶어 관리한다.

## 3. Chat API 계약

```text
POST /api/v1/chat
Authorization: Bearer <access_token>
```

요청:

```json
{
  "conversation_id": "4af9c95a-9580-4380-88bd-cf548c3ca932",
  "message": "오늘 사직 비 와?"
}
```

새 대화 시작 시:

```json
{
  "conversation_id": null,
  "message": "오늘 롯데 경기 있어?"
}
```

응답은 SSE(Server-Sent Events) 스트리밍으로 반환된다.

주요 이벤트:

```text
conversation.created  → conversation_id 발급
message.created       → user/assistant 메시지 ID 확정
tool.started          → tool 실행 시작
tool.completed        → tool 결과
assistant.delta       → 답변 텍스트 청크
assistant.completed   → 최종 답변
conversation.updated  → conversation 목록 갱신 신호
done                  → 스트림 종료
```

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

세션 사이드바는 로그인한 사용자의 conversation 목록을 표시한다.

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

구현된 API:

```text
GET /api/v1/conversations
Authorization: Bearer <access_token>

GET /api/v1/conversations/{conversation_id}/messages
Authorization: Bearer <access_token>
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
is_session_sidebar_collapsed
```

인증 토큰은 Supabase Auth가 쿠키로 관리한다. guest_id와 conversation cache는 사용하지 않는다.

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
→ 로그인 여부 확인 (미로그인 시 로그인 모달)
→ optimistic user message 표시
→ POST /api/v1/chat (SSE 스트림 시작)
→ conversation.created → activeConversationId 갱신
→ tool.started / tool.completed → tool card 갱신
→ assistant.delta → 답변 텍스트 스트리밍
→ done → 스트림 종료, conversation list invalidate
```

실패 시:

```text
network error
→ user message는 유지
→ assistant error block 표시
→ 다시 시도 버튼 제공
```

## 10. MVP에서 제외

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

- 1차 MVP는 `POST /api/v1/chat` SSE 스트리밍으로 구현됐다.
- 인증은 Supabase Auth 기반 로그인 필수(authenticated-first)로 확정됐다.
- 프론트는 sidebar 접힘 상태만 `localStorage`에 저장한다. guest_id는 사용하지 않는다.
- sidebar는 데스크톱 고정 영역, 모바일 overlay drawer로 동작한다.
- 좌석 추천 UI는 MVP에서 제외한다.
- Tool 결과는 답변 아래 compact card로 표시한다.
- 출처와 기준 시점은 Source Drawer로 분리한다 (현재 UI placeholder 구현, 데이터 연결은 MVP1 제외 → 스펙업으로 이동).
