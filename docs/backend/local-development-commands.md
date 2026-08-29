# 백엔드 로컬 개발 명령어

> 라벨: `CURRENT`  
> 기준 작업공간: `/Users/hong/Desktop/내꺼연습/baseball-agent-v2`
> 구성: Supabase CLI + Docker + Python 3.13 + uv + FastAPI

이 문서는 로컬 Supabase와 FastAPI를 실행하고 migration 및 API를 확인할 때 사용하는 명령을 정리한다.

## 1. 현재 사용자 처리 방식

로그인은 Supabase Auth 기반으로 구현되어 있다. 비로그인 상태에서는 `/api/v1/chat`을 포함한 주요 API를 호출할 수 없다.

```text
user_id  = auth.users.id  (로그인한 사용자)
guest_id = NULL
```

인증 흐름:

```text
Frontend
→ FastAPI /api/v1/auth/google
→ Supabase Auth Google OAuth
→ FastAPI /api/v1/auth/callback
→ FastAPI가 HttpOnly cookie 세션 발급
→ 이후 frontend fetch는 credentials: "include"로 cookie 포함
→ FastAPI가 cookie의 access token으로 user_profile_id 추출
```

API에서 클라이언트가 Supabase 테이블을 직접 호출하지 않는다.

```text
Frontend
→ FastAPI
→ SQLAlchemy
→ Supabase PostgreSQL
```

## 2. 터미널 구성

로컬 개발 시 터미널을 두 개 사용하는 것이 편리하다.

```text
터미널 1: Supabase와 Docker 상태 관리
터미널 2: FastAPI 개발 서버 실행
```

모든 Supabase 명령은 프로젝트 루트에서 실행한다.

```bash
cd /Users/hong/Desktop/내꺼연습/baseball-agent-v2
```

FastAPI 명령은 `backend` 디렉터리에서 실행한다.

```bash
cd /Users/hong/Desktop/내꺼연습/baseball-agent-v2/backend
```

## 3. Docker 기본 확인

Docker Desktop을 먼저 실행한 뒤 Docker Engine 상태를 확인한다.

```bash
docker version
```

실행 중인 컨테이너를 확인한다.

```bash
docker ps
```

컨테이너 이름, 상태, 포트를 보기 쉽게 출력하려면 다음 명령을 사용한다.

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Supabase 로컬 컨테이너는 직접 `docker run`으로 생성하지 않는다. 이 프로젝트에서는 Supabase CLI가 Docker 컨테이너 구성을 관리한다.

```text
권장: supabase start, supabase stop, supabase status
지양: Supabase 컨테이너를 개별 docker run 명령으로 직접 생성
```

## 4. Supabase 로컬 실행

프로젝트 루트에서 로컬 Supabase를 시작한다.

```bash
supabase start
```

이미 실행 중이어도 현재 상태를 확인하고 필요한 서비스만 유지한다.

로컬 Supabase 상태와 접속 정보를 확인한다.

```bash
supabase status
```

로컬 Supabase를 중지한다.

```bash
supabase stop
```

Supabase 서비스가 정상인지 확인할 때 주로 사용하는 주소는 다음과 같다.

| 서비스 | 주소 |
|---|---|
| Supabase API | `http://127.0.0.1:54321` |
| PostgreSQL | `127.0.0.1:54322` |
| Supabase Studio | `http://127.0.0.1:54323` |
| 로컬 이메일 UI | `http://127.0.0.1:54324` |

포트는 `supabase/config.toml`을 기준으로 한다.

## 5. Supabase migration

새 migration 파일을 생성한다.

```bash
supabase migration new migration_name
```

예:

```bash
supabase migration new create_chat_conversations
```

생성되는 파일:

```text
supabase/migrations/<timestamp>_create_chat_conversations.sql
```

아직 적용되지 않은 migration을 로컬 DB에 적용한다.

```bash
supabase migration up
```

이미 성공한 migration은 다시 실행하지 않고 새 migration만 타임스탬프 순서로 적용한다.

