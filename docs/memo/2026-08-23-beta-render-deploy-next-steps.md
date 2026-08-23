# 2026-08-23 Beta Render Deploy Next Steps

## 오늘 완료한 것

- [x] 운영 프론트 도메인 확정: `https://kbo-mate.dev-hong.it.kr`
- [x] 운영 백엔드 도메인 확정: `https://api.kbo-mate.dev-hong.it.kr`
- [x] Vercel 프론트 도메인 추가
- [x] Vercel production env 추가: `NEXT_PUBLIC_API_BASE_URL=https://api.kbo-mate.dev-hong.it.kr`
- [x] Supabase Auth redirect URL 추가
- [x] Google OAuth authorized redirect URI 추가

## 다음에 이어서 할 것

- [ ] 백엔드 배포용 `Dockerfile` 추가
- [ ] Render Web Service 생성
- [ ] Render build/start 설정 확인
- [ ] Render production env 입력
- [ ] Render 기본 배포 URL로 `/health` 확인
- [ ] Render 기본 배포 URL로 `/health/db` 확인
- [ ] Render custom domain에 `api.kbo-mate.dev-hong.it.kr` 추가
- [ ] DNS에 Render가 안내하는 CNAME 또는 A record 추가
- [ ] `https://api.kbo-mate.dev-hong.it.kr/health` 확인
- [ ] `https://api.kbo-mate.dev-hong.it.kr/health/db` 확인
- [ ] Vercel production redeploy
- [ ] `https://kbo-mate.dev-hong.it.kr`에서 로그인 플로우 확인
- [ ] 운영 채팅 end-to-end smoke test
- [ ] 운영 RAG 검색 smoke test
- [ ] 운영 일정 질문 smoke test
- [ ] 운영 구장 가이드 질문 smoke test
- [ ] 운영 야구 규칙 질문 smoke test
- [ ] 운영 날씨 질문 smoke test

## Render env 후보

```env
APP_ENV=production
APP_BASE_URL=https://api.kbo-mate.dev-hong.it.kr
FRONTEND_APP_URL=https://kbo-mate.dev-hong.it.kr
CORS_ALLOW_ORIGINS=https://kbo-mate.dev-hong.it.kr
APP_DEBUG=false
API_RESPONSE_LOGGING_ENABLED=false
AUTH_COOKIE_SECURE=true

DATABASE_URL=<production-supabase-database-url>
OPENAI_API_KEY=<openai-api-key>
OPENAI_MODEL=gpt-5-mini
SUPABASE_URL=<production-supabase-url>
SUPABASE_ANON_KEY=<production-supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<production-supabase-service-role-key>
KMA_SERVICE_KEY=<kma-service-key>
```

## 배포 순서 메모

1. 백엔드 `Dockerfile`을 먼저 만든다.
2. Render에서 GitHub repo를 연결하고 backend 서비스로 생성한다.
3. Render env를 입력한다.
4. Render 기본 URL로 health check를 먼저 통과시킨다.
5. 그 다음 `api.kbo-mate.dev-hong.it.kr` custom domain을 붙인다.
6. 백엔드 도메인이 정상화되면 Vercel을 redeploy한다.
7. 최종적으로 운영 프론트에서 로그인과 채팅 smoke test를 진행한다.

## 주의사항

- Google OAuth에는 Supabase callback URL을 넣는다.
- Supabase Auth redirect allow list에는 백엔드 callback URL을 넣는다.
- 운영 DB에는 `supabase db reset`을 사용하지 않는다.
- Render 무료 플랜은 cold start가 있을 수 있으므로 베타 테스트 시 첫 요청이 느릴 수 있다.
