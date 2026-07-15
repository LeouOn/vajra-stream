"""
Unit tests for the Divination Service
"""

import importlib.util
import os

# backend.core.services.__init__ eagerly imports vajra_service, which has a
# pre-existing circular import through the API endpoint layer. The repo's own
# tests/conftest.py documents the same problem (see the "_deterministic_geocoding"
# fixture) and solves it by loading the service module by file path via importlib
# to side-step the package __init__ chain. We do the same here so the divination
# tests run in any environment — and fall back to the canonical import when the
# package chain is clean.

_divination_service = None
try:
    from backend.core.services.divination_service import (  # type: ignore
        SPREAD_POSITIONS,
        divination_service,
    )
except ImportError:  # pragma: no cover — exercised only in environments with the circular import
    _here = os.path.dirname(os.path.abspath(__file__))
    _mod_path = os.path.join(
        os.path.dirname(os.path.dirname(_here)),
        "backend",
        "core",
        "services",
        "divination_service.py",
    )
    _spec = importlib.util.spec_from_file_location("_test_divination_service", _mod_path)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mod)
    divination_service = _mod.divination_service
    SPREAD_POSITIONS = _mod.SPREAD_POSITIONS


# ---------------------------------------------------------------------------
# Original tests (preserved for backward compatibility)
# ---------------------------------------------------------------------------


def test_tarot_drawing():
    # Test drawing 1 card
    cards = divination_service.draw_tarot(1)
    assert len(cards) == 1
    assert "name" in cards[0]
    assert "reversed" in cards[0]
    assert "svg" in cards[0]

    # Test drawing 3 cards
    spread = divination_service.draw_tarot(3)
    assert len(spread) == 3
    # Check that they are unique cards
    drawn_ids = [card["id"] for card in spread]
    assert len(set(drawn_ids)) == 3


def test_iching_casting():
    result = divination_service.cast_i_ching()
    assert "cast_lines" in result
    assert len(result["cast_lines"]) == 6
    for val in result["cast_lines"]:
        assert val in [6, 7, 8, 9]

    assert "primary" in result
    assert "relating" in result
    assert len(result["primary"]["pattern"]) == 6
    assert "svg" in result


def test_geomancy_casting():
    result = divination_service.cast_geomancy()
    assert "figures" in result
    assert "houses" in result
    assert (
        len(result["figures"]) == 16
    )  # Mothers (4) + Daughters (4) + Nieces (4) + Witnesses (2) + Judge (1) + Reconciler (1)

    # Test calculation mod 2 parity
    # Mother 1 + Mother 2 -> Niece 1
    m1 = result["figures"]["Mother 1"]["pattern"]
    m2 = result["figures"]["Mother 2"]["pattern"]
    n1 = result["figures"]["Niece 1"]["pattern"]

    for a, b, res in zip(m1, m2, n1):
        expected = 2 if (a + b) % 2 == 0 else 1
        assert res == expected

    # Check house projections
    assert len(result["houses"]) == 12
    assert result["houses"][1]["pattern"] == m1


# ---------------------------------------------------------------------------
# Phase 5 — comprehensive deck / SVG / spread / RNG tests
# ---------------------------------------------------------------------------


def test_full_deck_loads_78_cards_from_json():
    """All 78 cards (22 Major + 56 Minor) load from knowledge/tarot_deck.json."""
    deck = divination_service.deck
    assert len(deck) == 78, f"expected 78 cards, got {len(deck)}"

    major = [c for c in deck if c["arcana"] == "major"]
    minor = [c for c in deck if c["arcana"] == "minor"]
    assert len(major) == 22
    assert len(minor) == 56

    # All 4 suits present with 14 cards each (Ace, 2-10, Page, Knight, Queen, King).
    from collections import Counter

    suit_counts = Counter(c.get("suit") for c in minor)
    for suit in ("Wands", "Cups", "Swords", "Pentacles"):
        assert suit_counts[suit] == 14, f"{suit} has {suit_counts[suit]} cards"

    # Every card has the required fields.
    required = {"id", "name", "arcana", "number", "element", "keywords", "upright", "reversed", "desc"}
    for card in deck:
        missing = required - set(card.keys())
        assert not missing, f"card {card.get('id')} missing fields: {missing}"

    # All IDs are unique.
    ids = [c["id"] for c in deck]
    assert len(set(ids)) == 78


