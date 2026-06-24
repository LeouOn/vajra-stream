"""
Tests for ``core.intelligent_composer`` — harmonic audio composition.

Covers the public API:
- :class:`HarmonicRelationship` enum — five documented categories.
- :class:`IntelligentComposer.analyze_harmonic_relationship` — perfect fifth,
  octave, unison, major second (mild dissonance), major seventh (sharp
  dissonance), and out-of-octave normalisation.
- :class:`IntelligentComposer.select_harmonic_frequencies` — short list
  passthrough, octave rejection of dissonant neighbours, min_consonance
  threshold behaviour.
- :class:`IntelligentComposer.create_spatial_panning` — documented positions
  for 1, 2, 3, 4 and N>4 frequencies.
- :class:`IntelligentComposer.compose_frequency_pattern` — all four
  composition patterns return normalised non-empty waveforms; unknown
  pattern_type falls back to ``"evolving"``.
- :class:`AudioOrchestrator.create_blessing_composition` /
  ``create_chakra_healing_composition`` — return numpy arrays of the
  correct length; ``HARMONIC_BLESSING_SETS`` export contains the
  documented keys.
- :class:`IntelligentComposer.create_intention_modulation` — same intention
  produces the same modulated waveform (seeded by intention text).

No audio hardware is touched; numpy arrays are verified for shape and
range only.
"""
from __future__ import annotations

import numpy as np
import pytest

from core.intelligent_composer import (
    AudioOrchestrator,
    HARMONIC_BLESSING_SETS,
    HarmonicRelationship,
    IntelligentComposer,
)


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.intelligent_composer as mod

    expected = (
        "HarmonicRelationship",
        "IntelligentComposer",
        "AudioOrchestrator",
        "HARMONIC_BLESSING_SETS",
    )
    for name in expected:
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. HarmonicRelationship enum — five categories
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_harmonic_relationship_has_five_documented_categories():
    """The enum exposes exactly the five documented relationship categories."""
    names = {m.name for m in HarmonicRelationship}
    assert names == {
        "PERFECT_CONSONANCE",
        "IMPERFECT_CONSONANCE",
        "MILD_DIATONIC_DISONANCE",
        "SHARP_DISONANCE",
        "EXTREME_DISONANCE",
    }


# ---------------------------------------------------------------------------
# 3. IntelligentComposer.analyze_harmonic_relationship
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_analyze_harmonic_relationship_perfect_fifth_is_perfect_consonance():
    """A 2:3 ratio (a perfect fifth) is the textbook perfect consonance."""
    composer = IntelligentComposer(sample_rate=44100)
    rel, score = composer.analyze_harmonic_relationship(220.0, 330.0)  # 3:2

    assert rel == HarmonicRelationship.PERFECT_CONSONANCE
    # Score is 1.0 when ratio lands exactly on a consonant reference.
    assert score == pytest.approx(1.0)


@pytest.mark.unit
def test_analyze_harmonic_relationship_octave_and_unison_are_perfect_consonance():
    """Both the octave (2:1) and unison (1:1) classify as perfect consonance."""
    composer = IntelligentComposer(sample_rate=44100)

    rel_octave, _ = composer.analyze_harmonic_relationship(220.0, 440.0)
    rel_unison, _ = composer.analyze_harmonic_relationship(220.0, 220.0)

    assert rel_octave == HarmonicRelationship.PERFECT_CONSONANCE
    assert rel_unison == HarmonicRelationship.PERFECT_CONSONANCE


@pytest.mark.unit
def test_analyze_harmonic_relationship_mild_and_sharp_dissonance_categories():
    """A 9:8 ratio is MILD_DIATONIC_DISONANCE, 15:8 is SHARP_DISONANCE."""
    composer = IntelligentComposer(sample_rate=44100)

    # 9:8 = 1.125 → MILD_DIATONIC_DISONANCE
    rel_mild, _ = composer.analyze_harmonic_relationship(440.0, 440.0 * 9 / 8)
    # 15:8 = 1.875 → SHARP_DISONANCE
    rel_sharp, _ = composer.analyze_harmonic_relationship(440.0, 440.0 * 15 / 8)

    assert rel_mild == HarmonicRelationship.MILD_DIATONIC_DISONANCE
    assert rel_sharp == HarmonicRelationship.SHARP_DISONANCE


