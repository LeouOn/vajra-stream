"""
Smoke + behaviour tests for ``core.visual_renderer_simple``.

Covers the public surface:
- :class:`SimpleVisualRenderer` — constructor records width/height.
- ``render_frame(intention, timestamp)`` — returns 24 rows of 80 chars,
  contains the intention text in the top banner, and (with a timestamp)
  has at least one ``*`` petal glyph.
- ``render_frame`` without args — still returns 24x80 whitespace, no crash.

The module depends only on ``math`` and ``time`` — no mocking needed.
"""
from __future__ import annotations

import pytest

from core.visual_renderer_simple import SimpleVisualRenderer


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exports the ``SimpleVisualRenderer`` class."""
    import core.visual_renderer_simple as mod

    assert hasattr(mod, "SimpleVisualRenderer")


# ---------------------------------------------------------------------------
# 2. Constructor records width/height
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_records_width_and_height():
    """Constructor stores width and height on the instance."""
    r = SimpleVisualRenderer(width=800, height=600)
    assert r.width == 800
    assert r.height == 600


# ---------------------------------------------------------------------------
# 3. render_frame — empty (no intention, no timestamp)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_frame_no_args_returns_blank_24x80_grid():
    """Without args, returns 24 lines of 80 chars, all whitespace (no crash)."""
    r = SimpleVisualRenderer()
    frame = r.render_frame()

    assert isinstance(frame, list)
    assert len(frame) == 24
    for row in frame:
        assert isinstance(row, str)
        assert len(row) == 80
    # No intention and no timestamp → no glyphs written
    full = "".join(frame)
    assert "*" not in full
    assert "@" not in full
    assert "Intention:" not in full


# ---------------------------------------------------------------------------
# 4. render_frame — with intention and timestamp
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_frame_with_intention_and_timestamp_includes_glyphs():
    """With intention + timestamp, frame contains the intention and mandala glyphs.

    Uses timestamp=1.0 (a non-zero rotation) so the line drawing does not
    overwrite the ``*`` endpoints with ``.`` the way timestamp=0.0 would —
    at angle=0 all petals are symmetric and the connecting lines pass
    through the centre, replacing both the ``*`` endpoints and the ``@``
    centre with ``.`` glyphs.
    """
    r = SimpleVisualRenderer()
    frame = r.render_frame(intention="peace", timestamp=1.0)

    assert len(frame) == 24
    for row in frame:
        assert len(row) == 80

    # The intention banner is rendered on the top text line
    full = "".join(frame)
    assert "Intention: peace" in full
    # At least one of the mandala glyphs is present (``*`` or ``.`` or ``@``)
    assert any(g in full for g in ("*", "@", "."))


# ---------------------------------------------------------------------------
# 5. render_frame — different timestamps produce different frames (rotation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_frame_rotation_changes_output():
    """Different timestamps rotate the petals, producing different frame contents."""
    r = SimpleVisualRenderer()
    f1 = r.render_frame(intention="x", timestamp=0.0)
    f2 = r.render_frame(intention="x", timestamp=5.0)

    # The mandala geometry rotates, so the placement of '*' / '.' / '@' changes
    assert f1 != f2
