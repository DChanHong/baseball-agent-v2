"""Render blog figures and a public dataset reading view from recorded results.

No network, DB access, evaluation execution or paid calls.
Requires matplotlib. Example: python blog/assets/ragas-baseline-2026-10-15/generate_figures.py
"""

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/baseball-blog-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATASET = ROOT / "data/chat/evaluation/cases/agent_golden_candidates_v1.json"
RUN = ROOT / "data/chat/evaluation/runs/ragas/2026-10-15-agent-golden-readonly-baseline-v1.json"
dataset = json.loads(DATASET.read_text())
run = json.loads(RUN.read_text())
assert dataset["content_sha256"] == run["dataset_sha256"]
font_path = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
if font_path.exists():
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font_path)).get_name()
plt.rcParams.update({"font.size": 12, "axes.unicode_minus": False, "figure.facecolor": "#fafbfe", "axes.facecolor": "#fafbfe", "text.color": "#18243b", "axes.labelcolor": "#526079", "xtick.color": "#526079", "ytick.color": "#18243b", "savefig.facecolor": "#fafbfe"})


def tidy(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color="#e3e8f1", linewidth=0.8)


def save(fig, name):
    fig.savefig(OUT / name, dpi=180)
    plt.close(fig)


names = {"stadium_guide": "구장 이용 안내", "ticketing": "예매 안내", "baseball_knowledge": "야구 지식", "mixed_follow_up": "복합·후속 질문", "insufficient_out_of_scope": "근거 부족·범위 밖"}
fig, ax = plt.subplots(figsize=(10, 5.7))
fig.subplots_adjust(left=0.25, right=0.92, top=0.77, bottom=0.19)
cats = list(names)
counts = [dataset["category_counts"][k] for k in cats]
ax.barh(range(5), counts, height=0.53, color=["#4169d8", "#6686dd", "#4169d8", "#9bb0e8", "#9bb0e8"])
ax.set_yticks(range(5), list(names.values()))
ax.invert_yaxis()
ax.set_xlim(0, 17)
ax.set_xticks([0, 5, 10, 15])
ax.set_xlabel("후보 질문 수")
for i, value in enumerate(counts):
    ax.text(value + 0.3, i, f"{value}건", va="center", weight="bold")
tidy(ax)
fig.text(0.06, 0.91, "골든 데이터셋 후보 50건의 구성", fontsize=21, weight="bold")
fig.text(0.06, 0.845, "단일 주제뿐 아니라 문맥·복합 질문과 답하기 어려운 상황도 포함", color="#526079")
fig.text(0.06, 0.055, "사람 검수 전 후보 데이터셋 · 실제 실행 49건 / 출처 충돌 보류 1건", fontsize=11, color="#526079")
save(fig, "01-dataset-composition.png")

keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
labels = ["Faithfulness\n근거 준수", "Answer relevancy*\n질문 관련성", "Context precision\n검색 정밀도", "Context recall*\n검색 회수율"]
metrics = run["aggregate"]["metrics"]
fig, ax = plt.subplots(figsize=(11, 6.5))
fig.subplots_adjust(left=0.255, right=0.87, top=0.75, bottom=0.29)
values = [metrics[k]["mean"] for k in keys]
ax.barh(range(4), values, height=0.57, color=["#4169d8", "#d79b38", "#4169d8", "#4169d8"])
ax.set_yticks(range(4), labels)
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
ax.set_xlabel("지표별 평균 점수 (정답률 아님)")
for i, (key, value) in enumerate(zip(keys, values)):
    ax.text(value - 0.015 if value > 0.5 else value + 0.018, i, f"{value:.3f}", va="center", ha="right" if value > 0.5 else "left", color="white" if value > 0.5 else "#18243b", weight="bold", fontsize=13)
    ax.text(1.025, i, f"n={metrics[key]['scored']}", transform=ax.get_yaxis_transform(), va="center", fontsize=11, color="#526079")
tidy(ax)
fig.text(0.06, 0.92, "현재 agent의 RAGAS 기준선", fontsize=22, weight="bold")
fig.text(0.06, 0.853, "2026-10-15 · 49건 실제 실행 · 지표별 채점 대상이 다름", color="#526079")
fig.text(0.06, 0.145, "* 질문 관련성: 질문+고정 문맥 JSON 입력으로 일반 기준선과 직접 비교 불가", fontsize=11, color="#8b601b")
fig.text(0.06, 0.095, "* 검색 회수율: 일부 과대평가 사례 확인 · 미측정은 평균에서 제외", fontsize=11, color="#526079")
fig.text(0.06, 0.045, "RAGAS 0.4.3 / judge: gpt-4o-mini-2024-07-18 · 종합 점수를 산출하지 않음", fontsize=10, color="#526079")
save(fig, "02-ragas-metrics.png")

