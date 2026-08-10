# Trail of Bits Skill Mapping

## 출처와 라이선스

이 문서는 Trail of Bits `skills` repository의 보안 감사 관점을 Baseball Agent frontend에 맞게 요약한 mapping이다.

- Repository: `https://github.com/trailofbits/skills`
- Focus: security research, vulnerability detection, audit workflows
- License: Creative Commons Attribution-ShareAlike 4.0 International

원본 skill 전체를 vendoring하지 않는다. 이 프로젝트에서는 frontend 보안 리뷰에 필요한 관점만 얇게 참조한다.

## 이 프로젝트에 유용한 Trail of Bits 계열

### audit-context-building

코드를 바로 지적하기 전에 구조와 trust boundary를 먼저 만든다.

적용:
- `src/features/chat-stream`
- `src/entities/tool-result`
- `src/widgets/source-drawer`
- `src/shared/api`

### differential-review

변경분 중심으로 보안 회귀를 찾는다.

적용:
- PR/commit review
- dependency 변경
- auth/session/storage 변경
- tool result renderer 변경

### insecure-defaults

안전하지 않은 기본값, hardcoded credential, fail-open pattern을 찾는다.

적용:
- `.env.example`
- `next.config.ts`
- guest session/localStorage fallback
- API base URL fallback
- error fallback UI

### sharp-edges

위험한 API와 footgun을 찾는다.

적용:
- `dangerouslySetInnerHTML`
- unsafe external links
- `window`/`document` 직접 접근
- unvalidated URL
- global event listener

### static-analysis

ESLint, TypeScript, Semgrep 같은 정적 분석을 보조 수단으로 사용한다.

적용:
- 기본 검증: `pnpm lint`, `pnpm typecheck`
- 필요 시 Semgrep rule 제안
- scanner 결과는 finding의 시작점이지 결론이 아니다.

### supply-chain-risk-auditor

dependency threat landscape를 본다.

적용:
- `package.json`
- `pnpm-lock.yaml`
- package scripts
- transitive dependency 증가

### variant-analysis

한 곳에서 발견한 취약 패턴이 다른 component에도 반복되는지 찾는다.

적용:
- 여러 tool card의 source URL rendering
- 여러 storage helper의 schema/version 처리
- 여러 API parser의 unknown payload 처리

## 이 프로젝트에는 우선순위가 낮은 항목

- smart contract 전용 skill
- C/C++/Rust memory safety review
- mobile APK/Firebase scanner
- malware/YARA authoring
- cryptographic constant-time analysis

필요해지기 전까지 frontend skill에 포함하지 않는다.
