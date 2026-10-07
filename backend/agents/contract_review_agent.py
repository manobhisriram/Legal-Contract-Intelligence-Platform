"""Four-stage contract review pipeline.

Stages run sequentially, each backed by a different model provider:

1. Extractor     - Anthropic (Claude Sonnet): segments the contract into typed clauses.
2. Risk Analyst  - OpenAI (GPT-4o): classifies each clause against the risk pattern library.
3. Comparator    - Google (Gemini Pro): flags deviations from the standard template for the contract type.
4. Synthesis     - Anthropic (Claude Opus): produces the structured report, priorities and redlines.

Every stage degrades gracefully: a provider failure is logged, recorded as a metric and
returned as an empty result so the remaining stages still run.
"""
import json
import time
from typing import Dict, Any, List
from datetime import datetime

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.datadog_setup import LLMSpan
from backend.core import metrics

logger = get_logger(__name__)

# Risk patterns library for Risk Analyst agent
RISK_PATTERNS = {
    "data_rights": {
        "keywords": ["use your data", "train", "improve our services", "anonymized data", "aggregate data"],
        "risk_level": "critical",
        "description": "Vendor can use your data for AI training or product improvement",
    },
    "liability_cap_missing": {
        "keywords": ["unlimited liability", "no cap", "shall not limit"],
        "risk_level": "high",
        "description": "No liability cap specified — exposure is unlimited",
    },
    "liability_cap_low": {
        "keywords": ["liability", "cap", "limited to", "not exceed", "maximum"],
        "risk_level": "medium",
        "description": "Liability cap may be insufficient relative to contract value",
    },
    "auto_renewal": {
        "keywords": ["automatically renew", "auto-renew", "unless terminated", "automatic renewal"],
        "risk_level": "high",
        "description": "Contract auto-renews — must track and cancel proactively",
    },
    "unilateral_modification": {
        "keywords": ["may modify", "reserves the right to change", "at our discretion", "without notice"],
        "risk_level": "high",
        "description": "Vendor can unilaterally modify terms without your consent",
    },
    "ip_ownership_risk": {
        "keywords": ["all intellectual property", "work for hire", "assign all rights", "owns all"],
        "risk_level": "critical",
        "description": "IP ownership may transfer to vendor — review carefully",
    },
    "governing_law_unfavorable": {
        "keywords": ["laws of", "jurisdiction", "courts of", "arbitration in"],
        "risk_level": "medium",
        "description": "Governing law or dispute venue may be unfavorable",
    },
    "indemnification_broad": {
        "keywords": ["indemnify", "hold harmless", "defend", "indemnification"],
        "risk_level": "high",
        "description": "Broad indemnification obligations — scope needs review",
    },
    "termination_restrictive": {
        "keywords": ["termination for convenience", "30 days notice", "60 days", "without cause"],
        "risk_level": "medium",
        "description": "Termination notice period or conditions may be restrictive",
    },
    "confidentiality_weak": {
        "keywords": ["confidential information", "non-disclosure", "proprietary"],
        "risk_level": "medium",
        "description": "Confidentiality protections need careful review",
    },
}

STANDARD_CLAUSES = {
    "nda": {
        "confidentiality_period": "2 years",
        "scope": "both parties",
        "governing_law": "jurisdiction of company headquarters",
        "permitted_disclosure": "legal requirement or court order",
    },
    "saas": {
        "uptime_sla": "99.9%",
        "data_ownership": "customer retains all data ownership",
        "termination_notice": "30 days",
        "liability_cap": "12 months of fees paid",
        "governing_law": "company jurisdiction",
    },
    "vendor": {
        "payment_terms": "net 30",
        "liability_cap": "contract value",
        "ip_ownership": "customer owns all custom work",
        "termination_for_cause": "14 days notice",
    },
}


