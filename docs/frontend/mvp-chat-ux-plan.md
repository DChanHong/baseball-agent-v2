# MVP Chat UX Plan

> 라벨: `CURRENT`  
> 상태: MVP1 구현 완료 및 운영 배포 확인  
> 최근 업데이트: 2026-08-25  
> 범위: 프론트엔드 채팅 UX, 인증 전제, 세션/대화 흐름, API 사용 방식

## 1. MVP1 목표

MVP1의 목표는 사용자가 로그인한 뒤 한 화면에서 KBO 관련 질문을 입력하고, Agent가 필요한 Tool을 사용해 근거 있는 답변을 스트리밍으로 반환하는 채팅 경험을 완성하는 것이다.

지원 대표 질문:

```text
오늘 롯데 경기 있어?
사직구장 주소 알려줘
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

MVP1 완료 기준:

- Google OAuth 로그인이 동작한다.
- 로그인 후 현재 사용자 조회가 동작한다.
- 채팅 메시지를 전송할 수 있다.
- SSE로 assistant 답변과 tool 실행 상태를 받을 수 있다.
- 경기 일정, 구장 정보, 날씨, 예매/구장 가이드, 야구 지식 Tool 결과를 카드로 볼 수 있다.
- 대화 목록과 대화 메시지를 로그인 사용자 기준으로 불러올 수 있다.

## 2. 인증과 세션 정책

MVP1은 authenticated-first 정책이다. 비로그인 사용자는 채팅을 사용할 수 없다.

```text
Google OAuth
-> Supabase Auth
-> FastAPI backend callback
-> HttpOnly cookie session
-> frontend fetch with credentials: "include"
```

프론트엔드는 access token과 refresh token을 직접 저장하거나 읽지 않는다. 세션 쿠키는 백엔드 API 도메인에 HttpOnly cookie로 저장된다.

운영 기준:

```text
Frontend: https://kbo-mate.dev-hong.it.kr
Backend:  https://api.kbo-mate.dev-hong.it.kr
```

로그인 시작 URL:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/google
```

로그인 성공 후 프론트는 현재 사용자를 조회한다.

```text
GET /api/v1/auth/me
credentials: "include"
```

## 3. Chat API 계약

채팅 전송:

```text
POST /api/v1/chat
credentials: "include"
Accept: text/event-stream
Content-Type: application/json
```

요청:

```json
{
  "conversation_id": "4af9c95a-9580-4380-88bd-cf548c3ca932",
  "message": "오늘 사직 비 와?"
}
```

새 대화 시작:

```json
{
  "conversation_id": null,
  "message": "오늘 롯데 경기 있어?"
}
```

주요 SSE 이벤트:

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

프론트는 SSE payload를 Zod로 검증하고 UI 타입으로 변환한다.

## 4. 화면 구조

MVP1 최상위 화면:

```text
ChatPage
├── ChatSidebar
├── ChatPanel
└── GlobalModal
```

현재 화면 구성:

- 좌측 통합 사이드바
- 중앙 채팅 패널
- 로그인 모달
- 프로필 모달
- Tool result compact card
- SourceDrawer 코드는 보존하되 MVP1 UI에서는 렌더링하지 않음

전역 fixed header는 제거됐고, 브랜드/새 채팅/대화 목록/계정 진입점은 사이드바로 통합됐다.

## 5. Sidebar

사이드바 역할:

- 브랜드 표시
- 새 채팅 시작
- 로그인한 사용자의 최근 대화 목록 표시
- 현재 대화 선택
- 로그인/프로필/로그아웃 진입

대화 목록 API:

```text
GET /api/v1/conversations?limit=50
credentials: "include"
```

대화 메시지 API:

```text
GET /api/v1/conversations/{conversation_id}/messages?limit=100
credentials: "include"
```

동작:

```text
새 채팅 클릭
-> activeConversationId = null
-> 메시지 영역 초기화
-> 첫 전송 시 서버가 conversation.created 이벤트로 새 ID 반환
```

```text
대화 항목 클릭
-> activeConversationId 변경
-> 서버에서 메시지 목록 조회
-> message list 표시
```

## 6. Chat Panel

첫 화면은 hero state로 표시된다.

- KBO Mate 브랜드
- 질문 입력창
- 예시 질문

메시지가 하나 이상 있거나 대화 내역을 불러오면 active chat workspace로 전환된다.

- scrollable message list
- assistant typing indicator
- tool result cards
- inline error block
- fixed/floating composer

전송 흐름:

```text
사용자 입력
-> 로그인 상태 확인
-> 비로그인 시 로그인 모달
-> optimistic user message 표시
-> assistant placeholder 표시
-> POST /api/v1/chat SSE 시작
-> conversation.created 수신 시 activeConversationId 갱신
-> tool.started/completed/failed 수신 시 tool card 갱신
-> assistant.delta 수신 시 답변 누적
-> done 수신 시 conversation list invalidate
```

## 7. Tool Result Cards

MVP1에서 표시하는 Tool:

| Tool | UI 요약 |
|---|---|
| `find_kbo_game` | 날짜, 팀, 구장, 경기 상태 |
| `get_stadium_info` | 구장명, 주소, 돔 여부, 홈팀 |
| `get_weather_context` | 날씨, 강수, 바람, 직관 condition |
| `search_ticketing_guide` | 예매처/방법 요약, 공식 출처 |
| `search_stadium_guide` | 반입/교통/시설 요약, 출처 |
| `search_baseball_knowledge` | 야구 규칙/지식 요약, 문서 출처 |

상태:

- `running`: 확인 중 상태와 로딩 표시
- `completed`: 핵심 결과 요약
- `failed`: 짧은 실패 메시지

Tool별 개별 재시도 버튼은 MVP1에 포함하지 않는다. 전체 응답 실패 시에는 메시지 영역의 `다시 시도` 버튼으로 마지막 사용자 메시지를 다시 전송한다.

## 8. Source Drawer

SourceDrawer 관련 코드는 남겨둔다.

```text
frontend/src/widgets/source-drawer/
```

MVP1 운영 UI에서는 렌더링하지 않는다.

이유:

- Tool card 내부 출처 링크만으로 MVP1 검증이 가능하다.
- 별도 출처 패널 UX는 MVP2에서 재설계할 수 있다.
- 현재 우선순위는 로그인, 채팅, Tool card, 대화 저장 흐름이다.

## 9. MVP1 제외 범위

- 좌석 추천
- 실시간 티켓 잔여석
- 대화방 검색
- 대화방 삭제
- 대화방 이름 변경
- 별도 설정 페이지
- SourceDrawer 운영 노출
- 복잡한 multi-tool timeline
- Toast 시스템
- 긴 메시지 리스트 virtualization

## 10. MVP2 후보

- SourceDrawer 재설계 및 출처 UX 강화
- Tool card별 디자인 고도화
- 대화방 검색/삭제/이름 변경
- 프로필/마이페이지 UX 확장
- Toast 시스템
- 모바일 active chat UX 추가 개선
- 긴 대화 virtualization
- 추천 후속 질문 UI

## 11. 삭제 여부

이 문서는 삭제하지 않는다.

이유:

- MVP1의 현재 채팅 UX와 API 사용 방식을 가장 짧게 설명하는 기준 문서다.
- `frontend-layout-spec.md`보다 요약성이 높아 업그레이드 전 진입점으로 유용하다.
- MVP2 작업 전 "현재 되는 것과 제외된 것"을 빠르게 확인할 수 있다.
