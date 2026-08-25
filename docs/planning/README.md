# Planning Documentation Map

> 라벨: `CURRENT`  
> MVP1 완료 기준으로 planning 문서의 현재 역할을 정리한다.

## Labels

| Label | Meaning |
|---|---|
| `CURRENT` | 현재 MVP1 기준으로 바로 참고하는 문서 |
| `MVP2` | 다음 업그레이드 계획 문서 |
| `REFERENCE` | 데이터 수집, Tool 설계, 정책 판단에 참고하는 문서 |
| `LONG_TERM` | MVP2 이후 장기 로드맵 |

## Priority

기획과 구현 범위가 오래된 메모와 충돌하면 아래 우선순위를 따른다.

1. 현재 운영 배포 스펙: `docs/deployment-production.md`
2. MVP1 상태/UX/Auth 기준: `docs/planning/001-service-and-mvp.md`, `docs/frontend/mvp-chat-ux-plan.md`, `docs/planning/login-spec/001-auth-login-spec.md`
3. Backend/Frontend 현재 구현 문서: `docs/backend/README.md`, `docs/frontend/frontend-layout-spec.md`
4. MVP2 계획: `docs/planning/002-mvp2-backend-upgrade-plan.md`
5. 날짜별 메모: `docs/memo/v1/*.md`

## Current MVP1 Documents

| File | Label | Role |
|---|---|---|
| `001-service-and-mvp.md` | `CURRENT` | 서비스 정의와 MVP1 완료/제외 범위 |
| `login-spec/001-auth-login-spec.md` | `CURRENT` | Google OAuth, HttpOnly cookie 세션, 사용자 프로필 정책 |
| `003-langchain-langgraph-adoption-plan.md` | `CURRENT` | LangGraph 1차 도입 상태와 후속 개선 후보 |

## MVP2 Documents

| File | Label | Role |
|---|---|---|
| `002-mvp2-backend-upgrade-plan.md` | `MVP2` | RAG 검색 품질, 프롬프트, 관측성, 평가 개선 계획 |

## Data And Tool Reference

| File | Label | Role |
|---|---|---|
| `game-schedule/001-data-collection-and-db.md` | `REFERENCE` | KBO 경기 일정 수집 전략과 DB 기준 |
| `stadium-guide/001-data-collection.md` | `REFERENCE` | 구장 가이드 데이터 수집과 정형/RAG 분리 기준 |

## Related Roadmap

| File | Label | Role |
|---|---|---|
| `../roadmap/001-supabase-pgvector.md` | `CURRENT` | pgvector 채택 ADR |
| `../roadmap/roadmap.md` | `LONG_TERM` | 프로젝트 장기 로드맵 |

## Cleanup Notes

- MVP1은 운영 배포, Google OAuth 로그인, 채팅 응답 수신까지 1차 완료로 본다.
- MVP1 제외 범위와 MVP2 후보는 `001-service-and-mvp.md`와 `002-mvp2-backend-upgrade-plan.md`에 분리한다.
- guest-first 또는 Bearer token 기반 설명은 과거 설계 기록으로만 본다. 현재 기준은 Google OAuth + backend HttpOnly cookie 세션이다.
