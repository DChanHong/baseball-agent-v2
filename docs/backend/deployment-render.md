# Render Backend Deployment Spec

## Service

- Platform: Render Web Service
- Runtime: Docker
- Root directory: `backend`
- Production API domain: `https://api.kbo-mate.dev-hong.it.kr`
- Default Render domain: `https://baseball-agent-v2.onrender.com`
- Container port: `10000`

The Docker image starts Uvicorn with Render's `PORT` when present:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
```

## Local Docker Smoke Test

Build the backend image from `backend`:

```bash
docker build -t baseball-agent-backend:render-smoke .
```

Run the image locally with the backend `.env` file:

```bash
docker run --env-file .env -p 4000:10000 baseball-agent-backend:render-smoke
```

The host port `4000` maps to the container port `10000`.

## Required Render Environment Variables

```env
APP_ENV=production
APP_BASE_URL=https://api.kbo-mate.dev-hong.it.kr
FRONTEND_APP_URL=https://kbo-mate.dev-hong.it.kr
CORS_ALLOW_ORIGINS=https://kbo-mate.dev-hong.it.kr
APP_DEBUG=false
API_RESPONSE_LOGGING_ENABLED=false
AUTH_COOKIE_SECURE=true

DATABASE_URL=<supabase-postgres-url-for-ztopdfbdvspzatbrcwif>
OPENAI_API_KEY=<openai-api-key>
OPENAI_MODEL=gpt-5-mini
SUPABASE_URL=https://ztopdfbdvspzatbrcwif.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key-for-ztopdfbdvspzatbrcwif>
SUPABASE_SERVICE_ROLE_KEY=<supabase-service-role-key-for-ztopdfbdvspzatbrcwif>
KMA_SERVICE_KEY=<kma-service-key>
```

`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` must all belong to the same Supabase project. A mismatched `DATABASE_URL` can allow Google login to create an auth user in one project while the backend reads or writes application profiles in another database.

For Render Web Service connections to Supabase, prefer the session pooler host/port unless the application is explicitly tuned for transaction pooling.

## Health Checks

Use these checks after every deploy:

```bash
curl https://api.kbo-mate.dev-hong.it.kr/health
curl https://api.kbo-mate.dev-hong.it.kr/health/db
```

Expected:

```json
{"status":"ok","message":"New Baseball API is running"}
{"status":"ok","message":"Database connection is healthy"}
```

## OAuth Callback Requirements

The backend builds this callback URL during Google login:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/callback?oauth_state=...
```

Supabase Redirect URLs must therefore include:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/callback**
```

Without the `**` wildcard suffix, Supabase can reject the query-bearing callback URL and fall back to the frontend Site URL.

## Expected Render Logs

OAuth start:

```text
GET /api/v1/auth/google HTTP/1.1" 307
```

Successful OAuth callback:

```text
GET /api/v1/auth/callback?... HTTP/1.1" 307
```

Authenticated session check:

```text
GET /api/v1/auth/me HTTP/1.1" 200
```

Unauthenticated checks before login commonly show:

```text
GET /api/v1/auth/me HTTP/1.1" 401
POST /api/v1/auth/refresh HTTP/1.1" 401
```

Those are expected only before a valid login session exists.
