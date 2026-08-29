# Frontend Layout Spec

> 라벨: `CURRENT`  
> 상태: MVP1 구현 완료 및 운영 배포 확인  
> 최근 업데이트: 2026-08-25  
> 범위: 현재 프론트엔드 레이아웃, 화면 구조, 주요 컴포넌트 책임, MVP2 후보

## 1. 목적

이 문서는 MVP1 기준 프론트엔드 레이아웃의 현재 상태를 고정한다. UI 개선 전 계획 문서가 아니라, 운영 배포까지 확인된 화면 구조와 남은 개선 후보를 구분하기 위한 기준 문서다.

요약 문서는 [`mvp-chat-ux-plan.md`](mvp-chat-ux-plan.md)를 참고한다. 운영 배포와 OAuth 기준은 [`../deployment-production.md`](../deployment-production.md), Vercel 기준은 [`deployment-vercel.md`](deployment-vercel.md)를 참고한다.

## 2. 현재 구현 범위

프론트엔드는 `frontend/`의 Next.js App Router 단일 페이지 앱이다.

주요 진입점:

```text
frontend/src/app/page.tsx
-> frontend/src/views/chat/ui/chat-page.tsx
```

최상위 화면 구조:

```text
ChatPage
├── ChatSidebar
├── ChatPanel
└── GlobalModal
```

현재 MVP1 구현:

- 전역 fixed header 제거
- 브랜드/새 채팅/대화 목록/계정 진입점을 좌측 사이드바로 통합
- Google OAuth 로그인 모달 연결
- 프로필 모달과 프로필 저장 API 연결
- 채팅 입력과 `/api/v1/chat` SSE 스트림 연결
- 대화 목록 API 연결
- 대화 메시지 조회 API 연결
- Tool result card 렌더링
- SourceDrawer 코드는 보존하되 렌더링 비활성화

## 3. 비목표

MVP1에 포함하지 않는 것:

- 팀/구장 전용 네비게이션
- 별도 설정 페이지
- 좌석 추천 UI
- 실시간 티켓 잔여석
- 대화방 검색/삭제/이름 변경
- SourceDrawer 운영 노출
- Toast 시스템
- 긴 메시지 리스트 virtualization
- 파일 첨부
- 음성 입력
- 복잡한 작업 timeline 패널

## 4. 사용자 흐름

```text
1. 사용자가 https://kbo-mate.dev-hong.it.kr 로 진입한다.
2. Home page가 ChatPage를 렌더링한다.
3. 사용자는 사이드바 하단에서 로그인 모달을 열 수 있다.
4. Google OAuth 로그인은 backend /api/v1/auth/google 에서 시작한다.
5. 백엔드 callback이 HttpOnly cookie를 설정하고 프론트로 돌려보낸다.
6. 프론트는 /api/v1/auth/me 로 현재 사용자를 확인한다.
7. 사용자는 hero 상태의 ChatComposer에 질문을 입력한다.
8. 프론트는 credentials: "include"로 /api/v1/chat SSE 요청을 보낸다.
9. SSE 이벤트를 받아 메시지, Tool card, assistant 답변을 갱신한다.
10. conversation.created 또는 done 이후 대화 목록을 invalidate한다.
```

## 5. App Shell

파일:

```text
frontend/src/views/chat/ui/chat-page.tsx
```

현재 구조:

- `Shell`: `min-height: 100vh`
- `Workspace`: desktop에서 `auto minmax(0, 1fr)` grid
- mobile에서는 sidebar rail 또는 off-canvas 패턴에 맞춰 main 영역 padding 조정

`SourceDrawer`는 import와 render 호출이 주석 처리되어 있다.

## 6. Sidebar

파일:

```text
frontend/src/widgets/chat-sidebar/ui/chat-sidebar.tsx
```

역할:

- 브랜드 표시
- 새 채팅 버튼
- 대화 목록 표시
- 현재 대화 강조
- 사이드바 접기/펼치기
- 모바일 off-canvas sidebar
- 로그인/프로필/로그아웃 계정 영역

대화 목록은 React Query로 조회한다.

```text
GET /api/v1/conversations?limit=50
credentials: "include"
```

대화 항목을 선택하면 `activeConversationId`가 바뀌고, ChatPanel이 해당 대화 메시지를 조회한다.

## 7. Chat Panel

파일:

```text
frontend/src/widgets/chat/ui/chat-panel.tsx
```

역할:

- 인증 상태 확인
- 비로그인 사용자의 채팅 전송 차단
- hero state와 active chat state 전환
- 대화 메시지 조회
- optimistic user message 추가
- assistant placeholder 관리
- SSE 이벤트 처리
- Tool card upsert
- conversation list invalidate
- 실패 시 inline error와 재시도 버튼 표시

