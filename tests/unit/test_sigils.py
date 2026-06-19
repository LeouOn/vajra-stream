"""
Unit tests for the Sigil Generation Service
"""

from backend.core.services.sigil_service import sigil_service


def test_letter_reduction():
    # 'Vajra Stream' -> V, J, R, S, T, M (removes A, E, I, O, U, duplicate R, space)
    reduced = sigil_service.reduce_text("Vajra Stream")
    assert reduced == "VJRSTM"

    # Empty string should handle gracefully
    empty_reduced = sigil_service.reduce_text("")
    assert empty_reduced == ""


def test_coordinates_mapping():
    # Test Saturn Kamea
    coords = sigil_service.text_to_coordinates("Vajra Stream", "saturn")
    assert len(coords) > 0
    for pt in coords:
        assert 0 <= pt["x"] < 3
        assert 0 <= pt["y"] < 3
        assert 1 <= pt["value"] <= 9

    # Test Mars Kamea
    coords_mars = sigil_service.text_to_coordinates("Vajra Stream", "mars")
    assert len(coords_mars) > 0
    for pt in coords_mars:
        assert 0 <= pt["x"] < 5
        assert 0 <= pt["y"] < 5
        assert 1 <= pt["value"] <= 25


def test_svg_generation():
    svg = sigil_service.generate_kamea_svg("Protection", "saturn")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert 'filter="url(#glow)"' in svg
    assert 'stroke="#00ffff"' in svg
