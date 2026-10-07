"""Shared pytest configuration and fixtures.

Tests validate agent, judge, red-team, configuration and API-validation logic without real
provider keys (model calls are mocked) or a live database.
"""
import os

# Settings are read at import time; provide inert placeholders so no real service is needed.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("DD_TRACE_ENABLED", "false")

import pytest
from typing import Dict, Any


# ─── Mock LLM Responses ───────────────────────────────────────────────────────

MOCK_EXTRACTOR_OUTPUT = {
    "clauses": [
        {
            "clause_type": "data_rights",
            "clause_text": "Provider may use Client data to train, fine-tune, and improve AI models. This license is perpetual and irrevocable.",
            "page_indicator": "Section 3.4",
        },
        {
            "clause_type": "liability_cap",
            "clause_text": "Provider liability limited to fees paid in the previous 30 days.",
            "page_indicator": "Section 11.2",
        },
        {
            "clause_type": "auto_renewal",
            "clause_text": "Agreement automatically renews for successive one-year terms unless terminated with 90 days notice.",
            "page_indicator": "Section 8.1",
        },
        {
            "clause_type": "governing_law",
            "clause_text": "This Agreement is governed by the laws of the Cayman Islands.",
            "page_indicator": "Section 14.1",
        },
        {
            "clause_type": "payment_terms",
            "clause_text": "Invoices due within net 30 days of receipt.",
            "page_indicator": "Section 5.1",
        },
    ],
    "tokens_used": 1247,
    "model": "claude-sonnet-4-5",
}

MOCK_RISK_ANALYST_OUTPUT = {
    "risk_assessments": [
        {
            "clause_type": "data_rights",
            "risk_level": "critical",
            "risk_reasoning": "Perpetual, irrevocable AI training license is a critical data rights waiver.",
            "risk_patterns_matched": ["data_rights"],
        },
        {
            "clause_type": "liability_cap",
            "risk_level": "high",
            "risk_reasoning": "30-day fee cap is commercially unreasonable for enterprise contracts.",
            "risk_patterns_matched": ["liability_cap_low"],
        },
        {
            "clause_type": "auto_renewal",
            "risk_level": "high",
            "risk_reasoning": "90-day notice requirement with automatic renewal creates lock-in risk.",
            "risk_patterns_matched": ["auto_renewal"],
        },
        {
            "clause_type": "governing_law",
            "risk_level": "medium",
            "risk_reasoning": "Cayman Islands jurisdiction is unfavorable for Indian companies.",
            "risk_patterns_matched": ["governing_law_unfavorable"],
        },
        {
            "clause_type": "payment_terms",
            "risk_level": "low",
            "risk_reasoning": "Net 30 is standard market terms.",
            "risk_patterns_matched": [],
        },
    ],
    "tokens_used": 1832,
    "model": "gpt-4o",
}

