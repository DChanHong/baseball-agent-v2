# Claude-To-Codex 변환 메모

## 원본 스킬

참고한 UI/UX Pro Max 저장소는 `ui-ux-pro-max`라는 Claude skill을 설명한다. 이 프로젝트에 유용한 부분은 priority model, design-system search 관점, accessibility checklist, icon discipline, responsive check, typography/color guidance, stack-specific Next.js awareness다.

Claude runtime 가정을 그대로 복사하지 않는다. 특히 `.claude/skills/...`, `${CLAUDE_PLUGIN_ROOT}`, Claude plugin 설치 가정은 Codex skill 관례로 바꾼다.

## Codex 스킬 구조

Codex skill에는 다음이 필요하다.

- `SKILL.md`
- `name`, `description`만 가진 YAML frontmatter
- Optional `agents/openai.yaml`
- Optional `references/`, `scripts/`, and `assets/`

이 프로젝트에서는 skill을 project-specific하고 짧게 유지한다. 상세 규칙은 `references/`에 두고, `SKILL.md`는 workflow와 trigger behavior 중심으로 유지한다.

## 가져올 것

- Accessibility first: contrast, focus, label, keyboard navigation.
- Touch and interaction check: 충분한 target size, spacing, loading feedback.
- Layout and responsive check: mobile-first, no horizontal scroll, dynamic content를 위한 reserved space.
- Typography and color guidance: semantic token, 읽기 쉬운 base size, line-height, component-level raw hex 난립 방지.
- Animation discipline: 상태 변경에는 150-300ms transition, 목적 없는 decorative motion 금지.
- Chart/data pattern: 나중에 dashboard surface가 생기면 legend, tooltip, color-only encoding 방지.
- Icon: 적절한 icon이 있으면 emoji나 임시 inline SVG 대신 lucide-react 사용.

## 피할 것

- 이 repo와 무관한 broad multi-stack instruction.
- `${CLAUDE_PLUGIN_ROOT}`에서 Claude-specific script를 설치하거나 실행하는 방식.
- project skill 안에 거대한 universal design database를 넣는 것.
- 기존 KBO chat app palette와 FSD 구조에 충돌하는 generated design system.

## 로컬 매핑

- Stack: Next.js App Router, React, TypeScript.
- Styling: styled-components with `frontend/src/shared/styles/theme.ts`.
- Icons: lucide-react.
- State: Jotai for UI state, TanStack Query for server state.
- Runtime validation: zod.
- Main product category: sports utility chat assistant.
- Best-fit UI style: content-first utility, minimal structure, compact evidence card, restrained sports accent.
