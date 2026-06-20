"""
Tests for RadionicsOperator — all methods tested via fallback paths (no LLM required).

These tests verify the operator's logic, dispatch, and fallback behavior.
"""

import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def operator():
    """Create a RadionicsOperator without LLM or container."""
    from infrastructure.event_bus import EnhancedEventBus
    from modules.radionics_operator import RadionicsOperator

    # Wave 4 Task 23 / ADR 003: event_bus is now required injection (no
    # silent fallback). Mint a private bus for these isolated unit tests.
    bus = EnhancedEventBus()
    op = RadionicsOperator(event_bus=bus, llm=MagicMock())  # Mock LLM to force fallback paths
    op._llm.client = None
    op._llm.local_model = None
    yield op
    bus.clear()


@pytest.fixture
def operator_with_container():
    """Create an operator with a container for dispatch tests."""
    from container import Container
    from modules.radionics_operator import RadionicsOperator

    c = Container()
    c._initialized = False
    c.__init__()
    op = RadionicsOperator(container=c, event_bus=c.event_bus, llm=MagicMock())
    op._llm.client = None
    op._llm.local_model = None
    return op


# ============================================================================
# Intention Analysis
# ============================================================================


class TestIntentionAnalysis:
    def test_analyze_healing_intention(self, operator):
        result = operator.analyze_intention("Help my friend with chronic back pain")
        assert "analysis" in result
        assert "suggested_rates" in result
        assert "recommended_frequency" in result
        assert result["recommended_frequency"] == 528  # "heal" keyword → 528 Hz
        assert len(result["suggested_rates"]) >= 1

    def test_analyze_fear_intention(self, operator):
        result = operator.analyze_intention("Release fear and anxiety")
        assert result["recommended_frequency"] == 396  # "fear" keyword → 396 Hz

    def test_analyze_relationship_intention(self, operator):
        result = operator.analyze_intention("Fix my relationship with my partner")
        assert result["recommended_frequency"] == 639  # "relationship" → 639 Hz

    def test_analyze_empty_intention(self, operator):
        result = operator.analyze_intention("")
        assert "analysis" in result
        assert "suggested_rates" in result


# ============================================================================
# Rate Suggestions
# ============================================================================


class TestRateSuggestions:
    def test_suggest_rates_returns_signature(self, operator):
        result = operator.suggest_rates("chronic pain")
        assert "source" in result
        assert result["source"] in ("database", "algorithmic")

    def test_suggest_rates_with_count(self, operator):
        result = operator.suggest_rates("test", count=3)
        if result["source"] == "algorithmic":
            assert "signature_rate" in result
            assert "balancing_rates" in result


# ============================================================================
# Insights
# ============================================================================


class TestInsights:
    def test_insight_empty_state(self, operator):
        result = operator.generate_insight()
        assert result["type"] in ("idle", "rule_based")
        # Fallback returns generic message for empty state — just verify it's a string
        assert isinstance(result["insight"], str)
        assert len(result["insight"]) > 0

    def test_insight_with_high_gv(self, operator):
        result = operator.generate_insight({"gv_measurement": 750})
        assert "high" in result["insight"].lower() or "strong" in result["insight"].lower()

    def test_insight_with_floating_needle(self, operator):
        result = operator.generate_insight({"rng_state": {"state": "floating"}})
        assert "floating" in result["insight"].lower() or "release" in result["insight"].lower()

    def test_insight_with_rock_slam(self, operator):
        result = operator.generate_insight({"rng_state": {"state": "rock_slam"}})
        assert "rock" in result["insight"].lower() or "resistance" in result["insight"].lower()


# ============================================================================
# Trend Analysis
# ============================================================================


class TestTrendAnalysis:
    def test_trends_no_data(self, operator):
        result = operator.analyze_trends([])
        assert "No session history" in result["analysis"]
        assert result["patterns"] == []

    def test_trends_with_data(self, operator):
        history = [
            {"name": "Session 1", "frequency": 528, "duration": 1800, "status": "completed"},
            {"name": "Session 2", "frequency": 528, "duration": 3600, "status": "completed"},
            {"name": "Session 3", "frequency": 396, "duration": 900, "status": "completed"},
        ]
        result = operator.analyze_trends(history)
        assert "analysis" in result
        # Fallback trends uses most common frequency
        assert result["most_used_frequency"] in (528, 396)
        assert len(result["recommendations"]) > 0