def test_reversed_cards_use_reversed_meaning():
    """When a card is drawn reversed, ``meaning`` equals the source reversed text,
    and when upright it equals the upright text (not the wrong orientation)."""
    # Draw a deterministic set; check every card against its source deck entry.
    drawn = divination_service.draw_tarot(20, seed=12345)
    deck_by_id = {c["id"]: c for c in divination_service.deck}
    assert len(drawn) == 20

    for card in drawn:
        source = deck_by_id[card["id"]]
        if card["reversed"]:
            assert card["meaning"] == source["reversed"], f"{card['name']} reversed should use reversed meaning"
        else:
            assert card["meaning"] == source["upright"], f"{card['name']} upright should use upright meaning"
        # The reversed boolean stays a real boolean (backward compat).
        assert isinstance(card["reversed"], bool)
        # The reversed meaning text is preserved under an unambiguous key.
        assert card.get("reversed_meaning") == source["reversed"]


def test_reversed_and_upright_meanings_differ():
    """No card has identical upright and reversed text — there must be a real
    distinction for every one of the 78 cards."""
    for card in divination_service.deck:
        upright = card.get("upright", "")
        reversed_text = card.get("reversed", "")
        assert upright.strip(), f"{card['id']} has empty upright meaning"
        assert reversed_text.strip(), f"{card['id']} has empty reversed meaning"
        # Normalised comparison so trivial whitespace differences don't mask real gaps.
        assert upright.strip() != reversed_text.strip(), (
            f"{card['id']} ({card['name']}) has identical upright/reversed meanings"
        )


def test_spread_positions_for_1_3_and_10_cards():
    """Known spread layouts are returned for 1, 3, and 10-card draws, and each
    drawn card carries its position metadata."""
    for count in (1, 3, 10):
        positions = SPREAD_POSITIONS[count]
        assert len(positions) == count
        # Each position has the documented shape.
        for pos in positions:
            assert {"id", "name", "label"} <= set(pos.keys())

        drawn = divination_service.draw_tarot(count, seed=42)
        assert len(drawn) == count
        for i, card in enumerate(drawn):
            assert "position" in card, f"card {i} of {count}-draw missing position"
            assert card["position"]["name"] == positions[i]["name"]

    # 3-card spread labels are Past/Present/Future.
    names = [p["name"] for p in SPREAD_POSITIONS[3]]
    assert names == ["Past", "Present", "Future"]

    # 10-card Celtic Cross includes the documented positions.
    cc_names = [p["name"] for p in SPREAD_POSITIONS[10]]
    assert "Present" in cc_names and "Challenge" in cc_names and "Outcome" in cc_names


def test_draw_tarot_spread_envelope():
    """The convenience wrapper returns the {cards, count, spread} envelope."""
    env = divination_service.draw_tarot_spread(3, seed=7)
    assert set(env.keys()) == {"cards", "count", "spread"}
    assert env["count"] == 3
    assert len(env["cards"]) == 3
    assert len(env["spread"]) == 3
    assert env["spread"][0]["name"] == "Past"


def test_seed_reproducibility():
    """The same seed yields the same cards and orientations every time."""
    seed = 2024
    first = divination_service.draw_tarot(10, seed=seed)
    second = divination_service.draw_tarot(10, seed=seed)

    assert [c["id"] for c in first] == [c["id"] for c in second], "card order differs"
    assert [c["reversed"] for c in first] == [c["reversed"] for c in second], "orientations differ"
    # And the meanings match because orientations match.
    assert [c["meaning"] for c in first] == [c["meaning"] for c in second]


