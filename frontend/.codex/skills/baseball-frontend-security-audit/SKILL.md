---
name: baseball-frontend-security-audit
description: Baseball Agent frontend 보안 감사를 수행할 때 사용한다. frontend/의 Next.js, React, TypeScript, API client, SSE streaming, LLM/tool result rendering, source/citation rendering, auth/guest session, localStorage, environment variables, dependency/supply-chain risk, XSS, insecure defaults, diff security review 작업에 사용한다.
---

# Baseball Frontend Security Audit

## 개요

이 스킬은 KBO Baseball Agent 프론트엔드의 보안 리뷰를 프로젝트 맥락에 맞게 수행하도록 돕는다. Trail of Bits `skills`의 감사 관점을 참고하되, 이 저장소에는 Next.js/React 클라이언트에 필요한 얇은 wrapper만 둔다.

## 먼저 읽을 것

보안 리뷰 전에는 필요한 범위만 읽는다.

- `frontend/AGENTS.md`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `frontend/next.config.ts`
- `frontend/.env.example`가 있으면 읽는다.
- 변경 대상과 관련된 `frontend/src/features`, `frontend/src/entities`, `frontend/src/shared/api`, `frontend/src/shared/lib`, `frontend/src/widgets` 하위 파일

상세 점검은 다음 참조를 필요할 때 읽는다.

- `references/frontend-security-checklist.md`: Next.js/React 프론트엔드 보안 체크리스트
- `references/review-workflow.md`: diff 또는 전체 코드 보안 리뷰 절차
- `references/trailofbits-skill-mapping.md`: Trail of Bits skill을 이 프로젝트에 매핑한 기준

## 감사 흐름

1. 변경 범위와 trust boundary를 식별한다.
2. 사용자 입력, backend 응답, LLM 출력, tool result, citation/source URL을 untrusted data로 표시한다.
3. secret/token/env 값이 client bundle, localStorage, 로그, URL query, 에러 메시지에 노출되지 않는지 확인한다.
4. XSS, unsafe link, unsafe HTML, data validation, SSE parsing, abort/retry/error handling을 확인한다.
5. dependency와 lockfile 변경이 있으면 supply-chain risk를 확인한다.
6. finding은 파일, 영향, 재현 조건, 최소 수정 방향, false positive 가능성을 포함해 작성한다.

## 주요 점검 대상

- LLM 응답과 tool result를 HTML로 신뢰하지 않는다.
- 외부 source URL은 정규화하고 안전한 link 속성을 사용한다.
- `NEXT_PUBLIC_*` 환경 변수에는 공개 가능한 값만 둔다.
- guest/session/conversation id는 권한의 근거로 단독 사용하지 않는다.
- localStorage/sessionStorage에는 secret, access token, 민감한 대화 전문을 저장하지 않는다.
- streaming parser는 malformed event, partial chunk, abort, retry 상황에서 fail-closed에 가깝게 동작해야 한다.
- zod schema 또는 명시적인 타입 좁히기 없이 backend payload를 신뢰하지 않는다.
- dependency 추가, install script, postinstall, lockfile 변화는 별도 위험으로 본다.

## Rationalizations to Reject

보안 리뷰에서 다음 식의 단정은 거부한다.

- "프론트엔드라서 심각한 보안 이슈가 아니다."
- "React가 escape하니까 XSS는 볼 필요가 없다."
- "TypeScript 타입이 있으니 런타임 payload도 안전하다."
- "토이 프로젝트라서 secret exposure는 괜찮다."
- "백엔드가 검증하니 클라이언트에서 어떤 URL/HTML을 렌더링해도 된다."
- "dependency가 유명하니 supply-chain risk는 없다."
- "테스트가 통과했으니 보안 문제는 없다."

## 전달 형식

문제가 있으면 심각도 순으로 짧게 작성한다.

- 위치: 파일과 가능하면 라인
- 분류: XSS, secret exposure, auth/session, storage, unsafe link, data validation, SSE/API, dependency, insecure default
- 영향: 사용자가 겪는 위험 또는 공격자가 얻는 이점
- 근거: 코드에서 확인한 사실
- 수정: 가장 작은 수정 방향
- 확신도: high/medium/low

문제가 없으면 "현재 확인 범위에서는 발견 없음"이라고 말하고, 남은 test gap이나 수동 확인이 필요한 부분을 덧붙인다.
