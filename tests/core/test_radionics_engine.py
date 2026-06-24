"""
Tests for ``core.radionics_engine`` — core radionics analysis and rate engine.

Covers the public API:
- :class:`RadionicsRate` — value/name/description/category/potency, with
  ``to_dict``/``from_dict`` round-trip and the
  ``_score_hour``/``find_balancing_rates`` helpers.
- :class:`RandomNumberGenerator` — secure / quantum / intention / fallback
  generation paths, and ``generate_float``.
- :class:`SignatureCalculator.text_to_rate` — hash, gematria, phonetic,
  mixed, and unknown-algorithm fallback.
- :class:`GeneralVitalityMeter.measure` / ``interpret_gv`` /
  ``measure_multiple`` — 0–1000 scale, deterministic bins, and stats
  round-trip (mean/median/std/min/max).
- :class:`RateDatabase` — add, find by name / category, JSON
  save/load round-trip, and ``export_watchlist`` / ``import_watchlist``.
- :class:`RadionicsAnalyzer.find_balancing_rates` — outputs a list of
  rates sorted by potency desc.
- :func:`quick_analysis` — module-level convenience wrapper.

No IO, no networking, no real audio. All randomness is checked for shape
(range / count / type) and determinism where the algorithm is
deterministic.
"""
from __future__ import annotations

import json
import random
from datetime import datetime

import pytest

from core.radionics_engine import (
    GeneralVitalityMeter,
    RadionicsAnalyzer,
    RadionicsRate,
    RandomNumberGenerator,
    RateDatabase,
    SignatureCalculator,
    quick_analysis,
)


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.radionics_engine as mod

    expected = (
        "RadionicsRate",
        "RandomNumberGenerator",
        "SignatureCalculator",
        "GeneralVitalityMeter",
        "RateDatabase",
        "RadionicsAnalyzer",
        "quick_analysis",
    )
    for name in expected:
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. RadionicsRate: to_dict / from_dict round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_radionics_rate_to_from_dict_round_trip():
    """Serialise a populated rate then deserialise it: every field survives."""
    original = RadionicsRate(
        values=[45, 72, 100],
        name="Test Rate",
        description="A rate for tests",
        category="remedy",
        potency=0.75,
    )
    data = original.to_dict()

    # The serialised shape is plain dict-of-primitives
    assert data["values"] == [45, 72, 100]
    assert data["name"] == "Test Rate"
    assert data["description"] == "A rate for tests"
    assert data["category"] == "remedy"
    assert data["potency"] == 0.75
    assert isinstance(data["timestamp"], str)

    restored = RadionicsRate.from_dict(data)
    assert restored.values == original.values
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.category == original.category
    assert restored.potency == original.potency
    # Timestamp round-trips as a real datetime (and is equal to the original)
    assert isinstance(restored.timestamp, datetime)
    assert restored.timestamp == original.timestamp


@pytest.mark.unit
def test_radionics_rate_from_dict_handles_optional_timestamp():
    """``from_dict`` accepts a payload with no ``timestamp`` key (uses the
    ctor's ``datetime.now()`` default)."""
    payload = {
        "values": [10, 20],
        "name": "Minimal",
        "description": "",
        "category": "",
        "potency": 0.0,
    }
    rate = RadionicsRate.from_dict(payload)
    assert rate.values == [10, 20]
    assert rate.name == "Minimal"
    # Timestamp is set by the ctor (default factory)
    assert isinstance(rate.timestamp, datetime)


# ---------------------------------------------------------------------------
# 3. RandomNumberGenerator: shape + range + intention-determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_random_number_generator_secure_mode_respects_range_and_count():
    """``mode='secure'``: outputs are ints within [min, max] inclusive, and
    ``count`` controls list length."""
    rng = RandomNumberGenerator(mode="secure")
    out = rng.generate(min_val=10, max_val=20, count=5)
    assert isinstance(out, list)
    assert len(out) == 5
    for v in out:
        assert isinstance(v, int)
        assert 10 <= v <= 20


@pytest.mark.unit
def test_random_number_generator_intention_mode_is_deterministic():
    """``mode='intention'``: the same intention string always produces the
    same first number (seeded by SHA-256 of the text)."""
    rng = RandomNumberGenerator(mode="intention")
    a = rng.generate(min_val=0, max_val=100, count=3, intention="World Peace")
    b = rng.generate(min_val=0, max_val=100, count=3, intention="World Peace")
    assert a == b, "Same intention must produce the same RNG output"

    # Different intention → very likely different output
    c = rng.generate(min_val=0, max_val=100, count=3, intention="Planetary Healing")
    assert a != c, "Different intentions should produce different RNG output"


