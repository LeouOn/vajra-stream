"""
Unit tests for the Divination Service
"""

import pytest
from backend.core.services.divination_service import divination_service

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
    assert len(result["figures"]) == 16  # Mothers (4) + Daughters (4) + Nieces (4) + Witnesses (2) + Judge (1) + Reconciler (1)
    
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
