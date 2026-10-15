"""Offline aggregation of a fixed baseline and agent fact-review annotations."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def percentile(values: list[float], p: float):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def aggregate(rows: list[dict[str, Any]]):
    result = {
        "case_count": len(rows),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "response_origins": dict(
            Counter(r["response_origin"] for r in rows if "response_origin" in r)
        ),
        "metrics": {},
    }
    for name in METRICS:
        metrics = [r["metrics"][name] for r in rows]
        values = [m["value"] for m in metrics if m["status"] == "scored"]
        result["metrics"][name] = {
            "mean": mean(values) if values else None,
            "scored": len(values),
            "status_counts": dict(Counter(m["status"] for m in metrics)),
            "reason_counts": dict(
                Counter(m.get("reason_code") for m in metrics if m.get("reason_code"))
            ),
        }
    durations = [r["duration_ms"] for r in rows if r.get("duration_ms") is not None]
    result["graph_latency_ms"] = {
        "count": len(durations),
        "mean": mean(durations) if durations else None,
        "p50": percentile(durations, 0.5),
        "p95": percentile(durations, 0.95),
    }
    checked = [r for r in rows if "tool_routing_match" in r]
    result["draft_expected_tool_match"] = {
        "matches": sum(r["tool_routing_match"] for r in checked),
        "count": len(checked),
        "scope": "candidate_expected_tool_agreement_not_independently_validated_routing_accuracy",
    }
    for k in ("3", "5"):
        ranks = [r["ranks"][k] for r in rows]
        valid = [r for r in ranks if r["status"] == "computed"]
        result["ranks_at_" + k] = {
            "computed": len(valid),
            "reason_counts": dict(
                Counter(
                    r.get("reason_code", "not_run")
                    for r in ranks
                    if r["status"] != "computed"
                )
            ),
            "mean": {
                name: mean(r[name] for r in valid) if valid else None
                for name in ("recall", "mrr", "ndcg")
            },
            "scope": "bounded_expected_filter_pool_not_global_recall",
        }
    stages = defaultdict(list)
    for row in rows:
        for event in row.get("stage_traces", []):
            if "duration_ms" in event:
                stages[event["event"]].append(event["duration_ms"])
    result["stages_ms"] = {
        key: {
            "count": len(values),
            "mean": mean(values),
            "p50": percentile(values, 0.5),
            "p95": percentile(values, 0.95),
        }
        for key, values in stages.items()
    }
    return result


def enrich(run, dataset, reviews):
    if run["dataset_sha256"] != dataset["content_sha256"]:
        raise ValueError("dataset hash mismatch")
    by_id = {c["case_id"]: c for c in dataset["cases"]}
    results = {r["case_id"]: r for r in run["results"]}
    if set(reviews) != {
        r["case_id"] for r in run["results"] if r["status"] != "not_run"
    }:
        raise ValueError("review/capture set mismatch")
    for key, review in reviews.items():
        case = by_id[key]
        if set(
            review["present"] + review["missing"] + review.get("context_only", [])
        ) != set(range(len(case["expected"]["required_facts"]))):
            raise ValueError("review fact index completeness")
        statuses = []
        for index in range(len(case["expected"]["required_facts"])):
            status = (
                "context_only"
                if index in review.get("context_only", [])
                else "incorrect_or_ambiguous"
                if index in review.get("incorrect", [])
                else "partial"
                if index in review.get("partial_facts", [])
                else "supported"
                if index in review["present"]
                else "missing"
            )
            statuses.append({"fact_index": index, "status": status})
        results[key]["answer_quality_review"] = {
            "reviewer_kind": "agent",
            "human_reviewed": False,
            "scope": "fixed_required_facts_not_overall_answer_accuracy",
            "full_required_facts": not review["missing"],
            "supported_fact_count": len(review["present"]),
            "required_fact_count": len(case["expected"]["required_facts"])
            - len(review.get("context_only", [])),
            "fact_labels": statuses,
            "note": review["note"],
            "additional_issue_noted": bool(
                review.get("reference_mismatch") or review.get("incorrect")
            ),
            "final_response_sha256": results[key].get("final_response_sha256"),
        }
    run["aggregate"] = aggregate(run["results"])
    run["by_category"] = {
        category: aggregate([r for r in run["results"] if r["category"] == category])
        for category in dataset["category_counts"]
    }
    run["by_split"] = {
        split: aggregate([r for r in run["results"] if r["split"] == split])
        for split in ("development", "held_out")
    }
    factual = [
        r
        for r in run["results"]
        if by_id[r["case_id"]]["expected"]["answerability"] == "source_answerable"
    ]
    policies = [
        r
        for r in run["results"]
        if by_id[r["case_id"]]["expected"]["answerability"] == "policy_only"
    ]

    def counts(rows):
        reviewed = [
            r["answer_quality_review"] for r in rows if "answer_quality_review" in r
        ]
        return {
            "evaluated": len(reviewed),
            "full_required_facts": sum(r["full_required_facts"] for r in reviewed),
            "some_required_facts": sum(
                not r["full_required_facts"]
                and any(
                    f["status"] in {"supported", "partial"} for f in r["fact_labels"]
                )
                for r in reviewed
            ),
            "no_supported_required_facts": sum(
                not any(
                    f["status"] in {"supported", "partial"} for f in r["fact_labels"]
                )
                for r in reviewed
            ),
            "required_fact_count": sum(r["required_fact_count"] for r in reviewed),
            "supported_fact_count": sum(r["supported_fact_count"] for r in reviewed),
        }

    run["agent_fact_review"] = {
        "reviewer_kind": "agent",
        "human_reviewed": False,
        "factual": counts(factual),
        "policy": counts(policies),
        "strict_required_fact_coverage_is_not_overall_question_accuracy": True,
    }
    usage = [u for r in run["results"] for u in r.get("provider_usage", [])] + run.get(
        "diagnostic_provider_usage", []
    )
    known = sum(u["usage_cost_upper_usd"] or 0 for u in usage)
    unknown = sum(
        u["reserved_microusd"] / 1e6 for u in usage if u["usage_cost_upper_usd"] is None
    )
    run["cost_analysis"] = {
        "observed_usage_cost_upper_usd": round(known, 8),
        "unobserved_usage_reserved_upper_usd": round(unknown, 8),
        "combined_cost_upper_usd": round(known + unknown, 8),
        "all_requests_reserved_upper_usd": run["budget_ledger"]["reserved_microusd"]
        / 1e6,
        "input_tokens_observed": sum(u["input_tokens"] or 0 for u in usage),
        "output_tokens_observed": sum(u["output_tokens"] or 0 for u in usage),
        "note": "undiscounted token prices; failed/cancelled requests with missing usage keep full reservation; not an invoice",
    }
    run["scope_adjustment"] = {
        "blocked_action": "synthetic Auth account and chat writes",
        "automatic_review_rejection_reason": "explicit_database_write_authorization_not_confirmed",
        "alternative": "PostgreSQL READ ONLY transactions; no Auth/account/chat writes",
        "paid_calls_before_scope_adjustment": 0,
    }
    run["metric_interpretation_notes"] = [
        "AnswerRelevancy user_input includes fixed-context JSON, so it is not directly comparable to plain-question baselines.",
        "Automatic ContextRecall scored 1 for guide_006 and guide_012 despite independently labeled required-fact gaps in actual retrieved content; judge output alone is not factual correctness.",
        "Full required-fact coverage is strict and can penalize omissions of supplementary facts even when the primary question is usefully answered.",
        "Draft expected filter/tool agreement is diagnostic; knowledge_006 and scope_003 show useful behavior despite differences from candidate routing expectations.",
    ]
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    args = parser.parse_args()
    run = json.loads(args.run.read_text())
    dataset = json.loads(args.dataset.read_text())
    reviews = json.loads(args.reviews.read_text())
    enriched = enrich(run, dataset, reviews)
    if enriched["cost_analysis"]["all_requests_reserved_upper_usd"] > 2.5:
        raise ValueError("budget ceiling exceeded")
    args.run.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "aggregate": enriched["aggregate"],
                "agent_fact_review": enriched["agent_fact_review"],
                "cost_analysis": enriched["cost_analysis"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
