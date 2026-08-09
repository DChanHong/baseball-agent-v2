# Baseball Agent V2 작업 지도

이 저장소는 KBO 직관 도우미를 만드는 monorepo다. 루트에서는 전체 폴더 역할만 파악하고, 세부 규칙은 작업 대상 폴더의 문서와 `AGENTS.md`를 우선해서 읽는다.

## 폴더 역할

- `backend/`: FastAPI 기반 API, agent routing, tool executor, domain service, repository 구현.
- `frontend/`: Next.js App Router 기반 웹 클라이언트. 상세 프론트엔드 규칙은 `frontend/AGENTS.md`를 읽는다.
- `supabase/`: local Supabase 설정, migration, seed SQL.
- `data/`: KBO schedule, stadium guide, baseball knowledge 원천/정규화/평가 데이터.
- `docs/`: 기획, 로드맵, backend/frontend 설계, RAG/embedding 계획, 작업 메모.
- `docs/spec/`: MVP 현재 구현 상태, UI/API 계약, 개선 전 기준선 문서.
- `utils/`: 임시 수집, 검사, 보조 스크립트.
- `blog/`: 작업 로그와 정리 글 초안.
- `.agent/`: 이 프로젝트에서 공유 가능한 Codex용 에이전트/스킬 지침.

## 먼저 볼 문서

- 서비스 범위가 궁금하면 `docs/planning/README.md`를 먼저 읽는다.
- 프론트엔드 구조가 궁금하면 `docs/frontend/folder-design.md`, `frontend/docs/stack-decisions.md`를 읽는다.
- backend 실행/검증 명령이 필요하면 `docs/backend/local-development-commands.md`를 읽는다.
- 데이터 폴더 구조는 `data/README.md`를 읽는다.

## 작업 원칙

- 작업 대상 폴더의 기존 구조와 문서를 먼저 확인한다.
- frontend 작업은 `frontend/AGENTS.md`를 따른다.
- spec 문서화 작업은 `.agent/spec/SKILL.md`의 기준을 따른다.
- 사용자 데이터, API key, 실제 사용자 대화 전문을 저장하지 않는다.
- 생성 데이터와 평가 결과를 다룰 때는 `raw`, `processed`/`normalized`, `evaluation/cases`, `evaluation/runs`의 의미를 유지한다.
