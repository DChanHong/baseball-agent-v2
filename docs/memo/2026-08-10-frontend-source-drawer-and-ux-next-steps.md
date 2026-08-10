# Frontend SourceDrawer and UX Next Steps

> 작성일: 2026-08-10  
> 목적: 로컬 데이터 세팅 전 보류할 클라이언트 후속 작업과 MVP 수준 UI/UX 보완 항목을 기록한다.

## 1. 현재 상태

- Header branding, fixed header, left sidebar, composer 정리, assistant typing indicator, tool card running/completed/failed 표현은 1차 구현됐다.
- 우측 하단 `작업 내역` 버튼과 tool 진행 내역 패널이 추가됐다.
- tool card 공통 shell은 MVP 수준으로 정돈됐지만, 카드별 도메인 UI는 더 다듬을 여지가 있다.
- 현재 로컬 환경은 데이터 세팅이 아직 완료되지 않아 실제 출처/근거 데이터 기반 검증은 보류한다.

## 2. 데이터 세팅 후 우선 작업

### 2.1 SourceDrawer 실제 연결

- SSE `assistant.completed`의 `sources`, `limitations`를 클라이언트 상태에 보관한다.
- tool result 내부의 출처성 데이터도 SourceDrawer에 모아 표시할 수 있는 형태로 정규화한다.
- 채팅 본문과 tool card는 핵심 흐름과 요약을 담당하고, SourceDrawer는 출처 제목, 원문 링크, 주의/참고를 담당한다.
- 출처 패널은 빈 상태, 로딩 상태, 출처 있음 상태를 분리한다.

### 2.2 SourceDrawer 1차 표시 기준

- 출처 제목
- 원문 링크
- 주의/참고 문구
- 너무 딱딱한 한계 고지보다 부드러운 안내 문구를 사용한다.
- 출처 유형, 관련 tool 이름, 기준 시점, trust level은 후속 확장 후보로 둔다.

## 3. 클라이언트 CSS/UX 보완 메모

현재 클라이언트 CSS는 MVP 수준이므로 제품 느낌을 높이기 위한 추가 보완이 필요하다.

### 3.1 Tool card 개별 고도화

- `find_kbo_game`: 경기 매치업, 날짜, 구장, 상태를 경기 카드처럼 더 명확하게 보여준다.
- `get_weather_context`: 기온, 강수 확률, 습도, 직관 컨디션을 시각적으로 비교하기 쉽게 다듬는다.
- `search_ticketing_guide`: 예매 상태, 공식 링크, 확인 실패 상태를 더 명확하게 분리한다.
- `search_stadium_guide`, `search_baseball_knowledge`: 긴 근거 텍스트를 카드 안에서 과밀하지 않게 요약한다.

### 3.2 Chat active state 다듬기

- 메시지 리스트와 composer dock 사이 간격을 viewport별로 점검한다.
- assistant placeholder, typing indicator, tool card가 이어질 때 빈 박스나 어색한 여백이 생기지 않는지 확인한다.
- 응답 실패 후 다시 시도 시 기존 실패 메시지를 유지할지, 새 메시지로 추가할지 정책을 정한다.

### 3.3 Mobile UX 점검

- 390px 폭 기준으로 fixed header, sidebar hamburger, composer dock, 작업 내역 버튼이 겹치지 않는지 확인한다.
- 우측 하단 `작업 내역` 버튼이 모바일 composer 입력 흐름을 방해하지 않도록 위치와 크기를 조정한다.
- off-canvas sidebar가 열린 상태에서 body scroll, overlay, focus 이동을 점검한다.

### 3.4 시각 품질 보완

- 현재 색상과 카드 스타일은 기능 확인에 충분한 MVP 수준이다.
- 카드 내부 grid, status badge, icon tile의 대비와 밀도를 더 정교하게 조정한다.
- 정보성 UI는 장식보다 스캔 가능성, 값의 우선순위, 반복 사용성을 우선한다.

## 4. 다음 권장 순서

1. 로컬 데이터 세팅 완료
2. 실제 SSE 응답으로 SourceDrawer 데이터 연결
3. tool card별 도메인 UI 고도화
4. 모바일 active chat 수동 QA
5. streaming 상태 관리 hook 분리 검토

## 5. 로그인/Auth 후속 메모

원활한 클라이언트 테스트와 실제 대화 저장 흐름을 위해 로그인 기능도 후속 작업으로 필요하다.

### 5.1 클라이언트 선행 작업

- 실제 provider 결정 전에는 localStorage 기반 mock/local auth로 header와 modal 흐름을 먼저 테스트할 수 있다.
- 로그인 모달에서 닉네임 또는 이름을 입력하면 header 우측을 `로그인` 버튼에서 `이름/닉네임 + 원형 프로필`로 전환한다.
- 프로필 dropdown에는 `마이페이지`, `로그아웃`을 둔다.
- 새로고침 후에도 테스트 로그인 상태가 유지되도록 한다.
- 실제 auth로 교체하기 쉽도록 `AuthUser` 같은 타입을 먼저 잡아둔다.

### 5.2 백엔드/Auth 연동 필요

- 실제 서비스 단계에서는 backend에도 로그인/auth 처리가 필요하다.
- auth provider는 Supabase Auth 또는 다른 provider 중 결정해야 한다.
- backend API에서 authenticated user와 guest user를 구분하는 계약이 필요하다.
- conversation, message, source/citation 데이터를 user owner와 연결해야 한다.
- guest conversation을 로그인 계정으로 이전할지 정책을 정해야 한다.
- 로그인 후 대화 목록 API와 sidebar session list를 실제 user conversation summary와 연결한다.
