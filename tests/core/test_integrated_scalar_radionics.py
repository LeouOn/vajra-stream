"""Tests for ``core.integrated_scalar_radionics`` — combined scalar + radionics broadcaster.

Covers the public API:
- Enum: :class:`IntentionType` (8 values).
- Dataclass: :class:`BroadcastConfiguration` (defaults + custom values).
- :class:`IntegratedScalarRadionicsBroadcaster`:
  - ``encode_intention`` — returns a frequency seed for every intention.
  - ``select_frequency`` — picks from the Solfeggio map.
  - ``broadcast_to_targets`` — pure fallback path (all subsystems
    mocked / disabled), so no audio / DB / LLM is exercised.

The heavy subsystems (``HybridScalarWaveGenerator``, ``BlessingDatabase``,
``EnergeticAnatomyDatabase``) are mocked at the module level so the
broadcaster falls back to its "universal field" code path. No audio
device, no DB file, no LLM call ever runs.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.integrated_scalar_radionics import (
    BroadcastConfiguration,
    IntegratedScalarRadionicsBroadcaster,
    IntentionType,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def broadcaster(monkeypatch: pytest.MonkeyPatch) -> IntegratedScalarRadionicsBroadcaster:
    """Build a broadcaster with all three heavy subsystems replaced by mocks.

    The real ``__init__`` instantiates ``HybridScalarWaveGenerator``,
    ``BlessingDatabase``, and ``EnergeticAnatomyDatabase`` — each of which
    can touch audio devices, sqlite files, or other side effects. We
    patch those three names on the already-imported module object so the
    constructor binds ``None`` for each subsystem (the module's
    ``HAS_*`` flags stay truthy but the conditional in ``__init__`` reads
    the names directly).
    """
    import core.integrated_scalar_radionics as mod

    monkeypatch.setattr(mod, "HybridScalarWaveGenerator", MagicMock(), raising=False)
    monkeypatch.setattr(mod, "BlessingDatabase", MagicMock(), raising=False)
    monkeypatch.setattr(mod, "EnergeticAnatomyDatabase", MagicMock(), raising=False)

    # Also patch the conditional flags so __init__ takes the None branch
    # (defensive — in case future refactors add HAS_* checks).
    monkeypatch.setattr(mod, "HAS_SCALAR", False, raising=False)
    monkeypatch.setattr(mod, "HAS_BLESSINGS", False, raising=False)
    monkeypatch.setattr(mod, "HAS_ANATOMY", False, raising=False)

    return IntegratedScalarRadionicsBroadcaster()


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports its three documented public symbols."""
    import core.integrated_scalar_radionics as mod

    for name in ("IntentionType", "BroadcastConfiguration", "IntegratedScalarRadionicsBroadcaster"):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Enum + dataclass contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_intention_type_enum_has_eight_values():
    """IntentionType covers the eight documented healing intentions."""
    assert len(IntentionType) == 8
    values = {i.value for i in IntentionType}
    assert values == {
        "healing",
        "liberation",
        "empowerment",
        "protection",
        "reconciliation",
        "peace",
        "love",
        "wisdom",
    }
    # IntentionType is a plain Enum (not str-subclass) — must compare via .value.
    assert IntentionType.HEALING.value == "healing"
    # The string value itself is what config consumers serialise.
    assert IntentionType(IntentionType.HEALING.value) is IntentionType.HEALING


@pytest.mark.unit
def test_broadcast_configuration_defaults_and_overrides():
    """BroadcastConfiguration accepts every field and exposes its defaults."""
    cfg = BroadcastConfiguration(
        intention=IntentionType.LOVE,
        target_count=7,
        duration_seconds=120.0,
        scalar_intensity=0.5,
        frequency_hz=528.0,
        mantra="Om Mani Padme Hum",
    )

    assert cfg.intention is IntentionType.LOVE
    assert cfg.target_count == 7
    assert cfg.duration_seconds == 120.0
    assert cfg.scalar_intensity == 0.5
    assert cfg.frequency_hz == 528.0
    assert cfg.mantra == "Om Mani Padme Hum"

    # Optional flags default to False
    assert cfg.use_meridians is False
    assert cfg.use_chakras is False
    assert cfg.breathing_pattern is False


