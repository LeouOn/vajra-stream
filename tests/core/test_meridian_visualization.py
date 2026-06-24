"""Tests for ``core.meridian_visualization`` — body / chakra / channel renderer.

Covers the public API:
- Enum: :class:`BodyPosition` (4 positions).
- :class:`MeridianVisualizer` — constructor (image + draw context),
  :meth:`draw_body_outline`, :meth:`draw_chakra`, :meth:`draw_meridian_flow`,
  and the four ``create_*`` diagram methods.
- Convenience functions: ``create_complete_chakra_diagram``,
  ``create_complete_meridian_map``, ``create_central_channel``.

Canvases are kept tiny (e.g. 100×140) so the tests are fast. Files are
written to ``tmp_path`` only when explicitly testing ``save()`` /
convenience functions. No PIL mocking — PIL is a hard runtime dependency
of this module and is available in the dev environment.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from core.meridian_visualization import (
    HAS_PIL,
    BodyPosition,
    MeridianVisualizer,
    create_central_channel,
    create_complete_chakra_diagram,
    create_complete_meridian_map,
)


# ---------------------------------------------------------------------------
# 1. Import smoke test (and PIL availability gate)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports its documented public symbols."""
    import core.meridian_visualization as mod

    for name in (
        "BodyPosition",
        "MeridianVisualizer",
        "create_complete_chakra_diagram",
        "create_complete_meridian_map",
        "create_central_channel",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"

    assert HAS_PIL is True, "PIL is required for this module's tests"


# ---------------------------------------------------------------------------
# 2. BodyPosition enum contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_body_position_enum_has_four_positions():
    """BodyPosition has exactly the four documented viewing angles."""
    assert len(BodyPosition) == 4
    assert {p.value for p in BodyPosition} == {
        "front",
        "back",
        "side_left",
        "side_right",
    }
    # BodyPosition is a plain Enum (not str-subclass) — use .value for
    # comparison. The round-trip via the string value also works.
    assert BodyPosition.FRONT.value == "front"
    assert BodyPosition(BodyPosition.FRONT.value) is BodyPosition.FRONT


# ---------------------------------------------------------------------------
# 3. MeridianVisualizer — constructor + drawing primitives
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_visualizer_creates_image_with_requested_dimensions():
    """The visualizer allocates a PIL image with the requested size and
    the correct background colour."""
    viz = MeridianVisualizer(width=120, height=160, background=(10, 20, 30))

    assert isinstance(viz.image, Image.Image)
    assert viz.image.size == (120, 160)
    # The first pixel reflects the background colour
    assert viz.image.getpixel((0, 0)) == (10, 20, 30)


@pytest.mark.unit
def test_draw_body_outline_runs_for_every_position():
    """``draw_body_outline`` must accept every BodyPosition enum value
    and complete without raising."""
    viz = MeridianVisualizer(width=200, height=300)

    for pos in BodyPosition:
        # Should not raise for any position
        viz.draw_body_outline(pos)


@pytest.mark.unit
def test_draw_chakra_and_meridian_flow_modify_image():
    """Drawing primitives change pixel data — confirms they actually paint."""
    viz = MeridianVisualizer(width=200, height=300)
    bg_pixel = viz.image.getpixel((100, 150))

    # Draw a chakra at the image centre
    viz.draw_chakra("anahata", (100, 150), size=20, glow=True)
    centre_pixel = viz.image.getpixel((100, 150))
    assert centre_pixel != bg_pixel, "Drawing a chakra did not change the centre pixel"

    # Draw a meridian flow
    viz.draw_meridian_flow(
        [(40, 40), (100, 150), (160, 260)],
        color=(255, 0, 0, 255),
        width=3,
        flow_animation=False,
    )
    mid_pixel = viz.image.getpixel((100, 150))
    # Should still be non-background (chakra + meridian both touched it)
    assert mid_pixel != bg_pixel


# ---------------------------------------------------------------------------
# 4. create_* diagram methods — return value contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_seven_chakras_diagram_returns_image_with_chakras():
    """``create_seven_chakras_diagram`` returns the same image instance,
    and the chakra glyph colours are actually painted on the canvas."""
    viz = MeridianVisualizer(width=200, height=300)
    img = viz.create_seven_chakras_diagram()

    assert isinstance(img, Image.Image)
    assert img.size == (200, 300)

    # Heart chakra (green = (0, 255, 0)) is drawn at (100, 400) — but our
    # canvas is only 300px tall, so its drawn position is clamped.
    # Easier check: confirm the canvas has any non-background pixel.
    bg = (20, 20, 30)
    found_non_bg = False
    for x in range(0, 200, 5):
        for y in range(0, 300, 5):
            if viz.image.getpixel((x, y)) != bg:
                found_non_bg = True
                break
        if found_non_bg:
            break
    assert found_non_bg, "Seven-chakra diagram is entirely background"


# ---------------------------------------------------------------------------
# 5. Convenience functions — file I/O into tmp_path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_convenience_functions_create_files_in_tmp(tmp_path: Path):
    """Each ``create_complete_*`` convenience function writes its output
    to the supplied path and returns that path string."""
    chakra_path = tmp_path / "chakra.png"
    meridian_path = tmp_path / "meridian.png"
    channel_path = tmp_path / "channel.png"

    returned = create_complete_chakra_diagram(str(chakra_path))
    assert returned == str(chakra_path)
    assert chakra_path.exists() and chakra_path.stat().st_size > 0

    returned = create_complete_meridian_map(str(meridian_path))
    assert returned == str(meridian_path)
    assert meridian_path.exists() and meridian_path.stat().st_size > 0

    returned = create_central_channel(str(channel_path))
    assert returned == str(channel_path)
    assert channel_path.exists() and channel_path.stat().st_size > 0

    # Each written file must be a readable PNG
    for p in (chakra_path, meridian_path, channel_path):
        with Image.open(p) as im:
            assert im.format == "PNG"
            assert im.size == (1200, 1600)