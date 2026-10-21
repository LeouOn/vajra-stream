"""GEO-2 T3: a tarot spread must never SILENTLY drop its positions.

RED-first. ``draw_tarot`` attaches a ``position`` key only for the indices
covered by ``SPREAD_POSITIONS``, so a spread of 2, 4, 6, 7, 8 or 9 cards came
back with the right number of cards and NO position metadata at all -- no
error, no warning, just a plain list. ``draw_tarot_spread`` returned an empty
``spread`` list for those sizes.

The supported sizes (1, 3, 5, 10) must be completely unchanged.

Offline and deterministic: a fixed seed makes every draw reproducible.
"""

from __future__ import annotations

import pytest

from backend.core.services.divination_service import SPREAD_POSITIONS, DivinationService

SUPPORTED = sorted(SPREAD_POSITIONS)
UNSUPPORTED = [2, 4, 6, 7, 8, 9]
POSITION_KEYS = {"id", "name", "position", "label"}


@pytest.fixture
def service() -> DivinationService:
    return DivinationService()


def test_supported_sizes_are_unchanged(service: DivinationService) -> None:
    """1, 3, 5 and 10 keep their documented positions exactly."""
    for count in SUPPORTED:
        cards = service.draw_tarot(count=count, seed=11)
        assert len(cards) == count
        for index, card in enumerate(cards):
            assert "position" in card, f"{count}-card draw, card {index} lost its position"
            assert card["position"] == SPREAD_POSITIONS[count][index]


def test_unsupported_sizes_still_return_the_cards(service: DivinationService) -> None:
    """Backward compatibility: the cards come back, and the count is right."""
    for count in UNSUPPORTED:
        cards = service.draw_tarot(count=count, seed=11)
        assert len(cards) == count, f"a {count}-card draw returned {len(cards)} cards"


@pytest.mark.parametrize("count", UNSUPPORTED)
def test_unsupported_sizes_give_every_card_a_position(service: DivinationService, count: int) -> None:
    """The fix: no card may silently lack its position."""
    cards = service.draw_tarot(count=count, seed=11)

    assert len(cards) == count
    for index, card in enumerate(cards):
        assert "position" in card, f"card {index} of a {count}-card draw has no position"
        position = card["position"]
        assert set(position) == POSITION_KEYS, f"card {index}: position shape {sorted(position)}"
        assert position["id"] == index + 1, "the position id must be the 1-based index"
        assert position["name"], "the position must have a name"


@pytest.mark.parametrize("count", UNSUPPORTED)
def test_generic_positions_do_not_invent_meanings(service: DivinationService, count: int) -> None:
    """A generic position must not claim to be a known layout."""
    cards = service.draw_tarot(count=count, seed=11)
    for index, card in enumerate(cards):
        position = card["position"]
        assert position["name"] == f"Card {index + 1}"
        # It must not be one of the named layout positions.
        named = {p["name"] for positions in SPREAD_POSITIONS.values() for p in positions}
        assert position["name"] not in named


@pytest.mark.parametrize("count", UNSUPPORTED)
def test_spread_result_says_it_is_a_custom_layout(service: DivinationService, count: int) -> None:
    """The spread envelope must say so, additively."""
    result = service.draw_tarot_spread(count=count, seed=11)

    assert result["count"] == count
    assert result["is_custom_layout"] is True
    # and the flag is what a consumer keys off
    assert result.get("is_custom_layout") is True
    # the spread list must now carry the generic positions, not be empty
    assert len(result["spread"]) == count
    for index, position in enumerate(result["spread"]):
        assert position["id"] == index + 1
        assert position["name"] == f"Card {index + 1}"


@pytest.mark.parametrize("count", SUPPORTED)
def test_spread_result_marks_known_layouts_as_not_custom(service: DivinationService, count: int) -> None:
    result = service.draw_tarot_spread(count=count, seed=11)

    # A named layout has nothing new to say, so the envelope keeps its exact
    # existing key set -- the flag appears only where it carries information.
    assert "is_custom_layout" not in result
    assert result.get("is_custom_layout") is None
    assert len(result["spread"]) == count
    for index, position in enumerate(result["spread"]):
        assert position["name"] == SPREAD_POSITIONS[count][index]["name"]