@pytest.mark.unit
def test_analyze_harmonic_relationship_normalises_ratios_above_octave():
    """A 4:1 ratio is reduced to a 2:1 octave (still PERFECT_CONSONANCE)."""
    composer = IntelligentComposer(sample_rate=44100)

    rel, _ = composer.analyze_harmonic_relationship(110.0, 440.0)  # ratio 4.0
    # Reduced to 2.0 (octave) within the analysis loop.
    assert rel == HarmonicRelationship.PERFECT_CONSONANCE


# ---------------------------------------------------------------------------
# 4. IntelligentComposer.select_harmonic_frequencies
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_select_harmonic_frequencies_passthrough_for_short_lists():
    """Lists with <= 2 entries are returned unchanged (no filtering)."""
    composer = IntelligentComposer(sample_rate=44100)

    empty = composer.select_harmonic_frequencies([])
    single = composer.select_harmonic_frequencies([528.0])
    pair = composer.select_harmonic_frequencies([440.0, 660.0])

    assert empty == []
    assert single == [528.0]
    # Two consonant (3:2) frequencies are kept together.
    assert pair == [440.0, 660.0]


@pytest.mark.unit
def test_select_harmonic_frequencies_filters_dissonant_neighbours():
    """A frequency highly dissonant with the seed (score < min_consonance) is
    dropped from the selection."""
    composer = IntelligentComposer(sample_rate=44100)

    # 220 and 330 form a perfect fifth (consonant).
    # 220 * sqrt(2) ≈ 311.13 — ratio to 220 is ~1.4142, far from any
    # consonant reference; consonance score should be <= 0.5.
    dissonant_neighbour = 220.0 * (2 ** 0.5)
    selected = composer.select_harmonic_frequencies(
        [220.0, 330.0, dissonant_neighbour],
        min_consonance=0.6,
    )

    assert 220.0 in selected
    assert 330.0 in selected
    assert dissonant_neighbour not in selected


@pytest.mark.unit
def test_select_harmonic_frequencies_with_permissive_threshold_keeps_all():
    """With min_consonance = 0.0 every frequency is kept (all scores >= 0)."""
    composer = IntelligentComposer(sample_rate=44100)

    freqs = [220.0, 330.0, 440.0, 555.0]
    selected = composer.select_harmonic_frequencies(freqs, min_consonance=0.0)
    assert selected == freqs


# ---------------------------------------------------------------------------
# 5. IntelligentComposer.create_spatial_panning
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_spatial_panning_returns_documented_positions():
    """The 1/2/3/4-frequency cases return the documented pan positions."""
    composer = IntelligentComposer(sample_rate=44100)

    assert composer.create_spatial_panning(1) == [0.0]
    assert composer.create_spatial_panning(2) == [-0.5, 0.5]
    assert composer.create_spatial_panning(3) == [-0.7, 0.0, 0.7]
    assert composer.create_spatial_panning(4) == [-0.8, -0.2, 0.2, 0.8]


@pytest.mark.unit
def test_create_spatial_panning_distributes_many_frequencies_evenly():
    """For >=5 frequencies the positions are evenly distributed across [-0.9, 0.9]."""
    composer = IntelligentComposer(sample_rate=44100)

    n = 6
    pans = composer.create_spatial_panning(n)
    assert len(pans) == n
    # Endpoints should hit -0.9 and +0.9 (the documented spread).
    assert pans[0] == pytest.approx(-0.9)
    assert pans[-1] == pytest.approx(0.9)
    # All values lie in [-0.9, 0.9].
    for p in pans:
        assert -0.9 <= p <= 0.9


