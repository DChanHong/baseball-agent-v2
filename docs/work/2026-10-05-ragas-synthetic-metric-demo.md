# RAGAS 실제 지표 계산 smoke

> 작성일: 2026-10-05
> 범위: 가상 구장 합성 입력 2개 / 실제 judge·embedding API 평가
> 상태: 8개 지표 계산 완료. 서비스 baseline·공식 정책 reference 검수·E2E QA는 미실행.
> 결과: [실행 요약](../../data/chat/evaluation/runs/ragas/2026-10-05_synthetic-metric-demo-v1.json)

## 입력과 실행 설정

사용자가 실제 지표 테스트 실행을 요청했다. DB 조회 없이 통제된 가상 구장 안내를 작성했다. 질문은 입장 시간과 입구를 함께 묻는다.

- 정상 사례: 근거에 있는 17시 30분·북문으로 답변. 검색 순서는 필요한 근거 → 매점 노이즈.
- 비교 사례: 20시·남문으로 틀리게 답변. 검색 순서는 매점 노이즈 → 입장 시간만 있는 불완전 근거. 북문 정보가 없다.

두 답변 모두 실서비스 생성 답변이 아니라 직접 작성한 합성 답변이다. reference 승인 필드는 가상 fixture 원문과의 일치만 agent가 검토한 상태이며, 공식 KBO 정책이나 사람이 검수한 서비스 정답셋 승격을 뜻하지 않는다. reference의 출처도 `synthetic://` fixture다. 입력·답변 전문은 `/private/tmp/baseball-ragas-metric-demo-input.jsonl`에만 두었다. 재실행 스크립트는 `/private/tmp/baseball-ragas-metric-demo.py`다. 둘 다 임시 자료이며 저장소에 보관하지 않는다.

RAGAS 0.4.3, judge `gpt-4o-mini-2024-07-18`, embedding `text-embedding-3-small`, temperature 0, strictness 3, judge 출력 상한 1,024 token, API timeout 25초·metric timeout 60초다. SDK retry 0·Instructor 최대 시도 1·runner retry 0으로 실행했다. 최대 요청 24회·평가 비용 상한 0.05달러로 제한했다. 답변 생성 API·DB·SSE는 실행하지 않았다.

## 결과

| 지표 | 정상 답변·검색 | 틀린 답변·불완전 검색 |
|---|---:|---:|
| Faithfulness | 1.000 | 0.000 |
| Answer Relevancy | 0.358 | 0.358 |
| Context Precision | 약 1.000 | 0.000 |
| Context Recall | 1.000 | 0.333 |

8개 지표 모두 scored이며 judge 오류·timeout은 없었다. RAGAS가 precision에 반환한 원래 값은 `0.9999999999`로 요약 JSON에 그대로 보관했다.

Faithfulness는 근거와 충돌하는 답변을 구분했다. precision·recall은 검색의 노이즈·정보 부족에 반응했다. Recall 0.333은 judge가 분해한 사실 단위의 비율이므로 입력 사실을 사람이 두 개로 센 비율과 같다고 가정하지 않는다.

Relevancy는 두 답변 모두 시간·입구를 다루므로 사실 정확성을 구분하는 지표로 쓰면 안 된다. 정상 답변도 0.358에 머물렀다. 원인 분석을 위한 생성 질문 전문은 이번 요약에 보관하지 않았으므로 한국어와 평가 prompt 언어의 영향은 아직 확인되지 않은 가설이다. 다음에는 한국어 평가 prompt·생성 질문을 임시 검토 자료로 확인해야 한다. 이 1회 결과로 합격선이나 서비스 성공률을 정하지 않는다.

## 시간과 비용

전체 평가 35.551초, API 요청 20회(LLM 16회·embedding 4회), 평가 비용 추정 **0.00255013 USD**다. response usage의 token과 2026-10-05에 확인한 단가로 계산한 추정치이며 청구서 확정 금액이 아니다.

단가는 100만 token당 judge input $0.15·cached input $0.075·output $0.60, embedding $0.02를 사용했다. [Judge 단가](https://developers.openai.com/api/docs/models/gpt-4o-mini), [Embedding 단가](https://developers.openai.com/api/docs/models/text-embedding-3-small)

저장 run은 질문·답변·근거·judge 출력 전문 없이 설정·hash·점수·duration·token usage만 담는다. 요약 JSON은 2개 사례·8개 scored·유효 수치·요청/비용 상한·API 응답 성공 여부를 로컬에서 검증했다. production 평가 run schema·manifest 및 비용 runner 구현이 완료됐다는 의미는 아니다.
