# Production Deployment Spec

## Production Domains

- Frontend: `https://kbo-mate.dev-hong.it.kr`
- Backend API: `https://api.kbo-mate.dev-hong.it.kr`
- Render default backend URL: `https://baseball-agent-v2.onrender.com`
- Supabase project ref: `ztopdfbdvspzatbrcwif`

## Service Map

```text
Browser
-> Vercel frontend: https://kbo-mate.dev-hong.it.kr
-> Render backend: https://api.kbo-mate.dev-hong.it.kr
-> Supabase Postgres and Auth
-> Google OAuth provider
```

The browser starts Google login through the backend:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/google
```

The backend redirects to Supabase Auth, Supabase redirects to Google, Google returns to Supabase, and Supabase must finally redirect to the backend callback:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/callback?oauth_state=...
```

The backend exchanges the OAuth code for a Supabase session, sets HttpOnly cookies, then redirects the browser back to the frontend.

## OAuth URL Rules

Google Cloud Console authorized redirect URI must point to the Supabase Auth callback:

```text
https://ztopdfbdvspzatbrcwif.supabase.co/auth/v1/callback
```

Supabase Auth Redirect URLs must allow the backend callback. The production entry needs the wildcard suffix because the backend includes `oauth_state` as a query string:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/callback**
```

Local callback entries can use the same pattern:

```text
http://127.0.0.1:4000/api/v1/auth/callback**
http://localhost:4000/api/v1/auth/callback**
```

Supabase Site URL should remain the frontend URL:

```text
https://kbo-mate.dev-hong.it.kr
```

If Supabase redirects to `https://kbo-mate.dev-hong.it.kr/?code=...`, it means the backend callback URL did not match the Supabase Redirect URLs allow list and Supabase fell back to the Site URL.

## Cookie Session

The backend manages the browser session with HttpOnly cookies:

- `nb_access_token`
- `nb_refresh_token`
- `nb_oauth_state`
- `nb_oauth_code_verifier` or the value configured by `AUTH_OAUTH_VERIFIER_COOKIE_NAME`

Successful login should leave `nb_access_token` and `nb_refresh_token` under `api.kbo-mate.dev-hong.it.kr`.

## Production Smoke Test

Run backend health checks:

```bash
curl https://api.kbo-mate.dev-hong.it.kr/health
curl https://api.kbo-mate.dev-hong.it.kr/health/db
```

Expected responses:

```json
{"status":"ok","message":"New Baseball API is running"}
{"status":"ok","message":"Database connection is healthy"}
```

Then verify from the production frontend:

- Google login completes and returns to `https://kbo-mate.dev-hong.it.kr`
- `GET https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/me` returns 200 after login
- Browser cookies include `nb_access_token` and `nb_refresh_token`
- A chat message can be sent end to end
- RAG, schedule, stadium guide, baseball rules, and weather questions return usable answers

## Common Failure Signals

- `/api/v1/auth/me` returns 401 after login: backend session cookies were not created or not sent.
- Final URL is `/?code=...` on the frontend: Supabase did not accept the backend callback redirect URL.
- Final URL contains `bad_oauth_callback`: Google/Supabase OAuth state handling failed before the backend callback.
- Render logs do not show `/api/v1/auth/callback`: the flow did not reach the backend callback.
- Render logs show `/api/v1/auth/google` with 307: OAuth start endpoint is working.