# ---------------------------------------------------------------------------
# 6. IntelligentComposer.compose_frequency_pattern
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compose_frequency_pattern_all_documented_patterns_return_audio():
    """Every documented pattern returns a non-empty numpy waveform of the
    expected duration in samples."""
    composer = IntelligentComposer(sample_rate=1000)  # tiny SR for fast tests

    duration = 0.5  # → 500 samples
    freqs = [220.0, 330.0]

    for pattern in ("alternating", "layered", "evolving", "harmonic_chords"):
        wave = composer.compose_frequency_pattern(freqs, duration=duration, pattern_type=pattern)
        assert isinstance(wave, np.ndarray), f"{pattern}: not an ndarray"
        assert wave.ndim == 1, f"{pattern}: not 1-D"
        # +- a handful of samples due to rounding inside linspace
        assert abs(len(wave) - duration * 1000) < 5, f"{pattern}: wrong length"
        # Normalised: peak magnitude should be ~1.0 (or 0 for a degenerate waveform).
        peak = float(np.max(np.abs(wave))) if len(wave) else 0.0
        assert peak <= 1.0 + 1e-6, f"{pattern}: not normalised (peak={peak})"


@pytest.mark.unit
def test_compose_frequency_pattern_unknown_type_falls_back_to_evolving():
    """An unknown ``pattern_type`` silently falls back to ``"evolving"``."""
    composer = IntelligentComposer(sample_rate=1000)
    freqs = [220.0, 330.0]
    duration = 0.2

    wave_fallback = composer.compose_frequency_pattern(freqs, duration=duration, pattern_type="not-a-pattern")
    wave_evolving = composer.compose_frequency_pattern(freqs, duration=duration, pattern_type="evolving")

    # Same shape (and identical waveform because the fallback path is the same).
    assert wave_fallback.shape == wave_evolving.shape
    np.testing.assert_array_equal(wave_fallback, wave_evolving)


# ---------------------------------------------------------------------------
# 7. AudioOrchestrator high-level composition
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_audio_orchestrator_create_blessing_composition_returns_normalised_wave():
    """``create_blessing_composition`` returns a 1-D numpy waveform of the
    requested duration in samples (modulated)."""
    orchestrator = AudioOrchestrator(sample_rate=1000)
    duration_sec = 0.5

    wave = orchestrator.create_blessing_composition(
        frequencies=[220.0, 330.0, 440.0],
        intention="May all beings be at peace",
        duration=duration_sec,
        pattern_type="evolving",
    )

    assert isinstance(wave, np.ndarray)
    assert wave.ndim == 1
    # duration × sample_rate = 500 samples (allow tiny rounding tolerance).
    assert abs(len(wave) - duration_sec * 1000) < 5


@pytest.mark.unit
def test_audio_orchestrator_create_chakra_healing_composition_returns_layered_wave():
    """``create_chakra_healing_composition`` builds a layered composition
    around the requested chakra frequency."""
    orchestrator = AudioOrchestrator(sample_rate=1000)
    duration_sec = 0.3

    wave = orchestrator.create_chakra_healing_composition(
        chakra_freq=528.0,
        duration=duration_sec,
        intention="Heart healing",
    )

    assert isinstance(wave, np.ndarray)
    assert wave.ndim == 1
    assert abs(len(wave) - duration_sec * 1000) < 5


# ---------------------------------------------------------------------------
# 8. HARMONIC_BLESSING_SETS export
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_harmonic_blessing_sets_contains_documented_keys():
    """``HARMONIC_BLESSING_SETS`` exposes the four documented preset sets,
    each a non-empty list of positive floats."""
    expected_keys = {"earth_harmony", "love_resonance", "heart_chord", "full_spectrum"}
    assert set(HARMONIC_BLESSING_SETS.keys()) >= expected_keys

    for key in expected_keys:
        freqs = HARMONIC_BLESSING_SETS[key]
        assert isinstance(freqs, list)
        assert len(freqs) >= 2
        for f in freqs:
            assert isinstance(f, (int, float))
            assert f > 0


# ---------------------------------------------------------------------------
# 9. create_intention_modulation — deterministic for the same intention
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_intention_modulation_is_deterministic_per_intention():
    """The same intention text seeds the RNG the same way: the modulated
    waveform is byte-for-byte identical across two calls."""
    composer = IntelligentComposer(sample_rate=1000)

    base = np.linspace(-1.0, 1.0, 500)
    intention = "Compassion for all beings"

    a = composer.create_intention_modulation(intention, base, modulation_depth=0.1)
    b = composer.create_intention_modulation(intention, base, modulation_depth=0.1)

    np.testing.assert_array_equal(a, b)
    # The output is the input * a modulation envelope that stays close to 1.
    assert a.shape == base.shape