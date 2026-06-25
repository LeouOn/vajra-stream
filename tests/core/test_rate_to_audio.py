"""Tests for core.rate_to_audio — the radionics rate to prayer bowl bridge."""

from core.rate_to_audio import (
    CarrierFrequencySet,
    SOLFEGGIO_FREQUENCIES,
    SCHUMANN_BASE_HZ,
    map_rate_to_carriers,
    _snap_to_solfeggio,
    _potency_to_amplitude,
    _potency_to_overtone_richness,
)


class TestSnapToSolfeggio:
    def test_zero_maps_to_first_tone(self):
        assert _snap_to_solfeggio(0) == 396.0

    def test_max_maps_to_last_tone(self):
        assert _snap_to_solfeggio(100) == 963.0

    def test_midpoint_maps_to_middle_tone(self):
        # 50/100 * 7 segments = 3.5 → index 3 → 639.0
        assert _snap_to_solfeggio(50) == 639.0

    def test_clamps_negative(self):
        assert _snap_to_solfeggio(-10) == 396.0

    def test_clamps_over_100(self):
        assert _snap_to_solfeggio(150) == 963.0

    def test_all_seven_segments(self):
        """Every segment should map to a valid Solfeggio tone."""
        for i in range(7):
            dial = int(i * 100 / 7) + 1
            result = _snap_to_solfeggio(dial)
            assert result in SOLFEGGIO_FREQUENCIES


class TestPotencyMapping:
    def test_zero_potency_minimum_amplitude(self):
        assert _potency_to_amplitude(0.0) == 0.15

    def test_max_potency_maximum_amplitude(self):
        assert _potency_to_amplitude(1.0) == 0.50

    def test_mid_potency_midpoint(self):
        mid = _potency_to_amplitude(0.5)
        assert 0.30 < mid < 0.35  # ~0.325

    def test_overtone_zero(self):
        assert _potency_to_overtone_richness(0.0) == 0.3

    def test_overtone_max(self):
        assert _potency_to_overtone_richness(1.0) == 1.0


class TestMapRateToCarriers:
    def test_single_dial_value(self):
        result = map_rate_to_carriers([50], potency=0.8)
        assert isinstance(result, CarrierFrequencySet)
        assert len(result.frequencies) == 2  # Schumann + one Solfeggio
        assert result.frequencies[0] == SCHUMANN_BASE_HZ
        assert result.frequencies[1] in SOLFEGGIO_FREQUENCIES

    def test_multiple_dial_values(self):
        result = map_rate_to_carriers([10, 50, 90], potency=0.5)
        assert len(result.frequencies) >= 3  # Schumann + at least 2 unique
        assert result.frequencies[0] == SCHUMANN_BASE_HZ

    def test_duplicate_dial_values_deduplicated(self):
        """If two dials snap to the same Solfeggio, only one carrier."""
        result = map_rate_to_carriers([5, 10, 12], potency=0.5)
        # All three map to 396.0 (first segment), so only 1 unique + Schumann
        assert len(result.frequencies) == 2

    def test_always_includes_schumann(self):
        result = map_rate_to_carriers([50], potency=0.5)
        assert SCHUMANN_BASE_HZ in result.frequencies

    def test_solfeggio_names_populated(self):
        result = map_rate_to_carriers([50], potency=0.5)
        assert len(result.solfeggio_names) == len(result.frequencies)
        assert result.solfeggio_names[0] == "Schumann Base"

    def test_empty_rate_values(self):
        """Empty rate list still produces Schumann base."""
        result = map_rate_to_carriers([], potency=0.5)
        assert result.frequencies == [SCHUMANN_BASE_HZ]

    def test_potency_affects_amplitude(self):
        low = map_rate_to_carriers([50], potency=0.1)
        high = map_rate_to_carriers([50], potency=0.9)
        assert high.amplitude > low.amplitude

    def test_rate_values_preserved(self):
        result = map_rate_to_carriers([42, 60, 77], potency=0.85)
        assert result.rate_values == [42, 60, 77]

    def test_iterable(self):
        result = map_rate_to_carriers([50], potency=0.5)
        freqs = list(result)
        assert SCHUMANN_BASE_HZ in freqs

    def test_all_frequencies_are_valid_solfeggio_or_schumann(self):
        result = map_rate_to_carriers([5, 20, 35, 50, 65, 80, 95], potency=1.0)
        for f in result.frequencies:
            assert f == SCHUMANN_BASE_HZ or f in SOLFEGGIO_FREQUENCIES
