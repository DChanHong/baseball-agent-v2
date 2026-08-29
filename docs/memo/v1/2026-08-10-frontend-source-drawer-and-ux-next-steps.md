# Auth Priority, SourceDrawer, and UX Next Steps

> 작성일: 2026-08-10  
> 목적: Auth 구현을 우선순위로 두고, 이후 SourceDrawer 연결과 MVP 수준 UI/UX 보완 항목을 이어가기 위한 작업 순서를 기록한다.

## 1. 현재 상태

- Header branding, fixed header, left sidebar, composer 정리, assistant typing indicator, tool card running/completed/failed 표현은 1차 구현됐다.
- 우측 하단 `작업 내역` 버튼과 tool 진행 내역 패널이 추가됐다.
- tool card 공통 shell은 MVP 수준으로 정돈됐지만, 카드별 도메인 UI는 더 다듬을 여지가 있다.
- 현재 로컬 환경은 데이터 세팅이 아직 완료되지 않아 실제 출처/근거 데이터 기반 검증은 보류한다.
- 로그인/Auth 스펙은 별도 문서로 확정됐다.

## 2. 최우선 작업: Auth 구현

SourceDrawer와 tool card UX 고도화 전에 Auth를 먼저 붙인다. 로그인 이후 실제 사용자 기준으로 대화 저장, 사이드바 대화 목록, 마이페이지, 회원탈퇴 흐름을 잡아야 이후 클라이언트 QA가 안정적이다.

Auth 구현 기준 문서:

- [`docs/planning/login-spec/001-auth-login-spec.md`](../planning/login-spec/001-auth-login-spec.md)

### 2.1 확정된 Auth 방향

- Hosted Supabase를 사용한다.
- MVP 로그인 provider는 Google OAuth만 지원한다.
- 이메일/비밀번호 로그인은 만들지 않는다.
- 비로그인 사용자는 채팅을 사용할 수 없다.
- 비로그인 사용자가 채팅 입력 또는 전송을 시도하면 로그인 모달을 표시한다.
- OAuth callback, cookie 발급, session 검증, refresh, logout은 FastAPI backend가 담당한다.
- access token과 refresh token은 HttpOnly cookie로 관리한다.
- client는 token을 직접 저장하거나 읽지 않는다.
- 최초 가입 시 랜덤 닉네임을 생성한다.
- 닉네임은 unique여야 한다.
- 응원팀은 선택값이며 마이페이지에서 수정한다.
- 회원정보는 hard delete, 채팅 대화방과 메시지는 soft delete한다.

### 2.2 Backend Auth 작업

- Supabase Auth 연동 설정과 환경변수를 정리한다.
- `public.user_profiles` migration을 추가한다.
- 기존 `chat_conversations`, `chat_messages`에 auth용 컬럼과 soft delete 컬럼을 보완한다.
- Auth router/service/dependency를 추가한다.
- `GET /api/v1/auth/google`
- `GET /api/v1/auth/callback`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `PATCH /api/v1/auth/me`
- `DELETE /api/v1/auth/me`
- 채팅 API에서 guest 기반 요청을 로그인 사용자 기반 요청으로 변경한다.
- 회원탈퇴 시 user profile hard delete, Supabase Auth user 삭제, conversation/message soft delete를 처리한다.

### 2.3 Client Auth 작업

- 기존 local/mock auth 흐름을 실제 auth API 흐름으로 교체한다.
- 로그인 모달을 Google OAuth only로 정리한다.
- 비로그인 상태에서 채팅 전송 시 로그인 모달을 표시한다.
- 앱 부팅 또는 chat page 진입 시 `GET /api/v1/auth/me`로 세션을 확인한다.
- Header 우측에 로그인 전/후 상태를 표시한다.
- profile dropdown에 마이페이지와 로그아웃을 추가한다.
- 마이페이지에서 닉네임 수정, 응원팀 선택/수정, 회원탈퇴를 제공한다.
- 채팅 요청에서 `guest_id`를 제거한다.
- `401 unauthenticated` 응답을 받으면 로그인 모달을 표시한다.

