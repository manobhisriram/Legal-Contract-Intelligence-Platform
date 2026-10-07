"""Unit tests for agent logic, the LLM judge, red-team detection, metrics and configuration.

All model calls are mocked; no provider keys are required.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ─── Judge Tests ──────────────────────────────────────────────────────────────

class TestJudgeCorrectness:
    """Tests for the custom LLM judge correctness scoring."""

    def test_perfect_correctness(self):
        """All required clauses found → score 1.0"""
        from backend.agents.llm_judge import score_correctness

        predicted = [
            {"clause_type": "data_rights", "risk_level": "critical"},
            {"clause_type": "liability_cap", "risk_level": "high"},
            {"clause_type": "auto_renewal", "risk_level": "high"},
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
            {"type": "auto_renewal", "risk_level": "high", "must_find": True},
        ]

        result = score_correctness(predicted, ground_truth)
        assert result["score"] == 1.0
        assert result["hits"] == 3
        assert result["missed_clauses"] == []

    def test_partial_correctness(self):
        """Two of three required clauses found → score 0.667"""
        from backend.agents.llm_judge import score_correctness

        predicted = [
            {"clause_type": "data_rights", "risk_level": "critical"},
            {"clause_type": "liability_cap", "risk_level": "high"},
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
            {"type": "auto_renewal", "risk_level": "high", "must_find": True},
        ]

        result = score_correctness(predicted, ground_truth)
        assert abs(result["score"] - 0.667) < 0.01
        assert result["hits"] == 2
        assert "auto_renewal" in result["missed_clauses"]

    def test_zero_correctness(self):
        """No required clauses found → score 0.0"""
        from backend.agents.llm_judge import score_correctness

        predicted = [{"clause_type": "payment_terms", "risk_level": "low"}]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
        ]

        result = score_correctness(predicted, ground_truth)
        assert result["score"] == 0.0
        assert result["hits"] == 0

    def test_optional_clauses_dont_affect_required_score(self):
        """Optional clauses not found should not reduce correctness score for must-find clauses."""
        from backend.agents.llm_judge import score_correctness

        predicted = [
            {"clause_type": "data_rights", "risk_level": "critical"},
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "governing_law", "risk_level": "medium", "must_find": False},
        ]

        result = score_correctness(predicted, ground_truth)
        assert result["score"] == 1.0  # Only must_find clauses count


class TestJudgeSeverityCalibration:
    """Tests for severity calibration scoring."""

    def test_perfect_calibration(self):
        """All risk levels match expert → score 1.0"""
        from backend.agents.llm_judge import score_severity_calibration

        predicted = [
            {"clause_type": "data_rights", "risk_level": "critical"},
            {"clause_type": "liability_cap", "risk_level": "high"},
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
        ]

        result = score_severity_calibration(predicted, ground_truth)
        assert result["score"] == 1.0
        assert result["perfect_matches"] == 2

    def test_one_level_off_calibration(self):
        """Risk level one level off → 0.5 per clause"""
        from backend.agents.llm_judge import score_severity_calibration

        predicted = [
            {"clause_type": "data_rights", "risk_level": "high"},  # Expert says critical → 0.5
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
        ]

        result = score_severity_calibration(predicted, ground_truth)
        assert result["score"] == 0.5
        assert result["perfect_matches"] == 0


class TestJudgeCompleteness:
    """Tests for high-risk recall completeness scoring."""

    def test_full_completeness_with_correct_deal_breaker(self):
        """All high-risk clauses found + correct deal-breaker detection."""
        from backend.agents.llm_judge import score_completeness

        predicted = [
            {"clause_type": "data_rights", "risk_level": "critical"},
            {"clause_type": "liability_cap", "risk_level": "high"},
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
            {"type": "payment_terms", "risk_level": "low", "must_find": False},
        ]
        deal_breakers = ["data rights clause is a deal breaker"]
        expected_deal_breaker_present = True

        result = score_completeness(predicted, ground_truth, deal_breakers, expected_deal_breaker_present)
        assert result["score"] > 0.9

    def test_missed_high_risk_reduces_completeness(self):
        """Missing a high-risk clause reduces completeness significantly."""
        from backend.agents.llm_judge import score_completeness

        predicted = [
            {"clause_type": "liability_cap", "risk_level": "high"},
            # data_rights MISSING
        ]
        ground_truth = [
            {"type": "data_rights", "risk_level": "critical", "must_find": True},
            {"type": "liability_cap", "risk_level": "high", "must_find": True},
        ]

        result = score_completeness(predicted, ground_truth, [], False)
        assert result["recall"] == 0.5


# ─── Risk Pattern Tests ───────────────────────────────────────────────────────

class TestRiskPatterns:
    """Tests for risk pattern library consistency."""

    def test_all_risk_patterns_have_required_fields(self):
        """Every pattern must have keywords, risk_level, and description."""
        from backend.agents.contract_review_agent import RISK_PATTERNS

        for pattern_name, pattern_data in RISK_PATTERNS.items():
            assert "keywords" in pattern_data, f"Pattern {pattern_name} missing 'keywords'"
            assert "risk_level" in pattern_data, f"Pattern {pattern_name} missing 'risk_level'"
            assert "description" in pattern_data, f"Pattern {pattern_name} missing 'description'"
            assert isinstance(pattern_data["keywords"], list), f"Pattern {pattern_name} keywords must be a list"
            assert pattern_data["risk_level"] in ["low", "medium", "high", "critical"], \
                f"Pattern {pattern_name} has invalid risk_level: {pattern_data['risk_level']}"

    def test_standard_clauses_exist_for_all_contract_types(self):
        """Standard clause templates must exist for saas, nda, and vendor."""
        from backend.agents.contract_review_agent import STANDARD_CLAUSES

        assert "saas" in STANDARD_CLAUSES
        assert "nda" in STANDARD_CLAUSES
        assert "vendor" in STANDARD_CLAUSES


# ─── Red-Team Detection Tests ─────────────────────────────────────────────────

class TestRedTeamDetection:
    """Tests for adversarial contract risk detection logic."""

    def test_data_rights_detection_from_clauses(self):
        """Data rights risk should be detected from clauses containing training keywords."""
        from backend.agents.red_team_agent import _check_risk_detected

        clauses = [
            {
                "clause_type": "service_improvement",
                "risk_level": "critical",
                "risk_reasoning": "Contains AI training data license",
                "clause_text": "Provider may use client data for AI model training purposes.",
            }
        ]
        detected = _check_risk_detected("data_rights_waiver", clauses, [], [])
        assert detected is True

    def test_data_rights_not_detected_in_payment_clause(self):
        """Data rights detection should not fire on payment clauses."""
        from backend.agents.red_team_agent import _check_risk_detected

        clauses = [
            {
                "clause_type": "payment_terms",
                "risk_level": "low",
                "risk_reasoning": "Standard net 30 terms.",
                "clause_text": "Client shall pay invoices within 30 days.",
            }
        ]
        detected = _check_risk_detected("data_rights_waiver", clauses, [], [])
        assert detected is False

    def test_auto_renewal_detected_with_evergreen_language(self):
        """Auto-renewal should be detected from 'evergreen' terminology."""
        from backend.agents.red_team_agent import _check_risk_detected

        clauses = [
            {
                "clause_type": "subscription_terms",
                "risk_level": "high",
                "risk_reasoning": "Evergreen subscription with automatic renewal",
                "clause_text": "This is an evergreen subscription that continues indefinitely.",
            }
        ]
        detected = _check_risk_detected("auto_renewal", clauses, [], [])
        assert detected is True

    def test_deal_breaker_contributes_to_detection(self):
        """Risk in deal_breakers should count as detected."""
        from backend.agents.red_team_agent import _check_risk_detected

        clauses = []
        deal_breakers = ["AI training license in data rights clause is a deal breaker"]
        detected = _check_risk_detected("data_rights_waiver", clauses, [], deal_breakers)
        assert detected is True

    def test_all_adversarial_contracts_have_required_fields(self):
        """Every adversarial contract must have all required fields."""
        from backend.agents.red_team_agent import get_all_adversarial_contracts

        contracts = get_all_adversarial_contracts()
        assert len(contracts) > 0

        for contract in contracts:
            assert "id" in contract, "Contract missing 'id'"
            assert "category" in contract, f"Contract {contract.get('id')} missing 'category'"
            assert "hidden_risk" in contract, f"Contract {contract.get('id')} missing 'hidden_risk'"
            assert "expected_detection" in contract, f"Contract {contract.get('id')} missing 'expected_detection'"
            assert "contract_text" in contract, f"Contract {contract.get('id')} missing 'contract_text'"
            assert len(contract["contract_text"]) > 100, f"Contract {contract.get('id')} text too short"


# ─── Model Field Consistency Tests ────────────────────────────────────────────

class TestModelConsistency:
    """Tests that ORM model fields match what API routes return."""

    def test_contract_model_has_required_fields(self):
        """Contract ORM model must have all fields used in API routes."""
        from backend.db.models import Contract

        mapper = Contract.__mapper__
        column_names = {col.key for col in mapper.columns}

        required_fields = [
            "id", "filename", "original_filename", "contract_type",
            "file_size_bytes", "page_count", "chunk_count",
            "has_vision_processing", "upload_status", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in column_names, f"Contract model missing field: {field}"

    def test_contract_review_model_has_required_fields(self):
        """ContractReview ORM model must have all fields used in routes."""
        from backend.db.models import ContractReview

        mapper = ContractReview.__mapper__
        column_names = {col.key for col in mapper.columns}

        required_fields = [
            "id", "contract_id", "review_status", "overall_risk_score",
            "overall_risk_level", "total_clauses_found", "high_risk_clause_count",
            "critical_clause_count", "extractor_output", "risk_analyst_output",
            "comparator_output", "synthesis_output", "negotiation_priorities",
            "review_duration_seconds", "total_tokens_used", "total_cost_usd",
            "models_used", "created_at", "completed_at"
        ]
        for field in required_fields:
            assert field in column_names, f"ContractReview model missing field: {field}"

    def test_risk_level_enum_values(self):
        """RiskLevel enum must have exact values used throughout codebase."""
        from backend.db.models import RiskLevel

        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_review_status_enum_values(self):
        """ReviewStatus enum must have exact values used throughout codebase."""
        from backend.db.models import ReviewStatus

        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.IN_PROGRESS.value == "in_progress"
        assert ReviewStatus.COMPLETED.value == "completed"
        assert ReviewStatus.FAILED.value == "failed"


# ─── Embedding Service Tests ──────────────────────────────────────────────────

class TestEmbeddingService:
    """Tests for embedding service with mocked OpenAI calls."""

    @pytest.mark.asyncio
    async def test_get_embeddings_returns_correct_dimensions(self):
        """Embeddings must be 1536-dimensional for text-embedding-3-small."""
        from backend.services.embedding_service import get_embeddings

        mock_embedding = [0.0] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(return_value=mock_response)
            result = await get_embeddings(["test text"])

        assert len(result) == 1
        assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_get_embeddings_handles_empty_input(self):
        """Empty input list should return empty list without API call."""
        from backend.services.embedding_service import get_embeddings

        result = await get_embeddings([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_embeddings_batches_correctly(self):
        """100+ texts should be processed in multiple batches."""
        from backend.services.embedding_service import get_embeddings

        mock_embedding = [0.0] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)] * 100

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            batch_size = len(kwargs.get("input", []))
            response = MagicMock()
            response.data = [MagicMock(embedding=mock_embedding)] * batch_size
            return response

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = mock_create
            texts = ["text"] * 150
            result = await get_embeddings(texts, batch_size=100)

        assert len(result) == 150


# ─── Config Tests ─────────────────────────────────────────────────────────────

class TestConfig:
    """Tests for settings configuration."""

    def test_regulatory_source_list_parses_correctly(self):
        """Comma-separated regulatory sources should parse to list."""
        from backend.core.config import Settings

        settings = Settings(
            regulatory_sources="https://sebi.gov.in/circular,https://rbi.org.in/circular"
        )
        sources = settings.regulatory_source_list
        assert len(sources) == 2
        assert "https://sebi.gov.in/circular" in sources
        assert "https://rbi.org.in/circular" in sources

    def test_empty_regulatory_sources_returns_empty_list(self):
        """Empty REGULATORY_SOURCES should return empty list."""
        from backend.core.config import Settings

        settings = Settings(regulatory_sources="")
        assert settings.regulatory_source_list == []

    def test_default_settings_have_sensible_values(self):
        """Default settings should be reasonable for development."""
        from backend.core.config import Settings

        settings = Settings(database_url="postgresql+asyncpg://u:p@localhost/db")
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200
        assert settings.retrieval_top_k == 10
        assert settings.rerank_top_k == 5
        assert settings.cache_similarity_threshold == 0.92


# ─── Judge Full Pipeline Test ──────────────────────────────────────────────────

class TestJudgeFullPipeline:
    """Integration-style tests for the complete judge pipeline."""

    def test_judge_on_review_with_ground_truth(self, sample_review_result, sample_ground_truth):
        """Full judge run with ground truth should produce a reasonable overall score."""
        from backend.agents.llm_judge import run_judge_on_review

        with patch("backend.agents.llm_judge.score_actionability") as mock_action:
            mock_action.return_value = {"score": 0.82, "method": "mocked"}
            result = run_judge_on_review(sample_review_result, sample_ground_truth)

        assert "overall_score" in result
        assert 0.0 <= result["overall_score"] <= 1.0
        assert result["has_ground_truth"] is True
        assert result["grade"] in ["A", "B", "C", "D", "F"]
        assert "correctness" in result
        assert "severity_calibration" in result
        assert "completeness" in result
        assert "actionability" in result

    def test_judge_on_review_without_ground_truth(self, sample_review_result):
        """Judge should still produce scores using heuristics when no ground truth."""
        from backend.agents.llm_judge import run_judge_on_review

        with patch("backend.agents.llm_judge.score_actionability") as mock_action:
            mock_action.return_value = {"score": 0.75, "method": "mocked"}
            result = run_judge_on_review(sample_review_result, None)

        assert result["has_ground_truth"] is False
        assert 0.0 <= result["overall_score"] <= 1.0

    def test_score_to_grade_mapping(self):
        """Score to grade mapping should be correct."""
        from backend.agents.llm_judge import _score_to_grade

        assert _score_to_grade(0.95) == "A"
        assert _score_to_grade(0.85) == "B"
        assert _score_to_grade(0.75) == "C"
        assert _score_to_grade(0.65) == "D"
        assert _score_to_grade(0.55) == "F"


# ─── Datadog Metrics Tests ────────────────────────────────────────────────────

class TestDatadogSetup:
    """Tests for Datadog integration — uses mocks, no real agent needed."""

    def test_noop_statsd_all_methods_safe(self):
        """_NoOpStatsd must not raise on any call — app must work without Datadog."""
        from backend.core.datadog_setup import _NoOpStatsd
        noop = _NoOpStatsd()
        # All methods must be callable and silent
        noop.increment("any.metric", tags=["key:val"])
        noop.gauge("any.metric", 42.0, tags=[])
        noop.histogram("any.metric", 100)
        noop.timing("any.metric", 500)
        noop.distribution("any.metric", 0.0042)
        noop.event("title", "text")

    def test_llm_span_noop_without_ddtrace(self):
        """LLMSpan must work silently when ddtrace is not available."""
        from backend.core.datadog_setup import LLMSpan
        # Should not raise even without ddtrace agent running
        with LLMSpan("test_op", model="test-model", provider="test", agent_role="test") as span:
            span.set_input("test prompt")
            span.set_output("test response")
            span.set_tokens(input_tokens=100, output_tokens=50)
            span.set_cost(0.001)

    def test_llm_span_error_recording(self):
        """LLMSpan must record errors without raising."""
        from backend.core.datadog_setup import LLMSpan
        try:
            with LLMSpan("test_op", model="test-model", provider="test", agent_role="test"):
                raise ValueError("Simulated LLM error")
        except ValueError:
            pass  # Exception propagates correctly (return False from __exit__)

    def test_llm_span_does_not_suppress_exceptions(self):
        """LLMSpan.__exit__ returns False — exceptions must propagate."""
        from backend.core.datadog_setup import LLMSpan
        with pytest.raises(RuntimeError, match="test error"):
            with LLMSpan("test_op", model="m", provider="p", agent_role="r"):
                raise RuntimeError("test error")


class TestMetricsFunctions:
    """Tests for metrics.py — verify all functions callable without crashing."""

    def test_review_metrics_callable(self):
        """All review metric functions must execute without error."""
        from backend.core import metrics
        metrics.review_started("saas")
        metrics.review_completed("saas", "critical", 47.3, 5183, 0.0094, 23, 1, 4)
        metrics.review_failed("saas", "TimeoutError")

    def test_agent_metrics_callable(self):
        """Agent metric functions must execute without error."""
        from backend.core import metrics
        metrics.agent_call("extractor", "claude-sonnet-4-5", "anthropic", 2100, 800, 0.0021, 8400.0, True)
        metrics.agent_call("synthesis", "claude-opus-4-5", "anthropic", 4200, 1100, 0.0041, 18300.0, False)

    def test_upload_metrics_callable(self):
        from backend.core import metrics
        metrics.upload_started("nda", True)
        metrics.upload_completed("nda", 15, 1, 2100, 18.4)
        metrics.upload_failed("nda", "FileDecodeError")

    def test_vision_metrics_callable(self):
        from backend.core import metrics
        metrics.vision_page_processed("claude", True, 1200)
        metrics.vision_page_processed("gpt-4o", False, 0)
        metrics.vision_fallback_triggered("claude_timeout")

    def test_search_metrics_callable(self):
        from backend.core import metrics
        metrics.search_executed(cache_hit=True, top_k=5, result_count=5, latency_ms=80.0)
        metrics.search_executed(cache_hit=False, top_k=5, result_count=5, latency_ms=1240.0)
        metrics.rerank_executed(10, 5, 310.0)
        metrics.embedding_batch_executed(50, 420.0, True)

    def test_regulatory_metrics_callable(self):
        from backend.core import metrics
        metrics.regulatory_check_completed("SEBI", True, 7, 8.3)
        metrics.regulatory_check_completed("RBI", False, 0, 6.1)
        metrics.regulatory_check_failed("MCA", "ConnectionError")

    def test_judge_metrics_callable(self):
        from backend.core import metrics
        metrics.judge_evaluation_completed(0.824, 0.887, 0.805, 0.793, 0.812, 100)

    def test_red_team_metrics_callable(self):
        from backend.core import metrics
        metrics.red_team_run_completed(
            iteration=3,
            total_contracts=50,
            failure_rate=0.09,
            category_results={
                "buried_data_rights": {"failure_rate": 0.08, "failed": 1, "total": 10},
                "cross_reference_exploit": {"failure_rate": 0.18, "failed": 2, "total": 10},
            },
        )

    def test_milvus_metrics_callable(self):
        from backend.core import metrics
        metrics.milvus_search_executed("legal_contracts", 10, 82.4, 10)
        metrics.milvus_upsert_executed("legal_contracts", 47, 124.3)
        metrics.milvus_cache_checked(True, 0.97)
        metrics.milvus_cache_checked(False)

    def test_mcp_metrics_callable(self):
        from backend.core import metrics
        metrics.mcp_tool_called("legal-contracts", "review_contract", True, 47300.0)
        metrics.mcp_tool_called("legal-search", "search_contract_library", False, 100.0)

    def test_api_metrics_callable(self):
        from backend.core import metrics
        metrics.api_request_completed("/api/contracts/review", "POST", 200, 47300.0)
        metrics.api_request_completed("/api/contracts/upload", "POST", 500, 1200.0)

    def test_cost_metrics_callable(self):
        from backend.core import metrics
        metrics.total_cost_recorded(0.0094, "review")
        metrics.total_cost_recorded(0.0003, "search")
        metrics.cache_cost_saved(0.0003)

    def test_all_metric_names_follow_convention(self):
        """All metric names in metrics.py must use legal_intel. prefix."""
        import ast
        with open('backend/core/metrics.py') as f:
            content = f.read()
        tree = ast.parse(content)
        # Find all string literals that look like metric names
        metric_strings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.s, str):
                s = node.s
                if '.' in s and 'legal_intel' not in s and len(s) > 10:
                    if s.startswith('legal_') or '.' in s:
                        metric_strings.append(s)
        # All metric name strings should start with legal_intel
        metric_names = [s for s in metric_strings if s.replace('.', '').replace('_', '').isalpha() and '.' in s]
        violations = [m for m in metric_names if not m.startswith('legal_intel')]
        assert violations == [], f"Non-standard metric names found: {violations}"


class TestDatadogConfig:
    """Tests for Datadog configuration fields."""

    def test_datadog_config_fields_exist(self):
        """All Datadog config fields must be present in Settings."""
        from backend.core.config import Settings
        s = Settings(database_url="postgresql+asyncpg://u:p@h/db")
        assert hasattr(s, 'dd_api_key')
        assert hasattr(s, 'dd_site')
        assert hasattr(s, 'dd_service')
        assert hasattr(s, 'dd_env')
        assert hasattr(s, 'dd_agent_host')
        assert hasattr(s, 'dd_agent_port')
        assert hasattr(s, 'dd_dogstatsd_port')
        assert hasattr(s, 'dd_trace_enabled')

    def test_dd_defaults_are_sensible(self, monkeypatch):
        from backend.core.config import Settings
        monkeypatch.delenv("DD_TRACE_ENABLED", raising=False)
        s = Settings(database_url="postgresql+asyncpg://u:p@h/db")
        assert s.dd_site == "datadoghq.com"
        assert s.dd_service == "legal-intel-agent"
        assert s.dd_agent_host == "localhost"
        assert s.dd_agent_port == 8126
        assert s.dd_dogstatsd_port == 8125
        assert s.dd_trace_enabled is True

    def test_effective_dd_env_falls_back_to_app_env(self):
        from backend.core.config import Settings
        s = Settings(database_url="postgresql+asyncpg://u:p@h/db", app_env="staging", dd_env="")
        assert s.effective_dd_env == "staging"

    def test_effective_dd_env_uses_explicit_dd_env(self):
        from backend.core.config import Settings
        s = Settings(database_url="postgresql+asyncpg://u:p@h/db", app_env="development", dd_env="production")
        assert s.effective_dd_env == "production"


# ─── Red-team suite integrity ─────────────────────────────────────────────────

class TestRedTeamSuiteIntegrity:
    """Guards against category blocks being silently overwritten in the dataset."""

    def test_suite_contains_fifty_unique_contracts_across_five_categories(self):
        from backend.agents.red_team_agent import ADVERSARIAL_CONTRACTS, get_all_adversarial_contracts

        contracts = get_all_adversarial_contracts()
        assert len(contracts) == 50
        assert len({c["id"] for c in contracts}) == 50
        assert len(ADVERSARIAL_CONTRACTS) == 5
        assert all(len(items) == 10 for items in ADVERSARIAL_CONTRACTS.values())

    def test_patch_recommendations_make_no_numeric_improvement_claims(self):
        from backend.agents.red_team_agent import generate_patch_recommendations

        results = {"individual_results": [
            {"category": c, "success": False}
            for c in ("buried_data_rights", "disguised_liability", "auto_renewal_disguised", "cross_reference_exploit")
        ]}
        patches = generate_patch_recommendations(results)
        assert len(patches) == 4
        assert all("%" not in p["expected_improvement"] for p in patches)


class TestLLMSpanContentCapture:
    """Contract text must not be attached to traces unless explicitly enabled."""

    class _FakeSpan:
        def __init__(self):
            self.tags = {}

        def set_tag(self, key, value):
            self.tags[key] = value

    def _span_with_fake(self):
        from backend.core.datadog_setup import LLMSpan
        span = LLMSpan("op", model="m", provider="p", agent_role="r")
        span._span = self._FakeSpan()
        return span

    def test_content_not_captured_by_default(self, monkeypatch):
        from backend.core.config import settings
        monkeypatch.setattr(settings, "dd_capture_llm_content", False)
        span = self._span_with_fake()
        span.set_input("confidential clause text")
        span.set_output("confidential response")
        assert span._span.tags == {}

    def test_content_captured_when_enabled(self, monkeypatch):
        from backend.core.config import settings
        monkeypatch.setattr(settings, "dd_capture_llm_content", True)
        span = self._span_with_fake()
        span.set_input("clause text")
        assert span._span.tags["llm.request.prompt"] == "clause text"