def run_extractor_agent(contract_text: str) -> Dict[str, Any]:
    """Extractor Agent — Claude Sonnet (instrumented with an LLM span)."""
    start_ms = time.time() * 1000
    with LLMSpan("extractor_agent", model="claude-sonnet-4-5", provider="anthropic", agent_role="extractor") as span:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            system_prompt = (
                "You are a legal clause extraction specialist. Read the contract and identify every "
                "meaningful clause by type. For each clause extract: clause_type, clause_text (first 500 chars), "
                "page_indicator, notes. Types include: liability_cap, data_rights, termination, governing_law, "
                "indemnification, ip_ownership, confidentiality, payment_terms, auto_renewal, sla, warranty. "
                "Return JSON with a 'clauses' array. Be thorough."
            )
            prompt = f"Extract all clauses from this contract:\n\n{contract_text[:15000]}"
            span.set_input(prompt[:800])
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            span.set_output(text[:500])
            span.set_tokens(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
            cost = (response.usage.input_tokens / 1_000_000) * 3.0 + (response.usage.output_tokens / 1_000_000) * 15.0
            span.set_cost(cost)
            try:
                s = text.find("{"); e = text.rfind("}") + 1
                result = json.loads(text[s:e]) if s >= 0 and e > s else {"clauses": []}
            except json.JSONDecodeError:
                result = {"clauses": [], "raw_output": text[:2000]}
            result["tokens_used"] = response.usage.input_tokens + response.usage.output_tokens
            result["model"] = "claude-sonnet-4-5"
            latency_ms = time.time() * 1000 - start_ms
            metrics.agent_call("extractor", "claude-sonnet-4-5", "anthropic",
                               response.usage.input_tokens, response.usage.output_tokens, cost, latency_ms)
            logger.info("Extractor agent complete", clauses=len(result.get("clauses", [])), latency_ms=round(latency_ms))
            return result
        except Exception as e:
            span.set_error(e)
            logger.error("Extractor agent failed", error=str(e))
            metrics.agent_call("extractor", "claude-sonnet-4-5", "anthropic", 0, 0, 0, time.time()*1000 - start_ms, success=False)
            return {"clauses": [], "error": str(e), "tokens_used": 0}


def run_risk_analyst_agent(clauses: List[Dict], contract_context: str = "") -> Dict[str, Any]:
    """Risk Analyst Agent — GPT-4o (instrumented with an LLM span)."""
    start_ms = time.time() * 1000
    with LLMSpan("risk_analyst_agent", model="gpt-4o", provider="openai", agent_role="risk_analyst") as span:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            pattern_summary = json.dumps(RISK_PATTERNS, indent=2)[:3000]
            system_prompt = (
                f"You are a legal risk analyst. For each clause, assess risk_level (low/medium/high/critical), "
                f"risk_reasoning, risk_patterns_matched, and financial_exposure. "
                f"Known patterns:\n{pattern_summary}\n"
                f"Return JSON with 'risk_assessments' array, one per clause."
            )
            clauses_text = json.dumps(clauses[:30], indent=2)[:8000]
            span.set_input(clauses_text[:800])
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=3000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Assess risk for these clauses:\n{clauses_text}"},
                ],
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            span.set_output(str(result)[:500])
            span.set_tokens(input_tokens=response.usage.prompt_tokens, output_tokens=response.usage.completion_tokens)
            cost = (response.usage.prompt_tokens / 1_000_000) * 5.0 + (response.usage.completion_tokens / 1_000_000) * 15.0
            span.set_cost(cost)
            result["tokens_used"] = response.usage.total_tokens
            result["model"] = "gpt-4o"
            latency_ms = time.time() * 1000 - start_ms
            metrics.agent_call("risk_analyst", "gpt-4o", "openai",
                               response.usage.prompt_tokens, response.usage.completion_tokens, cost, latency_ms)
            logger.info("Risk analyst complete", assessments=len(result.get("risk_assessments", [])), latency_ms=round(latency_ms))
            return result
        except Exception as e:
            span.set_error(e)
            logger.error("Risk analyst agent failed", error=str(e))
            metrics.agent_call("risk_analyst", "gpt-4o", "openai", 0, 0, 0, time.time()*1000 - start_ms, success=False)
            return {"risk_assessments": [], "error": str(e), "tokens_used": 0}


