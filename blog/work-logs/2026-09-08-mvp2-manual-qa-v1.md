# MVP2 실사용 QA v1 작업 로그

## 기본 정보

```text
날짜: 2026-09-08
작업 범위: MVP2 3-1 상태 정리, 3-2 평가 데이터 골격과 smoke QA 준비
관련 브랜치/커밋: 미커밋
관련 파일:
- docs/planning/002-mvp2-backend-upgrade-plan.md
- docs/work/2026-09-08-mvp2-3-2-manual-qa-evaluation-dataset-plan.md
- data/chat/evaluation/
- backend/scripts/validate_chat_evaluation_data.py
- backend/tests/api/test_chat_evaluation_data.py
- blog/work-log-template.md
- blog/blog-5-manual-qa-evaluation-dataset-draft.md
```

## 오늘의 목표

```text
cron을 사용하지 않는 3-1 운영 결정을 계획에 반영한다.
3-2에서 사용할 run, candidate, evaluation case의 역할과 형식을 고정한다.
기존 대표 질문 6개와 follow-up 3개를 첫 smoke QA run으로 준비한다.
```

## 왜 이 작업을 하는가

MVP 기능이 구현되어 있어도 실제 질문에서 Tool routing, 데이터 최신성, 검색 근거, 답변 정책, SSE UI가 함께 동작하는지는 별도로 확인해야 한다. 실패를 그때그때 수정하면 개선 전후를 같은 기준으로 비교하기 어렵기 때문에 먼저 재현 가능한 평가 데이터로 남긴다.

## 작업 전 상태

```text
- MVP2 계획에는 cron 또는 동등한 스케줄러 연결이 3-1 범위로 남아 있었다.
- Tool별 evaluation case와 run은 존재했지만 chat end-to-end 전용 데이터 폴더는 없었다.
- MVP1 수동 QA용 대표 질문 6개와 follow-up 3개가 문서에만 있었다.
- 일반 작업 로그 템플릿에는 QA 집계와 데이터셋 변경 기록란이 없었다.
```

## 오늘 결정한 것

```text
- 3-1은 비용 문제로 cron을 보류하고 수동 sync 운영으로 완료 처리한다.
- 합성 질문을 초기 QA의 기본 입력으로 사용한다.
- 실행 결과, 실패 후보, 정식 평가셋을 run / candidate / case로 분리한다.
- milestone run만 Git에 보관한다.
- 실제 사용자 대화 전문과 사용자 식별자는 저장하지 않는다.
- 3-2 블로그는 blog-4에 합치지 않고 별도 blog-5로 작성한다.
```

## 구현하거나 만든 것

```text
- MVP2 상위 계획의 3-1 상태와 다음 작업 갱신
- 3-2 상세 작업 기획서
- data/chat/evaluation README와 JSON Schema 3종
- 30개 chat end-to-end evaluation case
- 기존 9개 질문 기반 manual QA v1 준비 run
- Pydantic 기반 chat evaluation 데이터 검증 스크립트
- 평가 데이터 정합성 검증 회귀 테스트 3개
- 작업 로그 템플릿의 QA 선택 섹션
- blog-5 공개 글 초안 골격
```

## 확인한 결과

```text
- 초기 질문 세트는 game, stadium, weather, ticketing, stadium guide, baseball knowledge, follow-up, unsupported/policy 범위를 포함한다.
- 9개 smoke QA 결과는 passed 4, ambiguous 3, failed 2였다.
- 경기 일정과 selected_game 기반 follow-up 3개는 통과했다.
- 사직구장 주소는 Tool이 완료됐지만 주소 데이터가 없어 실패했다.
- 고척돔 음식물 반입 질문은 음료 용기 제한만 검색되어 실패했다.
- 날씨 답변의 구두점과 RAG Tool의 일반적인 최종 답변은 ambiguous로 분류했다.
- 실제 관찰 결과에서 candidate 5개를 만들었다.
- candidate 4개를 기존 정식 evaluation case에 연결했고 1개는 보류했다.
- 데이터 검증 스크립트가 cases=30, candidates=5, runs=1로 통과했다.
- backend 전체 테스트 50개가 통과했다.
- 새 검증 스크립트와 테스트의 ruff, mypy 검사가 통과했다.
- frontend lint와 typecheck가 통과했다.
- 로컬 frontend 초기 화면이 정상 로드되고 로그인 전 채팅 화면이 표시됐다.
```

