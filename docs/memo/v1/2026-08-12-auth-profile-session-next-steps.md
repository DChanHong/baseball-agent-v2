# Auth Profile Session Next Steps

> 작성일: 2026-08-12
> 목적: Google OAuth 로그인/세션 흐름 완료 후 다음 세션에서 이어갈 Auth 작업을 기록한다.

## 1. 현재 완료된 상태

- 로컬 Supabase Auth Google provider 설정을 반영했다.
  - `supabase/config.toml`에는 `[auth.external.google]`가 설정되어 있다.
  - 로컬 Supabase 재시작 시 root `.env`를 export한 상태로 실행해야 Google provider env가 컨테이너에 들어간다.
- Google OAuth 로그인 callback 흐름을 브라우저로 확인했다.
  - 프론트 로그인 버튼에서 backend `/api/v1/auth/google`로 이동한다.
  - Supabase Google OAuth callback 후 backend `/api/v1/auth/callback`으로 돌아온다.
  - backend가 Supabase session을 교환하고 HttpOnly cookie를 설정한다.
  - 프론트가 `/api/v1/auth/me`로 현재 사용자를 조회한다.
  - Header에 닉네임이 표시된다.
- Supabase OAuth `bad_oauth_state` 문제를 수정했다.
  - Supabase `/auth/v1/authorize` 최상위 `state`는 사용하지 않는다.
  - backend 검증용 state는 `redirect_to` 내부 `oauth_state`로 전달한다.
- Next dev HMR cross-origin 경고를 해결했다.
  - `frontend/next.config.ts`에 `allowedDevOrigins`를 추가했다.
- callback 후 현재 사용자 확인 중 Header에 로딩 상태를 표시한다.

관련 커밋:

```text
7d65516 Fix local OAuth callback flow
```

## 2. 다음 구현 작업

### 2.1 `PATCH /api/v1/auth/me`

목적:

- 현재 로그인 사용자의 앱 프로필을 수정한다.

대상 필드:

- `nickname`
- `favoriteTeam`

구현 고려사항:

- access token cookie로 현재 Supabase user를 확인한다.
- `public.user_profiles.auth_user_id` 기준으로 profile을 찾는다.
- nickname은 공백 제거 후 빈 문자열을 거부한다.
- nickname 중복 시 명확한 409 응답을 반환한다.
- `favoriteTeam`은 `null` 또는 KBO team id만 허용한다.
- 응답은 현재 `GET /auth/me`와 같은 shape을 유지한다.

### 2.2 `DELETE /api/v1/auth/me`

목적:

- 현재 로그인 사용자의 회원탈퇴를 처리한다.

구현 고려사항:

- access token cookie로 현재 Supabase user를 확인한다.
- Supabase Auth admin delete user API 또는 적절한 server-side 삭제 방식을 사용한다.
- `public.user_profiles`는 `auth.users` FK `on delete cascade`로 삭제되는 구조다.
- 삭제 후 `nb_access_token`, `nb_refresh_token` cookie를 제거한다.
- 채팅 데이터 삭제/익명화 정책은 별도 결정이 필요하다.

주의:

- 회원탈퇴는 사용자 데이터 삭제 정책과 연결되므로 구현 전 삭제 범위를 명확히 정한다.

### 2.3 Refresh 자동 호출

현재 상태:

- backend에는 `POST /api/v1/auth/refresh`가 있다.
- refresh token은 DB에 저장하지 않고 HttpOnly cookie `nb_refresh_token`에 보관한다.
- refresh 성공 시 새 access/refresh token cookie로 덮어쓴다.

다음 작업:

- 프론트 API fetch 레벨에서 `/auth/me` 또는 인증 API가 401을 받았을 때 `/auth/refresh`를 한 번 호출하고 원 요청을 재시도할지 결정한다.
- 무한 retry를 막기 위해 요청당 refresh retry는 1회로 제한한다.
- refresh도 401이면 current user cache를 `null`로 비운다.

### 2.4 채팅 API owner 전환

목적:

- 기존 guest 기반 채팅 소유권을 로그인 사용자 `user_profile_id` 기준으로 전환한다.

현재 DB 준비 상태:

- `chat_conversations.user_profile_id`
- `chat_messages.user_profile_id`
- `chat_messages.deleted_at`

구현 고려사항:

- 로그인 사용자는 cookie 기반 현재 profile을 resolve해서 `user_profile_id`를 사용한다.
- 비로그인 사용자는 기존처럼 `guest_id`를 유지할지, 로그인 필수로 바꿀지 정책을 정한다.
- 로그인 직후 기존 guest 대화를 사용자 profile로 이전할지 결정한다.
- repository query는 `guest_id` 조건과 `user_profile_id` 조건이 섞이지 않게 분리한다.
- 메시지 soft delete 정책은 `deleted_at is null` 조건을 일관되게 적용한다.

## 3. 로컬 Supabase 실행/중지 메모

Google provider env를 반영해서 로컬 Supabase를 시작할 때:

```bash
cd /Users/hong/Desktop/baseball-agent-v2
set -a
source .env
set +a
supabase start
```

로컬 Supabase를 중지할 때:

```bash
cd /Users/hong/Desktop/baseball-agent-v2
supabase stop
```

주의:

- `supabase stop`은 DB volume을 삭제하지 않는다.
- DB 데이터를 지우는 명령은 `supabase stop --no-backup` 또는 `supabase db reset`이다.
- reset은 현재 작업 흐름에서 사용하지 않는다.
