"""Tests for core/auspicious_timing.py Bodhicitta transmutations."""

import pytest

from core.auspicious_timing import AuspiciousTiming


@pytest.fixture
def timing():
    return AuspiciousTiming(astrology_engine=None)


BODHICITTA_GENRES = [
    "healing",
    "compassion",
    "wisdom",
    "creativity",
    "prosperity",
    "protection",
    "victory",
]


def test_bodhicitta_transmutations_exist_for_all_genres(timing):
    for genre in BODHICITTA_GENRES:
        result = timing._get_transmutation(genre, "Bodhicitta")
        assert result is not None, f"missing Bodhicitta transmutation for genre={genre}"
        assert isinstance(result, tuple), f"expected tuple for {genre}, got {type(result)}"
        assert len(result) == 2, f"expected (message, mantra) 2-tuple for {genre}"


def test_bodhicitta_transmutations_have_non_empty_message_and_mantra(timing):
    for genre in BODHICITTA_GENRES:
        message, mantra = timing._get_transmutation(genre, "Bodhicitta")
        assert isinstance(message, str) and len(message) > 20, f"{genre}: message too short: {message!r}"
        assert isinstance(mantra, str) and len(mantra) > 5, f"{genre}: mantra too short: {mantra!r}"
        assert mantra.startswith("Om ") or mantra.startswith(
            "Gate "
        ), f"{genre}: mantra should start with 'Om ' or 'Gate ': {mantra!r}"


def test_bodhicitta_messages_reference_bodhicitta_or_bodhisattva(timing):
    keywords = ("bodhicitta", "bodhisattva", "awakened", "compassion")
    for genre in BODHICITTA_GENRES:
        message, _ = timing._get_transmutation(genre, "Bodhicitta")
        msg_lower = message.lower()
        assert any(
            kw in msg_lower for kw in keywords
        ), f"{genre}: message should mention bodhicitta/bodhisattva: {message!r}"


def test_bodhicitta_mantras_are_known_phrases(timing):
    known_phrase_substrings = (
        "Mani Padme Hum",
        "Gate Paragate",
        "Vajrasattva",
        "Ah Hum",
        "Vajra Guru",
        "Dzambhala",
        "Tare Tuttare",
    )
    for genre in BODHICITTA_GENRES:
        _, mantra = timing._get_transmutation(genre, "Bodhicitta")
        assert any(
            sub in mantra for sub in known_phrase_substrings
        ), f"{genre}: mantra {mantra!r} doesn't match any known phrase"


def test_bodhicitta_uses_unique_mantras_across_genres(timing):
    mantras = [timing._get_transmutation(g, "Bodhicitta")[1] for g in BODHICITTA_GENRES]
    assert len(set(mantras)) >= 4, f"expected at least 4 distinct mantras, got {len(set(mantras))} from {mantras}"


def test_non_bodhicitta_combinations_still_work(timing):
    result = timing._get_transmutation("healing", "Sun")
    assert result is not None
    message, mantra = result
    assert "Sun" in message or "sun" in message.lower()


def test_unknown_combination_returns_generic_fallback(timing):
    message, mantra = timing._get_transmutation("nonexistent_genre", "Pluto")
    assert "Pluto" in message
    assert mantra.startswith("Om ")
