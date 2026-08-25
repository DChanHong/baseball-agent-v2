# Vercel Frontend Deployment Spec

## Service

- Platform: Vercel
- Production domain: `https://kbo-mate.dev-hong.it.kr`
- Backend API base URL: `https://api.kbo-mate.dev-hong.it.kr`

## Required Vercel Environment Variables

```env
NEXT_PUBLIC_API_BASE_URL=https://api.kbo-mate.dev-hong.it.kr
```

Redeploy the production deployment after changing environment variables.

## Auth Flow

The frontend starts Google login by navigating the browser to:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/google
```

The frontend does not exchange the Google OAuth code directly. The backend callback handles the code exchange, sets HttpOnly cookies on `api.kbo-mate.dev-hong.it.kr`, and redirects back to:

```text
https://kbo-mate.dev-hong.it.kr
```

Frontend API requests that need the session must include credentials. The current auth API uses `credentials: "include"` for session-aware requests.

## Production Verification

After deployment, open:

```text
https://kbo-mate.dev-hong.it.kr
```

Verify:

- Google login opens from the login modal
- Login returns to the frontend without `error`, `error_code`, or stray `code` query parameters
- `GET https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/me` returns 200
- Header/profile UI shows the logged-in user
- Chat send works after login
- Conversation list and conversation messages load with the logged-in session

## Troubleshooting

If login returns to:

```text
https://kbo-mate.dev-hong.it.kr/?code=...
```

then Supabase sent the OAuth code to the frontend instead of the backend callback. Check that Supabase Redirect URLs include:

```text
https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/callback**
```

If the browser console shows:

```text
GET https://api.kbo-mate.dev-hong.it.kr/api/v1/auth/me 401
```

after a completed login, check whether `nb_access_token` and `nb_refresh_token` exist under `api.kbo-mate.dev-hong.it.kr`. If they are missing, the backend callback did not complete successfully.

If the frontend still calls an old backend URL, confirm `NEXT_PUBLIC_API_BASE_URL` in Vercel production settings and redeploy.
