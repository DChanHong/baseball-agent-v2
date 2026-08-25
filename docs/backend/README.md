# Backend Documentation Map

> MVP1 완료 기준으로 backend 문서의 현재 역할을 정리한다.

## Labels

| Label | Meaning |
|---|---|
| `CURRENT` | 현재 MVP1/운영 기준으로 바로 참고해도 되는 문서 |
| `NEEDS_UPDATE` | 중요한 문서지만 현재 구현과 일부 불일치가 있어 갱신이 필요한 문서 |
| `REFERENCE` | 구조, 학습, 정책 참고용 문서 |
| `ARCHIVE` | 과거 진행 기록 또는 v1 설계 기록 |

## Current Entry Points

| File | Label | Role |
|---|---|---|
| `deployment-render.md` | `CURRENT` | Render 백엔드 배포 스펙 |
| `database-environment-switching.md` | `CURRENT` | 로컬/운영 DB 전환 기준 |
| `local-development-commands.md` | `CURRENT` | 로컬 Supabase/FastAPI 실행과 기본 API 확인 명령 |
| `policy/conversation-entry-policy.md` | `CURRENT` | 로그인 사용자 채팅 진입과 경기 일정 조회 정책 |

## Structure And Learning

| File | Label | Role |
|---|---|---|
| `folder-design/00-backend-learning-map.md` | `REFERENCE` | 백엔드 학습 로드맵 |
| `folder-design/01-current-backend-folder-tour.md` | `REFERENCE` | 현재 backend 폴더별 역할 |
| `folder-design/02-python-library-reading-guide.md` | `REFERENCE` | Python/FastAPI/라이브러리 읽기 가이드 |
| `folder-design/03-request-flow-walkthroughs.md` | `REFERENCE` | 주요 API 요청 흐름 |
| `folder-design/folder-design.md` | `REFERENCE` | 도메인 중심 백엔드 구조 설계 기준 |

## Policy

| File | Label | Role |
|---|---|---|
| `policy/conversation-entry-policy.md` | `CURRENT` | 로그인/응원팀/야구 범위 제한 정책 |
| `policy/logging-policy.md` | `REFERENCE` | 백엔드 로깅 정책 초안 |

## V1 Archive

| File | Label | Role |
|---|---|---|
| `v1/rag-tool-development-plan.md` | `ARCHIVE` | MVP1 RAG/Tool 개발 진행 기록 |

## Cleanup Notes

- `in-progress/` 폴더의 RAG 진행 문서는 `v1/`로 이동했다.
- 현재 인증 기준은 Google OAuth + backend HttpOnly cookie 세션이다.
- Bearer token 또는 guest-first 설명은 과거 설계 기록으로만 본다.
