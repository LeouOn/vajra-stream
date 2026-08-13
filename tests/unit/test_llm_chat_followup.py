"""Follow-up prompt compaction — do not stuff SVG/JSON blobs back into the LLM."""

from __future__ import annotations

import json

import pytest

from backend.app.api.v1.endpoints.llm import _summarize_tool_result


@pytest.mark.unit
def test_summarize_drops_svg_and_caps_length():
    blob = {
        "primary": {"name": "Hexagram 11", "meaning": "Peace"},
        "svg": "<svg>" + ("M" * 3000) + "</svg>",
        "ai_image": "data:image/png;base64,AAAA",
        "changing_lines": [2, 5],
    }
    text = _summarize_tool_result(blob)
    assert "svg" not in text.lower() or "omitted" in text
    assert "<svg" not in text
    assert "Hexagram 11" in text
    assert len(text) <= 800


@pytest.mark.unit
def test_summarize_strips_svg_from_card_list():
    cards = [
        {"name": "The Star", "svg": "<svg>big</svg>", "orientation": "upright"},
        {"name": "The Moon", "svg": "<svg>also</svg>", "orientation": "reversed"},
    ]
    text = _summarize_tool_result({"cards": cards})
    parsed = json.loads(text)
    assert "svg" not in parsed["cards"][0]
    assert parsed["cards"][0]["name"] == "The Star"


@pytest.mark.unit
def test_summarize_non_dict_is_truncated():
    assert _summarize_tool_result("x" * 2000) == "x" * 800