def test_seed_offers_variety():
    """Different seeds should generally produce different draws (sanity check
    that the seed actually parameterises the shuffle)."""
    a = divination_service.draw_tarot(5, seed=1)
    b = divination_service.draw_tarot(5, seed=2)
    assert [c["id"] for c in a] != [c["id"] for c in b]


def test_svg_is_unique_per_card():
    """Each of the 78 cards renders a distinct SVG (no generic shared artwork)."""
    svgs = []
    for card in divination_service.deck:
        rendered = divination_service._render_tarot_card_svg({**card, "orientation": "upright"})
        svgs.append(rendered)
    assert len(set(svgs)) == 78, "SVG artwork is not unique per card"


def test_svg_reversed_rotation():
    """A reversed card rotates its central artwork 180° around the card centre."""
    card = divination_service.deck[0]
    upright = divination_service._render_tarot_card_svg({**card, "orientation": "upright"})
    reversed_svg = divination_service._render_tarot_card_svg({**card, "orientation": "reversed"})
    assert "rotate(180 120 190)" in reversed_svg
    assert "rotate(180 120 190)" not in upright
    # Title text stays upright (readable) in both.
    assert card["name"] in reversed_svg


def test_svg_major_cards_have_unique_glyphs():
    """Major Arcana cards carry per-card glyph identifiers rather than the old
    generic circle+triangle that every card shared."""
    deck_by_number = {c["number"]: c for c in divination_service.deck if c["arcana"] == "major"}
    # The old generic artwork was a dashed circle + triangle; ensure none of the
    # new major glyphs include both of those exact primitives together.
    for number, card in deck_by_number.items():
        svg = divination_service._render_tarot_card_svg({**card, "orientation": "upright"})
        has_old_circle = 'stroke-dasharray="4,4"' in svg
        has_old_triangle = "120,115 155,190 85,190" in svg
        assert not (has_old_circle and has_old_triangle), (
            f"major card {number} ({card['name']}) still uses the generic artwork"
        )


def test_backward_compat_card_fields():
    """All consumers (outlook_generator, LLM tools, CommandCenter, OperationsPanel)
    depend on these fields existing on every drawn card."""
    card = divination_service.draw_tarot(1, seed=3)[0]
    for field in ("id", "name", "svg", "reversed", "meaning", "orientation", "element"):
        assert field in card, f"missing backward-compat field: {field}"
    # Hebrew/ruler present on major cards (and harmless if absent on minor).
    if card["arcana"] == "major":
        assert "hebrew" in card and "ruler" in card


def test_draw_respects_count_limit():
    """Cannot draw more cards than the deck holds."""
    too_many = divination_service.draw_tarot(999)
    assert len(too_many) == 78
    # All unique.
    assert len({c["id"] for c in too_many}) == 78


def test_iching_rich_database():
    """Test that I Ching database correctly loads rich attributes from iching.json."""
    assert hasattr(divination_service, "iching")
    assert len(divination_service.iching) == 64

    # Check a specific hexagram details
    details = divination_service._get_hexagram_details([1, 1, 1, 1, 1, 1])  # Qián
    assert details["name_chinese"] == "乾"
    assert details["name_pinyin"] == "Qián"
    assert details["name_english"] == "The Creative"
    assert "sublime success" in details["judgment"]
    assert "untiring" in details["images"]
    assert len(details["lines"]) == 6


def test_iching_changing_line_resolution():
    """Test that changing lines correctly resolve to specific line descriptions in the result."""
    result = divination_service.cast_i_ching()
    assert "changing_lines_details" in result

    # If there are changing lines, verify their structure
    if result["has_changes"]:
        for item in result["changing_lines_details"]:
            assert "line" in item
            assert "value" in item
            assert item["value"] in [6, 9]
            assert "meaning" in item
            assert len(item["meaning"]) > 0
