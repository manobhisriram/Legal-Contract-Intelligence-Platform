"""
Custom LLM Judge — built from scratch, not using Ragas or DeepEval.
Evaluates contract review quality on four dimensions:
1. Correctness — did it find the clauses that are actually there
2. Severity Calibration — did it classify risk levels correctly
3. Completeness — what percentage of risky clauses did it catch
4. Actionability — are the suggested redlines specific and usable
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core import metrics

logger = get_logger(__name__)

# CUAD-style ground truth structure for benchmark contracts
BENCHMARK_GROUND_TRUTH = [
    {
        "contract_id": "benchmark_001",
        "filename": "saas_vendor_agreement_acme.pdf",
        "contract_type": "saas",
        "expected_clauses": [
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "auto_renewal", "risk_level": "high", "must_find": True},
            {"type": "indemnification", "risk_level": "high", "must_find": True},
            {"type": "governing_law", "risk_level": "medium", "must_find": False},
        ],
        "expected_risk_level": "critical",
        "expected_risk_score_range": [70, 90],
        "deal_breaker_present": True,
    },
    {
        "contract_id": "benchmark_002",
        "filename": "nda_mutual_techcorp.pdf",
        "contract_type": "nda",
        "expected_clauses": [
            {"type": "confidentiality", "risk_level": "medium", "must_find": True},
            {"type": "ip_ownership", "risk_level": "high", "must_find": True},
            {"type": "termination", "risk_level": "medium", "must_find": True},
        ],
        "expected_risk_level": "medium",
        "expected_risk_score_range": [30, 60],
        "deal_breaker_present": False,
    },
    {
        "contract_id": "benchmark_003",
        "filename": "vendor_services_globaltech.pdf",
        "contract_type": "vendor",
        "expected_clauses": [
            {"type": "payment_terms", "risk_level": "low", "must_find": True},
            {"type": "liability_cap", "risk_level": "medium", "must_find": True},
            {"type": "ip_ownership", "risk_level": "critical", "must_find": True},
            {"type": "indemnification", "risk_level": "high", "must_find": True},
            {"type": "unilateral_modification", "risk_level": "high", "must_find": True},
        ],
        "expected_risk_level": "high",
        "expected_risk_score_range": [60, 85],
        "deal_breaker_present": True,
    },
]


def score_correctness(
    predicted_clauses: List[Dict],
    ground_truth_clauses: List[Dict],
) -> Dict[str, Any]:
    """Score how many ground truth clauses were correctly found."""
    if not ground_truth_clauses:
        return {"score": 1.0, "details": "No ground truth clauses to check"}

    found_types = {c.get("clause_type", "").lower() for c in predicted_clauses}
    must_find = [c for c in ground_truth_clauses if c.get("must_find", False)]

    hits = 0
    misses = []
    for expected in must_find:
        expected_type = expected["type"].lower()
        # Check for exact or partial match
        found = any(
            expected_type in ft or ft in expected_type
            for ft in found_types
        )
        if found:
            hits += 1
        else:
            misses.append(expected_type)

    score = hits / len(must_find) if must_find else 1.0
    return {
        "score": round(score, 3),
        "hits": hits,
        "total_required": len(must_find),
        "missed_clauses": misses,
    }


def score_severity_calibration(
    predicted_clauses: List[Dict],
    ground_truth_clauses: List[Dict],
) -> Dict[str, Any]:
    """Score how accurately risk levels were assigned."""
    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    calibration_scores = []
    for gt_clause in ground_truth_clauses:
        gt_type = gt_clause["type"].lower()
        gt_risk = gt_clause["risk_level"].lower()

        # Find matching predicted clause
        matching = [
            c for c in predicted_clauses
            if gt_type in c.get("clause_type", "").lower()
            or c.get("clause_type", "").lower() in gt_type
        ]

        if not matching:
            calibration_scores.append(0.0)
            continue

        pred_risk = matching[0].get("risk_level", "low").lower()
        gt_num = risk_order.get(gt_risk, 0)
        pred_num = risk_order.get(pred_risk, 0)

        diff = abs(gt_num - pred_num)
        if diff == 0:
            calibration_scores.append(1.0)
        elif diff == 1:
            calibration_scores.append(0.5)
        else:
            calibration_scores.append(0.0)

    score = sum(calibration_scores) / len(calibration_scores) if calibration_scores else 0.0
    return {
        "score": round(score, 3),
        "samples_evaluated": len(calibration_scores),
        "perfect_matches": sum(1 for s in calibration_scores if s == 1.0),
    }


def score_completeness(
    predicted_clauses: List[Dict],
    ground_truth_clauses: List[Dict],
    predicted_deal_breakers: List,
    expected_deal_breaker_present: bool,
) -> Dict[str, Any]:
    """Score what percentage of risky clauses were caught including deal breakers."""
    high_risk_gt = [c for c in ground_truth_clauses if c["risk_level"] in ["high", "critical"]]
    if not high_risk_gt:
        return {"score": 1.0, "details": "No high-risk ground truth clauses"}

    high_risk_found = {c.get("clause_type", "").lower() for c in predicted_clauses
                       if c.get("risk_level", "").lower() in ["high", "critical"]}

    caught = sum(
        1 for gt in high_risk_gt
        if any(gt["type"].lower() in ft or ft in gt["type"].lower() for ft in high_risk_found)
    )

    recall = caught / len(high_risk_gt) if high_risk_gt else 1.0

    # Bonus for correctly identifying deal breakers
    deal_breaker_score = 1.0
    if expected_deal_breaker_present and not predicted_deal_breakers:
        deal_breaker_score = 0.5
    elif not expected_deal_breaker_present and predicted_deal_breakers:
        deal_breaker_score = 0.8  # Minor penalty for false positive

    final_score = (recall * 0.7) + (deal_breaker_score * 0.3)
    return {
        "score": round(final_score, 3),
        "recall": round(recall, 3),
        "deal_breaker_detection": deal_breaker_score,
        "high_risk_caught": caught,
        "high_risk_total": len(high_risk_gt),
    }


def score_actionability(
    top_issues: List[Dict],
    suggested_redlines: List[str],
) -> Dict[str, Any]:
    """Use LLM to score actionability of review recommendations."""
    if not top_issues:
        return {"score": 0.2, "reason": "No issues identified"}

    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)

        issues_text = json.dumps(top_issues[:5], indent=2)[:3000]

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            max_tokens=400,
            messages=[
                {
                    "role": "system",
                    "content": """You are evaluating the actionability of contract review recommendations.
