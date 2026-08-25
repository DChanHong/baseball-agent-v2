# Database Environment Switching

> 라벨: `CURRENT`  
> 기준 작업공간: `/Users/hong/Desktop/내꺼연습/baseball-agent-v2`

로컬 개발 중 backend가 사용할 DB를 로컬 Supabase와 운영 Supabase 사이에서 전환할 때 참고한다.

## 기준

backend가 실제로 접속하는 DB는 `backend/.env`의 `DATABASE_URL`로 결정된다.

backend 앱에서는 SQLAlchemy async driver를 쓰므로 `DATABASE_URL`은 `postgresql+asyncpg://` 형식을 사용한다.

```bash
DATABASE_URL=postgresql+asyncpg://...
```

`psql`, `pg_dump` 같은 CLI 도구에서 쓰는 URL은 `postgresql://` 형식을 사용한다.

```bash
PROD_DATABASE_URL=postgresql://...
```

## 로컬 DB 사용

로컬 Supabase DB를 사용할 때:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
```

로컬 Supabase 상태와 DB URL은 다음 명령으로 확인한다.

```bash
supabase status
```

## 운영 DB 사용

운영 Supabase DB를 backend에서 사용할 때:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:<URL_ENCODED_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
```

예:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:abc%40123@db.ztopdfbdvspzatbrcwif.supabase.co:5432/postgres
SUPABASE_URL=https://ztopdfbdvspzatbrcwif.supabase.co
```

## 비밀번호 URL 인코딩

DB 비밀번호에 URL 예약 문자가 들어가면 반드시 인코딩한다.

특히 `@`가 비밀번호에 들어가면 host 구분자로 오해되므로 `%40`으로 바꿔야 한다.

```text
@  -> %40
#  -> %23
?  -> %3F
&  -> %26
%  -> %25
/  -> %2F
:  -> %3A
```

예:

```bash
# 잘못된 예
DATABASE_URL=postgresql+asyncpg://postgres:abc@123@db.example.supabase.co:5432/postgres

# 올바른 예
DATABASE_URL=postgresql+asyncpg://postgres:abc%40123@db.example.supabase.co:5432/postgres
```

## 추천 운영 방식

실수 방지를 위해 env 파일을 나눠두고, 실행 전에 `backend/.env`로 복사해서 쓴다.

```text
backend/.env.local
backend/.env.production
backend/.env
```

로컬 DB로 실행:

```bash
cp backend/.env.local backend/.env
```

운영 DB로 로컬 테스트:

```bash
cp backend/.env.production backend/.env
```

파일을 바꾼 뒤에는 backend 서버를 재시작해야 반영된다.

## 주의

- 운영 DB를 물고 있는 상태에서 import, seed, reset 계열 스크립트를 무심코 실행하지 않는다.
- `supabase db reset`은 로컬 DB 재구성용으로만 사용한다.
- `DATABASE_URL` 기반 스크립트는 운영 DB를 직접 변경할 수 있다.
- 운영 DB smoke test가 끝나면 다시 로컬 DB 설정으로 되돌리는 습관을 둔다.
- 운영 배포 env에는 운영 DB URL, 운영 Supabase Auth URL/key, 운영 CORS/cookie 설정을 별도로 넣는다.