## 3. Auth 이후: 데이터 세팅 후 SourceDrawer 작업

Auth 구현과 기본 로그인 QA가 끝난 뒤 SourceDrawer를 실제 데이터에 연결한다.

### 3.1 SourceDrawer 실제 연결

- SSE `assistant.completed`의 `sources`, `limitations`를 클라이언트 상태에 보관한다.
- tool result 내부의 출처성 데이터도 SourceDrawer에 모아 표시할 수 있는 형태로 정규화한다.
- 채팅 본문과 tool card는 핵심 흐름과 요약을 담당하고, SourceDrawer는 출처 제목, 원문 링크, 주의/참고를 담당한다.
- 출처 패널은 빈 상태, 로딩 상태, 출처 있음 상태를 분리한다.

### 3.2 SourceDrawer 1차 표시 기준

- 출처 제목
- 원문 링크
- 주의/참고 문구
- 너무 딱딱한 한계 고지보다 부드러운 안내 문구를 사용한다.
- 출처 유형, 관련 tool 이름, 기준 시점, trust level은 후속 확장 후보로 둔다.

## 4. Auth 이후: 클라이언트 CSS/UX 보완 메모

현재 클라이언트 CSS는 MVP 수준이므로 제품 느낌을 높이기 위한 추가 보완이 필요하다.

### 4.1 Tool card 개별 고도화

- `find_kbo_game`: 경기 매치업, 날짜, 구장, 상태를 경기 카드처럼 더 명확하게 보여준다.
- `get_weather_context`: 기온, 강수 확률, 습도, 직관 컨디션을 시각적으로 비교하기 쉽게 다듬는다.
- `search_ticketing_guide`: 예매 상태, 공식 링크, 확인 실패 상태를 더 명확하게 분리한다.
- `search_stadium_guide`, `search_baseball_knowledge`: 긴 근거 텍스트를 카드 안에서 과밀하지 않게 요약한다.

### 4.2 Chat active state 다듬기

- 메시지 리스트와 composer dock 사이 간격을 viewport별로 점검한다.
- assistant placeholder, typing indicator, tool card가 이어질 때 빈 박스나 어색한 여백이 생기지 않는지 확인한다.
- 응답 실패 후 다시 시도 시 기존 실패 메시지를 유지할지, 새 메시지로 추가할지 정책을 정한다.

### 4.3 Mobile UX 점검

- 390px 폭 기준으로 fixed header, sidebar hamburger, composer dock, 작업 내역 버튼이 겹치지 않는지 확인한다.
- 우측 하단 `작업 내역` 버튼이 모바일 composer 입력 흐름을 방해하지 않도록 위치와 크기를 조정한다.
- off-canvas sidebar가 열린 상태에서 body scroll, overlay, focus 이동을 점검한다.

### 4.4 시각 품질 보완

- 현재 색상과 카드 스타일은 기능 확인에 충분한 MVP 수준이다.
- 카드 내부 grid, status badge, icon tile의 대비와 밀도를 더 정교하게 조정한다.
- 정보성 UI는 장식보다 스캔 가능성, 값의 우선순위, 반복 사용성을 우선한다.

## 5. 다음 권장 순서

1. Auth 스펙 문서를 기준으로 backend migration과 Auth API를 구현한다.
2. client 로그인 모달, header, 마이페이지, 채팅 인증 흐름을 실제 Auth API에 연결한다.
3. 비로그인 채팅 차단과 `401 unauthenticated` 처리 UX를 QA한다.
4. 로컬 데이터 세팅을 완료한다.
5. 실제 SSE 응답으로 SourceDrawer 데이터 연결을 진행한다.
6. tool card별 도메인 UI를 고도화한다.
7. 모바일 active chat을 수동 QA한다.
8. streaming 상태 관리 hook 분리를 검토한다.
