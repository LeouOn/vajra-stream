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


@pytest.mark.unit
def test_summarize_population_list_dedups_names():
    rows = [{"name": "California", "mantra_preference": "chenrezig"} for _ in range(40)]
    rows.append({"name": "Myanmar", "mantra_preference": "om"})
    text = _summarize_tool_result(rows)
    assert text.count("California") == 1
    assert "Myanmar" in text
    assert "unique" in text


@pytest.mark.unit
def test_summarize_outlook_uses_excerpt_not_full_sutra():
    text = _summarize_tool_result(
        {
            "genre": "healing",
            "narrative": "I. Invocatio " + ("om " * 400),
            "astrology_used": "New Moon",
            "model_used": "deepseek/deepseek-v4-flash",
        }
    )
    parsed = json.loads(text)
    assert parsed["genre"] == "healing"
    assert "narrative_excerpt" in parsed
    assert len(parsed["narrative_excerpt"]) <= 280


@pytest.mark.unit
def test_intention_skips_meta_followup():
    from types import SimpleNamespace

    from backend.app.api.v1.endpoints.llm import _intention_from_messages

    msgs = [
        SimpleNamespace(role="user", content="let's evaluate how to generate an operation for world peace"),
        SimpleNamespace(role="assistant", content="ok"),
        SimpleNamespace(
            role="user",
            content="nice glad you finally run some lists do you have the information that you need? and maybe check out if we can get a good outlook",
        ),
    ]
    assert "world peace" in _intention_from_messages(msgs).lower()