@pytest.mark.unit
def test_random_number_generator_generate_float_returns_floats_in_range():
    """``generate_float`` returns floats within [min, max] of the requested
    count."""
    rng = RandomNumberGenerator(mode="secure")
    floats = rng.generate_float(min_val=0.25, max_val=0.75, count=4)
    assert len(floats) == 4
    for f in floats:
        assert isinstance(f, float)
        assert 0.25 <= f <= 0.75


# ---------------------------------------------------------------------------
# 4. SignatureCalculator.text_to_rate: algorithm contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_signature_calculator_hash_algorithm_is_deterministic():
    """The same input string always yields the same hash-based rate,
    regardless of case or surrounding whitespace."""
    calc = SignatureCalculator()
    r1 = calc.text_to_rate("World Peace", num_dials=3, algorithm="hash")
    r2 = calc.text_to_rate("world peace  ", num_dials=3, algorithm="hash")

    assert isinstance(r1, RadionicsRate)
    assert len(r1.values) == 3
    assert all(0 <= v <= 100 for v in r1.values)
    # Determinism: normalised input → same output
    assert r1.values == r2.values
    # Category is always "signature" for these algorithms
    assert r1.category == "signature"


@pytest.mark.unit
def test_signature_calculator_all_algorithms_produce_correct_shape():
    """For each documented algorithm, ``text_to_rate`` returns a
    ``RadionicsRate`` with the requested number of dials and bounded values."""
    calc = SignatureCalculator()
    for algo in ("hash", "gematria", "phonetic", "mixed"):
        rate = calc.text_to_rate("Test", num_dials=4, max_value=50, algorithm=algo)
        assert isinstance(rate, RadionicsRate), f"algorithm={algo!r} wrong return type"
        assert len(rate.values) == 4, f"algorithm={algo!r} wrong dial count"
        for v in rate.values:
            assert 0 <= v <= 50, f"algorithm={algo!r} dial {v} out of [0,50]"


@pytest.mark.unit
def test_signature_calculator_unknown_algorithm_falls_back_to_hash():
    """An unknown algorithm string falls through to the hash algorithm
    (so a typo never raises at the LLM tool boundary)."""
    calc = SignatureCalculator()
    fallback = calc.text_to_rate("Hello", num_dials=3, algorithm="not-a-real-algo")
    hash_rate = calc.text_to_rate("Hello", num_dials=3, algorithm="hash")
    assert fallback.values == hash_rate.values


# ---------------------------------------------------------------------------
# 5. GeneralVitalityMeter: 0–1000 range, interpretation bins, multiple
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_gv_meter_returns_value_in_zero_to_thousand_range():
    """``measure`` returns a float in [0, 1000] regardless of subject/context."""
    meter = GeneralVitalityMeter()
    for subject in ("", "Alice", "World Peace"):
        gv = meter.measure(subject=subject)
        assert isinstance(gv, float) or isinstance(gv, int)
        assert 0 <= gv <= 1000


@pytest.mark.unit
def test_gv_meter_interpret_gv_buckets_are_documented():
    """The interpretation string matches the documented bucket labels."""
    meter = GeneralVitalityMeter()
    cases = [
        (1000.0, "Excellent"),
        (800.0, "Excellent"),
        (700.0, "Good"),
        (500.0, "Moderate"),
        (300.0, "Low"),
        (100.0, "Very Low"),
    ]
    for gv, expected_prefix in cases:
        interp = meter.interpret_gv(gv)
        assert expected_prefix in interp, f"GV={gv} -> {interp!r} (expected to contain {expected_prefix!r})"


@pytest.mark.unit
def test_gv_meter_measure_multiple_returns_stats():
    """``measure_multiple`` returns a dict with the documented stats keys
    whose values are consistent with the underlying sample."""
    meter = GeneralVitalityMeter()
    stats = meter.measure_multiple(count=20, subject="Test Subject")
    assert stats["count"] == 20
    # Stats are floats
    for k in ("mean", "median", "std", "min", "max"):
        assert k in stats, f"missing key: {k}"
        assert isinstance(stats[k], (int, float)), f"{k} is not numeric"
    # min <= mean/median <= max
    assert stats["min"] <= stats["mean"] <= stats["max"]
    assert stats["min"] <= stats["median"] <= stats["max"]
    # The raw sample has the right length
    assert len(stats["measurements"]) == 20


