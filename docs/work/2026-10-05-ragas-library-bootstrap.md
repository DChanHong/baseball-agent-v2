# RAGAS 평가 라이브러리 도입

> 작성일: 2026-10-05
> 상태: 의존성 설치·지표 factory·입력 adapter·offline 검증 완료 / 실제 baseline 미실행
> 계약: [평가 지표와 입력](../spec/2026-10-05-ragas-evaluation-contract-spec.md)

## 1. 도입 내용

- `backend/pyproject.toml`의 별도 `evaluation` dependency group에 `ragas==0.4.3`, `langchain-community==0.4.1`을 고정했다. 일반 앱 dependencies에는 RAGAS를 넣지 않았다.
- `uv.lock`을 갱신하고 Python 3.13 환경에서 설치·import를 확인했다.
- RAGAS가 import하는 `langchain_community.chat_models.vertexai`가 0.4.2에는 없어 import 실패가 발생했다. 0.4.1 고정으로 해결했다. RAGAS 도입으로 기존 lock의 `jiter`는 0.16.0 → 0.14.0으로 조정됐다.
- [평가 모듈](../../backend/scripts/ragas_evaluation.py)에 입력 검증, 지표별 입력 변환, 네 지표 factory, 명시적으로 호출하는 비동기 scoring 함수를 추가했다.

실제 installed API는 `ragas.metrics.collections`의 `Faithfulness`, `AnswerRelevancy`, `ContextPrecision`, `ContextRecall`이다. `ascore()` 인자와 `result.value` 사용 형태를 확인했다. 지표 factory는 명시적으로 구성한 LLM·embedding 객체를 주입받으며 앱 설정이나 `.env`를 읽지 않는다. RAGAS telemetry는 factory import 전에 비활성화한다.

## 2. 구현 범위

`EvaluationSample`은 합성 질문만 허용하고, approved reference에는 본문·공식 출처 목록·검수일·검수 주체를 요구한다. 이 필드 검증은 실제 사람의 내용 검수를 대체하지 않는다.

답변 지표는 후처리 전 `model_response`를 사용한다. Faithfulness에는 실제 수집한 `generation_evidence`만 전달하고 검색 원문으로 복원하지 않는다. 검색 지표는 `retrieval_items` 순서를 유지한다. 빈 tool_result를 검색 문서로 취급하지 않는다. metadata는 해당 단계에서 수집된 공개 payload만 사용한다.

reference 미검수, 잘못된 routing, 빈 근거 정책 사례, fallback을 명시적으로 제외한다. 생성이 실패해도 reference가 있는 검색 지표는 실행할 수 있다. 점수 0, 음수, NaN, judge 오류·timeout을 구분하고 오류/제외 점수는 null로 남긴다. metric별 실패가 뒤의 지표를 중단시키지 않는다. 함수는 순차 실행하며 자체 재시도는 하지 않는다. 주입한 provider의 재시도 정책은 실제 실행 설정에서 별도로 고정해야 한다.

CLI는 **offline 입력 검증 전용**이다. 입력 JSONL을 검증하고 metric별 ready/excluded 사유를 저장한다. ready는 점수 측정 완료가 아니다. 요약에는 질문·답변·검색 본문·judge 출력 전문을 저장하지 않는다. scoring 함수 반환값은 metric별 status/value/reason_code/duration_ms이며 실제 run manifest 저장과 비용 수집은 후속 작업이다.

## 3. 설치와 검증 명령

저장소 루트에서:

```bash
cd backend
uv sync --locked --group evaluation
RAGAS_DO_NOT_TRACK=true .venv/bin/python -m pytest -q tests/api/test_ragas_evaluation.py
.venv/bin/ruff check scripts/ragas_evaluation.py tests/api/test_ragas_evaluation.py
.venv/bin/python -m mypy --explicit-package-bases scripts/ragas_evaluation.py
```

실제 수집·검수된 합성 입력 JSONL이 준비된 뒤 사용하는 offline 명령:

```bash
cd backend
.venv/bin/python scripts/ragas_evaluation.py \
  --input /private/tmp/baseball-ragas-input.jsonl \
  --output /private/tmp/baseball-ragas-input-summary.json
```

입력 shape는 `EvaluationSample` 정의를 따른다. 기존 `chat_mvp_cases.jsonl`이나 답변 모델 비교 fixture를 그대로 넣을 수 없다. 실제 generation evidence·후처리 전 답변·reference 검수 정보가 필요하다. 합성 테스트 자료는 정답셋으로 승격하지 않았다.

## 4. 검증 결과와 남은 작업

- 신규 테스트: 11개 통과. 근거 분리·reference 검수 요구·빈 근거·routing 불일치·fallback·judge 오류/timeout·NaN·0·음수·CLI 요약 보관·실제 지표 factory/인자 호환성 확인.
- 의존성 변경 후 기존 backend 전체와 첫 신규 테스트 9개: 122개 통과. 이후 입력 검증 보강·테스트 2개 추가 후 전용 테스트 11개 재검증.
- 변경 파일 Ruff 및 평가 모듈 mypy 통과. 실제 LLM/embedding API는 호출하지 않았다.

다음 작업은 공식 근거를 확인한 reference 보강, 합성 평가 전용 실제 입력 수집, judge/embedding 모델·timeout·재시도·비용 상한 결정, 실행 manifest/metric 결과 저장이다. 이 작업까지 마친 뒤 최소 평가 runner 완료로 표시한다. DB 접속·실제 생성/평가 API 실행·commit·push는 이번 회차에 수행하지 않았다.