def run_comparator_agent(clauses: List[Dict], contract_type: str = "saas") -> Dict[str, Any]:
    """Comparator Agent — Gemini Pro (instrumented with an LLM span)."""
    start_ms = time.time() * 1000
    with LLMSpan("comparator_agent", model="gemini-1.5-pro", provider="google", agent_role="comparator") as span:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            model = genai.GenerativeModel("gemini-1.5-pro")
            standard = STANDARD_CLAUSES.get(contract_type, STANDARD_CLAUSES["saas"])
            clauses_text = json.dumps(clauses[:20], indent=2)[:6000]
            prompt = (
                f"You are a contract comparison specialist. Compare these clauses against the "
                f"{contract_type.upper()} standard:\n{json.dumps(standard, indent=2)}\n\n"
                f"CLAUSES:\n{clauses_text}\n\n"
                f"For each deviation: clause_type, deviation, standard_says, contract_says, "
                f"severity (minor/moderate/significant), recommended_action. Return JSON with 'deviations' array."
            )
            span.set_input(prompt[:800])
            response = model.generate_content(prompt)
            text = response.text
            span.set_output(text[:500])
            try:
                s = text.find("{"); e = text.rfind("}") + 1
                result = json.loads(text[s:e]) if s >= 0 and e > s else {"deviations": []}
            except json.JSONDecodeError:
                result = {"deviations": [], "raw_output": text[:2000]}
            result["model"] = "gemini-1.5-pro"
            result["tokens_used"] = 0
            latency_ms = time.time() * 1000 - start_ms
            metrics.agent_call("comparator", "gemini-1.5-pro", "google", 0, 0, 0.0, latency_ms)
            logger.info("Comparator agent complete", deviations=len(result.get("deviations", [])), latency_ms=round(latency_ms))
            return result
        except Exception as e:
            span.set_error(e)
            logger.error("Comparator agent failed", error=str(e))
            metrics.agent_call("comparator", "gemini-1.5-pro", "google", 0, 0, 0, time.time()*1000 - start_ms, success=False)
            return {"deviations": [], "error": str(e), "tokens_used": 0}