# ============================================================================
# Blessing Loop
# ============================================================================


class TestBlessingLoop:
    def test_start_blessing_loop(self, operator_with_container):
        op = operator_with_container
        result = op.start_blessing_loop("all beings", interval_seconds=5)
        assert result["status"] == "started"
        assert "first_blessing" in result
        assert result["first_blessing"] is not None
        assert "text" in result["first_blessing"]

    def test_blessing_loop_status(self, operator_with_container):
        op = operator_with_container
        op.start_blessing_loop("peace", 5)
        status = op.get_blessing_loop_status()
        assert status["active"] is True
        assert status["intention"] == "peace"

    def test_generate_next_blessing(self, operator_with_container):
        op = operator_with_container
        op.start_blessing_loop("healing", 5)
        blessing = op.generate_next_blessing()
        assert blessing is not None
        assert "text" in blessing
        assert len(blessing["text"]) > 0

    def test_stop_blessing_loop(self, operator_with_container):
        op = operator_with_container
        op.start_blessing_loop("test", 5)
        result = op.stop_blessing_loop()
        assert result["status"] == "stopped"
        assert result["blessings_generated"] >= 1

    def test_blessing_stream(self, operator_with_container):
        op = operator_with_container
        op.start_blessing_loop("test", 5)
        blessings = op.get_blessing_stream()
        assert len(blessings) >= 1
        # Fetch since index 0
        since_zero = op.get_blessing_stream(since=0)
        assert len(since_zero) >= 1
        op.stop_blessing_loop()

    @pytest.mark.asyncio
    async def test_blessing_loop_async_task(self, operator_with_container):
        op = operator_with_container
        # We start the blessing loop with a very short interval for testing
        result = op.start_blessing_loop("peace", interval_seconds=0.01)
        assert result["status"] == "started"
        assert op._blessing_loop_active is True
        assert op._blessing_loop_task is not None
        assert not op._blessing_loop_task.done()

        # Let the task tick multiple times in background
        await asyncio.sleep(0.05)
        # Verify that more blessings were generated (first one immediate, and then at least one tick)
        assert len(op._blessing_stream) > 1

        # Stop the blessing loop and check task cancellation
        stop_result = op.stop_blessing_loop()
        assert stop_result["status"] == "stopped"
        assert op._blessing_loop_active is False
        assert op._blessing_loop_task is None


# ============================================================================
# Autonomous Mode
# ============================================================================


class TestAutonomousMode:
    def test_start_autonomous(self, operator):
        result = operator.start_autonomous_mode(interval_seconds=60)
        assert result["status"] == "started"
        assert "message" in result
        operator.stop_autonomous_mode()

    def test_autonomous_status(self, operator):
        operator.start_autonomous_mode(60)
        status = operator.get_autonomous_status()
        assert status["active"] is True
        assert status["interval_seconds"] == 60
        operator.stop_autonomous_mode()

    def test_stop_autonomous(self, operator):
        operator.start_autonomous_mode(60)
        result = operator.stop_autonomous_mode()
        assert result["status"] == "stopped"

    def test_approve_dismiss_suggestions(self, operator):
        operator.start_autonomous_mode(60)
        operator._autonomous_suggestions = [
            {
                "title": "Test Suggestion",
                "target": "Test",
                "action": "broadcast_healing",
                "frequency": 528,
                "duration_minutes": 30,
            }
        ]
        approved = operator.approve_suggestion(0)
        assert approved["status"] in ("executed", "error")

        operator._autonomous_suggestions = [{"title": "Test"}]
        dismissed = operator.dismiss_suggestion(0)
        assert dismissed["status"] == "dismissed"
        operator.stop_autonomous_mode()

    @pytest.mark.asyncio
    async def test_autonomous_loop_async_task(self, operator):
        # We start autonomous mode with a short interval
        result = operator.start_autonomous_mode(interval_seconds=1)
        assert result["status"] == "started"
        assert operator._autonomous_active is True
        assert operator._autonomous_task is not None
        assert not operator._autonomous_task.done()

        # Stop autonomous mode and check task cancellation
        stop_result = operator.stop_autonomous_mode()
        assert stop_result["status"] == "stopped"
        assert operator._autonomous_active is False
        assert operator._autonomous_task is None


