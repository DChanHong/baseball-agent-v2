# Frontend Layout UI/UX Next Steps

> 작성일: 2026-08-09  
> 목적: 다음 작업에서 frontend layout spec을 기준으로 UI/UX 개선 개발을 바로 시작하기 위한 메모  
> 기준 문서: `docs/frontend/layout/2026-08-09-frontend-layout-spec.md`

## 1. 다음 작업 목표

다음 작업은 오늘 확정한 frontend layout spec을 기준으로 현재 MVP UI를 재구성하는 것이다.

핵심 목표:

```text
전역 header + 접힘 가능한 좌측 sidebar + main chat + right SourceDrawer
```

기존 UI 텍스트와 임시 기능은 spec 기준에 맞춰 정리한다.

## 2. 먼저 읽을 문서

```text
AGENTS.md
frontend/AGENTS.md
docs/frontend/layout/2026-08-09-frontend-layout-spec.md
docs/frontend/folder-design.md
frontend/docs/stack-decisions.md
```

프론트엔드 코드를 수정할 때는 `frontend/AGENTS.md`의 규칙을 우선한다.

## 3. 구현 우선순위

### 3.1 App Shell/Layout

- 전역 header는 상단 바 역할만 유지한다.
- 좌측 sidebar를 추가한다.
- sidebar는 펼침/닫힘을 지원한다.
- collapsed 상태에서는 얇은 icon rail을 남긴다.
- collapsed rail에는 새 채팅 버튼과 펼치기 버튼만 표시한다.
- main chat 영역에는 대화 제목/상태 바, 메시지 리스트, composer를 배치한다.
- right SourceDrawer는 실제 출처/근거 패널로 살린다.

### 3.2 Header

- 좌측에는 서비스 로고 영역을 둔다.
- 로고 이미지는 추후 제작 예정이므로 우선 placeholder를 둔다.
- 우측은 인증 상태 기준으로 나눈다.
  - 비로그인: 로그인 버튼
  - 로그인: 이름 또는 별명 + 원형 프로필
- 원형 프로필 dropdown에는 `마이페이지`, `로그아웃`을 둔다.
- 로그인 화면은 별도 route가 아니라 modal로 유지한다.

### 3.3 Sidebar

- 상단에 새 채팅 버튼을 둔다.
- 그 아래에는 채팅 목록 세션만 표시한다.
- 세션 item은 대화 제목만 1줄 ellipsis로 표시한다.
- active 세션은 배경색 강조 + 굵은 글자로 표시한다.
- hover 상태는 연한 배경으로 표시한다.
- 1차 범위에서 마지막 메시지 시간, 삭제, rename, streaming/error 상태는 표시하지 않는다.

### 3.4 Chat Area

- 채팅창 상단에 현재 대화 제목/상태 바를 둔다.
- 상태 바에는 현재 대화 제목과 응답 상태만 표시한다.
- SourceDrawer 버튼은 상태 바에 넣지 않는다.
- 상태 문구는 spec의 1차 문구를 따른다.
- composer는 `입력창`, `전송 버튼`, `질문 예시`만 남긴다.
- 질문 예시는 첫 화면(hero/empty state)에서만 표시한다.
- active chat 상태에서는 질문 예시를 숨긴다.
- `일정 검색`, `원정 조사`, `추천 근거`, `직관 자료 추가`, 음성 입력은 1차 UI에서 제거하거나 숨긴다.

### 3.5 SSE Loading UX

- 사용자 메시지는 전송 즉시 추가한다.
- 응답 완료 전까지 composer는 disabled 처리한다.
- tool running 상태도 채팅 메시지 안의 카드로 보여준다.
- running tool card에는 툴 이름, 상태 문구, 로딩 표시만 보여준다.
- completed tool card에는 툴 이름, 완료 상태, 핵심 결과 1~3줄을 보여준다.
- failed tool card에는 실패 상태와 짧은 사용자 친화적 메시지만 보여준다.
- assistant typing indicator는 점 3개 애니메이션으로 표시한다.
- 전체 응답 실패 시 메시지 영역에 error block과 `다시 시도` 버튼을 표시한다.

### 3.6 SourceDrawer

- SourceDrawer는 tool card와 역할을 분리한다.
- tool card는 채팅 흐름 안의 핵심 결과 요약을 담당한다.
- SourceDrawer는 출처 제목, 원문 링크, 주의/참고를 모아 보여준다.
- `주의/참고`는 딱딱한 한계 고지가 아니라 부드러운 어투와 당구장 표시 같은 시각 표현으로 처리한다.

### 3.7 Toast UX

- 1차 UI에 toast 시스템을 포함한다.
- desktop 위치는 우하단이다.
- mobile 위치는 상단 중앙이다.
- 기본 지속 시간은 3초다.
- 채팅 응답 실패 같은 핵심 오류는 toast만 쓰지 않고 inline error block을 우선한다.

## 4. 검증 명령

프론트엔드 변경 후 최소 검증:

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/frontend
pnpm lint
pnpm typecheck
```

로컬 실행:

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/frontend
pnpm dev
```

확인 URL:

```text
http://127.0.0.1:3001
```

## 5. 수동 검증 포인트

최소 viewport:

```text
desktop: 1440x900
tablet: 1024x768
mobile: 390x844
```

확인할 것:

- header가 desktop/mobile에서 깨지지 않는가
- sidebar expanded/collapsed 상태가 자연스러운가
- active 세션 표시가 명확한가
- hero 상태와 active chat 상태가 분리되는가
- composer가 active chat에서 간결하게 보이는가
- SSE running/completed/failed tool card가 흐름 안에서 이해되는가
- SourceDrawer가 메시지와 겹치지 않는가
- toast가 composer나 핵심 텍스트를 가리지 않는가

## 6. 남은 결정

다음 구현 중 아직 결정이 필요한 항목:

```text
실제 auth 연동 방식과 provider
마이페이지를 modal/drawer/route 중 어디에 둘지
대화/메시지 상태를 React Query cache로 승격할지 여부
composer input을 textarea로 바꿀지 여부
mobile drawer overlay/background scroll 처리 방식
modal focus trap/Escape close 접근성 보강
```