MOCK_SYNTHESIS_OUTPUT = {
    "overall_risk_score": 78,
    "overall_risk_level": "critical",
    "executive_summary": "This contract has two critical issues. The data rights clause grants perpetual AI training rights. The liability cap is commercially unreasonable.",
    "top_5_issues": [
        {
            "issue_title": "AI Training Data Rights Waiver",
            "severity": "critical",
            "description": "Section 3.4 grants perpetual, irrevocable rights to use client data for AI training.",
            "recommended_action": "reject",
            "suggested_redline": "Provider shall not use Client Data for any AI/ML training purposes.",
        },
        {
            "issue_title": "Liability Cap — 30 Days Fees",
            "severity": "high",
            "description": "Liability cap is 30 days of fees — commercially unreasonable.",
            "recommended_action": "negotiate",
            "suggested_redline": "Cap shall not exceed 12 months of fees paid.",
        },
    ],
    "negotiation_priorities": [
        "Remove Section 3.4 AI training rights clause",
        "Increase liability cap to 12 months of fees",
        "Reduce auto-renewal notice to 30 days",
    ],
    "deal_breakers": ["Section 3.4 AI Training License — must be removed entirely"],
    "acceptable_as_is": ["Net 30 payment terms"],
    "confidence_score": 89,
    "tokens_used": 2104,
    "model": "claude-opus-4-5",
}


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_contract_text() -> str:
    return """
MASTER SERVICES AGREEMENT

1. SERVICES
Provider shall deliver software services as described in Schedule A.

2. PAYMENT TERMS
Client shall pay invoices within thirty (30) days of receipt.

3. DATA RIGHTS AND SERVICE IMPROVEMENT
In order to continuously improve our platform, Provider may use Client data,
including all inputs, outputs, and derivatives thereof, to train, fine-tune,
and improve Provider's artificial intelligence models. This license is
perpetual and irrevocable.

4. LIMITATION OF LIABILITY
Provider's maximum aggregate liability shall be limited to the fees paid
in the thirty (30) days preceding the claim.

5. AUTO-RENEWAL
This Agreement automatically renews for successive one-year terms unless
either party provides ninety (90) days written notice prior to renewal.

6. GOVERNING LAW
This Agreement shall be governed by the laws of the Cayman Islands.
"""


@pytest.fixture
def mock_extractor_response():
    return MOCK_EXTRACTOR_OUTPUT


@pytest.fixture
def mock_risk_response():
    return MOCK_RISK_ANALYST_OUTPUT


@pytest.fixture
def mock_synthesis_response():
    return MOCK_SYNTHESIS_OUTPUT


@pytest.fixture
def sample_review_result() -> Dict[str, Any]:
    """A complete review result for use in evaluation tests."""
    clauses = MOCK_EXTRACTOR_OUTPUT["clauses"].copy()
    for i, clause in enumerate(clauses):
        if i < len(MOCK_RISK_ANALYST_OUTPUT["risk_assessments"]):
            clause.update(MOCK_RISK_ANALYST_OUTPUT["risk_assessments"][i])

    return {
        "contract_id": "test-contract-001",
        "contract_filename": "test_saas_agreement.pdf",
        "review_status": "completed",
        "overall_risk_score": 78,
        "overall_risk_level": "critical",
        "executive_summary": MOCK_SYNTHESIS_OUTPUT["executive_summary"],
        "total_clauses_found": 5,
        "risk_counts": {"low": 1, "medium": 1, "high": 2, "critical": 1},
        "high_risk_count": 2,
        "critical_count": 1,
        "top_5_issues": MOCK_SYNTHESIS_OUTPUT["top_5_issues"],
        "negotiation_priorities": MOCK_SYNTHESIS_OUTPUT["negotiation_priorities"],
        "deal_breakers": MOCK_SYNTHESIS_OUTPUT["deal_breakers"],
        "acceptable_as_is": MOCK_SYNTHESIS_OUTPUT["acceptable_as_is"],
        "confidence_score": 89,
        "all_clauses": clauses,
        "review_duration_seconds": 42.7,
        "total_tokens_used": 5183,
        "total_cost_usd": 0.0094,
        "models_used": ["claude-sonnet-4-5", "gpt-4o", "gemini-1.5-pro", "claude-opus-4-5"],
    }


@pytest.fixture
def sample_ground_truth() -> Dict[str, Any]:
    """Ground truth labels for the sample contract (simulating CUAD-style annotations)."""
    return {
        "contract_id": "test-contract-001",
        "filename": "test_saas_agreement.pdf",
        "contract_type": "saas",
        "expected_clauses": [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
            {"type": "auto_renewal", "risk_level": "high", "must_find": True},
            {"type": "governing_law", "risk_level": "medium", "must_find": False},
            {"type": "payment_terms", "risk_level": "low", "must_find": False},
        ],
        "expected_risk_level": "critical",
        "expected_risk_score_range": [70, 90],
        "deal_breaker_present": True,
    }
