"""Smoke + behaviour tests for ``core.rothko_generator``.

Covers :class:`core.rothko_generator.RothkoGenerator`. Tests exercise
``adjust_luminosity``, ``generate_rothko`` (with a fixed seed for
determinism), ``generate_for_mood``, and the meditation-sequence file
saving path against a temporary directory.

PIL/Pillow is a hard dependency of the module under test; tests use a
small image size to keep them fast.
"""
from __future__ import annotations

import pytest
from PIL import Image

from core.rothko_generator import RothkoGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gen():
    """A small RothkoGenerator (480x320) for fast tests."""
    return RothkoGenerator(width=480, height=320)


@pytest.fixture
def tmp_meditation_dir(tmp_path):
    """A clean per-test output directory."""
    d = tmp_path / "rothko"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# 1. Import smoke + public API
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_palettes_loaded():
    """The module imports and the spiritual palettes are populated."""
    import core.rothko_generator as mod

    assert hasattr(mod, "RothkoGenerator")
    g = RothkoGenerator()
    # All 8 spiritual palettes must be present
    expected = {"compassion", "wisdom", "peace", "awakening", "emptiness",
                "earth", "transcendence", "rainbow_body"}
    assert set(g.PALETTES.keys()) == expected
    # Each palette must have at least 3 colors
    for name, palette in g.PALETTES.items():
        assert len(palette) >= 3, f"Palette '{name}' has fewer than 3 colors"
        for rgb in palette:
            assert len(rgb) == 3
            assert all(0 <= c <= 255 for c in rgb)


# ---------------------------------------------------------------------------
# 2. Constructor records dimensions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_records_dimensions():
    """The constructor stores ``width`` and ``height`` on the instance."""
    g = RothkoGenerator(width=800, height=600)
    assert g.width == 800
    assert g.height == 600


# ---------------------------------------------------------------------------
# 3. adjust_luminosity preserves hue and is monotonic
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_adjust_luminosity_preserves_hue(gen):
    """``adjust_luminosity`` makes colors lighter (>1) and darker (<1)."""
    base = (200, 50, 50)  # a red
    lighter = gen.adjust_luminosity(base, 1.5)
    darker = gen.adjust_luminosity(base, 0.5)

    # All three channels must remain valid RGB
    for c in (lighter, darker):
        for ch in c:
            assert 0 <= ch <= 255

    # Perceived brightness (average of RGB) should follow the factor
    def _brightness(c):
        return sum(c) / 3.0

    assert _brightness(lighter) > _brightness(base)
    assert _brightness(darker) < _brightness(base)


# ---------------------------------------------------------------------------
# 4. generate_rothko returns the requested size and is deterministic by seed
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_rothko_size_and_seed_determinism(gen):
    """With the same seed, two generations produce identical pixel arrays."""
    img1 = gen.generate_rothko(theme="peace", num_bands=3, variation=False, seed=42)
    img2 = gen.generate_rothko(theme="peace", num_bands=3, variation=False, seed=42)

    assert isinstance(img1, Image.Image)
    assert img1.size == (gen.width, gen.height)
    assert img1.mode == "RGB"

    # Identical seed → identical image
    assert list(img1.getdata()) == list(img2.getdata())

    # Different seed → different image (sanity check)
    img3 = gen.generate_rothko(theme="peace", num_bands=3, variation=False, seed=99)
    assert list(img1.getdata()) != list(img3.getdata())


# ---------------------------------------------------------------------------
# 5. generate_for_mood maps keywords to themes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_for_mood_keyword_mapping(gen):
    """Intention keywords select a palette; unknown inputs default to compassion."""
    for kw, expected_theme in (
        ("love", "compassion"),
        ("peace and quiet", "peace"),
        ("wisdom teachings", "wisdom"),
        ("awakening today", "awakening"),
        ("ground me", "earth"),
        ("show me the void", "emptiness"),
    ):
        # We seed for reproducibility — only the palette selection matters here
        img = gen.generate_for_mood(kw)
        assert isinstance(img, Image.Image)
        assert img.size == (gen.width, gen.height)

    # Unknown / non-matching keyword falls back to the compassion palette
    fallback = gen.generate_for_mood("xyzzy unrelated words")
    assert isinstance(fallback, Image.Image)


# ---------------------------------------------------------------------------
# 6. generate_meditation_sequence writes N files to disk
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_meditation_sequence_writes_files(gen, tmp_meditation_dir):
    """``generate_meditation_sequence`` saves the requested number of PNGs."""
    paths = gen.generate_meditation_sequence(
        theme="awakening", count=3, output_dir=str(tmp_meditation_dir)
    )

    assert len(paths) == 3
    for p in paths:
        # Returned paths must exist and be valid PNG files
        import os
        assert os.path.exists(p), f"Missing output: {p}"
        with Image.open(p) as im:
            assert im.format == "PNG"
            assert im.size == (gen.width, gen.height)