def run_synthesis_agent(
    clauses: List[Dict],
    risk_assessments: List[Dict],
    deviations: List[Dict],
    contract_filename: str = "",
) -> Dict[str, Any]:
    """Synthesis Agent — Claude Opus (instrumented with an LLM span)."""
    start_ms = time.time() * 1000
    with LLMSpan("synthesis_agent", model="claude-opus-4-5", provider="anthropic", agent_role="synthesis") as span:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
            for a in risk_assessments:
                level = a.get("risk_level", "low").lower()
                if level in risk_counts:
                    risk_counts[level] += 1
            context = {
                "total_clauses": len(clauses),
                "risk_counts": risk_counts,
                "deviations_count": len(deviations),
                "top_risks": [a for a in risk_assessments if a.get("risk_level") in ["high", "critical"]][:10],
                "top_deviations": [d for d in deviations if d.get("severity") in ["moderate", "significant"]][:10],
            }
            system_prompt = (
                "You are a senior legal counsel synthesising a contract review. Return JSON with: "
                "overall_risk_score (0-100), overall_risk_level (low/medium/high/critical), "
                "executive_summary (2-3 sentences), top_5_issues (array with issue_title, description, "
                "severity, specific_clause_text, recommended_action, suggested_redline), "
                "negotiation_priorities (ordered list), deal_breakers (list), acceptable_as_is (list), "
                "confidence_score (0-100)."
            )
            prompt = f"Synthesise review for '{contract_filename}':\n{json.dumps(context, indent=2)[:8000]}"
            span.set_input(prompt[:800])
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            span.set_output(text[:500])
            span.set_tokens(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
            cost = (response.usage.input_tokens / 1_000_000) * 15.0 + (response.usage.output_tokens / 1_000_000) * 75.0
            span.set_cost(cost)
            try:
                s = text.find("{"); e = text.rfind("}") + 1
                result = json.loads(text[s:e]) if s >= 0 and e > s else {"overall_risk_level": "medium"}
            except json.JSONDecodeError:
                result = {"overall_risk_level": "medium", "executive_summary": text[:500]}
            result["tokens_used"] = response.usage.input_tokens + response.usage.output_tokens
            result["model"] = "claude-opus-4-5"
            latency_ms = time.time() * 1000 - start_ms
            metrics.agent_call("synthesis", "claude-opus-4-5", "anthropic",
                               response.usage.input_tokens, response.usage.output_tokens, cost, latency_ms)
            logger.info("Synthesis agent complete", risk_level=result.get("overall_risk_level"), latency_ms=round(latency_ms))
            return result
        except Exception as e:
            span.set_error(e)
            logger.error("Synthesis agent failed", error=str(e))
            metrics.agent_call("synthesis", "claude-opus-4-5", "anthropic", 0, 0, 0, time.time()*1000 - start_ms, success=False)
            return {"overall_risk_level": "unknown", "executive_summary": "Review failed — please retry", "error": str(e), "tokens_used": 0}


async def run_full_contract_review(
    contract_text: str,
    contract_id: str,
    contract_filename: str,
    contract_type: str = "saas",
) -> Dict[str, Any]:
    """Run the sequential four-agent review pipeline (extract, assess, compare, synthesize)."""
    from backend.core.datadog_setup import statsd
    start_time = time.time()
    total_tokens = 0
    models_used = []

    logger.info("Starting full contract review", contract_id=contract_id)
    statsd.increment("legal_intel.review.pipeline_started", tags=[f"contract_type:{contract_type}"])

    extractor_result = run_extractor_agent(contract_text)
    clauses = extractor_result.get("clauses", [])
    total_tokens += extractor_result.get("tokens_used", 0)
    models_used.append(extractor_result.get("model", "claude-sonnet-4-5"))

    risk_result = run_risk_analyst_agent(clauses, contract_text[:2000])
    risk_assessments = risk_result.get("risk_assessments", [])
    total_tokens += risk_result.get("tokens_used", 0)
    models_used.append(risk_result.get("model", "gpt-4o"))

    for i, clause in enumerate(clauses):
        if i < len(risk_assessments):
            clause.update(risk_assessments[i])

    comparator_result = run_comparator_agent(clauses, contract_type)
    deviations = comparator_result.get("deviations", [])
    total_tokens += comparator_result.get("tokens_used", 0)
    models_used.append(comparator_result.get("model", "gemini-1.5-pro"))

    synthesis_result = run_synthesis_agent(clauses, risk_assessments, deviations, contract_filename)
    total_tokens += synthesis_result.get("tokens_used", 0)
    models_used.append(synthesis_result.get("model", "claude-opus-4-5"))

    duration = time.time() - start_time
    # Approximate blended rate for the aggregate figure; per-agent costs use provider list
    # prices and are emitted individually as LLM span / DogStatsD metrics.
    cost_estimate = (total_tokens / 1_000_000) * 15.0

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for clause in clauses:
        level = clause.get("risk_level", "low").lower()
        if level in risk_counts:
            risk_counts[level] += 1

    statsd.distribution("legal_intel.review.pipeline_duration_seconds", duration,
                        tags=[f"contract_type:{contract_type}",
                              f"risk_level:{synthesis_result.get('overall_risk_level','unknown')}"])

    return {
        "contract_id": contract_id,
        "contract_filename": contract_filename,
        "review_status": "completed",
        "overall_risk_score": synthesis_result.get("overall_risk_score", 50),
        "overall_risk_level": synthesis_result.get("overall_risk_level", "medium"),
        "executive_summary": synthesis_result.get("executive_summary", ""),
        "total_clauses_found": len(clauses),
        "risk_counts": risk_counts,
        "high_risk_count": risk_counts.get("high", 0),
        "critical_count": risk_counts.get("critical", 0),
        "top_5_issues": synthesis_result.get("top_5_issues", []),
        "negotiation_priorities": synthesis_result.get("negotiation_priorities", []),
        "deal_breakers": synthesis_result.get("deal_breakers", []),
        "acceptable_as_is": synthesis_result.get("acceptable_as_is", []),
        "confidence_score": synthesis_result.get("confidence_score", 70),
        "deviations_from_standard": deviations,
        "all_clauses": clauses,
        "extractor_output": extractor_result,
        "risk_analyst_output": risk_result,
        "comparator_output": comparator_result,
        "synthesis_output": synthesis_result,
        "review_duration_seconds": round(duration, 2),
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(cost_estimate, 4),
        "models_used": list(set(models_used)),
        "completed_at": datetime.utcnow().isoformat(),
    }