로컬 DB를 migration 기준으로 처음부터 다시 구성하려면 다음 명령을 사용한다.

```bash
supabase db reset
```

`db reset`은 로컬 DB 데이터를 삭제하고 migration과 seed를 다시 적용하는 명령이다. 필요한 로컬 데이터가 있는지 확인한 후 실행한다.

적용된 테이블은 Supabase Studio에서 확인한다.

```text
http://127.0.0.1:54323
→ Table Editor
→ public schema
```

## 6. Python 프로젝트 최초 설정

`backend` 디렉터리로 이동한다.

```bash
cd backend
```

`pyproject.toml`과 `uv.lock`을 기준으로 의존성을 설치하거나 동기화한다.

```bash
uv sync
```

환경변수 파일을 최초 한 번 생성한다.

```bash
cp .env.example .env
```

현재 로컬 DB 접속 문자열:

```text
postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
```

실제 `.env`는 Git에 커밋하지 않는다. 공유 가능한 예시는 `.env.example`에만 작성한다.

## 7. Python 가상환경

`uv run`을 사용하면 가상환경을 직접 활성화하지 않아도 된다.

```bash
uv run python --version
```

가상환경을 직접 활성화하고 싶다면 macOS 또는 Linux에서 다음 명령을 사용한다.

```bash
source .venv/bin/activate
```

활성화 후 터미널 앞에 환경 이름이 표시된다.

```text
(backend) user@machine backend %
```

가상환경을 종료한다.

```bash
deactivate
```

이 프로젝트에서는 가상환경 활성화 여부와 관계없이 `uv run` 명령을 사용하면 일관된 환경에서 실행할 수 있다.

## 8. FastAPI 실행

`backend` 디렉터리에서 개발 서버를 실행한다.

```bash
uv run uvicorn app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 4000
```

한 줄로 실행할 수도 있다.

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

옵션 의미:

| 옵션 | 의미 |
|---|---|
| `app.main:app` | `app/main.py`에 있는 FastAPI `app` 객체 실행 |
| `--reload` | Python 파일 변경 시 개발 서버 자동 재시작 |
| `--host 127.0.0.1` | 현재 컴퓨터에서만 접근 |
| `--port 4000` | FastAPI 서버 포트 |

정상 실행 로그:

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:4000
```

서버를 종료하려면 서버가 실행 중인 터미널에서 `Control + C`를 누른다.

## 9. Health Check

애플리케이션 상태를 확인한다.

```bash
curl http://127.0.0.1:4000/health
```

DB 연결까지 확인한다.

```bash
curl http://127.0.0.1:4000/health/db
```

정상 응답 예:

```json
{
  "status": "ok",
  "message": "Database connection is healthy"
}
```

## 10. Swagger와 OpenAPI

FastAPI에는 Swagger UI가 기본 포함되어 있으므로 별도 설치가 필요 없다.

| 문서 | 주소 |
|---|---|
| Swagger UI | `http://127.0.0.1:4000/docs` |
| ReDoc | `http://127.0.0.1:4000/redoc` |
| OpenAPI JSON | `http://127.0.0.1:4000/openapi.json` |

Swagger에서 API를 호출하는 순서:

1. 엔드포인트를 펼친다.
2. `Try it out`을 누른다.
3. Request body를 입력한다.
4. `Execute`를 누른다.
5. Response status와 body를 확인한다.

## 11. 인증/채팅 API 호출

브라우저 기반 Google OAuth는 다음 URL에서 시작한다.

```text
http://127.0.0.1:4000/api/v1/auth/google
```

로그인 후 현재 사용자 확인:

```bash
curl --include \
  --cookie "nb_access_token=<access-token-cookie-value>" \
  http://127.0.0.1:4000/api/v1/auth/me
```

실제 브라우저/프론트 테스트에서는 access token을 직접 읽지 않고, 브라우저가 HttpOnly cookie를 자동으로 포함한다.

채팅 API는 로그인 cookie가 필요하다.

