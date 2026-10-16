"""Image prompts never carry numbers; the real values travel beside the image as caption_facts.

Evidence that motivated this (hosted outputs in generated/images/): prompts that
embedded "Moon at 19.3° Scorpio (44% illuminated)", house numbers and dates came
back painted as "Moon (60% Illuminato)", "Full Moon 90%", garbled degrees and an
"I. Invocatio" banner. Nothing here contacts an image model or ComfyUI.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

import core.working as working
from backend.core.services.render import jobs
from backend.core.services.render import worker as worker_mod
from backend.core.services.render.comfyui import BACKEND_NAME, ComfyUIQwenImage21Adapter
from backend.core.services.render.jobs import RenderJobRequest, normalize_request
from backend.core.services.render.worker import RenderWorker
from core import image_prompts, operations
from core.image_prompts import (
    NO_TEXT_SUFFIX,
    caption_fact,
    finalize_image_prompt,
    moon_at,
    moon_imagery,
    moon_imagery_from_phase_name,
    outlook_illustration_prompt,
    sanitize_image_text,
)
from tests.unit.test_render_engine import FakeComfy

NUMERIC = re.compile(r"[0-9°%º×]")

# Text of the kind that produced the painted numbers (from real Outlook narratives).
CHART_TEXT = """**I. Invocatio (Awakening & Invocation)**

Bhaisajyaguru, Lapis Lazuli Radiance, rises from Vaiduryanirbhasa. Fire-Horse Year (丙戌),
Dog Hour, 7th Day, 7th Month. Sun at 26.5° Leo (House II). Moon at 19.3° Scorpio (House IV)
in Vishakha Nakshatra (Pada 2), Moon (44% illuminated). Jupiter 7.1° Leo in the second house,
Mercury 20° 12' Cancer, Venus in the 10th house. Saka Dawa Duchen 2027-05-21; May 21, 2027
at 14:30 UTC. Merit ×100,000. ♌ ☽ ♏

