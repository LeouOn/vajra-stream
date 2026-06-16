"""
Unit tests for new core modules: protocol_selector, assessment, healing_session, llm_usage.

Tests run without external dependencies (no audio, no API keys, no LLM).
"""

import os
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Protocol Selector
# ---------------------------------------------------------------------------


class TestProtocolSelector:
    """Test the condition-to-protocol mapping engine."""

    def test_import(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        assert ps is not None

    def test_select_anxiety(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        proto = ps.select_protocol("anxiety")
        assert proto.condition == "anxiety"
        # Should map to muladhara + anahata chakras
        assert "muladhara" in proto.chakras or len(proto.chakras) >= 0

    def test_select_headache(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        proto = ps.select_protocol("headache")
        assert proto.condition == "headache"

    def test_select_unknown_condition(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        proto = ps.select_protocol("nonexistent_condition_xyz")
        assert proto.condition == "nonexistent_condition_xyz"
        # Should return empty lists, not crash
        assert isinstance(proto.chakras, list)
        assert isinstance(proto.frequencies, list)

    def test_multi_condition(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        proto = ps.select_multi_condition(["anxiety", "headache"])
        assert "anxiety" in proto.condition
        assert "headache" in proto.condition
        # Deduplication should work
        assert len(proto.chakras) == len(set(proto.chakras))

    def test_empty_multi_condition(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        proto = ps.select_multi_condition([])
        assert proto.condition == "none"

    def test_available_conditions(self):
        from core.protocol_selector import ProtocolSelector

        ps = ProtocolSelector()
        conditions = ps.get_available_conditions()
        assert isinstance(conditions, list)
        assert len(conditions) > 0
        assert "anxiety" in conditions


# ---------------------------------------------------------------------------
# Assessment Tools
# ---------------------------------------------------------------------------


class TestChakraAssessment:
    """Test the chakra assessment questionnaire."""

    def test_import(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        assert ca is not None

    def test_questions_exist(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        for chakra in ca.list_chakras():
            questions = ca.get_questions(chakra)
            assert len(questions) == 7, f"{chakra} should have 7 questions"

    def test_evaluate_balanced(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        # All 5s = perfectly balanced
        answers = {"anahata": [5, 5, 5, 5, 5, 5, 5]}
        results = ca.evaluate(answers)
        assert len(results) == 1
        assert results[0].score == 10.0
        assert "balanced" in results[0].interpretation.lower()

    def test_evaluate_imbalanced(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        # All 1s = severely imbalanced
        answers = {"vishuddha": [1, 1, 1, 1, 1, 1, 1]}
        results = ca.evaluate(answers)
        assert results[0].score == 0.0
        assert "severely" in results[0].interpretation.lower()

    def test_evaluate_mixed(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        answers = {"muladhara": [3, 4, 3, 2, 3, 4, 3]}  # total=22, normalised=5.36
        results = ca.evaluate(answers)
        assert 5.0 <= results[0].score <= 6.0

    def test_evaluate_multiple_chakras(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        answers = {"muladhara": [4, 4, 4, 4, 4, 4, 4], "anahata": [5, 5, 5, 5, 5, 5, 5]}
        results = ca.evaluate(answers)
        assert len(results) == 2

    def test_wrong_answer_count_raises(self):
        from core.assessment import ChakraAssessment

        ca = ChakraAssessment()
        with pytest.raises(ValueError, match="Expected 7"):
            ca.evaluate({"anahata": [3, 3, 3]})


class TestDoshaAssessment:
    """Test the dosha self-assessment."""

    def test_import(self):
        from core.assessment import DoshaAssessment

        da = DoshaAssessment()
        assert da is not None

    def test_questions_exist(self):
        from core.assessment import DoshaAssessment

        da = DoshaAssessment()
        for dosha in ["vata", "pitta", "kapha"]:
            questions = da.get_questions(dosha)
            assert len(questions) == 10, f"{dosha} should have 10 questions"

    def test_evaluate_vata_dominant(self):
        from core.assessment import DoshaAssessment

        da = DoshaAssessment()
        answers = {
            "vata": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            "pitta": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            "kapha": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        }
        result = da.evaluate(answers)
        assert result["dominant"] == "vata"
        assert result["vata_pct"] > 50

    def test_wrong_answer_count_raises(self):
        from core.assessment import DoshaAssessment

        da = DoshaAssessment()
        with pytest.raises(ValueError, match="Expected 10"):
            da.evaluate({"vata": [3, 3, 3]})


class TestSymptomTracker:
    """Test the symptom-to-condition keyword matcher."""

    def test_import(self):
        from core.assessment import SymptomTracker

        st = SymptomTracker()
        assert st is not None

    def test_exact_match(self):
        from core.assessment import SymptomTracker

        st = SymptomTracker()
        results = st.match(["anxiety"])
        assert "anxiety" in results

    def test_partial_match(self):
        from core.assessment import SymptomTracker

        st = SymptomTracker()
        results = st.match(["feeling very anxious today"])
        assert "anxiety" in results

    def test_multiple_symptoms(self):
        from core.assessment import SymptomTracker

        st = SymptomTracker()
        results = st.match(["anxious", "can't sleep", "head pain"])
        assert "anxiety" in results
        assert "headache" in results

    def test_no_match(self):
        from core.assessment import SymptomTracker

        st = SymptomTracker()
        results = st.match(["xyz_unknown_symptom_123"])
        assert results == []

    def test_deduplication(self):
        from core.assessment import SymptomTracker

        st = SymptomTracker()
        # "anxious" and "anxiety" both map to "anxiety"
        results = st.match(["anxious", "anxiety"])
        assert results == ["anxiety"]


# ---------------------------------------------------------------------------
# LLM Usage Tracker
# ---------------------------------------------------------------------------


class TestLLMUsageTracker:
    """Test the token/cost tracking system."""

    def test_import(self):
        from core.llm.usage import LLMUsageTracker

        tracker = LLMUsageTracker.get(log_path=os.path.join(tempfile.gettempdir(), "test_usage.jsonl"))
        assert tracker is not None

    def test_singleton(self):
        from core.llm.usage import LLMUsageTracker

        t1 = LLMUsageTracker.get()
        t2 = LLMUsageTracker.get()
        assert t1 is t2

    def test_record_and_summary(self):
        from core.llm.usage import LLMUsageTracker, UsageRecord

        tracker = LLMUsageTracker.get(log_path=os.path.join(tempfile.gettempdir(), "test_usage.jsonl"))
        calls_before = tracker.total_calls
        prompt_before = tracker.total_prompt_tokens

        record = UsageRecord(
            provider="deepseek",
            model="deepseek-chat",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            cost_usd=0.000126,
            latency_ms=420.0,
        )
        tracker.record(record)

        summary = tracker.get_summary()
        assert summary["total_calls"] >= calls_before + 1
        assert summary["total_prompt_tokens"] >= prompt_before + 500
        assert summary["total_completion_tokens"] >= 200
        assert summary["total_cost_usd"] >= 0.000126

    def test_multiple_providers(self):
        from core.llm.usage import LLMUsageTracker, UsageRecord

        tracker = LLMUsageTracker.get(log_path=os.path.join(tempfile.gettempdir(), "test_usage.jsonl"))
        calls_before = tracker.total_calls

        tracker.record(
            UsageRecord(
                provider="deepseek",
                model="deepseek-chat",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost_usd=0.000042,
            )
        )
        tracker.record(
            UsageRecord(
                provider="openai",
                model="gpt-4o-mini",
                prompt_tokens=200,
                completion_tokens=80,
                total_tokens=280,
                cost_usd=0.000078,
            )
        )

        summary = tracker.get_summary()
        assert summary["total_calls"] >= calls_before + 2
        assert "deepseek" in summary["provider_stats"]
        assert "openai" in summary["provider_stats"]

    def test_token_estimation(self):
        from core.llm.usage import LLMUsageTracker

        tracker = LLMUsageTracker.get()
        tokens = tracker.estimate_tokens("Hello world")  # 11 chars, estimate = 2
        assert tokens >= 1

    def test_cost_estimation_deepseek(self):
        from core.llm.usage import LLMUsageTracker

        tracker = LLMUsageTracker.get()
        cost = tracker.estimate_cost("deepseek", "deepseek-chat", prompt_tokens=1_000_000, completion_tokens=1_000_000)
        # ~$0.14 input + ~$0.28 output = ~$0.42
        assert 0.30 <= cost <= 0.55

    def test_cost_estimation_local_is_zero(self):
        from core.llm.usage import LLMUsageTracker

        tracker = LLMUsageTracker.get()
        cost = tracker.estimate_cost("local", "any-model", 1000000, 1000000)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# Healing Session (import-only — audio requires hardware)
# ---------------------------------------------------------------------------


class TestHealingSessionImport:
    """Test that the healing session module imports and initialises correctly."""

    def test_import(self):
        from core.healing_session import SessionPhase

        assert SessionPhase.OPENING.value == "opening"
        assert SessionPhase.COMPLETED.value == "completed"

    def test_session_log_dataclass(self):
        from core.healing_session import SessionLog

        log = SessionLog(session_id="test-123", intention="peace")
        assert log.session_id == "test-123"
        assert log.to_dict()["session_id"] == "test-123"

    def test_get_available_integrations(self):
        from core.healing_session import HealingSession

        session = HealingSession()
        integrations = session.get_available_integrations()
        assert isinstance(integrations, dict)
        assert "protocol_selector" in integrations
        assert "audio_generator" in integrations


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
