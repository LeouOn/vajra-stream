"""GEO-2 T2: ``cast_geomancy`` must be seedable, and its derivation must stay right.

RED-first. Before this ticket ``cast_geomancy`` took no ``seed`` at all: the
Mothers were drawn with ``secrets.randbelow(2)`` and could not be reproduced.

The shape follows IR-2's I Ching work exactly: ``seed=None`` keeps the
``secrets`` path, an integer seeds ``random.Random(seed)`` with the SAME
per-line draw, so the distribution is identical and a cast can be replayed.

The oracle in this file is written from the plain-language derivation and NOT
copied from the service, so the comparison is a real check on the derivation
rather than a restatement of it:

  * 4 MOTHER figures, each 4 lines of 1 or 2 points;
  * 4 DAUGHTERS: the first line of each Mother in order forms Daughter 1, the
    second lines form Daughter 2, and so on;
  * 4 NIECES: M1+M2, M3+M4, D1+D2, D3+D4, where adding two figures is
    line-by-line and the result is 2 points when the two point-counts sum to an
    EVEN number and 1 point when they sum to an ODD number;
  * RIGHT WITNESS = N1+N2, LEFT WITNESS = N3+N4, JUDGE = RW+LW;
  * RECONCILER = JUDGE + the figure in House 1 (Mother 1);
  * the 12-house projection: Mothers 1-4, Daughters 1-4, Nieces 1-4.

Offline, deterministic, no network, no database.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from backend.core.services import divination_service as ds
from backend.core.services.divination_service import DivinationService

# ---------------------------------------------------------------------------
# the independent oracle
# ---------------------------------------------------------------------------


def _add(a: list[int], b: list[int]) -> list[int]:
    """Line-by-line addition: even sum of point-counts -> 2 points, odd -> 1."""
    return [2 if (x + y) % 2 == 0 else 1 for x, y in zip(a, b)]


def oracle_figures(mothers: list[list[int]]) -> dict[str, list[int]]:
    """The whole chart, derived from the 4 Mothers."""
    m = {i + 1: mothers[i] for i in range(4)}
    daughters = {i: [m[1][i - 1], m[2][i - 1], m[3][i - 1], m[4][i - 1]] for i in range(1, 5)}
    nieces = {
        1: _add(m[1], m[2]),
        2: _add(m[3], m[4]),
        3: _add(daughters[1], daughters[2]),
        4: _add(daughters[3], daughters[4]),
    }
    right_witness = _add(nieces[1], nieces[2])
    left_witness = _add(nieces[3], nieces[4])
    judge = _add(right_witness, left_witness)
    reconciler = _add(judge, m[1])

    out: dict[str, list[int]] = {}
    for i in range(1, 5):
        out[f"Mother {i}"] = m[i]
    for i in range(1, 5):
        out[f"Daughter {i}"] = daughters[i]
    for i in range(1, 5):
        out[f"Niece {i}"] = nieces[i]
    out["Right Witness"] = right_witness
    out["Left Witness"] = left_witness
    out["Judge"] = judge
    out["Reconciler"] = reconciler
    return out


def seeded_mothers(seed: int) -> list[list[int]]:
    """The Mothers a seeded cast must produce.

    This is the SPECIFICATION of the seeded path, not a copy of the service:
    16 draws from ``random.Random(seed)`` in mother-major order, each
    ``randrange(2)`` giving 1 point (0) or 2 points (1). If the service drew in
    a different order or a different number of times, the derived figures would
    not match the oracle and these tests would fail.
    """
    rng = random.Random(seed)
    values = [rng.randrange(2) + 1 for _ in range(16)]
    return [values[i * 4 : (i + 1) * 4] for i in range(4)]


@pytest.fixture
def service() -> DivinationService:
    return DivinationService()


# ---------------------------------------------------------------------------
# the seed
# ---------------------------------------------------------------------------


def test_same_seed_gives_the_same_cast(service: DivinationService) -> None:
    first = service.cast_geomancy(seed=1234)
    second = service.cast_geomancy(seed=1234)

    assert first["figures"] == second["figures"]
    assert first["houses"] == second["houses"]


def test_different_seeds_differ_across_a_sample(service: DivinationService) -> None:
    seen = set()
    for seed in range(40):
        figures = service.cast_geomancy(seed=seed)["figures"]
        seen.add(tuple(tuple(figures[f"Mother {i}"]["pattern"]) for i in range(1, 5)))
    assert len(seen) > 30, f"40 seeds produced only {len(seen)} distinct Mother sets"


def test_seed_none_still_uses_the_secrets_draw(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    """The default path must be untouched: still the cryptographic draw."""
    calls = {"n": 0}

    def counting_randbelow(n: int) -> int:
        calls["n"] += 1
        return 0  # 0 -> 1 point

    monkeypatch.setattr(ds.secrets, "randbelow", counting_randbelow)

    result = service.cast_geomancy()

    assert calls["n"] == 16, "the secrets path must still draw 16 times"
    assert result["figures"]["Mother 1"]["pattern"] == [1, 1, 1, 1]


def test_seeded_path_never_touches_secrets(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(n: int) -> int:
        raise AssertionError("the seeded path must not use secrets.randbelow")

    monkeypatch.setattr(ds.secrets, "randbelow", explode)

    result = service.cast_geomancy(seed=7)
    assert result["figures"]["Mother 1"]["pattern"] == seeded_mothers(7)[0]


def test_unseeded_path_never_touches_random(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    """The unseeded path must not reach for ``random`` at all."""

    def explode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the unseeded path must not use random.Random")

    monkeypatch.setattr(ds.random, "Random", explode)

    result = service.cast_geomancy()
    assert len(result["figures"]["Mother 1"]["pattern"]) == 4


def test_seeded_mother_values_are_all_valid(service: DivinationService) -> None:
    for seed in range(200):
        for i in range(1, 5):
            pattern = service.cast_geomancy(seed=seed)["figures"][f"Mother {i}"]["pattern"]
            assert len(pattern) == 4
            assert set(pattern) <= {1, 2}, f"seed {seed} produced {pattern}"


# ---------------------------------------------------------------------------
# the derivation, against the independent oracle
# ---------------------------------------------------------------------------


def test_seeded_cast_matches_the_independent_oracle(service: DivinationService) -> None:
    """The seeded path must derive exactly what the oracle derives."""
    for seed in range(200):
        mothers = seeded_mothers(seed)
        result = service.cast_geomancy(seed=seed)
        expected = oracle_figures(mothers)
        for name, pattern in expected.items():
            assert result["figures"][name]["pattern"] == pattern, f"seed {seed}, {name}"


def test_derivation_matches_the_oracle_over_4000_casts(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The audit's 4 000-cast oracle comparison, as a permanent test.

    The Mothers are forced through the ``secrets`` seam so that the comparison
    is over the DERIVATION and not over the RNG. The figures the service
    computes are checked against the oracle's, one field at a time.
    """
    rng = random.Random(20261021)
    for _ in range(4000):
        mothers = [[rng.choice((1, 2)) for _ in range(4)] for _ in range(4)]
        lines = [0 if v == 1 else 1 for figure in mothers for v in figure]
        counter = {"n": 0}

        def fake_randbelow(n: int, _lines: list[int] = lines, _counter: dict = counter) -> int:
            index = _counter["n"]
            _counter["n"] += 1
            return _lines[index]

        monkeypatch.setattr(ds.secrets, "randbelow", fake_randbelow)
        result = service.cast_geomancy()
        monkeypatch.undo()

        expected = oracle_figures(mothers)
        for name, pattern in expected.items():
            assert result["figures"][name]["pattern"] == pattern, name
            assert result["figures"][name]["name"] != "Unknown", name

        # the house projection: Mothers 1-4, Daughters 1-4, Nieces 1-4
        layout = (
            [f"Mother {i}" for i in range(1, 5)]
            + [f"Daughter {i}" for i in range(1, 5)]
            + [f"Niece {i}" for i in range(1, 5)]
        )
        for house in range(1, 13):
            key = layout[house - 1]
            assert result["houses"][house]["pattern"] == expected[key], f"house {house}"
            assert result["houses"][house]["name"] == result["figures"][key]["name"]

        # the Judge always has an EVEN number of total points
        assert sum(result["figures"]["Judge"]["pattern"]) % 2 == 0

        # the Reconciler is the Judge plus the figure in House 1
        assert result["figures"]["Reconciler"]["pattern"] == _add(expected["Judge"], expected["Mother 1"])


