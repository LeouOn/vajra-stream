"""Tests for the RadionicsOperator's prepare_crystal_broadcast method.

Verifies that the LLM-backed radionics orchestrator can take a free-text
intention and produce a complete crystal bowl broadcast configuration
(Solfeggio carrier frequencies + prayer bowl parameters) via the
core.rate_to_audio bridge.
"""

import pytest
from unittest.mock import MagicMock

from core.rate_to_audio import SOLFEGGIO_FREQUENCIES
from modules.radionics_operator import RadionicsOperator


@pytest.fixture
def operator():
    """Create a RadionicsOperator with a mock LLM (no real API calls)."""
    op = RadionicsOperator(
        container=None,
        event_bus=None,
        llm=None,
    )
    return op


class TestPrepareCrystalBroadcast:
    def test_returns_broadcast_config_with_carrier_frequencies(self, operator):
        """The result must include a CarrierFrequencySet with
        Solfeggio-aligned frequencies (7.83 Schumann base is always
        prepended by the rate_to_audio bridge)."""
        result = operator.prepare_crystal_broadcast(
            intention="Heal my friend with chronic back pain",
            duration_minutes=10,
        )

        assert "carriers" in result
        assert "rate" in result
        assert "solfeggio_names" in result
        assert "broadcast_config" in result

        # The base Solfeggio tone is always the Schumann 7.83 Hz
        assert result["carriers"].frequencies[0] == 7.83

        # All remaining frequencies must be valid Solfeggio tones
        for f in result["carriers"].frequencies[1:]:
            assert f in SOLFEGGIO_FREQUENCIES

    def test_broadcast_config_has_all_required_fields(self, operator):
        """The broadcast_config dict must contain everything the crystal
        broadcaster needs: intention, duration, rate_values, potency,
        frequencies, amplitude, prayer_bowl flag."""
        result = operator.prepare_crystal_broadcast(
            intention="Send love and protection to all beings",
            duration_minutes=30,
        )

        config = result["broadcast_config"]
        required = [
            "intention", "duration_minutes", "rate_values", "potency",
            "frequencies", "solfeggio_names", "amplitude",
            "overtone_richness", "prayer_bowl",
        ]
        for field in required:
            assert field in config, f"Missing required field: {field}"

        assert config["intention"] == "Send love and protection to all beings"
        assert config["duration_minutes"] == 30
        assert config["prayer_bowl"] is True
        assert config["potency"] == 0.8
        assert 0.15 <= config["amplitude"] <= 0.50

    def test_fallback_path_produces_valid_carriers(self, operator):
        """Even without a real LLM, the method should work via the
        fallback path and produce valid Solfeggio carriers."""
        result = operator.prepare_crystal_broadcast(
            intention="Quick test intention",
            duration_minutes=5,
        )

        # Should still produce valid Solfeggio carriers
        assert result["carriers"].frequencies[0] == 7.83
        assert all(f in SOLFEGGIO_FREQUENCIES for f in result["carriers"].frequencies[1:])

        # Rate values must be valid (0-100)
        for v in result["rate"]:
            assert 0 <= v <= 100

    def test_amplitude_in_valid_range(self, operator):
        """Amplitude should be between min and max from the bridge."""
        result = operator.prepare_crystal_broadcast(
            intention="Amplitude test", duration_minutes=5,
        )
        assert 0.15 <= result["carriers"].amplitude <= 0.50

    def test_rate_is_a_list_of_dial_values(self, operator):
        """The rate must be a list of dial values (2-5 elements depending
        on the analysis path — fallback uses 3 dials, database may use
        more)."""
        result = operator.prepare_crystal_broadcast(
            intention="Test rate format", duration_minutes=5,
        )
        assert isinstance(result["rate"], list)
        assert 2 <= len(result["rate"]) <= 5
        for v in result["rate"]:
            assert isinstance(v, (int, float))
            assert 0 <= v <= 100

    def test_event_published_to_event_bus(self):
        """When event_bus is set, prepare_crystal_broadcast should
        publish a BroadcastStarted event."""
        mock_bus = MagicMock()
        op = RadionicsOperator(container=None, event_bus=mock_bus, llm=None)

        op.prepare_crystal_broadcast(
            intention="Test event publishing",
            duration_minutes=5,
        )
        assert mock_bus.publish.called
        call_args = mock_bus.publish.call_args
        event = call_args[0][0]
        assert hasattr(event, "frequencies")
        assert hasattr(event, "session_id")
        assert event.frequencies[0] == 7.83  # Schumann base

    def test_session_history_recorded(self, operator):
        """prepare_crystal_broadcast should record to session history."""
        operator.prepare_crystal_broadcast(
            intention="Test history",
            duration_minutes=5,
        )
        # SessionContext stores events in history
        assert len(operator._session.history) >= 1

    def test_solfeggio_names_match_frequencies(self, operator):
        """Each frequency in the result must have a matching name."""
        result = operator.prepare_crystal_broadcast(
            intention="Test names matching",
            duration_minutes=5,
        )
        assert len(result["carriers"].frequencies) == len(result["solfeggio_names"])
        # First name is always Schumann
        assert result["solfeggio_names"][0] == "Schumann Base"