Score each issue on:
- Is the description specific (not vague)?
- Does it cite specific clause text?
- Is the recommended action clear and executable?
- Is the suggested redline (if present) professionally worded?

Return JSON: {"overall_score": 0-1, "specific_feedbacks": [...], "average_specificity": 0-1, "average_clarity": 0-1}""",
                },
                {
                    "role": "user",
                    "content": f"Evaluate actionability of these contract review issues:\n{issues_text}",
                },
            ],
        )

        text = response.choices[0].message.content
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            result = json.loads(text[start:end]) if start >= 0 else {"overall_score": 0.6}
            return {"score": result.get("overall_score", 0.6), **result}
        except Exception:
            return {"score": 0.6, "reason": "Could not parse LLM response"}

    except Exception as e:
        logger.error("Actionability scoring failed", error=str(e))
        # Heuristic fallback
        if not top_issues:
            return {"score": 0.2}
        avg_length = sum(len(str(issue)) for issue in top_issues) / len(top_issues)
        has_redlines = bool(suggested_redlines)
        score = min(0.9, (avg_length / 500) * 0.6 + (0.4 if has_redlines else 0.0))
        return {"score": round(score, 3), "method": "heuristic"}


def run_judge_on_review(
    review_result: Dict[str, Any],
    ground_truth: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the custom LLM judge on a single contract review result."""
    predicted_clauses = review_result.get("all_clauses", [])
    top_issues = review_result.get("top_5_issues", [])
    deal_breakers = review_result.get("deal_breakers", [])
    redlines = [issue.get("suggested_redline", "") for issue in top_issues if issue.get("suggested_redline")]

    if ground_truth:
        gt_clauses = ground_truth.get("expected_clauses", [])
        correctness = score_correctness(predicted_clauses, gt_clauses)
        calibration = score_severity_calibration(predicted_clauses, gt_clauses)
        completeness = score_completeness(
            predicted_clauses,
            gt_clauses,
            deal_breakers,
            ground_truth.get("deal_breaker_present", False),
        )
    else:
        # Without ground truth, use heuristic scoring
        correctness = {"score": min(0.9, len(predicted_clauses) / 10), "method": "heuristic"}
        calibration = {"score": 0.7, "method": "heuristic"}
        completeness = {
            "score": min(0.9, len([c for c in predicted_clauses if c.get("risk_level") in ["high", "critical"]]) / max(1, len(predicted_clauses) * 0.3)),
            "method": "heuristic",
        }

    actionability = score_actionability(top_issues, redlines)

    # Weighted overall score
    overall = (
        correctness["score"] * 0.30 +
        calibration["score"] * 0.25 +
        completeness["score"] * 0.25 +
        actionability["score"] * 0.20
    )

    return {
        "overall_score": round(overall, 3),
        "correctness": correctness,
        "severity_calibration": calibration,
        "completeness": completeness,
        "actionability": actionability,
        "evaluated_at": datetime.utcnow().isoformat(),
        "has_ground_truth": ground_truth is not None,
        "grade": _score_to_grade(overall),
    }