def test_every_figure_gets_a_name(service: DivinationService) -> None:
    """No figure may come back as "Unknown"."""
    for seed in range(200):
        result = service.cast_geomancy(seed=seed)
        for name, data in result["figures"].items():
            assert data["name"] != "Unknown", f"seed {seed}, {name}"


# ---------------------------------------------------------------------------
# distribution
# ---------------------------------------------------------------------------


def test_mother_figure_distribution_is_uniform_over_16000_seeded_draws(
    service: DivinationService,
) -> None:
    """16 000 Mother figures over the 16 patterns, within 5 sigma.

    For 16 000 draws over 16 equally likely patterns the expected count is
    1 000 and the binomial standard deviation is sqrt(16000/16 * 15/16) ~= 30.6,
    so the 5 sigma band is 847..1153.
    """
    from collections import Counter

    counter: Counter[str] = Counter()
    for seed in range(4000):  # 4000 casts x 4 Mothers = 16 000 figures
        result = service.cast_geomancy(seed=seed)
        for i in range(1, 5):
            counter["".join(str(v) for v in result["figures"][f"Mother {i}"]["pattern"])] += 1

    total = sum(counter.values())
    assert total == 16_000
    expected = total / 16
    sigma = (total * (1 / 16) * (15 / 16)) ** 0.5
    low, high = expected - 5 * sigma, expected + 5 * sigma
    assert len(counter) == 16, f"only {len(counter)} distinct patterns appeared"
    for pattern, count in counter.items():
        assert low <= count <= high, f"pattern {pattern}: {count} outside 5 sigma ({low:.0f}..{high:.0f})"