review = run["agent_fact_review"]["factual"]
values = [review["full_required_facts"], review["some_required_facts"], review["no_supported_required_facts"]]
fig, ax = plt.subplots(figsize=(10, 5.8))
fig.subplots_adjust(left=0.26, right=0.91, top=0.74, bottom=0.26)
ax.barh(range(3), values, height=0.52, color=["#258b76", "#6686dd", "#c87845"])
ax.set_yticks(range(3), ["모든 기대 사실 충족", "일부 기대 사실 충족", "충족한 기대 사실 없음"])
ax.invert_yaxis()
ax.set_xlim(0, 23)
ax.set_xticks([0, 5, 10, 15, 20])
ax.set_xlabel("사실 답변 사례 수")
for i, value in enumerate(values):
    ax.text(value + 0.35, i, f"{value}건", va="center", weight="bold", fontsize=14)
tidy(ax)
fig.text(0.06, 0.91, "실제 답변은 기대 사실을 얼마나 담았나", fontsize=21, weight="bold")
fig.text(0.06, 0.839, "사실 질문 43건 · 정책·고정 문맥 응답 6건은 별도", color="#526079")
fig.text(0.06, 0.12, "Agent가 후보 required_facts와 대조한 검토 · 사람 검수 전", fontsize=11, color="#526079")
fig.text(0.06, 0.065, "부가 사실 누락도 일부 충족으로 분류하므로 전체 정답률을 뜻하지 않음", fontsize=11, color="#526079")
save(fig, "03-required-fact-coverage.png")

sources = {s["source_id"]: s for s in dataset["sources"]}
selected = {"golden_guide_003", "golden_ticket_001", "golden_knowledge_006", "golden_mixed_003", "golden_scope_005"}
examples = []
lines = ["# RAGAS 평가 후보 데이터셋 전체 보기", "", "2026-10-14 기준으로 구성한 50개 합성 질문이다. 사람 검수 전 후보이며 기대답변은 실제 agent 출력이 아니다. 정책·고정 문맥 사례는 외부 사실 출처 대신 서비스 계약 또는 합성 fixture를 사용한다. 출처 링크는 당시 확인 기록이며 현재 정책을 보장하지 않는다.", "", "이 목록은 원본 JSON의 읽기용 축약본이다. 실제 실행 상태는 2026-10-15 결과 파일을 따른다.", "", "| ID | 유형 | 질문 | 기대 사실 | 출처·기준 | 실행 |", "|---|---|---|---|---|---|"]
results = {r["case_id"]: r for r in run["results"]}


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


for case in dataset["cases"]:
    ev = []
    for evidence in case["evidence"]:
        source = sources[evidence["source_id"]]
        label = evidence["locator"]
        ev.append(f"[{label}]({source['url']})" if source.get("url") else label)
    if case["case_id"] in selected:
        examples.append({"case_id": case["case_id"], "question": case["input"]["question"], "context": case["input"]["conversation_context"], "reference_answer": case["expected"]["reference_answer"], "required_facts": case["expected"]["required_facts"], "forbidden_claims": case["expected"]["forbidden_claims"], "sources": [{"source_id": e["source_id"], "locator": e["locator"], "url": sources[e["source_id"]].get("url")} for e in case["evidence"]], "human_reviewed": False})
    state = "보류: 출처 확인 필요" if results[case["case_id"]]["status"] == "not_run" else "실행 완료"
    lines.append("| " + " | ".join(cell(v) for v in [case["case_id"], names[case["category"]], case["input"]["question"], "; ".join(case["expected"]["required_facts"]), "; ".join(ev), state]) + " |")
(OUT / "dataset-50-case-overview.md").write_text("\n".join(lines) + "\n")
(OUT / "dataset-5-examples.json").write_text(json.dumps({"human_reviewed": False, "scope": "reading_view_not_evaluation_input", "examples": examples}, ensure_ascii=False, indent=2) + "\n")
print("Created 3 PNG figures, 50-case Markdown overview and 5-example JSON from recorded data.")