def test_spread_result_keeps_its_existing_keys(service: DivinationService) -> None:
    """Additive only: the existing keys and their types are untouched."""
    result = service.draw_tarot_spread(count=3, seed=11)

    for key in ("cards", "count", "spread"):
        assert key in result
    assert isinstance(result["cards"], list)
    assert isinstance(result["count"], int)
    assert isinstance(result["spread"], list)
    assert isinstance(result["cards"][0], dict)


def test_out_of_range_counts_keep_their_clamp(service: DivinationService) -> None:
    """The count clamp is unchanged by this ticket."""
    assert len(service.draw_tarot(count=0, seed=11)) == 0
    assert len(service.draw_tarot(count=-5, seed=11)) == 0
    assert len(service.draw_tarot(count=78, seed=11)) == 78
    assert len(service.draw_tarot(count=79, seed=11)) == 78
    assert len(service.draw_tarot(count=200, seed=11)) == 78


def test_zero_cards_get_no_positions(service: DivinationService) -> None:
    """A zero-card draw has nothing to position."""
    assert service.draw_tarot(count=0, seed=11) == []
    result = service.draw_tarot_spread(count=0, seed=11)
    assert result["count"] == 0
    assert result["spread"] == []


# ---------------------------------------------------------------------------
# GEO-2b (1): the HTTP envelope must agree with the cards it carries
# ---------------------------------------------------------------------------
#
# The route built its own envelope and filled ``spread`` straight from
# SPREAD_POSITIONS, so for an unnamed size the HTTP response had
# ``spread: []`` while every card in the same response carried a position.
# The service's draw_tarot_spread() already got this right; the route did not
# use it.


async def test_http_tarot_draw_envelope_fills_the_spread_for_an_unnamed_size() -> None:
    """The route and the service must say the same thing."""
    from backend.app.api.v1.endpoints.divination import DrawTarotRequest, draw_tarot

    response = await draw_tarot(DrawTarotRequest(count=2))

    assert response["count"] == 2
    assert len(response["spread"]) == 2, f"the envelope spread is {response['spread']}"
    assert response["spread"][0]["name"] == "Card 1"
    assert response["spread"][1]["name"] == "Card 2"
    # and it agrees with the positions on the cards themselves
    for index, card in enumerate(response["cards"]):
        assert card["position"]["name"] == response["spread"][index]["name"]
        assert card["position"]["id"] == response["spread"][index]["id"]


async def test_http_tarot_draw_named_layouts_keep_their_exact_key_set() -> None:
    """The named layouts must not gain or lose a key."""
    from backend.app.api.v1.endpoints.divination import DrawTarotRequest, draw_tarot

    for count in (1, 3, 5, 10):
        response = await draw_tarot(DrawTarotRequest(count=count))
        assert set(response.keys()) == {
            "status",
            "cards",
            "count",
            "spread",
            "timestamp",
            "provenance",
        }, f"count={count} changed the envelope keys"
        assert len(response["spread"]) == count
        assert response["spread"][0]["name"] != "Card 1", "a named layout must keep its own names"


async def test_http_tarot_draw_matches_the_service_envelope() -> None:
    """The route and draw_tarot_spread must produce the same cards and spread."""
    from backend.app.api.v1.endpoints.divination import DrawTarotRequest, draw_tarot
    from backend.core.services.divination_service import divination_service

    response = await draw_tarot(DrawTarotRequest(count=7))
    service = divination_service.draw_tarot_spread(count=7)

    assert [p["name"] for p in response["spread"]] == [p["name"] for p in service["spread"]]
    assert response["count"] == service["count"]


# ---------------------------------------------------------------------------
# GEO-2b (2): an EMPTY draw has no layout, so it is not a custom one
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [0, -1, -5])
def test_an_empty_draw_is_not_marked_as_a_custom_layout(service: DivinationService, count: int) -> None:
    """A zero-card draw has no layout to be custom about."""
    result = service.draw_tarot_spread(count=count, seed=1)

    assert result["count"] == 0
    assert result["spread"] == []
    assert "is_custom_layout" not in result, "an empty draw must not be flagged as custom"


def test_a_non_empty_unnamed_draw_is_still_marked_custom(service: DivinationService) -> None:
    """The flag must survive for the case it is actually for."""
    result = service.draw_tarot_spread(count=2, seed=1)

    assert result["count"] == 2
    assert result["is_custom_layout"] is True
    assert len(result["spread"]) == 2