```bash
curl --request POST http://127.0.0.1:4000/api/v1/chat \
  --cookie "nb_access_token=<access-token-cookie-value>" \
  --header 'Content-Type: application/json' \
  --header 'Accept: text/event-stream' \
  --data '{
    "conversation_id": null,
    "message": "오늘 롯데 경기 있어?"
  }'
```

대화 목록 API도 로그인 cookie가 필요하다.

```bash
curl --cookie "nb_access_token=<access-token-cookie-value>" \
  http://127.0.0.1:4000/api/v1/conversations?limit=50
```

## 12. 코드 검사와 포맷

`backend` 디렉터리에서 전체 Python lint를 실행한다.

```bash
uv run ruff check app tests
```

특정 파일만 검사할 수도 있다.

```bash
uv run ruff check app/domains/conversation/domain/entities.py
```

코드 포맷을 적용한다.

```bash
uv run ruff format app tests
```

코드를 변경하지 않고 포맷 여부만 확인한다.

```bash
uv run ruff format --check app tests
```

Python 문법과 import 가능한 bytecode 생성을 확인한다.

```bash
uv run python -m compileall -q app tests
```

테스트 코드를 추가한 후 전체 테스트를 실행한다.

```bash
uv run pytest
```

## 13. Git 기본 명령

프로젝트 루트에서 변경 파일을 확인한다.

```bash
git status --short
```

실제 변경 내용을 확인한다.

```bash
git diff
```

staging 전에 공백 오류를 검사한다.

```bash
git diff --check
```

변경 파일을 staging 한다.

```bash
git add .
```

커밋한다.

```bash
git commit -m "feat: describe change"
```

원격 저장소에 반영한다.

```bash
git push origin main
```

`.env`, `.venv`, `__pycache__`, `supabase/.temp`가 staging 목록에 포함되지 않았는지 항상 확인한다.

## 14. 일반적인 로컬 실행 순서

프로젝트를 다시 시작할 때 다음 순서로 실행한다.

터미널 1:

```bash
cd /Users/hong/Desktop/내꺼연습/baseball-agent-v2
supabase start
supabase status
```

터미널 2:

```bash
cd /Users/hong/Desktop/내꺼연습/baseball-agent-v2/backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

브라우저:

```text
FastAPI Swagger  http://127.0.0.1:4000/docs
Supabase Studio  http://127.0.0.1:54323
```

작업 종료:

```text
FastAPI 터미널에서 Control + C
프로젝트 루트에서 supabase stop
```

## 15. 문제 해결

### 15.1 FastAPI 4000번 포트가 이미 사용 중

점유 프로세스를 확인한다.

```bash
lsof -nP -iTCP:4000 -sTCP:LISTEN
```

기존 개발 서버 터미널을 찾아 `Control + C`로 정상 종료한다. 임의로 프로세스를 강제 종료하기 전에 어떤 프로그램인지 확인한다.

### 15.2 FastAPI가 DB에 연결되지 않음

다음 순서로 확인한다.

```bash
supabase status
```

```bash
curl http://127.0.0.1:4000/health/db
```

`backend/.env`의 `DATABASE_URL`이 다음 로컬 포트를 사용하는지 확인한다.

```text
127.0.0.1:54322
```

### 15.3 migration이 적용되지 않음

프로젝트 루트에서 실행했는지 확인한다.

```bash
pwd
supabase migration up
```

성공 출력:

```text
Applying migration <migration-file>.sql...
Local database is up to date.
```

### 15.4 Swagger에 새 API가 보이지 않음

다음을 확인한다.

1. Uvicorn을 `--reload`로 실행했는가?
2. 도메인 Router가 `app/api/v1/router.py`에 포함됐는가?
3. v1 Router가 `app/api/router.py`에 포함됐는가?
4. `api_router`가 `app/main.py`에 포함됐는가?
5. 브라우저의 Swagger 페이지를 새로고침했는가?

라우터 연결 구조:

```text
domain controller router
→ app/api/v1/router.py
→ app/api/router.py
→ app/main.py
```