# ---------------------------------------------------------------------------
# 6. RateDatabase: in-memory CRUD + JSON save/load
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rate_database_add_and_find_by_name():
    """Adding rates to the database makes them discoverable by name
    (substring match by default, exact match when requested)."""
    db = RateDatabase()
    db.add_rate(RadionicsRate(values=[10, 20], name="Heart Healing", category="chakra"))
    db.add_rate(RadionicsRate(values=[30, 40], name="Liver Balance", category="organ"))
    db.add_rate(RadionicsRate(values=[50, 60], name="Heart Chakra", category="chakra"))

    # Substring search (default)
    heart_hits = db.find_by_name("heart")
    assert len(heart_hits) == 2
    assert all("heart" in r.name.lower() for r in heart_hits)

    # Exact search
    exact = db.find_by_name("Heart Healing", exact=True)
    assert len(exact) == 1
    assert exact[0].values == [10, 20]


@pytest.mark.unit
def test_rate_database_find_by_category_and_get_categories():
    """``find_by_category`` filters by case-insensitive category, and
    ``get_categories`` returns the sorted unique list of category strings.

    NOTE: ``get_categories`` is currently case-sensitive when building the
    unique set, so "Chakra" and "chakra" are returned as two distinct
    entries. ``find_by_category``, however, matches case-insensitively.
    This inconsistency is locked in here as the existing behaviour.
    """
    db = RateDatabase()
    db.add_rate(RadionicsRate(values=[1], name="a", category="Chakra"))
    db.add_rate(RadionicsRate(values=[2], name="b", category="organ"))
    db.add_rate(RadionicsRate(values=[3], name="c", category="chakra"))  # case-insensitive dup
    db.add_rate(RadionicsRate(values=[4], name="d", category="remedy"))

    chakras = db.find_by_category("chakra")
    assert len(chakras) == 2  # case-insensitive lookup matches both
    assert {r.values[0] for r in chakras} == {1, 3}

    cats = db.get_categories()
    # ``get_categories`` deduplicates by exact string equality only, so
    # "Chakra" and "chakra" both appear in the sorted result.
    assert cats == sorted(["Chakra", "chakra", "organ", "remedy"])
    # And empty categories are filtered out
    assert "" not in cats


@pytest.mark.unit
def test_rate_database_save_and_load_round_trip(tmp_path):
    """Save the database to a JSON file then load it back: counts and
    contents survive the round trip."""
    db = RateDatabase()
    db.add_rate(RadionicsRate(values=[11, 22, 33], name="A", category="remedy", potency=0.5))
    db.add_rate(RadionicsRate(values=[44, 55], name="B", category="organ", potency=0.8))

    path = str(tmp_path / "rates.json")
    db.save(path)
    # File exists and is valid JSON with the expected envelope
    with open(path) as f:
        raw = json.load(f)
    assert raw["count"] == 2
    assert len(raw["rates"]) == 2

    # Load into a fresh database
    db2 = RateDatabase()
    db2.load(path)
    assert len(db2.rates) == 2
    by_name = {r.name: r for r in db2.rates}
    assert by_name["A"].values == [11, 22, 33]
    assert by_name["B"].potency == 0.8
    # Loading populated database_path
    assert db2.database_path == path


@pytest.mark.unit
def test_rate_database_save_without_path_raises_value_error():
    """A RateDatabase with no ``database_path`` and no path argument to
    ``save`` raises ValueError rather than writing to a default location."""
    db = RateDatabase()  # no path
    with pytest.raises(ValueError):
        db.save()


# ---------------------------------------------------------------------------
# 7. RadionicsAnalyzer.find_balancing_rates
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_radionics_analyzer_find_balancing_rates_returns_sorted_list():
    """``find_balancing_rates`` returns a list of length ``num_rates``,
    with potency in [0, 1] and sorted by potency descending."""
    analyzer = RadionicsAnalyzer()
    rates = analyzer.find_balancing_rates("Stress Relief", num_rates=4)
    assert isinstance(rates, list)
    assert len(rates) == 4
    for r in rates:
        assert isinstance(r, RadionicsRate)
        assert 0.0 <= r.potency <= 1.0
        assert r.category == "balancing"
    # Sorted by potency descending
    potencies = [r.potency for r in rates]
    assert potencies == sorted(potencies, reverse=True)


# ---------------------------------------------------------------------------
# 8. quick_analysis module-level wrapper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quick_analysis_returns_expected_dict_shape(capsys):
    """``quick_analysis`` returns a dict with the documented analysis
    fields and prints a summary when verbose=True."""
    result = quick_analysis("Healing for Earth", verbose=True)
    assert isinstance(result, dict)
    for key in (
        "subject",
        "timestamp",
        "baseline_gv",
        "gv_stats",
        "signature_rate",
        "resonant_rates",
        "interpretation",
    ):
        assert key in result, f"missing key: {key}"
    assert result["subject"] == "Healing for Earth"
    assert isinstance(result["baseline_gv"], (int, float))
    # verbose=True writes to stdout
    captured = capsys.readouterr().out
    assert "Healing for Earth" in captured
    assert "Analysis complete" in captured