hero state:

- KBO Mate 브랜드
- 질문 입력창
- 예시 질문

active state:

- message list
- assistant typing indicator
- tool result cards
- 하단 composer dock

## 8. Chat Composer

파일:

```text
frontend/src/features/send-message/ui/chat-composer.tsx
```

입력 정책:

- textarea 사용
- Enter 전송
- Shift+Enter 줄바꿈
- streaming/auth 확인 중에는 disabled
- hero state에서만 예시 질문 표시

MVP1에서 제거한 것:

- 파일 추가
- 음성 입력
- 일정 검색/원정 조사/추천 근거 모드 토글

## 9. Message Bubble

파일:

```text
frontend/src/entities/message/ui/message-bubble.tsx
```

표시 정책:

- user message는 오른쪽 정렬
- assistant message는 왼쪽 정렬
- assistant message에는 KBO Mate 프로필 row 표시
- assistant content가 비어 있고 streaming 중이면 typing indicator 표시
- content, tool result, typing indicator가 모두 없으면 빈 assistant bubble을 렌더링하지 않음

## 10. Tool Result Cards

파일:

```text
frontend/src/entities/tool-result/ui/tool-result-card.tsx
```

지원 Tool:

```text
find_kbo_game
get_stadium_info
get_weather_context
search_stadium_guide
search_ticketing_guide
search_baseball_knowledge
```

상태:

- `running`: 공통 loading card
- `completed`: tool 이름별 카드
- `failed`: 공통 실패 card

Tool card는 답변 흐름 안에서 핵심 결과를 요약한다. 별도 SourceDrawer는 MVP1에서 열지 않고, 카드 내부 출처 링크만 유지한다.

## 11. Login And Profile

파일:

```text
frontend/src/features/auth/ui/login-modal.tsx
frontend/src/features/profile/ui/profile-modal.tsx
frontend/src/shared/ui/modal/modal.tsx
```

로그인:

- Google OAuth만 지원
- 별도 route가 아니라 modal 유지
- 로그인 시작 시 `window.location.assign(`${API_BASE_URL}/api/v1/auth/google`)`

현재 사용자:

```text
GET /api/v1/auth/me
credentials: "include"
```

프로필:

- 닉네임 수정
- 응원팀 선택/수정
- React Query current user cache 갱신

로그아웃:

```text
POST /api/v1/auth/logout
credentials: "include"
```

## 12. API 계약

### Chat Stream

```text
POST /api/v1/chat
credentials: "include"
Accept: text/event-stream
Content-Type: application/json
```

Request:

```json
{
  "conversation_id": "string | null",
  "message": "string"
}
```

SSE events:

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

### Conversation List

```text
GET /api/v1/conversations?limit=50
credentials: "include"
```

UI type:

```ts
type ConversationSummary = {
  id: string;
  title: string | null;
  status: string;
  lastMessageAt: string | null;
  createdAt: string;
  updatedAt: string;
};
```

### Conversation Messages

```text
GET /api/v1/conversations/{conversation_id}/messages?limit=100
credentials: "include"
```

Unauthorized, forbidden, or missing conversations return an empty UI list.

## 13. State Model

Local state:

- active conversation id
- current message list
- streaming flag
- response status
- failed request message
- active assistant message id
- chat input atom
- login/profile modal atoms

React Query:

- current user
- conversation list
- conversation messages

LocalStorage:

- sidebar collapsed/open preference

Auth tokens are not stored in frontend state or localStorage.

## 14. Error Handling

Implemented:

- 401 current user lookup returns logged-out state
- 401 conversation list returns empty list
- 401/403/404 conversation messages return empty list
- chat stream failure creates inline error block
- retry button resends the last submitted message
- unknown SSE event or invalid payload is ignored or falls into error handling
- active request is aborted on component unmount

## 15. MVP2 후보

- SourceDrawer 재설계
- Tool card별 시각 디자인 고도화
- 모바일 active chat polish
- 긴 대화 virtualization
- Toast 시스템
- 대화 검색/삭제/이름 변경
- 후속 질문 suggestion UI
- 계정 패널/마이페이지 기능 확장

## 16. 삭제/이동 여부

이 문서는 삭제하지 않는다.

추천:

- 현재는 `docs/frontend/frontend-layout-spec.md` 위치를 유지한다.
- `mvp-chat-ux-plan.md`는 요약 문서, 이 문서는 상세 레이아웃 기준 문서로 역할이 다르다.
- 나중에 MVP2 레이아웃 스펙을 새로 만들 때 `docs/frontend/v1/frontend-layout-spec.md`로 이동하는 것을 추천한다.
