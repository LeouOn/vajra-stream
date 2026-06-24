"""Tests for ``core.assessment`` — chakra, dosha, symptom, meridian utilities.

Covers the public API:
- :class:`ChakraAssessment` — 7-question-per-chakra evaluation.
- :class:`DoshaAssessment` — Vata/Pitta/Kapha self-assessment.
- :class:`SymptomTracker` — keyword→condition matcher.
- :func:`get_current_meridian` — Chinese Medicine Clock lookup.

The module is pure in-memory logic plus a lazy import of ``core.healing_systems``;
all tests exercise behavior against the real ``MeridianSystem`` (no mocks).
"""
from __future__ import annotations

from datetime import datetime

import pytest

from core.assessment import (
    ChakraAssessment,
    ChakraResult,
    DoshaAssessment,
    SymptomTracker,
    get_current_meridian,
)


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols."""
    import core.assessment as mod

    for name in (
        "ChakraResult",
        "ChakraAssessment",
        "DoshaAssessment",
        "SymptomTracker",
        "get_current_meridian",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. ChakraAssessment
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chakra_assessment_evaluate_max_scores_produces_ten_point_result():
    """All 5s → normalised score 10/10 with the 'well-balanced' interpretation."""
    assess = ChakraAssessment()

    results = assess.evaluate({"muladhara": [5, 5, 5, 5, 5, 5, 5]})

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ChakraResult)
    assert r.chakra_name == "muladhara"
    assert r.english_name == "Root Chakra"
    assert r.score == 10.0
    assert r.interpretation == "Well-balanced and flowing freely."


@pytest.mark.unit
def test_chakra_assessment_evaluate_rejects_wrong_length_list():
    """``evaluate`` must raise ValueError when the answer list is not 7 long."""
    assess = ChakraAssessment()

    with pytest.raises(ValueError, match="Expected 7 answers for anahata"):
        assess.evaluate({"anahata": [4, 4, 4]})  # only 3 answers

    with pytest.raises(ValueError, match="Expected 7 answers for manipura"):
        assess.evaluate({"manipura": [1] * 8})  # 8 answers — too many


@pytest.mark.unit
def test_chakra_assessment_list_chakras_returns_sorted_sanskrit_names():
    """``list_chakras`` returns all 7 Sanskrit chakra names alphabetically."""
    assess = ChakraAssessment()

    names = assess.list_chakras()

    assert names == sorted([
        "muladhara",
        "svadhisthana",
        "manipura",
        "anahata",
        "vishuddha",
        "ajna",
        "sahasrara",
    ])
    assert len(names) == 7
    # Questions must be retrievable for each listed chakra
    for n in names:
        questions = assess.get_questions(n)
        assert len(questions) == 7, f"{n} should have 7 questions"
    # Unknown chakra → empty list
    assert assess.get_questions("not_a_real_chakra") == []


@pytest.mark.unit
def test_chakra_assessment_evaluate_unknown_chakra_falls_back_to_sanskrit_name():
    """Unknown chakra names use the Sanskrit name as the English fallback."""
    assess = ChakraAssessment()

    results = assess.evaluate({"foo_bar": [3, 3, 3, 3, 3, 3, 3]})

    assert results[0].english_name == "foo_bar"
    # Normalised: sum=21 → ((21-7)/(35-7))*10 = (14/28)*10 = 5.0
    assert results[0].score == 5.0
    # 5.0 falls in the >= 4.0 "moderately imbalanced" bucket
    assert "Moderately imbalanced" in results[0].interpretation


# ---------------------------------------------------------------------------
# 3. DoshaAssessment
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dosha_assessment_evaluate_returns_dominant_and_percentages():
    """``evaluate`` returns the dominant dosha, percentages, and a breakdown dict."""
    assess = DoshaAssessment()

    # Vata-heavy profile
    answers = {
        "vata": [5, 5, 5, 5, 5, 4, 5, 5, 5, 5],  # 49
        "pitta": [2, 2, 2, 2, 2, 3, 2, 2, 2, 2],  # 21
        "kapha": [2, 2, 2, 2, 2, 3, 2, 2, 2, 2],  # 21
    }

    result = assess.evaluate(answers)

    assert result["dominant"] == "vata"
    assert result["vata_pct"] == pytest.approx(53.8, abs=0.1)
    assert result["pitta_pct"] == pytest.approx(23.1, abs=0.1)
    assert result["kapha_pct"] == pytest.approx(23.1, abs=0.1)
    assert result["breakdown"] == {"vata": 49, "pitta": 21, "kapha": 21}


@pytest.mark.unit
def test_dosha_assessment_evaluate_rejects_wrong_length_list():
    """``evaluate`` must raise ValueError when any dosha list is not 10 long."""
    assess = DoshaAssessment()

    with pytest.raises(ValueError, match="Expected 10 answers for vata"):
        assess.evaluate({"vata": [1, 2, 3]})

    with pytest.raises(ValueError, match="Expected 10 answers for kapha"):
        assess.evaluate({
            "vata": [3] * 10,
            "pitta": [3] * 10,
            "kapha": [3] * 11,
        })


@pytest.mark.unit
def test_dosha_assessment_evaluate_zero_totals_returns_unknown_dominant():
    """When every total is 0, the function returns 'unknown' with 0% across the board."""
    assess = DoshaAssessment()

    result = assess.evaluate({
        "vata": [0] * 10,
        "pitta": [0] * 10,
        "kapha": [0] * 10,
    })

    assert result["dominant"] == "unknown"
    assert result["vata_pct"] == 0.0
    assert result["pitta_pct"] == 0.0
    assert result["kapha_pct"] == 0.0
    assert result["breakdown"] == {"vata": 0, "pitta": 0, "kapha": 0}


# ---------------------------------------------------------------------------
# 4. SymptomTracker
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_symptom_tracker_match_dedupes_and_handles_substring_matches():
    """``match`` is case-insensitive, handles substrings, and dedupes conditions."""
    tracker = SymptomTracker()

    # Substring: "head pain" → "headache"; exact: "anxious" → "anxiety"
    matched = tracker.match(["ANXIOUS", "head pain", "I feel anxious"])

    # All map to anxiety + headache — dedupe yields exactly two conditions
    assert set(matched) == {"anxiety", "headache"}


@pytest.mark.unit
def test_symptom_tracker_match_returns_empty_for_no_matches():
    """Free text with no recognised keyword returns an empty list."""
    tracker = SymptomTracker()

    assert tracker.match(["this is unrelated text", "another thing"]) == []
    assert tracker.match([]) == []


@pytest.mark.unit
def test_symptom_tracker_get_keywords_returns_sorted_unique_list():
    """``get_keywords`` returns all known keywords as a sorted list (unique)."""
    tracker = SymptomTracker()

    keywords = tracker.get_keywords()

    assert isinstance(keywords, list)
    assert keywords == sorted(keywords)
    # Every keyword is a non-empty string
    assert all(isinstance(k, str) and k for k in keywords)
    # The keyword map must be a strict superset of these
    assert set(keywords) == set(tracker.KEYWORD_MAP.keys())


# ---------------------------------------------------------------------------
# 5. get_current_meridian
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_current_meridian_uses_meridian_system_for_given_hour():
    """``get_current_meridian`` delegates to ``MeridianSystem`` based on ``dt.hour``."""
    # 3 AM → lung; 12 PM (noon) → heart; 22:00 → triple_warmer (21-23 window);
    # midnight (00:00) → gallbladder (23-01 window)
    assert get_current_meridian(datetime(2026, 6, 24, 3, 0)) == "lung"
    assert get_current_meridian(datetime(2026, 6, 24, 12, 0)) == "heart"
    assert get_current_meridian(datetime(2026, 6, 24, 22, 0)) == "triple_warmer"
    assert get_current_meridian(datetime(2026, 6, 24, 0, 0)) == "gallbladder"
