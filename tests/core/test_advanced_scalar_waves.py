"""
Smoke + behaviour tests for ``core.advanced_scalar_waves``.

Covers:
* Module import — every public class/enum is exposed
* :class:`WaveMethod` enum — all 7 documented methods are present
* :class:`QuantumRNG` — ``generate`` returns floats in [0, 1);
  ``generate_int`` returns ints in [min, max)
* :class:`LorenzAttractor` — ``step`` advances state and returns floats;
  ``generate_stream`` produces values in [0, 1]
* :class:`CellularAutomata1D` — ``step`` evolves the grid;
  ``get_entropy`` returns a float in [0, 1]
* :class:`KuramotoOscillator` — ``get_order_parameter`` returns a float
  in [0, 1]; ``step`` runs without raising
* :class:`CryptoMixer` — ``mix`` returns 32 bytes; successive calls produce
  different output (avalanche property)
* :class:`HybridScalarWaveGenerator` — ``generate_hybrid_stream`` returns a
  list of floats of the requested length
"""

from __future__ import annotations

import pytest

from core import advanced_scalar_waves as asw

# ---------------------------------------------------------------------------
# 1. Import smoke + public surface
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_public_surface():
    """Module imports cleanly and exposes every public class/enum."""
    # Enum
    assert set(asw.WaveMethod) == {
        asw.WaveMethod.QUANTUM_RNG,
        asw.WaveMethod.CHAOTIC_ATTRACTOR,
        asw.WaveMethod.CELLULAR_AUTOMATA,
        asw.WaveMethod.NEURAL_OSCILLATOR,
        asw.WaveMethod.CRYPTO_HASH,
        asw.WaveMethod.PRIME_HARMONIC,
        asw.WaveMethod.HYBRID_SYNTHESIS,
    }

    # Dataclasses
    assert asw.ThermalState is not None
    assert asw.MOPSMetrics is not None

    # Public classes (one of each method + the hybrid + thermal monitor)
    for cls_name in (
        "ThermalMonitor",
        "QuantumRNG",
        "LorenzAttractor",
        "RosslerAttractor",
        "CellularAutomata1D",
        "KuramotoOscillator",
        "CryptoMixer",
        "PrimeHarmonics",
        "HybridScalarWaveGenerator",
    ):
        assert hasattr(asw, cls_name), f"missing class: {cls_name}"


# ---------------------------------------------------------------------------
# 2. QuantumRNG — float range + int range
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quantum_rng_generate_returns_floats_in_unit_range():
    """``QuantumRNG.generate`` returns floats strictly inside [0, 1)."""
    rng = asw.QuantumRNG()
    values = rng.generate(64)
    assert len(values) == 64
    for v in values:
        assert isinstance(v, float)
        assert 0.0 <= v < 1.0


@pytest.mark.unit
def test_quantum_rng_generate_int_is_in_range():
    """``QuantumRNG.generate_int`` returns ints in [min_val, max_val)."""
    rng = asw.QuantumRNG()
    for _ in range(32):
        n = rng.generate_int(5, 10)
        assert isinstance(n, int)
        assert 5 <= n < 10


# ---------------------------------------------------------------------------
# 3. LorenzAttractor — step advances state, stream stays in [0, 1]
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lorenz_attractor_step_changes_state_and_returns_floats():
    """``step`` returns a 3-tuple of floats and advances the state."""
    lorenz = asw.LorenzAttractor()
    x0, y0, z0 = lorenz.x, lorenz.y, lorenz.z
    out = lorenz.step()
    assert isinstance(out, tuple) and len(out) == 3
    assert all(isinstance(v, float) for v in out)
    # State must have moved (Lorenz is chaotic — virtually never returns to
    # the exact starting point in a single step).
    assert (lorenz.x, lorenz.y, lorenz.z) != (x0, y0, z0)


@pytest.mark.unit
def test_lorenz_attractor_generate_stream_is_normalised():
    """``generate_stream`` returns values in approximately [0, 1]."""
    lorenz = asw.LorenzAttractor()
    stream = lorenz.generate_stream(50)
    assert len(stream) == 50
    for v in stream:
        assert isinstance(v, float)
        assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# 4. CellularAutomata1D — step + entropy bounds
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cellular_automata_step_evolves_and_entropy_is_bounded():
    """``step`` mutates the grid and ``get_entropy`` stays in [0, 1]."""
    ca = asw.CellularAutomata1D(size=64, rule=110)
    before = list(ca.cells)
    ca.step()
    after = ca.cells
    assert len(after) == 64
    # The grid must have evolved (rule 110 with a single seed never stays
    # unchanged after one step).
    assert before != after

    e = ca.get_entropy()
    assert isinstance(e, float)
    assert 0.0 <= e <= 1.0


# ---------------------------------------------------------------------------
# 5. KuramotoOscillator — order parameter in [0, 1]
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_kuramoto_oscillator_order_parameter_in_unit_range():
    """``get_order_parameter`` returns a float in [0, 1]."""
    osc = asw.KuramotoOscillator(n_oscillators=16)
    # A few steps so the oscillators have actually moved
    for _ in range(5):
        osc.step()
    r = osc.get_order_parameter()
    assert isinstance(r, float)
    assert 0.0 <= r <= 1.0


# ---------------------------------------------------------------------------
# 6. CryptoMixer — bytes output + avalanche
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_crypto_mixer_returns_bytes_and_avalanche():
    """``mix`` returns 32 bytes and successive calls produce different output."""
    mixer = asw.CryptoMixer()
    out1 = mixer.mix()
    assert isinstance(out1, bytes)
    assert len(out1) == 32

    out2 = mixer.mix(b"a small perturbation")
    assert isinstance(out2, bytes)
    assert len(out2) == 32
    # Different output even though the input was tiny
    assert out1 != out2


# ---------------------------------------------------------------------------
# 7. HybridScalarWaveGenerator — returns a list of floats of the requested size
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hybrid_scalar_wave_generator_returns_requested_count():
    """``generate_hybrid_stream(N)`` returns N floats (throttle permitting)."""
    gen = asw.HybridScalarWaveGenerator()
    out = gen.generate_hybrid_stream(32)
    assert isinstance(out, list)
    # Throttle may scale the count but never below 1.
    assert 1 <= len(out) <= 32
    for v in out:
        assert isinstance(v, float)
