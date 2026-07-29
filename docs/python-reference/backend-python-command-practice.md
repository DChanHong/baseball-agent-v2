# Backend Python Command Practice

> 기준 위치: `/Users/hong/Desktop/baseball-agent-v2`
> 백엔드 위치: `/Users/hong/Desktop/baseball-agent-v2/backend`

이 문서는 FastAPI 백엔드 프로젝트를 처음 클론한 뒤, Python 가상환경과 패키지 설치, 로컬 실행, 검사, 테스트 명령을 연습하기 위한 메모다.

## 1. 용어 정리

### venv

`venv`는 Python 가상환경이다.

프로젝트마다 독립된 Python 패키지 설치 공간을 만드는 역할을 한다.

예를 들어 A 프로젝트는 FastAPI 0.140을 쓰고, B 프로젝트는 다른 버전을 쓸 수 있다. 이때 패키지들이 서로 섞이지 않게 해주는 것이 가상환경이다.

보통 프로젝트 안에 `.venv` 폴더로 만든다.

```bash
python3 -m venv .venv
```

활성화:

```bash
source .venv/bin/activate
```

비활성화:

```bash
deactivate
```

### .env

`.env`는 Python 가상환경이 아니다.

`.env`는 환경변수 파일이다. DB 주소, API 키, 비밀번호처럼 코드에 직접 넣으면 안 되는 값을 저장한다.

이 프로젝트에서는 예시 파일이 있다.

```bash
backend/.env.example
```

처음 설정할 때는 보통 다음처럼 복사한다.

```bash
cp .env.example .env
```

`.env`는 보통 Git에 커밋하지 않는다.

### pip

`pip`는 Python 패키지 설치 도구다.

전통적인 방식에서는 `requirements.txt`를 기준으로 패키지를 설치한다.

```bash
pip install -r requirements.txt
```

개발용 패키지까지 설치할 때:

```bash
pip install -r requirements-dev.txt
```

### uv

`uv`는 빠른 Python 패키지/가상환경/실행 도구다.

이 프로젝트의 백엔드는 다음 파일을 가지고 있다.

```text
backend/pyproject.toml
backend/uv.lock
```

그래서 이 프로젝트에서는 `uv`를 기본으로 연습하는 것이 좋다.

`uv run`을 쓰면 가상환경을 직접 활성화하지 않아도, 프로젝트 환경 안에서 명령을 실행할 수 있다.

```bash
uv run python --version
```

## 2. 이 프로젝트의 추천 방식

이 프로젝트에서는 기본적으로 `uv`를 사용한다.

핵심 명령만 외우면 다음과 같다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
uv run ruff check app tests
uv run pytest
```

## 3. Git clone 직후 초기 설정 연습

저장소를 새로 받는다고 가정한다.

```bash
git clone <repo-url>
cd baseball-agent-v2
```

백엔드 폴더로 이동한다.

```bash
cd backend
```

의존성을 설치하거나 동기화한다.

```bash
uv sync
```

환경변수 파일을 만든다.

```bash
cp .env.example .env
```

Python 버전을 확인한다.

```bash
uv run python --version
```

## 4. FastAPI 로컬 실행

백엔드 폴더에서 실행한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
```

FastAPI 개발 서버를 실행한다.

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

옵션 의미:

| 옵션 | 의미 |
|---|---|
| `app.main:app` | `app/main.py` 파일 안의 FastAPI `app` 객체 실행 |
| `--reload` | 코드 변경 시 서버 자동 재시작 |
| `--host 127.0.0.1` | 내 컴퓨터에서만 접근 |
| `--port 4000` | 4000번 포트로 서버 실행 |

실행 후 브라우저에서 Swagger 문서를 확인한다.

```text
http://127.0.0.1:4000/docs
```

서버를 종료할 때는 실행 중인 터미널에서 `Control + C`를 누른다.

## 5. Health Check

서버가 켜져 있을 때 다른 터미널에서 확인한다.

```bash
curl http://127.0.0.1:4000/health
```

DB 연결까지 확인한다.

```bash
curl http://127.0.0.1:4000/health/db
```

## 6. 코드 검사와 포맷

백엔드 폴더에서 실행한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
```

Lint 검사:

```bash
uv run ruff check app tests
```

특정 파일만 검사:

```bash
uv run ruff check app/main.py
```

포맷 적용:

```bash
uv run ruff format app tests
```

포맷이 필요한지만 확인:

```bash
uv run ruff format --check app tests
```

Python 문법과 import 가능 여부 확인:

```bash
uv run python -m compileall -q app tests
```

## 7. 테스트 실행

전체 테스트:

```bash
uv run pytest
```

특정 폴더 테스트:

```bash
uv run pytest tests
```

특정 테스트 파일 실행:

```bash
uv run pytest tests/api/test_example.py
```

현재 프로젝트는 테스트 파일이 아직 거의 없을 수 있다. 이 경우 `collected 0 items`가 나올 수 있는데, 명령 실패라기보다 실행할 테스트가 없다는 뜻이다.

## 8. pip + venv 방식으로도 연습하기

`uv`가 아니라 전통적인 Python 방식으로 연습하려면 다음 흐름을 사용한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
deactivate
```

주의할 점:

- `source .venv/bin/activate`를 한 뒤에는 `python`, `pip`, `uvicorn`이 가상환경 기준으로 실행된다.
- `deactivate`하면 다시 시스템 Python 환경으로 돌아간다.
- 이 프로젝트에서는 `uv run ...`을 쓰면 직접 activate하지 않아도 된다.

## 9. Supabase를 함께 실행할 때

DB가 필요한 API까지 확인하려면 프로젝트 루트에서 Supabase를 먼저 실행한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2
supabase start
supabase status
```

그 다음 다른 터미널에서 FastAPI를 실행한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

작업 종료:

```bash
# FastAPI 터미널
Control + C
```

```bash
# 프로젝트 루트
supabase stop
```

## 10. 자주 쓰는 연습 순서

처음부터 다시 연습:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv sync
cp .env.example .env
uv run python --version
uv run ruff check app tests
uv run pytest
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

이미 설정된 프로젝트를 다시 실행:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

코드 변경 후 확인:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run ruff check app tests
uv run ruff format --check app tests
uv run python -m compileall -q app tests
uv run pytest
```

## 11. 빠른 암기표

| 하고 싶은 일 | 명령 |
|---|---|
| 백엔드 폴더 이동 | `cd /Users/hong/Desktop/baseball-agent-v2/backend` |
| 의존성 설치/동기화 | `uv sync` |
| Python 버전 확인 | `uv run python --version` |
| FastAPI 실행 | `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000` |
| Swagger 확인 | `http://127.0.0.1:4000/docs` |
| Lint 검사 | `uv run ruff check app tests` |
| 포맷 확인 | `uv run ruff format --check app tests` |
| 포맷 적용 | `uv run ruff format app tests` |
| 테스트 실행 | `uv run pytest` |
| 가상환경 활성화 | `source .venv/bin/activate` |
| 가상환경 종료 | `deactivate` |

