"""Tests for ``core.energetic_visualization`` — multi-modal PIL renderer.

Covers the public API:
- Color palettes: :data:`CHAKRA_COLORS`, :data:`ELEMENT_COLORS`,
  :data:`ROTHKO_PALETTES`, :data:`PLANET_COLORS`.
- Enums: :class:`VisualizationStyle`, :class:`RothkoLayout`.
- Dataclass: :class:`ColorField` (incl. :meth:`add_color_variation`).
- Visualizers: :class:`BaseVisualizer`, :class:`RothkoVisualizer`,
  :class:`SacredGeometryVisualizer`.
- Convenience functions: ``create_chakra_meditation``,
  ``create_seven_chakras_composition``, ``create_flower_of_life``.

Rendering uses small canvases (e.g. 64×64) to keep tests fast. Files are
written to ``tmp_path`` only when explicitly testing ``save()``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from core.energetic_visualization import (
    CHAKRA_COLORS,
    ELEMENT_COLORS,
    PLANET_COLORS,
    ROTHKO_PALETTES,
    BaseVisualizer,
    ColorField,
    RothkoLayout,
    RothkoVisualizer,
    SacredGeometryVisualizer,
    VisualizationStyle,
    create_chakra_meditation,
    create_flower_of_life,
    create_seven_chakras_composition,
)

# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exposes all expected palettes, classes, enums, and helpers."""
    import core.energetic_visualization as mod

    for name in (
        "CHAKRA_COLORS",
        "ELEMENT_COLORS",
        "ROTHKO_PALETTES",
        "PLANET_COLORS",
        "VisualizationStyle",
        "RothkoLayout",
        "ColorField",
        "BaseVisualizer",
        "RothkoVisualizer",
        "SacredGeometryVisualizer",
        "create_chakra_meditation",
        "create_seven_chakras_composition",
        "create_flower_of_life",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Palette contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chakra_colors_has_seven_classic_chakras_as_rgb_tuples():
    """CHAKRA_COLORS covers the 7 classic chakras as RGB tuples."""
    expected = {"muladhara", "svadhisthana", "manipura", "anahata", "vishuddha", "ajna", "sahasrara"}
    assert expected.issubset(set(CHAKRA_COLORS.keys()))

    # Every color is an RGB tuple of 3 ints in [0, 255]
    for name, color in CHAKRA_COLORS.items():
        assert isinstance(color, tuple) and len(color) == 3
        for channel in color:
            assert isinstance(channel, int) and 0 <= channel <= 255


@pytest.mark.unit
def test_rothko_palettes_and_element_colors_well_formed():
    """ROTHKO_PALETTES and ELEMENT_COLORS have valid structure."""
    # Five elements expected
    assert set(ELEMENT_COLORS.keys()) == {"wood", "fire", "earth", "metal", "water"}

    # Each Rothko palette is a non-empty list of RGB tuples
    assert len(ROTHKO_PALETTES) >= 5
    for name, colors in ROTHKO_PALETTES.items():
        assert isinstance(colors, list) and colors, f"Palette {name!r} is empty"
        for c in colors:
            assert isinstance(c, tuple) and len(c) == 3

    # Planetary colors cover the classical 10 (including luminaries)
    assert len(PLANET_COLORS) == 10
    assert set(PLANET_COLORS.keys()) >= {"sun", "moon", "mars", "jupiter", "saturn"}


# ---------------------------------------------------------------------------
# 3. Enum contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_visualization_style_and_rothko_layout_enums():
    """Enums expose expected members with string values."""
    style_values = {s.value for s in VisualizationStyle}
    assert {"rothko", "minimal", "detailed", "sacred_geometry"}.issubset(style_values)

    layout_values = {l.value for l in RothkoLayout}
    assert {"single", "two_h", "three_h", "two_v", "four_grid"}.issubset(layout_values)


# ---------------------------------------------------------------------------
# 4. ColorField dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_color_field_add_color_variation_stays_in_valid_range():
    """add_color_variation returns a new ColorField with channels clamped to [0, 255]."""
    field = ColorField(color=(128, 128, 128), position=(0.1, 0.1), size=(0.8, 0.8))
    varied = field.add_color_variation(amount=0.5)  # Large variation to test clamping

    assert varied is not field  # New instance, not mutation
    # Position/size/name must be preserved
    assert varied.position == field.position
    assert varied.size == field.size
    assert varied.name == field.name
    # Each channel must be a valid RGB int
    for channel in varied.color:
        assert isinstance(channel, int) and 0 <= channel <= 255


# ---------------------------------------------------------------------------
# 5. BaseVisualizer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_base_visualizer_init_creates_canvas_of_correct_size():
    """BaseVisualizer builds an RGB canvas of the requested dimensions."""
    viz = BaseVisualizer(width=64, height=48, background=(10, 20, 30))
    img = viz.get_image()
    assert isinstance(img, Image.Image)
    assert img.size == (64, 48)
    assert img.mode == "RGB"


@pytest.mark.unit
def test_base_visualizer_save_writes_png(tmp_path: Path):
    """BaseVisualizer.save writes a PNG file to disk and detects the format."""
    viz = BaseVisualizer(width=32, height=32, background=(255, 0, 0))
    out = tmp_path / "viz.png"
    viz.save(str(out))

    assert out.exists()
    # File should be a valid PNG
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (32, 32)


# ---------------------------------------------------------------------------
# 6. RothkoVisualizer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rothko_visualizer_create_from_palette_unknown_raises_value_error():
    """create_from_palette raises ValueError for an unknown palette name."""
    viz = RothkoVisualizer(width=64, height=48)
    with pytest.raises(ValueError, match="Unknown palette"):
        viz.create_from_palette("nonexistent_palette_name")


@pytest.mark.unit
def test_rothko_visualizer_create_from_palette_known_palette_creates_fields():
    """create_from_palette with a known palette populates the fields list."""
    viz = RothkoVisualizer(width=64, height=48)
    viz.create_from_palette("meditative", RothkoLayout.THREE_HORIZONTAL)
    assert len(viz.fields) == 3
    for field in viz.fields:
        assert isinstance(field, ColorField)


@pytest.mark.unit
def test_rothko_visualizer_create_chakra_field_unknown_chakra_raises():
    """create_chakra_field raises ValueError for unknown chakra."""
    viz = RothkoVisualizer(width=64, height=48)
    with pytest.raises(ValueError, match="Unknown chakra"):
        viz.create_chakra_field("not_a_real_chakra")


@pytest.mark.unit
def test_rothko_visualizer_create_seven_chakras_vertical_and_horizontal():
    """create_seven_chakras produces 7 fields in both orientations."""
    viz_v = RothkoVisualizer(width=48, height=96)
    viz_v.create_seven_chakras(vertical=True)
    assert len(viz_v.fields) == 7

    viz_h = RothkoVisualizer(width=96, height=48)
    viz_h.create_seven_chakras(vertical=False)
    assert len(viz_h.fields) == 7


# ---------------------------------------------------------------------------
# 7. SacredGeometryVisualizer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sacred_geometry_create_flower_of_life_does_not_error():
    """create_flower_of_life renders 19 circles without raising."""
    viz = SacredGeometryVisualizer(width=128, height=128)
    viz.create_flower_of_life(radius=20, glow=False)
    # Smoke check: canvas still has the correct dimensions
    assert viz.canvas.size == (128, 128)


@pytest.mark.unit
def test_sacred_geometry_create_seed_of_life_and_sri_yantra_smoke():
    """Other sacred-geometry helpers render without raising."""
    viz = SacredGeometryVisualizer(width=128, height=128)
    viz.create_seed_of_life(radius=20, glow=False)
    viz.create_sri_yantra_simple(size=80)
    assert viz.canvas.size == (128, 128)


# ---------------------------------------------------------------------------
# 8. Convenience functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_chakra_meditation_returns_pil_image_with_correct_size():
    """create_chakra_meditation returns a PIL Image at the requested size."""
    img = create_chakra_meditation("anahata", width=64, height=48, style="rothko")
    assert isinstance(img, Image.Image)
    assert img.size == (64, 48)


@pytest.mark.unit
def test_create_chakra_meditation_minimal_style_fallback():
    """The 'minimal' style branch returns a valid image (no Rothko code path)."""
    img = create_chakra_meditation("manipura", width=64, height=48, style="minimal")
    assert isinstance(img, Image.Image)
    assert img.size == (64, 48)


@pytest.mark.unit
def test_create_seven_chakras_composition_and_flower_of_life_smoke():
    """Top-level convenience functions return PIL images of the right size."""
    img1 = create_seven_chakras_composition(width=48, height=96, vertical=True)
    assert isinstance(img1, Image.Image) and img1.size == (48, 96)

    img2 = create_flower_of_life(width=128, height=128)
    assert isinstance(img2, Image.Image) and img2.size == (128, 128)


# ---------------------------------------------------------------------------
# 9. Error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_base_visualizer_save_propagates_oserror_for_invalid_path(tmp_path: Path):
    """BaseVisualizer.save should propagate OSError on an invalid target path."""
    viz = BaseVisualizer(width=32, height=32)

    # Point at a path inside a *file* so the open-for-write fails.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    bad = blocker / "nested" / "viz.png"

    with pytest.raises(OSError):
        viz.save(str(bad))
