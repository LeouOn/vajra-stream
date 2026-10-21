"""IR-2: the relating (transformed) hexagram and a seedable cast.

RED-first. The defect is in ``DivinationService.cast_i_ching``:

    relating_pattern = [1 if (v == 7 or v == 8) else (0 if v == 6 else 1) for v in lines]

which maps 8 -> 1 (young yin stays yang), 6 -> 0 (old yin does NOT become yang)
and 9 -> 1 (old yang does NOT become yin). Only 7 is correct, so ~11/16 of lines
are wrong and the relating hexagram is wrong on nearly every cast. The worst case
is a cast with no changing lines at all, where relating MUST equal primary:

    lines=[7,8,7,8,7,8]  primary=101010 (After Completion)
                         relating=111111 (The Creative)   <-- nonsense
                         correct=101010 (After Completion)

The correct rule: a line is yang (1) when its value is 7 or 6, yin (0) when it
is 8 or 9. Equivalently ``relating == primary XOR changing``.

Offline and deterministic: the provider of randomness is monkeypatched, and the
seeded path uses ``random.Random``. Nothing here touches the network or the DB.
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest

from backend.core.services import divination_service as ds_mod
from backend.core.services.divination_service import DivinationService

# rnd (a 0..15 draw) -> line value, per the yarrow method's probabilities.
# 6: 1/16, 7: 5/16, 8: 7/16, 9: 3/16.
DRAW_FOR_VALUE = {6: 0, 7: 1, 8: 6, 9: 13}
VALUE_FOR_DRAW = {0: 6}
for _n in range(1, 6):
    VALUE_FOR_DRAW[_n] = 7
for _n in range(6, 13):
    VALUE_FOR_DRAW[_n] = 8
for _n in range(13, 16):
    VALUE_FOR_DRAW[_n] = 9


@pytest.fixture
def service() -> DivinationService:
    return DivinationService()


@pytest.fixture(autouse=True)
def no_svg(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip SVG rendering.

    ``cast_i_ching`` renders an SVG on every call, and the property test calls it
    4096 times. The SVG is not what these tests are about.
    """
    monkeypatch.setattr(service, "_render_hexagram_svg", lambda *args: "<svg/>")


def force_lines(monkeypatch: pytest.MonkeyPatch, lines: list[int]) -> None:
    """Make the next six draws produce exactly ``lines``."""
    draws = [DRAW_FOR_VALUE[v] for v in lines]
    queue = iter(draws)
    monkeypatch.setattr(ds_mod.secrets, "randbelow", lambda n: next(queue))


def expected_primary(lines: list[int]) -> list[int]:
    """Yang for 7 and 9, yin for 6 and 8."""
    return [1 if v in (7, 9) else 0 for v in lines]


def expected_relating(lines: list[int]) -> list[int]:
    """Yang for 7 and 6, yin for 8 and 9 -- i.e. primary XOR changing."""
    return [1 if v in (6, 7) else 0 for v in lines]


def pattern_of(details: dict[str, Any]) -> str:
    return str(details["pattern"])


# ---------------------------------------------------------------------------
# 1. the forced vector from the row
# ---------------------------------------------------------------------------


