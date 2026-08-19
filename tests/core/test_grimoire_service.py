"""
Unit tests for GrimoireService multi-corpus indexing and search.
"""

from backend.core.services.grimoire_service import CORRESPONDENCES, grimoire_service


def test_grimoire_service_has_ten_planets():
    """GrimoireService should index 10 classical and modern planets."""
    assert len(CORRESPONDENCES) == 10
    assert "sun" in CORRESPONDENCES
    assert "moon" in CORRESPONDENCES
    assert "mercury" in CORRESPONDENCES
    assert "venus" in CORRESPONDENCES
    assert "mars" in CORRESPONDENCES
    assert "jupiter" in CORRESPONDENCES
    assert "saturn" in CORRESPONDENCES
    assert "uranus" in CORRESPONDENCES
    assert "neptune" in CORRESPONDENCES
    assert "pluto" in CORRESPONDENCES


def test_grimoire_categories_catalog():
    """Categories should list all 7 domains with item counts."""
    cats = grimoire_service.get_categories()
    keys = [c["key"] for c in cats]
    assert "all" in keys
    assert "planets" in keys
    assert "tarot" in keys
    assert "iching" in keys
    assert "mantras" in keys
    assert "sutras" in keys
    assert "frequencies" in keys

    # Verify counts
    all_cat = next(c for c in cats if c["key"] == "all")
    assert all_cat["count"] > 100


def test_grimoire_search_across_corpora():
    """Search should find entries across Tarot, I Ching, Mantras, Sutras, and Planets."""
    # 1. Search Tarot
    tarot_res = grimoire_service.search("Magician", category="tarot")
    assert len(tarot_res) > 0
    assert "Magician" in tarot_res[0]["title"]
    assert tarot_res[0]["category"] == "tarot"

    # 2. Search I Ching
    iching_res = grimoire_service.search("Creative", category="iching")
    assert len(iching_res) > 0
    assert iching_res[0]["category"] == "iching"
    assert "Hexagram 1" in iching_res[0]["title"] or "Qián" in iching_res[0]["title"]

    # 3. Search Mantras
    mantra_res = grimoire_service.search("Tara", category="mantras")
    assert len(mantra_res) > 0
    assert mantra_res[0]["category"] == "mantras"

    # 4. Search Sutras
    sutra_res = grimoire_service.search("Sanghata", category="sutras")
    assert len(sutra_res) > 0
    assert sutra_res[0]["category"] == "sutras"

    # 5. Search Planets
    planet_res = grimoire_service.search("Mercury", category="planets")
    assert len(planet_res) > 0
    assert planet_res[0]["planet"] == "Mercury"
    assert len(planet_res[0]["rates"]) > 0


def test_grimoire_get_planetary_hours():
    """Planetary hours calculator should compute traditional hour ruler."""
    hour_info = grimoire_service.get_planetary_hours(local_hour=12, weekday=0)
    assert "hour" in hour_info
    assert "day_ruler" in hour_info
    assert "hour_ruler" in hour_info
    assert "metal" in hour_info
    assert "frequency_hz" in hour_info