**IV. Sigillum (Kamea Sigil Trace)** The kamea path is traced at 432 Hz, 12 degrees.
"""


def has_swisseph() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    return True


needs_ephemeris = pytest.mark.skipif(not has_swisseph(), reason="pyswisseph not installed")


# -- sanitizing ---------------------------------------------------------------------


def test_sanitize_strips_every_number_degree_percent_date_and_glyph():
    out = sanitize_image_text(CHART_TEXT)
    assert not NUMERIC.search(out), out
    for gone in ("Invocatio", "Sigillum", "House", "house", "丙", "♌", "☽", "illuminated", "UTC", "**"):
        assert gone not in out, (gone, out)
    # the imagery survives
    for kept in ("Bhaisajyaguru", "Lapis Lazuli Radiance", "Scorpio", "kamea path"):
        assert kept in out


@pytest.mark.parametrize(
    "text",
    [
        "Moon (60% Illuminato)",
        "Full Moon 90%",
        "Sun 9.5° Leo, Jupiter 7.1° Leo, Budha 20.2° Cancer",
        "the 4th house cusp at 19°21'04\"",
        "sealed 2026-08-15T12:00:00+00:00",
        "on 21/05/2027 at 6:45 pm",
        "Chapter 3 of 9",
        "merit x 108 and #3",
    ],
)
def test_sanitize_leaves_no_digits(text):
    assert not NUMERIC.search(sanitize_image_text(text))


def test_sanitize_keeps_ordinary_prose_untouched():
    text = "May all beings be happy, and may the river run clear under a quiet sky."
    assert sanitize_image_text(text) == text


def test_finalize_appends_the_no_text_suffix_once_and_is_idempotent():
    once = finalize_image_prompt(CHART_TEXT)
    assert once.endswith(NO_TEXT_SUFFIX)
    assert once.count(NO_TEXT_SUFFIX) == 1
    assert finalize_image_prompt(once) == once
    assert not NUMERIC.search(once)


def test_finalize_respects_max_chars():
    out = finalize_image_prompt("lotus " * 1000, max_chars=400)
    assert len(out) <= 400
    assert out.endswith(NO_TEXT_SUFFIX)


def test_no_text_suffix_names_lettering_numerals_glyphs_and_captions():
    for word in ("lettering", "numerals", "glyphs", "captions"):
        assert word in NO_TEXT_SUFFIX


# -- the moon ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("illumination", "waxing", "words"),
    [
        (0.5, True, "a moonless night sky, the new moon unseen"),
        (8.0, False, "a thin waning crescent moon"),
        (30.0, True, "a waxing crescent moon"),
        (44.0, False, "a waning half moon"),  # the chart that came back as "Full Moon 90%"
        (75.0, True, "a waxing gibbous moon"),
        (90.0, False, "a waning gibbous moon"),
        (99.2, None, "a full moon"),
    ],
)
def test_moon_imagery_from_computed_illumination(illumination, waxing, words):
    assert moon_imagery(illumination, waxing) == words


def test_full_moon_only_when_computed_full():
    for pct in range(0, 97):
        assert "full" not in moon_imagery(pct, True)
        assert "full" not in moon_imagery(pct, False)
    assert moon_imagery(97.5) == "a full moon"


def test_moon_imagery_from_phase_name():
    assert moon_imagery_from_phase_name("Waxing Gibbous") == "a waxing gibbous moon"
    assert moon_imagery_from_phase_name("full_moon") == "a full moon"
    assert moon_imagery_from_phase_name("Last Quarter") == "a waning half moon"
    assert moon_imagery_from_phase_name("blue") is None
    assert moon_imagery_from_phase_name(None) is None


@needs_ephemeris
def test_moon_at_known_full_and_new_moons():
    full = moon_at("2026-08-28T04:18:00+00:00")  # full moon (partial lunar eclipse)
    new = moon_at("2026-08-12T17:37:00+00:00")  # new moon (total solar eclipse)
    assert full is not None and new is not None
    assert full["illumination"] > 99
    assert moon_imagery(full["illumination"], full["waxing"]) == "a full moon"
    assert new["illumination"] < 1
    waxing = moon_at("2026-08-15T12:00:00+00:00")
    assert waxing is not None and waxing["waxing"] is True
    assert "waxing crescent" in moon_imagery(waxing["illumination"], waxing["waxing"])


def test_moon_at_bad_input_is_none():
    assert moon_at(None) is None
    assert moon_at("not a date") is None


def test_caption_fact_validates_provenance():
    assert caption_fact("Moon", "44% illuminated", "computed") == {
        "label": "Moon",
        "value": "44% illuminated",
        "provenance": "computed",
    }
    with pytest.raises(ValueError):
        caption_fact("Moon", "x", "measured")  # type: ignore[arg-type]


@needs_ephemeris
def test_moon_caption_fact_carries_the_number_the_image_does_not():
    moon = moon_at("2026-08-28T04:18:00+00:00")
    assert moon is not None
    fact = image_prompts.moon_caption_fact(moon)
    assert fact["provenance"] == "computed"
    assert fact["value"].startswith("100% illuminated")


# -- witness (core/working.py) --------------------------------------------------------

LEGACY_FOLIO: dict[str, Any] = {
    "working_id": "wrk_legacy",
    "sealed_at": "2026-08-15T12:00:00+00:00",
    "intention": "May the 3 rivers run clear by 2027",
    "target": "all beings",
    "saka_dawa": {
        "is_saka_dawa": False,
        "is_duchen": False,
        "multiplier": 1,
        "saka_dawa_duchen": "2027-05-21",
    },
    "hour_stamp": {"planetary_hour": "Venus", "moon_phase": None},
    # what folios stored before: a future festival's date and a full moon that was not in the sky
    "image_prompt": "Manifestation still ... no real people. Pale full moon for Saka Dawa Duchen 2027-05-21.",
}


def test_witness_prompt_rebuilds_instead_of_reusing_a_legacy_numeric_prompt():
    prompt = working.witness_prompt(LEGACY_FOLIO)
    assert prompt != LEGACY_FOLIO["image_prompt"]
    assert not NUMERIC.search(prompt), prompt
    assert "Saka Dawa" not in prompt  # the sitting was not in Saka Dawa
    assert prompt.endswith(NO_TEXT_SUFFIX)


_MOON_IMAGERY = re.compile(r"\b(?:crescent|gibbous|half moon|full moon|new moon|moonlit|moonlight)\b", re.I)


@needs_ephemeris
def test_witness_prompt_asks_for_an_empty_sky_not_a_painted_moon():
    # The true sky is drawn onto the render afterwards (core/sky_composite.py).
    prompt = working.witness_prompt(LEGACY_FOLIO)
    assert not _MOON_IMAGERY.search(prompt), prompt
    assert "In the sky," not in prompt
    assert "no moon, no stars, no planets" in prompt
    # the kind of sky asked for is computed: at 05:00 PDT in San Francisco the Sun is 16° down, at 13:00 up
    assert "clear, open night sky" in prompt
    midday = working.witness_prompt({**LEGACY_FOLIO, "sealed_at": "2026-08-15T20:00:00+00:00"})
    assert "clear, open daytime sky" in midday


def test_witness_prompt_never_paints_the_moon_even_from_a_stamped_phase_name(monkeypatch):
    monkeypatch.setattr(working.sky, "compute_sky", lambda *a, **k: None)
    folio = {**LEGACY_FOLIO, "hour_stamp": {"moon_phase": "Waning Gibbous"}}
    prompt = working.witness_prompt(folio)
    assert not _MOON_IMAGERY.search(prompt), prompt
    assert "clear, open sky" in prompt
    facts = {f["label"]: f for f in working.witness_caption_facts(folio)}
    assert facts["Moon phase"]["value"] == "Waning Gibbous"
    assert facts["Sky at sealing"]["value"].startswith("could not be computed")


def test_witness_names_saka_dawa_only_when_the_sitting_was_in_it():
    in_month = {**LEGACY_FOLIO, "saka_dawa": {**LEGACY_FOLIO["saka_dawa"], "is_saka_dawa": True, "multiplier": 10}}
    duchen = {**in_month, "saka_dawa": {**in_month["saka_dawa"], "is_duchen": True}}
    assert "Saka Dawa month" in working.witness_prompt(in_month)
    assert "Saka Dawa Duchen" in working.witness_prompt(duchen)
    assert not NUMERIC.search(working.witness_prompt(duchen))


def test_witness_caption_facts_carry_the_real_values():
    folio = {**LEGACY_FOLIO, "saka_dawa": {**LEGACY_FOLIO["saka_dawa"], "is_saka_dawa": True, "multiplier": 10}}
    facts = {f["label"]: f for f in working.witness_caption_facts(folio)}
    assert facts["Sealed"] == {"label": "Sealed", "value": folio["sealed_at"], "provenance": "record"}
    assert facts["Saka Dawa Duchen"]["value"] == "2027-05-21"
    assert facts["Saka Dawa Duchen"]["provenance"] == "computed"
    assert facts["Merit multiplier"]["value"] == "×10"
    assert facts["Planetary hour"]["value"] == "Venus"
    if has_swisseph():
        assert facts["Moon at sealing"]["provenance"] == "computed"
        assert "illuminated" in facts["Moon at sealing"]["value"]


def test_sealed_folio_prompt_has_no_numerals(tmp_path, monkeypatch):
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working("Peace for 8 billion beings at 108 temples", broadcast=False)
    assert folio["image_prompt"] == working.witness_prompt(folio)
    assert not NUMERIC.search(folio["image_prompt"])
    assert "Manifestation" in folio["image_prompt"]


def test_video_prompt_has_no_numerals():
    prompt = working.video_prompt_for(
        {
            "intention": "peace for the watershed",
            "target": "the river",
            "spoken_charge": "For the river: peace. Merit ×100,000.",
            "image_prompt": LEGACY_FOLIO["image_prompt"],
        }
    )
    assert not NUMERIC.search(prompt)
    assert len(prompt) >= 50


# -- witness render: facts in params, sidecar and folio ------------------------------


@pytest.fixture
def render_env(tmp_path, monkeypatch):
    monkeypatch.setattr(operations, "get_db_path", lambda: str(tmp_path / "ops.db"))
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    monkeypatch.setattr(worker_mod, "_worker", None)
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path / "workings")
    comfy = FakeComfy()
    adapter = ComfyUIQwenImage21Adapter(
        "http://comfy.test", transport=httpx.MockTransport(comfy.handler), poll_interval=0.001
    )
    monkeypatch.setitem(jobs.BACKENDS, BACKEND_NAME, lambda: adapter)
    yield tmp_path
    operations.remove_listener(working.witness_listener)


async def test_witness_render_carries_caption_facts_to_sidecar_and_folio(render_env):
    folio = working.run_working("a lamp in the dark", broadcast=False)
    op = working.submit_witness_render(folio["working_id"])["operation"]
    facts = working.witness_caption_facts(folio)
    assert op["params"]["caption_facts"] == facts
    assert not NUMERIC.search(op["params"]["prompt"])
    assert await RenderWorker(timeout_seconds=5).drain() == 1
    done = operations.get_operation(op["id"])
    assert done["status"] == "success", done["error"]
    sidecar = json.loads((render_env / done["result"]["sidecar_path"]).read_text(encoding="utf-8"))
    assert sidecar["caption_facts"] == facts
    # the folio's witness adds one fact: what the drawn sky overlay shows (or why there is none)
    witness_facts = working.load_working(folio["working_id"])["witness"]["caption_facts"]
    assert witness_facts[: len(facts)] == facts
    assert [f["label"] for f in witness_facts[len(facts) :]] == ["Sky overlay"]


def test_render_request_caption_facts_are_optional_and_validated():
    params, _ = normalize_request(RenderJobRequest(prompt="Green Tara"))
    assert "caption_facts" not in params
    params, _ = normalize_request(
        RenderJobRequest(prompt="x", caption_facts=[{"label": "Moon", "value": "44%", "provenance": "computed"}])
    )
    assert params["caption_facts"] == [{"label": "Moon", "value": "44%", "provenance": "computed"}]
    with pytest.raises(ValueError):
        RenderJobRequest(prompt="x", caption_facts=[{"label": "Moon", "value": "44%", "provenance": "measured"}])


# -- sigil ----------------------------------------------------------------------------


def test_sigil_prompt_has_no_numerals_runes_or_resolution_tags():
    from backend.core.services.sigil_service import sigil_image_prompt

    prompt = sigil_image_prompt("Protection for house 12 until 2027-01-01")
    assert not NUMERIC.search(prompt)
    assert "runes" not in prompt and "8k" not in prompt
    assert prompt.endswith(NO_TEXT_SUFFIX)


async def test_forged_sigil_stores_caption_facts(tmp_path, monkeypatch):
    from backend.core.services import sigil_service as module

    service = module.sigil_service
    monkeypatch.setattr(service, "storage_dir", tmp_path)
    monkeypatch.setattr(service, "image_provider", "none")
    sigil = await service.forge_sigil("Protection for the house", "jupiter")
    labels = {f["label"]: f for f in sigil["caption_facts"]}
    assert labels["Intention"]["value"] == "Protection for the house"
    assert labels["Kamea"] == {"label": "Kamea", "value": "jupiter", "provenance": "record"}
    assert labels["Forged"]["provenance"] == "record"
    saved = json.loads((tmp_path / f"{sigil['id']}.json").read_text(encoding="utf-8"))
    assert saved["caption_facts"] == sigil["caption_facts"]


# -- Outlook --------------------------------------------------------------------------


def test_outlook_illustration_prompt_has_no_chart_numbers_or_headings():
    prompt = outlook_illustration_prompt(CHART_TEXT, "healing", {"illumination": 44.0, "waxing": False})
    assert not NUMERIC.search(prompt), prompt
    assert "Invocatio" not in prompt
    assert "a waning half moon" in prompt
    assert "full moon" not in prompt.lower()
    assert prompt.endswith(NO_TEXT_SUFFIX)


async def test_outlook_illustration_route_sends_a_clean_prompt_and_returns_facts(monkeypatch):
    from backend.app.api.v1.endpoints import image_generation, outlook

    sent: dict[str, Any] = {}

    class FakeService:
        async def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
            sent["prompt"] = prompt
            sent.update(kwargs)
            return {"image_data_url": "data:image/png;base64,QQ==", "model": "m", "cost_usd": 0.0}

    monkeypatch.setattr(image_generation, "get_service", lambda: FakeService())
    body = await outlook.generate_illustration(
        outlook.IllustrationRequest(narrative=CHART_TEXT, genre="healing", date="2026-08-28T04:18:00+00:00")
    )
    assert not NUMERIC.search(sent["prompt"])
    assert body["prompt"] == sent["prompt"]
    assert sent["caption_facts"] == body["caption_facts"]
    labels = {f["label"]: f for f in body["caption_facts"]}
    assert labels["Chart time"]["provenance"] == "record"
    if has_swisseph():
        assert "a full moon" in sent["prompt"]
        assert labels["Moon at chart time"]["provenance"] == "computed"


# -- LLM tools and hosted service --------------------------------------------------------


async def test_llm_generate_image_tool_sanitizes_its_prompt(monkeypatch):
    from backend.app.api.v1.endpoints import image_generation
    from backend.core.llm_agent import tools

    sent: list[str] = []

    class FakeService:
        config = {"model_lock": True}

        async def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
            sent.append(prompt)
            return {"image_data_url": "data:image/png;base64,QQ=="}

    monkeypatch.setattr(image_generation, "get_service", lambda: FakeService())
    await tools.generate_image_for_tool(prompt="Medicine Buddha, Moon 19.3° Scorpio (44% illuminated), House IV")
    assert len(sent) == 1
    assert not NUMERIC.search(sent[0])
    assert sent[0].endswith(NO_TEXT_SUFFIX)


def test_generate_image_tool_schema_forbids_numbers():
    from backend.core.llm_agent import tools

    schema = next(s for s in tools.get_tool_schemas() if s["name"] == "generate_image")
    assert "no numbers" in schema["parameters"]["properties"]["prompt"]["description"]


async def test_hosted_service_echoes_and_writes_caption_facts(tmp_path, monkeypatch):
    from backend.core.services import image_generation_service as module

    service = module.ImageGenerationService({"enabled": True, "image_output_dir": str(tmp_path)})

    class FakeProvider:
        async def generate(self, **kwargs: Any) -> module.ProviderResult:
            return module.ProviderResult(
                image_data_url="data:image/png;base64,iVBORw0KGgo=",
                model="m",
                cost_usd=0.0,
                provider="openrouter",
            )

    monkeypatch.setattr(service, "_get_provider", lambda name: FakeProvider())
    facts = [caption_fact("Moon", "44% illuminated, waning", "computed")]
    result = await service.generate(prompt="a lotus", caption_facts=facts)
    assert result["caption_facts"] == facts
    sidecar_path = Path(result["image_file_path"]).with_suffix(".json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["caption_facts"] == facts
    assert sidecar["prompt"] == "a lotus"