## 막힌 점

```text
- 구장 기본 데이터에서 사직구장 주소와 돔 여부가 비어 있다.
- RAG Tool 최종 답변이 검색 내용을 직접 설명하지 않고 카드 확인을 유도한다.
- 고척 음식물 반입 여부를 직접 뒷받침하는 source 또는 chunk가 부족하다.
```

## 다음 작업

```text
- 사직구장 기본 데이터의 주소와 돔 여부 누락 원인을 확인한다.
- RAG 최종 자연어 답변이 첫 근거를 직접 요약하도록 개선 후보를 정리한다.
- 고척 음식물 반입 source와 chunk coverage를 점검한다.
- 개선 후 동일 9개 smoke case로 회귀 QA를 실행한다.
- 나머지 21개 case를 다음 milestone run에서 검증한다.
```

## 블로그에 살릴 포인트

```text
- 자동화 비용 때문에 cron을 포기한 것은 데이터 최신화를 포기한 것이 아니라 운영 수준에 맞는 수동 정책을 택한 것이다.
- Agent QA에서는 성공/실패 숫자보다 어느 계층에서 왜 실패했는지 다시 재현할 수 있어야 한다.
- 실제 대화를 쌓는 대신 합성 질문과 sanitization으로 개인정보 없이 평가셋을 성장시킬 수 있다.
- run, candidate, case를 분리하면 일회성 오류가 정식 평가셋을 오염시키는 것을 막을 수 있다.
```

## 블로그 초안 문장

```text
기능 목록을 모두 구현한 뒤에도 KBO Mate가 실제로 잘 동작한다고 말하기는 어려웠다.
일정 조회, 날씨, 구장 안내, 야구 지식 Tool이 각각 동작하는 것과 사용자의 한 문장이 올바른 Tool과 근거 있는 답변으로 이어지는 것은 다른 문제였다.
그래서 다음 기능을 추가하기 전에 실패를 고치는 순서부터 바꿨다. 먼저 질문을 실행하고, 관찰한 결과를 후보로 남긴 뒤, 반복할 가치가 있는 사례만 평가셋으로 승격하기로 했다.
```

## QA / 평가 작업일 때 추가 기록

### QA 실행 정보

```text
run_id: manual_qa_20260908_v1
실행 환경: local
질문 세트 버전: mvp2_manual_qa_v1
전체 질문 수: 9
passed: 4
ambiguous: 3
failed: 2
not_run: 0
candidate 생성 수: 5
evaluation case 승격 수: 4
```

### 발견한 실패 유형

```text
- source_limitation: 1
- answer_quality: 3
- rag_retrieval: 1
```

### 데이터셋 변경

```text
추가한 candidate: qa_candidate_001 ~ qa_candidate_005
승격한 evaluation case: qa_candidate_001, qa_candidate_003, qa_candidate_004, qa_candidate_005
새로 정의한 초기 evaluation case: 30개
보류한 candidate: qa_candidate_002
폐기한 candidate: 없음
변경 사유: 실제 smoke QA 실패를 이후 개선에서 재현하기 위함
```

### 다음 실행에서 검증할 가설

```text
- 명시적인 질문 6개가 기대 Tool로 routing되는가
- Tool card가 running에서 completed 또는 failed로 갱신되는가
- assistant 답변이 Tool 결과와 충돌하지 않는가
- 단일 경기 조회 이후 selected_game 기반 follow-up 3개가 Tool 재호출 없이 답변되는가
- 경기 취소 관련 표현이 날씨만으로 확정되지 않는가
```

## 커밋 메모

```text
커밋 전 확인:
- git status --short
- git diff --check
- JSON/JSONL Schema validation

커밋 메시지 후보:
docs: plan MVP2 manual chat QA dataset
```