def _score_to_grade(score: float) -> str:
    if score >= 0.90:
        return "A"
    elif score >= 0.80:
        return "B"
    elif score >= 0.70:
        return "C"
    elif score >= 0.60:
        return "D"
    else:
        return "F"


def run_benchmark_evaluation(
    review_results: List[Dict[str, Any]],
    ground_truths: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run full benchmark evaluation across multiple contracts."""
    all_scores = []
    individual_results = []

    for i, review in enumerate(review_results):
        gt = None
        if ground_truths and i < len(ground_truths):
            gt = ground_truths[i]

        judge_result = run_judge_on_review(review, gt)
        all_scores.append(judge_result["overall_score"])
        individual_results.append({
            "contract_id": review.get("contract_id", f"contract_{i}"),
            "filename": review.get("contract_filename", "unknown"),
            **judge_result,
        })

    if not all_scores:
        return {"error": "No reviews to evaluate"}

    avg_scores = {
        "correctness": sum(r["correctness"]["score"] for r in individual_results) / len(individual_results),
        "severity_calibration": sum(r["severity_calibration"]["score"] for r in individual_results) / len(individual_results),
        "completeness": sum(r["completeness"]["score"] for r in individual_results) / len(individual_results),
        "actionability": sum(r["actionability"]["score"] for r in individual_results) / len(individual_results),
    }

    overall = round(sum(all_scores) / len(all_scores), 3)
    # Emit judge scores to Datadog
    metrics.judge_evaluation_completed(
        overall_score=overall,
        correctness=avg_scores["correctness"],
        severity_calibration=avg_scores["severity_calibration"],
        completeness=avg_scores["completeness"],
        actionability=avg_scores["actionability"],
        contracts_evaluated=len(review_results),
    )
    return {
        "benchmark_name": f"Legal Intelligence Agent — {len(review_results)} contracts",
        "total_contracts_evaluated": len(review_results),
        "overall_score": overall,
        "overall_grade": _score_to_grade(overall),
        "dimension_scores": {k: round(v, 3) for k, v in avg_scores.items()},
        "individual_results": individual_results,
        "best_performing": max(individual_results, key=lambda x: x["overall_score"])["filename"],
        "worst_performing": min(individual_results, key=lambda x: x["overall_score"])["filename"],
        "evaluated_at": datetime.utcnow().isoformat(),
    }