def test_forced_vector_gives_the_documented_relating_pattern(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    force_lines(monkeypatch, [6, 7, 8, 9, 7, 8])

    result = service.cast_i_ching()

    assert pattern_of(result["primary"]) == "010110"
    assert pattern_of(result["relating"]) == "110010"


def test_every_single_line_value_transforms_correctly(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A line is correct only for 7 today; each value is checked on its own."""
    for value, want in ((6, "1"), (7, "1"), (8, "0"), (9, "0")):
        force_lines(monkeypatch, [value] * 6)
        result = service.cast_i_ching()
        relating = pattern_of(result["relating"])
        assert relating == want * 6, f"value {value}: relating {relating}, want {want * 6}"


# ---------------------------------------------------------------------------
# 2. property test over ALL 4**6 line vectors
# ---------------------------------------------------------------------------


def test_relating_is_primary_xor_changing_for_all_line_vectors(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every one of the 4096 possible casts.

    This is the property the rule encodes, checked exhaustively rather than by
    sampling: no vector may produce a relating pattern that is not the primary
    with its changing lines flipped.
    """
    wrong: list[str] = []
    for lines in itertools.product((6, 7, 8, 9), repeat=6):
        values = list(lines)
        force_lines(monkeypatch, values)
        result = service.cast_i_ching()
        got = pattern_of(result["relating"])
        want = "".join(str(b) for b in expected_relating(values))
        if got != want:
            wrong.append(f"{values}: got {got} want {want}")
            if len(wrong) >= 5:
                break
    assert not wrong, "relating != primary XOR changing: " + "; ".join(wrong)


def test_names_are_read_back_from_iching_json_for_every_vector(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both names must match the JSON entry for the reported pattern."""
    by_pattern = {hexagram["pattern"]: hexagram for hexagram in service._load_iching()}
    assert len(by_pattern) == 64, "iching.json must carry all 64 patterns"

    mismatched: list[str] = []
    for lines in itertools.product((6, 7, 8, 9), repeat=6):
        values = list(lines)
        force_lines(monkeypatch, values)
        result = service.cast_i_ching()
        for role in ("primary", "relating"):
            got = pattern_of(result[role])
            entry = by_pattern.get(got)
            if entry is None or result[role]["name_english"] != entry["name_english"]:
                mismatched.append(f"{values} {role}: {got} -> {result[role]['name_english']}")
                if len(mismatched) >= 5:
                    break
        if len(mismatched) >= 5:
            break
    assert not mismatched, "; ".join(mismatched)


# ---------------------------------------------------------------------------
# 3. golden pairs
# ---------------------------------------------------------------------------


def test_six_old_yang_gives_creative_to_receptive(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    force_lines(monkeypatch, [9] * 6)
    result = service.cast_i_ching()
    assert result["primary"]["name_english"] == "The Creative"
    assert result["relating"]["name_english"] == "The Receptive"
    assert result["changing_lines"] == [1, 2, 3, 4, 5, 6]


def test_six_old_yin_gives_receptive_to_creative(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    force_lines(monkeypatch, [6] * 6)
    result = service.cast_i_ching()
    assert result["primary"]["name_english"] == "The Receptive"
    assert result["relating"]["name_english"] == "The Creative"


def test_no_changing_lines_means_relating_equals_primary(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression that shows the old rule at its worst."""
    for lines in ([7, 8, 7, 8, 7, 8], [8, 7, 8, 7, 8, 7], [7] * 6, [8] * 6):
        force_lines(monkeypatch, lines)
        result = service.cast_i_ching()
        assert result["has_changes"] is False
        assert pattern_of(result["relating"]) == pattern_of(result["primary"]), lines
        assert result["relating"]["name_english"] == result["primary"]["name_english"]


def test_a_single_changing_line_flips_exactly_one_position(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    lines = [7, 7, 9, 7, 8, 8]
    force_lines(monkeypatch, lines)
    result = service.cast_i_ching()
    primary = expected_primary(lines)
    relating = expected_relating(lines)
    differing = [i for i in range(6) if primary[i] != relating[i]]
    assert differing == [2], "only the changing line may differ"
    assert result["changing_lines"] == [3]


# ---------------------------------------------------------------------------
# 4. the optional seed
# ---------------------------------------------------------------------------


def test_same_seed_gives_the_same_cast(service: DivinationService) -> None:
    first = service.cast_i_ching(seed=1234)
    second = service.cast_i_ching(seed=1234)
    assert first["cast_lines"] == second["cast_lines"]
    assert pattern_of(first["primary"]) == pattern_of(second["primary"])
    assert pattern_of(first["relating"]) == pattern_of(second["relating"])


def test_different_seeds_differ_across_a_sample(service: DivinationService) -> None:
    casts = {tuple(service.cast_i_ching(seed=seed)["cast_lines"]) for seed in range(40)}
    assert len(casts) > 30, f"40 seeds produced only {len(casts)} distinct casts"


def test_seed_none_still_uses_the_secrets_draw(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default behaviour unchanged: with no seed the cryptographic draw is used."""
    calls = {"n": 0}

    def counting_randbelow(n: int) -> int:
        calls["n"] += 1
        return 7  # rnd 7 -> line value 8

    monkeypatch.setattr(ds_mod.secrets, "randbelow", counting_randbelow)

    result = service.cast_i_ching()

    assert calls["n"] == 6, "the secrets path must still draw six times"
    assert result["cast_lines"] == [8] * 6


def test_seeded_draw_does_not_touch_secrets(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(n: int) -> int:
        raise AssertionError("the seeded path must not use secrets.randbelow")

    monkeypatch.setattr(ds_mod.secrets, "randbelow", explode)

    result = service.cast_i_ching(seed=7)
    assert len(result["cast_lines"]) == 6


def test_seeded_line_values_are_all_valid(service: DivinationService) -> None:
    for seed in range(200):
        lines = service.cast_i_ching(seed=seed)["cast_lines"]
        assert len(lines) == 6
        assert set(lines) <= {6, 7, 8, 9}, f"seed {seed} produced {lines}"


# ---------------------------------------------------------------------------
# 5. yarrow frequencies
# ---------------------------------------------------------------------------


def test_yarrow_frequencies_over_16000_seeded_draws(service: DivinationService) -> None:
    """6: 1/16, 7: 5/16, 8: 7/16, 9: 3/16, within 3 percentage points."""
    expected = {6: 1 / 16, 7: 5 / 16, 8: 7 / 16, 9: 3 / 16}
    draws: list[int] = []
    for seed in range(2667):  # 2667 * 6 = 16002 draws
        draws.extend(service.cast_i_ching(seed=seed)["cast_lines"])
    assert len(draws) == 16002

    for value, want in expected.items():
        share = draws.count(value) / len(draws)
        assert abs(share - want) <= 0.03, f"value {value}: {share:.4f} vs {want:.4f}"


# ---------------------------------------------------------------------------
# 6. the additive keys from knowledge/iching.json
# ---------------------------------------------------------------------------


def test_hexagram_details_surface_trigram_and_element_data(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    by_pattern = {hexagram["pattern"]: hexagram for hexagram in service._load_iching()}

    force_lines(monkeypatch, [7] * 6)  # The Creative
    result = service.cast_i_ching()
    primary = result["primary"]
    entry = by_pattern[pattern_of(primary)]

    assert primary["lower_trigram"] == entry["lower_trigram"]
    assert primary["upper_trigram"] == entry["upper_trigram"]
    assert primary["element"] == entry["element"]
    assert primary["keywords"] == entry["keywords"]
    assert primary["element"] == "Metal"


def test_new_keys_are_present_on_both_hexagrams_and_every_pattern(
    service: DivinationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing: list[str] = []
    for lines in itertools.product((6, 7, 8, 9), repeat=6):
        force_lines(monkeypatch, list(lines))
        result = service.cast_i_ching()
        for role in ("primary", "relating"):
            for key in ("lower_trigram", "upper_trigram", "element", "keywords"):
                if key not in result[role]:
                    missing.append(f"{lines} {role} missing {key}")
        if len(missing) >= 5:
            break
    assert not missing, "; ".join(missing)


def test_existing_keys_and_types_are_unchanged(service: DivinationService, monkeypatch: pytest.MonkeyPatch) -> None:
    """Additive only: everything that was there before is still there."""
    force_lines(monkeypatch, [6, 7, 8, 9, 7, 8])
    result = service.cast_i_ching()

    assert isinstance(result["cast_lines"], list)
    assert isinstance(result["primary"], dict)
    assert isinstance(result["relating"], dict)
    assert isinstance(result["changing_lines"], list)
    assert isinstance(result["changing_lines_details"], list)
    assert isinstance(result["has_changes"], bool)
    assert isinstance(result["svg"], str)
    for role in ("primary", "relating"):
        for key in (
            "pattern",
            "name",
            "name_chinese",
            "name_pinyin",
            "name_english",
            "meaning",
            "judgment",
            "images",
            "lines",
        ):
            assert key in result[role], f"{role} lost {key}"