# ============================================================================
# Tool Dispatcher
# ============================================================================


class TestToolDispatcher:
    def test_dispatch_get_chakra_info(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("get_chakra_info", {})
        assert "chakras" in result
        assert len(result["chakras"]) == 7

    def test_dispatch_get_meridian_info(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("get_meridian_info", {})
        assert "meridians" in result
        assert len(result["meridians"]) == 12

    def test_dispatch_get_available_intentions(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("get_available_intentions", {})
        assert "intentions" in result
        assert len(result["intentions"]) > 0

    def test_dispatch_get_sacred_frequencies(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("get_sacred_frequencies", {})
        assert "solfeggio" in result or len(result) > 0

    def test_dispatch_text_to_rate(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("text_to_rate", {"text": "test"})
        assert "values" in result
        assert len(result["values"]) == 3

    def test_dispatch_measure_gv(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("measure_general_vitality", {"subject": "test"})
        assert "gv_mean" in result
        assert 0 <= result["gv_mean"] <= 1000

    def test_dispatch_search_knowledge(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("search_knowledge", {"query": "heart"})
        assert "results" in result
        assert "count" in result

    def test_dispatch_get_world_context(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("get_world_context", {})
        assert "events_count" in result
        assert "planetary_hour" in result

    def test_dispatch_unknown_tool(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch("nonexistent_tool", {})
        assert "error" in result

    def test_dispatch_broadcast_healing(self, operator_with_container):
        result = operator_with_container.dispatcher.dispatch(
            "broadcast_healing", {"target_name": "Test Target", "duration_minutes": 1}
        )
        assert "session_id" in result
        assert result["target"] == "Test Target"


# ============================================================================
# Operator Status
# ============================================================================


class TestOperatorStatus:
    def test_status_no_llm(self, operator):
        status = operator.get_status()
        # LLMIntegration object exists but has no client — may report True or False
        assert status["container_available"] is False
        assert status["tools_count"] > 25  # 29 tools now
        assert status["autonomous_mode"] is False
        assert status["blessing_loop_active"] is False

    def test_status_with_llm(self, operator_with_container):
        status = operator_with_container.get_status()
        assert status["container_available"] is True
        assert status["tools_count"] > 25


# ============================================================================
# World Context (network-disabled fallback)
# ============================================================================


class TestWorldContext:
    def test_context_compilation_fallback(self):
        from core.internet_context import compile_world_context

        ctx = compile_world_context(include_disasters=False, include_headlines=False, include_astrology=False)
        assert ctx.events == []
        assert ctx.disasters == []
        # Should still give planetary hour
        assert ctx.planetary_hour != ""

    def test_context_formatting(self):
        from core.internet_context import compile_world_context, format_context_for_llm

        ctx = compile_world_context(include_disasters=False, include_headlines=False)
        formatted = format_context_for_llm(ctx)
        assert isinstance(formatted, str)
        # With disasters and headlines disabled but astrology still enabled,
        # should have at least the celestial timing section
        if ctx.planetary_hour:
            assert "Celestial Timing" in formatted or formatted == ""
        # Even empty context should be a valid string
        assert formatted is not None


# ============================================================================
# Knowledge Index
# ============================================================================


class TestKnowledgeIndex:
    def test_index_builds(self):
        from core.knowledge_index import get_knowledge_index

        idx = get_knowledge_index()
        stats = idx.get_stats()
        assert stats["total_chunks"] > 0
        assert stats["built"] is True

    def test_search_finds_results(self):
        from core.knowledge_index import search_knowledge

        results = search_knowledge("heart", top_k=3)
        assert len(results) > 0
        assert "text" in results[0]
        assert "score" in results[0]

    def test_search_category_filter(self):
        from core.knowledge_index import search_knowledge

        results = search_knowledge("om", top_k=3, category="mantra")
        assert len(results) >= 0  # May or may not find, but shouldn't error