# ---------------------------------------------------------------------------
# 3. encode_intention / select_frequency — pure maps
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_encode_intention_returns_known_seeds(broadcaster: IntegratedScalarRadionicsBroadcaster):
    """encode_intention returns a numeric seed for every intention."""
    known = {
        IntentionType.HEALING: 432,
        IntentionType.LIBERATION: 396,
        IntentionType.EMPOWERMENT: 528,
        IntentionType.PROTECTION: 741,
        IntentionType.RECONCILIATION: 639,
        IntentionType.PEACE: 852,
        IntentionType.LOVE: 528,
        IntentionType.WISDOM: 963,
    }
    for intention, expected in known.items():
        assert broadcaster.encode_intention(intention) == expected, (
            f"encode_intention({intention.value}) returned "
            f"{broadcaster.encode_intention(intention)}, expected {expected}"
        )


@pytest.mark.unit
def test_select_frequency_returns_mapped_solfeggio(broadcaster: IntegratedScalarRadionicsBroadcaster):
    """select_frequency returns the canonical Solfeggio for every intention."""
    expected_map = {
        IntentionType.HEALING: 528.0,
        IntentionType.LIBERATION: 396.0,
        IntentionType.EMPOWERMENT: 741.0,
        IntentionType.PROTECTION: 741.0,
        IntentionType.RECONCILIATION: 639.0,
        IntentionType.PEACE: 852.0,
        IntentionType.LOVE: 528.0,
        IntentionType.WISDOM: 963.0,
    }
    for intention, expected_freq in expected_map.items():
        actual = broadcaster.select_frequency(intention)
        assert actual == expected_freq, f"{intention} → {actual}, expected {expected_freq}"


# ---------------------------------------------------------------------------
# 4. broadcast_to_targets — pure fallback path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_broadcast_to_targets_runs_with_no_subsystems(
    broadcaster: IntegratedScalarRadionicsBroadcaster,
):
    """With all subsystems disabled, broadcast_to_targets runs the
    'universal field' path, returns a populated results dict, and
    updates the broadcaster's running statistics."""
    cfg = BroadcastConfiguration(
        intention=IntentionType.PEACE,
        target_count=3,
        duration_seconds=0.0,  # skip the scalar loop entirely
        scalar_intensity=0.5,
        frequency_hz=None,  # exercise the auto-select branch
        mantra="Om Ah Hum",
    )

    results = broadcaster.broadcast_to_targets(cfg)

    assert isinstance(results, dict)
    assert results["config"]["intention"] == "peace"
    assert results["config"]["targets"] == 3
    assert results["config"]["mantra"] == "Om Ah Hum"
    # frequency_hz was None → select_frequency(PROJECTION) ran
    assert results["config"]["frequency"] == 852.0
    # No targets because no blessing_db → universal field
    assert results["targets_blessed"] == 0
    # No meridians / chakras activated (anatomy_db disabled)
    assert results["meridians_activated"] == 0
    assert results["chakras_activated"] == 0
    # start / end timestamps present and parseable
    assert "start_time" in results
    assert "end_time" in results

    # Statistics updated by exactly one broadcast
    assert broadcaster.total_broadcasts == 1
    assert broadcaster.total_targets_blessed == 0


@pytest.mark.unit
def test_broadcast_to_targets_with_explicit_frequency_preserves_value(
    broadcaster: IntegratedScalarRadionicsBroadcaster,
):
    """When frequency_hz is supplied explicitly, it is preserved verbatim
    and the auto-selection map is not consulted."""
    cfg = BroadcastConfiguration(
        intention=IntentionType.HEALING,
        target_count=1,
        duration_seconds=0.0,
        scalar_intensity=0.1,
        frequency_hz=440.0,  # non-Solfeggio value, should be kept as-is
        mantra="Gate Gate",
    )

    results = broadcaster.broadcast_to_targets(cfg)

    assert results["config"]["frequency"] == 440.0
    assert broadcaster.total_broadcasts == 1
    assert broadcaster.total_operations == 0  # no scalar ops when duration == 0
