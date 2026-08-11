# Backend Auth OAuth Session Progress

> 작성일: 2026-08-11
> 목적: Supabase Auth 백엔드 구성 진행 상황과 다음 세션에서 이어갈 작업을 기록한다.

## 1. 이번 세션에서 완료한 것

- Supabase Google OAuth provider 설정을 진행했다.
  - Google Cloud Console에서 OAuth Client ID/Secret을 생성했다.
  - Supabase Dashboard의 Google provider에 Client ID/Secret을 등록했다.
  - Supabase callback URL을 Google Cloud Console 승인된 리디렉션 URI에 등록했다.
  - `Skip nonce checks`, `Allow users without an email`은 OFF로 유지했다.
- 로컬 Supabase DB에 Auth용 migration을 적용했고, `user_profiles` 테이블 추가를 확인했다.
- 백엔드 Auth 설정값을 추가했다.
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY` 또는 새 `sb_publishable_...` key
  - `SUPABASE_SERVICE_ROLE_KEY` 또는 새 `sb_secret_...` key
  - `APP_BASE_URL`
  - `FRONTEND_APP_URL`
  - Auth cookie 관련 설정
- 백엔드에 Auth 도메인 골격과 실제 OAuth session 흐름을 추가했다.

## 2. 주요 코드 변경

- Auth migration 추가:
  - `supabase/migrations/20260811090000_add_auth_user_profiles.sql`
- Auth API 라우터 추가:
  - `backend/app/domains/auth/controller/router.py`
- Supabase Auth REST client 추가:
  - `backend/app/domains/auth/infrastructure/supabase_auth_client.py`
- user profile repository 추가:
  - `backend/app/domains/auth/infrastructure/repositories.py`
- Auth service/dto 추가:
  - `backend/app/domains/auth/service/services.py`
  - `backend/app/domains/auth/service/dto.py`
- FastAPI 라우터/의존성 연결:
  - `backend/app/api/v1/router.py`
  - `backend/app/api/dependencies.py`
- cookie 사용을 위해 CORS credentials 허용:
  - `backend/app/main.py`
- conversation/message 모델에 Auth 전환용 컬럼 반영:
  - `user_profile_id`
  - `chat_messages.deleted_at`

## 3. 현재 구현된 Auth API

- `GET /api/v1/auth/google`
  - 서버에서 PKCE `state`, `code_verifier`를 생성한다.
  - 임시 HttpOnly cookie로 저장한다.
  - Hosted Supabase Google OAuth authorize URL로 redirect한다.
- `GET /api/v1/auth/callback`
  - Supabase가 돌려준 `code`, `state`를 검증한다.
  - `code_verifier`로 Supabase session을 교환한다.
  - `user_profiles`를 조회하거나 랜덤 닉네임으로 생성한다.
  - `nb_access_token`, `nb_refresh_token` HttpOnly cookie를 발급한다.
  - 프론트 앱으로 redirect한다.
- `GET /api/v1/auth/me`
  - access token cookie로 Supabase user를 확인한다.
  - 앱 profile을 반환한다.
- `POST /api/v1/auth/refresh`
  - refresh token cookie로 Supabase session을 갱신한다.
- `POST /api/v1/auth/logout`
  - auth cookie를 삭제한다.

## 4. 검증한 것

- `uv run ruff check app/domains/auth app/api/dependencies.py app/api/v1/router.py app/core/config.py app/main.py`
  - 통과
- `uv run python -m compileall app`
  - 통과
- FastAPI `TestClient` 확인:
  - `/api/v1/auth/google`이 307 redirect를 반환하고 임시 PKCE cookie를 설정한다.
  - `/api/v1/auth/me`는 비로그인 상태에서 `401 unauthenticated`를 반환한다.

## 5. 중요한 주의점

실제 Google OAuth callback까지 테스트하려면 Supabase Auth와 FastAPI가 쓰는 DB가 같은 Supabase 프로젝트를 바라봐야 한다.

현재 `.env`에서:

```text
SUPABASE_URL = Hosted Supabase Auth
DATABASE_URL = local Supabase DB
```

처럼 되어 있으면 Hosted Supabase Auth에는 사용자가 생기지만 local DB의 `auth.users`에는 같은 사용자가 없어서 `user_profiles.auth_user_id references auth.users(id)` FK에서 실패할 수 있다.

다음 세션에서 실제 OAuth QA를 하려면 둘 중 하나를 선택한다.

## 6. 다음 세션 권장 순서

### 선택지 A: Hosted Supabase DB로 QA

운영 방향과 가장 가깝다.

1. Supabase Dashboard에서 Hosted DB connection string을 확인한다.
2. `backend/.env`의 `DATABASE_URL`을 Hosted DB로 임시 변경한다.
3. Hosted DB에 migration을 적용한다.
   - 예: `supabase link --project-ref ztopdfbdvspzatbrcwif`
   - 예: `supabase db push`
4. FastAPI를 실행한다.
5. 브라우저에서 `http://127.0.0.1:4000/api/v1/auth/google` 접속 후 실제 로그인 callback을 테스트한다.
6. 로그인 후 `GET /api/v1/auth/me`가 profile을 반환하는지 확인한다.

주의: Hosted DB migration 적용은 실제 원격 DB 변경 작업이므로 사용자 확인 후 진행한다.

### 선택지 B: Local Supabase Auth로 QA

로컬 완전 격리 테스트에 적합하지만 Google OAuth 설정을 로컬 Supabase에도 추가해야 한다.

1. Google Cloud Console 승인된 리디렉션 URI에 `http://127.0.0.1:54321/auth/v1/callback`을 추가한다.
2. `supabase/config.toml`에 Google provider 설정을 추가한다.
3. `SUPABASE_URL=http://127.0.0.1:54321`로 바꾼다.
4. `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres`를 유지한다.
5. 로컬 Supabase Auth와 local DB 기준으로 OAuth를 테스트한다.

## 7. 다음 구현 작업

- 실제 OAuth callback 브라우저 QA
- 오류 발생 시 Supabase token exchange 응답에 맞춰 `supabase_auth_client.py` 보정
- `PATCH /api/v1/auth/me` 닉네임/응원팀 수정 구현
- `DELETE /api/v1/auth/me` 회원탈퇴 구현
- 채팅 API를 guest 기반에서 로그인 사용자 `user_profile_id` 기준으로 전환
- 프론트 로그인 모달/Header/auth state 연결
