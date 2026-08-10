# Auth and Login Spec v1

> 작성일: 2026-08-10  
> 목적: New Baseball MVP의 로그인, 세션, 사용자 프로필, 회원탈퇴 정책을 구현 전 기준 문서로 고정한다.

## 1. 결정 사항

- Auth provider는 Hosted Supabase를 사용한다.
- MVP 로그인 provider는 Google OAuth만 지원한다.
- 이메일/비밀번호 로그인은 지원하지 않는다.
- 카카오/네이버 로그인은 MVP 이후 확장 후보로 둔다.
- 비로그인 사용자는 채팅을 사용할 수 없다.
- 비로그인 사용자가 채팅 입력 또는 전송을 시도하면 로그인 모달을 표시한다.
- OAuth callback, 쿠키 발급, 세션 검증, refresh, logout은 FastAPI 백엔드가 담당한다.
- 프론트엔드는 access token과 refresh token을 직접 저장하거나 읽지 않는다.
- 세션은 HttpOnly cookie 기반 access token + refresh token 방식으로 관리한다.
- 최초 가입 시 완전 랜덤 닉네임을 자동 부여한다.
- 닉네임은 중복을 허용하지 않는다.
- 응원팀은 필수가 아니며, 마이페이지에서 선택 또는 수정할 수 있다.
- 회원정보는 회원탈퇴 시 hard delete한다.
- 채팅 대화방과 메시지는 회원탈퇴 시 soft delete한다.
- 회원탈퇴 시 Supabase Auth user도 삭제한다.

## 2. Supabase 구성

### 2.1 Hosted Supabase

Supabase는 공식 Hosted Supabase 프로젝트를 사용한다.

로컬 개발에서도 Auth 자체는 Hosted Supabase에 연결한다. 운영 도메인은 배포 시점에 Supabase Dashboard와 Google Cloud Console에 추가 등록한다.

### 2.2 Google OAuth

MVP에서 지원하는 provider는 Google OAuth 하나다.

등록해야 할 callback URL:

- Local: `http://127.0.0.1:4000/api/v1/auth/callback`
- Production: 배포 도메인 확정 후 추가

Google에서 받아오는 사용자 정보 중 앱 DB에 저장하는 값은 최소화한다.

- 실명/name은 앱 DB에 저장하지 않는다.
- 프로필 이미지는 MVP에서 저장하지 않는다.
- 이메일은 필요 시 암호화된 형태로만 앱 DB에 저장한다.

## 3. 세션과 쿠키

### 3.1 Token 구성

- `access_token`: 짧은 만료 주기
- `refresh_token`: 긴 만료 주기

Supabase Auth가 발급한 세션 토큰을 FastAPI가 HttpOnly cookie로 내려준다.

### 3.2 Cookie 이름

- `nb_access_token`
- `nb_refresh_token`

### 3.3 Cookie 옵션

운영:

- `HttpOnly=true`
- `Secure=true`
- `SameSite=Lax`
- `Path=/`

로컬 개발:

- `HttpOnly=true`
- `Secure=false`
- `SameSite=Lax`
- `Path=/`

### 3.4 Refresh 정책

- API 요청에서 access token 만료를 감지하면 refresh token으로 세션을 갱신한다.
- 별도 `POST /api/v1/auth/refresh` 엔드포인트를 제공한다.
- 프론트엔드는 앱 부팅 또는 화면 진입 시 `GET /api/v1/auth/me`로 로그인 상태를 확인한다.

## 4. 사용자 프로필

### 4.1 앱 프로필 테이블

Supabase `auth.users`는 Auth provider가 관리한다. 앱에서 필요한 닉네임, 응원팀, 암호화 이메일은 별도 public table에 저장한다.

권장 테이블명:

```text
public.user_profiles
```

권장 컬럼:

```text
id uuid primary key
auth_user_id uuid not null unique references auth.users(id) on delete cascade
encrypted_email text null
nickname varchar(32) not null unique
favorite_team varchar(30) null
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
last_login_at timestamptz null
```

### 4.2 Nickname 정책

- 최초 가입 시 서버에서 랜덤 닉네임을 생성한다.
- 닉네임은 중복을 허용하지 않는다.
- 중복이 발생하면 서버가 새 닉네임을 재시도한다.
- 사용자는 마이페이지에서 닉네임을 수정할 수 있다.
- 닉네임 수정 시에도 unique 제약을 지킨다.

예시 닉네임 형식:

```text
직관러-4831
야구친구-9284
불펜탐험가-1742
```

### 4.3 Favorite Team 정책

- `favorite_team`은 nullable이다.
- 가입 시 필수 선택으로 막지 않는다.
- 마이페이지에서 선택 또는 수정할 수 있다.
- 값은 KBO 10개 팀 enum으로 제한한다.

권장 enum 후보:

```text
LG
DOOSAN
KIWOOM
SSG
KT
KIA
SAMSUNG
LOTTE
HANWHA
NC
```

## 5. 기존 채팅 테이블 변경

현재 대화방과 메시지 테이블은 이미 존재한다.

- `public.chat_conversations`
- `public.chat_messages`

Auth 도입 시 새로 만들기보다 기존 테이블을 확장한다.

### 5.1 chat_conversations

현재 `user_id`는 `auth.users.id`를 직접 참조하는 구조다. 앱 프로필 hard delete와 채팅 soft delete 정책을 위해 `user_profile_id`를 추가한다.

권장 변경:

```text
user_profile_id uuid null references public.user_profiles(id) on delete set null
deleted_at timestamptz null -- already exists
```

기존 `guest_id`는 비로그인 채팅을 제거하면서 deprecated 처리한다. 실제 제거는 마이그레이션 안정화 이후 별도 작업으로 미룬다.

기존 `user_id`도 단계적으로 deprecated 처리한다. 최종적으로는 `user_profile_id`를 기준으로 조회한다.

### 5.2 chat_messages

권장 변경:

```text
user_profile_id uuid null references public.user_profiles(id) on delete set null
deleted_at timestamptz null
```

메시지 조회는 `deleted_at is null` 조건을 기본으로 한다.

기존 `user_id`는 단계적으로 deprecated 처리한다.

## 6. 회원탈퇴 정책

회원탈퇴 시 회원정보는 hard delete하고, 채팅 데이터는 soft delete한다.

처리 순서:

1. 현재 세션을 검증한다.
2. 현재 `user_profile_id`에 속한 `chat_conversations.deleted_at`을 현재 시각으로 설정한다.
3. 해당 대화방의 `chat_messages.deleted_at`을 현재 시각으로 설정한다.
4. `public.user_profiles` row를 hard delete한다.
5. Supabase Auth user를 삭제한다.
6. `nb_access_token`, `nb_refresh_token` 쿠키를 제거한다.

회원탈퇴 후 같은 Google 계정으로 다시 로그인하면 새 사용자로 가입된다.

일반 대화 목록, 메시지 목록, 검색 조회에서는 soft-deleted conversation/message를 제외한다.

## 7. Backend API

Auth router 권장 prefix:

```text
/api/v1/auth
```

필요 엔드포인트:

```text
GET    /api/v1/auth/google
GET    /api/v1/auth/callback
GET    /api/v1/auth/me
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
PATCH  /api/v1/auth/me
DELETE /api/v1/auth/me
```

### 7.1 GET /auth/google

Google OAuth 시작 URL로 redirect한다.

### 7.2 GET /auth/callback

Supabase OAuth callback을 처리한다.

성공 시:

- Supabase session을 확인한다.
- `public.user_profiles` row를 조회하거나 생성한다.
- 신규 가입이면 랜덤 unique 닉네임을 부여한다.
- `last_login_at`을 갱신한다.
- `nb_access_token`, `nb_refresh_token` 쿠키를 설정한다.
- 프론트 앱으로 redirect한다.

### 7.3 GET /auth/me

현재 로그인 사용자의 앱 프로필을 반환한다.

비로그인 또는 세션 만료 시 `401 unauthenticated`를 반환한다.

응답 예시:

```json
{
  "user": {
    "id": "profile uuid",
    "nickname": "직관러-4831",
    "favoriteTeam": null
  }
}
```

### 7.4 POST /auth/refresh

refresh token cookie를 사용해 Supabase session을 갱신하고 새 쿠키를 내려준다.

### 7.5 POST /auth/logout

Supabase session을 종료하고 쿠키를 제거한다.

### 7.6 PATCH /auth/me

마이페이지에서 닉네임과 응원팀을 수정한다.

수정 가능 필드:

```text
nickname
favorite_team
```

닉네임 중복 시 `409 nickname_already_exists`를 반환한다.

### 7.7 DELETE /auth/me

회원탈퇴를 처리한다.

성공 시:

- 앱 프로필 hard delete
- Supabase Auth user 삭제
- 대화방과 메시지 soft delete
- 쿠키 제거

## 8. Chat API 인증 정책

채팅 API는 로그인 사용자만 사용할 수 있다.

비로그인 요청:

```text
401 unauthenticated
```

프론트는 이 응답을 받으면 로그인 모달을 연다.

Auth 도입 후 채팅 요청에서 `guest_id`는 제거한다. `conversation_id`는 현재 로그인 사용자의 `user_profile_id`에 속한 대화인지 검증한다.

## 9. Frontend UX

### 9.1 Login Modal

- Google 로그인 버튼만 제공한다.
- 이메일/비밀번호 입력 UI는 만들지 않는다.
- 비로그인 사용자가 채팅 전송을 시도하면 모달을 표시한다.

### 9.2 Header

로그인 전:

- 로그인 버튼 표시

로그인 후:

- 닉네임 표시
- 프로필 버튼 표시
- dropdown에 마이페이지, 로그아웃 제공

### 9.3 My Page

마이페이지에서 제공할 기능:

- 닉네임 수정
- 응원팀 선택 또는 수정
- 로그아웃
- 회원탈퇴

회원탈퇴는 확인 modal을 거친다.

## 10. 구현 순서

1. Supabase Google OAuth 설정
2. `public.user_profiles` migration 추가
3. `chat_conversations`, `chat_messages` auth 관련 migration 추가
4. FastAPI Auth router 추가
5. 세션 cookie 설정/검증 dependency 추가
6. Chat API를 로그인 사용자 기준으로 변경
7. 프론트 로그인 모달을 Google OAuth redirect 방식으로 변경
8. Header 로그인 상태와 마이페이지 추가
9. 회원탈퇴 flow 구현
10. 기존 guest session localStorage 흐름 제거

## 11. 후속 확장 후보

- Kakao OAuth 추가
- Naver OAuth 또는 custom provider 검토
- CSRF token 추가
- 응원팀 기반 개인화 추천
- 닉네임 변경 횟수 제한
- 계정 재가입 제한 정책
- 탈퇴 데이터 보관 기간 정책 명문화
