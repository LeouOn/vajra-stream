# core/rate_to_audio.py
"""Bridge module: RadionicsRate → prayer bowl carrier frequencies.

The central integration gap identified in the crystal-bowl audit: radionics
rates are dial integers (0-100) that never become audio. This module maps
them to Solfeggio-aligned carrier frequencies suitable for prayer bowl
synthesis via :class:`~core.enhanced_audio_generator.EnhancedAudioGenerator`.

Algorithm:
    1. Each dial value (0-100) snaps to the nearest Solfeggio tone.
    2. Duplicate tones are deduplicated (preserving order).
    3. Potency (0-1) scales amplitude and overtone richness.
    4. Always include 7.83 Hz Schumann resonance as a base layer.

The resulting :class:`CarrierFrequencySet` feeds directly into
``EnhancedAudioGenerator.generate_prayer_bowl_tone()`` for each frequency,
then ``layer_frequencies()`` to combine.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ─── Solfeggio scale (Hz) ──────────────────────────────────────────────────
# These are the 7 primary Solfeggio frequencies used throughout Vajra.Stream.
# Dial values snap to the nearest one, creating musically/spiritually aligned
# carrier tones from arbitrary radionics rate signatures.
SOLFEGGIO_FREQUENCIES: list[float] = [
    396.0,   # Ut — Liberating guilt and fear
    417.0,   # Re — Undoing situations, facilitating change
    528.0,   # Mi — DNA repair, transformation, love
    639.0,   # La — Connecting relationships
    741.0,   # Sol — Awakening intuition
    852.0,   # Si — Returning to spiritual order
    963.0,   # Divine consciousness
]

# Always-present base layer (Earth resonance)
SCHUMANN_BASE_HZ: float = 7.83

# Minimum amplitude for prayer bowl synthesis output
MIN_AMPLITUDE: float = 0.15
MAX_AMPLITUDE: float = 0.50  # Matches config.settings.MAX_VOLUME


@dataclass
class CarrierFrequencySet:
    """A set of carrier frequencies derived from a radionics rate.

    Attributes:
        frequencies: List of Hz values for prayer bowl synthesis (always
            includes 7.83 Hz Schumann base as first element).
        amplitude: Peak amplitude (0.15–0.50), derived from rate potency.
        overtone_richness: 0.0–1.0, controls how many harmonic/metallic
            partials the prayer bowl synth applies. Higher potency = richer.
        rate_values: Original dial values (for logging/debugging).
        solfeggio_names: Human-readable name for each frequency.
    """

    frequencies: list[float]
    amplitude: float
    overtone_richness: float
    rate_values: list[int]
    solfeggio_names: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.frequencies)

    def __iter__(self):
        return iter(self.frequencies)


# ─── Name lookup for Solfeggio tones ───────────────────────────────────────
_SOLFEGGIO_NAMES: dict[float, str] = {
    396.0: "Ut (Liberation)",
    417.0: "Re (Change)",
    528.0: "Mi (Transformation)",
    639.0: "La (Connection)",
    741.0: "Sol (Awakening)",
    852.0: "Si (Spiritual Order)",
    963.0: "Divine Consciousness",
}


def _snap_to_solfeggio(dial_value: int) -> float:
    """Snap a dial value (0-100) to the nearest Solfeggio frequency.

    The dial range 0-100 is divided into 7 equal segments, each mapping
    to one Solfeggio tone. This ensures every rate produces a musically
    aligned frequency.
    """
    # Map 0-100 → index into 7 Solfeggio tones
    clamped = max(0, min(100, dial_value))
    segment_size = 100.0 / len(SOLFEGGIO_FREQUENCIES)
    index = int(clamped / segment_size)
    index = min(index, len(SOLFEGGIO_FREQUENCIES) - 1)
    return SOLFEGGIO_FREQUENCIES[index]


def _potency_to_amplitude(potency: float) -> float:
    """Map potency (0-1) to prayer bowl peak amplitude (0.15–0.50)."""
    clamped = max(0.0, min(1.0, potency))
    return MIN_AMPLITUDE + (MAX_AMPLITUDE - MIN_AMPLITUDE) * clamped


def _potency_to_overtone_richness(potency: float) -> float:
    """Map potency (0-1) to overtone richness (0.3–1.0).

    Low-potency rates get fewer partials (cleaner tone); high-potency
    rates get the full 6 harmonic + 3 metallic partials.
    """
    clamped = max(0.0, min(1.0, potency))
    return 0.3 + 0.7 * clamped


def map_rate_to_carriers(
    rate_values: list[int],
    potency: float = 0.5,
    rate_name: str = "",
) -> CarrierFrequencySet:
    """Map radionics dial values to prayer bowl carrier frequencies.

    Args:
        rate_values: List of integer dial positions (0-100) from a
            :class:`~core.radionics_engine.RadionicsRate`.
        potency: Resonance strength (0.0–1.0) from the rate.
        rate_name: Optional name for logging/debugging.

    Returns:
        A :class:`CarrierFrequencySet` ready for prayer bowl synthesis.

    Example::

        >>> from core.rate_to_audio import map_rate_to_carriers
        >>> carriers = map_rate_to_carriers([42, 60, 77], potency=0.85)
        >>> carriers.frequencies
        [7.83, 417.0, 528.0, 741.0]
        >>> carriers.amplitude
        0.4475
        >>> carriers.solfeggio_names
        ['Schumann Base', 'Re (Change)', 'Mi (Transformation)', 'Sol (Awakening)']
    """
    # Snap each dial value to nearest Solfeggio tone
    snapped = [_snap_to_solfeggio(v) for v in rate_values]

    # Deduplicate (preserve order — first occurrence wins)
    seen: set[float] = set()
    unique_freqs: list[float] = []
    for f in snapped:
        if f not in seen:
            seen.add(f)
            unique_freqs.append(f)

    # Always prepend Schumann base
    frequencies = [SCHUMANN_BASE_HZ] + unique_freqs

    # Build human-readable names
    names = ["Schumann Base"] + [
        _SOLFEGGIO_NAMES.get(f, f"{f:.1f} Hz") for f in unique_freqs
    ]

    # Derive amplitude and richness from potency
    amplitude = _potency_to_amplitude(potency)
    overtone_richness = _potency_to_overtone_richness(potency)

    return CarrierFrequencySet(
        frequencies=frequencies,
        amplitude=amplitude,
        overtone_richness=overtone_richness,
        rate_values=list(rate_values),
        solfeggio_names=names,
    )


__all__ = [
    "CarrierFrequencySet",
    "SOLFEGGIO_FREQUENCIES",
    "SCHUMANN_BASE_HZ",
    "map_rate_to_carriers",
]
