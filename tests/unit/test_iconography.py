"""Curated deity iconography (knowledge/iconography.json, core/iconography.py).

Data rules: every entry cites sources, unknown fields are null (never ""),
every deity the repo names resolves, the 88 Buddhas get no invented per-Buddha
iconography. Prompt rules: the clause carries the established attributes, no
digits or script, and the witness prompt still ends in the no-text suffix.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

import core.working as working
from core import iconography
from core.image_prompts import NO_TEXT_SUFFIX, finalize_image_prompt, outlook_illustration_prompt, sanitize_image_text

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = REPO_ROOT / "knowledge"
DATA = json.loads((KNOWLEDGE / "iconography.json").read_text(encoding="utf-8"))


def all_forms() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(entry, form) for entry in DATA["deities"] for form in entry["forms"]]


def walk(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from walk(item, f"{path}[{i}]")


# -- data ----------------------------------------------------------------------------


def test_every_entry_cites_known_sources():
    registry = DATA["sources"]
    for entry in DATA["deities"]:
        assert entry["sources"], f"{entry['id']} has no sources"
        for source_id in entry["sources"]:
            assert source_id in registry, f"{entry['id']} cites unknown source {source_id}"
    for source in registry.values():
        assert source["citation"].strip() and source["short"].strip()


def test_no_empty_string_placeholders():
    empty = [path for path, value in walk(DATA) if isinstance(value, str) and not value.strip()]
    assert empty == [], f"use null, not an empty string: {empty}"


def test_ids_forms_and_hands_are_well_formed():
    ids = [entry["id"] for entry in DATA["deities"]]
    assert len(ids) == len(set(ids))
    for entry, form in all_forms():
        form_ids = [f["id"] for f in entry["forms"]]
        assert len(form_ids) == len(set(form_ids)), entry["id"]
        assert entry["default_form"] in form_ids, entry["id"]
        assert entry["art_style"] in DATA["art_styles"]
        assert form["ornaments"] is None or form["ornaments"] in DATA["ornament_sets"]
        for hand in form["hands"]:
            label = hand["hand"]
            assert label in {"right", "left", "both", "principal pair", "upper right", "upper left"} or re.match(
                r"^(right|left) \(\w+\)$", label
            ), f"{entry['id']}/{form['id']}: unknown hand label {label!r}"


def test_aliases_are_unambiguous():
    assert iconography.alias_conflicts() == []


def test_the_88_buddhas_get_no_invented_individual_iconography():
    generic = iconography.get_deity("buddha_generic")
    assert generic is not None and generic["generic"] is True
    assert "individual_iconography" in generic and generic["individual_iconography"] is None
    assert "no individual" in generic["individual_iconography_note"]
    assert iconography.resolve("88_buddhas").id == "buddha_generic"
    facts = iconography.deity_caption_facts(generic)
    assert any("no individually established iconography" in f["value"] for f in facts)


# -- lookup --------------------------------------------------------------------------


def population_deities() -> list[str]:
    out = []
    for path in sorted((KNOWLEDGE / "blessing_populations").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("deity"):
            out.append(data["deity"])
    return out


def practices() -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((KNOWLEDGE / "practices").glob("*.json"))]


def test_every_population_deity_string_resolves():
    names = population_deities()
    assert "Avalokiteshvara (Chenrezig)" in names  # the scan really reads the files
    for name in names:
        assert iconography.resolve(name) is not None, name


def test_every_practice_id_and_practice_deity_resolves():
    for practice in practices():
        assert iconography.resolve(practice["practice_id"]) is not None, practice["practice_id"]
        if practice.get("deity"):
            assert iconography.resolve(practice["deity"]) is not None, practice["deity"]


def test_named_yidams_in_sacred_entities_resolve():
    entities = json.loads((KNOWLEDGE / "sacred_entities.json").read_text(encoding="utf-8"))
    for yidam in entities["yidams_and_mantras"]:
        assert iconography.resolve(yidam["name"]) is not None, yidam["name"]


@pytest.mark.parametrize(
    ("name", "deity_id", "form_id"),
    [
        ("Avalokiteshvara (Chenrezig)", "avalokiteshvara", "four_armed"),
        ("Green Tara", "green_tara", "standard"),
        ("Medicine Buddha (Bhaisajyaguru)", "medicine_buddha", "standard"),
        ("Zhunti (Cundi) Buddha Mother", "cundi", "eighteen_armed"),
        ("Cundi Buddha Mother (准提佛母 / Cundī Bhagavatī)", "cundi", "eighteen_armed"),
        ("heart_sutra", "prajnaparamita", "four_armed"),
        ("Avalokiteshvara / Chenrezig / Guanyin", "avalokiteshvara", "four_armed"),
        ("Thousand-armed Chenrezig", "avalokiteshvara", "thousand_armed"),
        ("avalokiteshvara:thousand_armed", "avalokiteshvara", "thousand_armed"),
        ("Buddha Shakyamuni (heart-essence)", "shakyamuni", "earth_touching"),
        ("千手觀音", "avalokiteshvara", "thousand_armed"),
    ],
)
def test_resolve(name, deity_id, form_id):
    ref = iconography.resolve(name)
    assert ref is not None and (ref.id, ref.form_id) == (deity_id, form_id)


@pytest.mark.parametrize("name", ["", "   ", None, "Zeus", "Tara", "avalokiteshvara:no_such_form"])
def test_resolve_rejects_unknown(name):
    assert iconography.resolve(name) is None


def test_named_deity_in_text_is_conservative():
    assert iconography.named_deity_in_text("We call on Chenrezig, may all beings be free.").id == "avalokiteshvara"
    assert iconography.named_deity_in_text("Green Tara and the Medicine Buddha") is None  # two deities
    assert iconography.named_deity_in_text("Recite the Prajnaparamita sutra") is None  # excluded
    assert iconography.named_deity_in_text("the 88 Buddhas repentance") is None  # generic form never inferred
    assert iconography.named_deity_in_text("a dharma talk") is None


# -- prompt clauses ------------------------------------------------------------------


@pytest.mark.parametrize(("entry", "form"), all_forms(), ids=lambda v: v["id"])
def test_clause_has_no_digits_or_script_and_survives_sanitizing(entry, form):
    clause = iconography.deity_prompt_clause(entry, form["id"])
    assert not re.search(r"\d", clause)
    assert sanitize_image_text(clause) == clause
    assert len(clause) < 1100
    assert "no seed syllables or mantra script" in clause


def test_green_tara_clause():
    clause = iconography.deity_prompt_clause(iconography.lookup("Green Tara"))
    for needle in ("green body", "right leg extended", "right hand", "varada mudra", "left hand", "blue utpala"):
        assert needle in clause, needle
    assert clause.index("right hand") < clause.index("varada") < clause.index("left hand") < clause.index("utpala")


def test_medicine_buddha_clause():
    clause = iconography.deity_prompt_clause(iconography.lookup("medicine_buddha"))
    for needle in (
        "lapis lazuli blue",
        "varada mudra",
        "myrobalan (arura)",
        "meditation gesture",
        "alms bowl",
        "robes",
    ):
        assert needle in clause, needle
    right, left = clause.index("the right hand"), clause.index("the left hand")
    assert right < clause.index("myrobalan") < left < clause.index("alms bowl")


def test_four_armed_avalokiteshvara_clause():
    clause = iconography.deity_prompt_clause(iconography.lookup("Avalokiteshvara (Chenrezig)"))
    for needle in (
        "white body",
        "four arms",
        "principal pair of hands at the heart",
        "joined palms",
        "wish-fulfilling jewel",
        "upper right hand",
        "crystal mala",
        "upper left hand",
        "white lotus",
        "jewelled crown",
    ):
        assert needle in clause, needle
    assert clause.index("upper right hand") < clause.index("crystal mala") < clause.index("upper left hand")


def test_unknown_fields_are_not_prompted():
    # Prajnaparamita's principal hands differ by lineage: null, so no gesture is invented for them.
    clause = iconography.deity_prompt_clause(iconography.lookup("prajnaparamita"))
    assert "principal pair" not in clause
    assert "vajra" in clause and "Perfection of Wisdom" in clause


def test_caption_facts_are_records_with_sources():
    facts = iconography.deity_caption_facts(iconography.lookup("green_tara"))
    assert {f["provenance"] for f in facts} == {"record"}
    labels = {f["label"]: f["value"] for f in facts}
    assert labels["Deity"].startswith("Green Tara")
    assert "Beer" in labels["Iconography source"]
    assert all(len(f["value"]) <= 300 for f in facts)


# -- wiring --------------------------------------------------------------------------


@pytest.fixture
def workings_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    return tmp_path


def test_run_working_seals_the_deity_and_paints_it(workings_dir):
    folio = working.run_working("May all beings find refuge", "all beings", broadcast=False, deity="Chenrezig")
    assert folio["deity"] == {
        "id": "avalokiteshvara",
        "form": "four_armed",
        "label": "Four-armed Avalokiteshvara (Chenrezig)",
    }
    assert folio["provenance"]["deity"] == "record"
    prompt = folio["image_prompt"]
    assert prompt.startswith("Traditional Tibetan thangka-style devotional painting of Four-armed Avalokiteshvara")
    assert "crystal mala" in prompt and "May all beings find refuge" in prompt
    assert prompt.endswith(NO_TEXT_SUFFIX)
    assert prompt == finalize_image_prompt(prompt, max_chars=iconography.DEITY_PROMPT_MAX_CHARS)  # idempotent
    reloaded = working.load_working(folio["working_id"])
    assert working.witness_prompt(reloaded) == prompt
    facts = working.witness_caption_facts(reloaded)
    assert any(f["label"] == "Deity" and f["value"].startswith("Four-armed Avalokiteshvara") for f in facts)
    assert any(f["label"] == "Iconography source" and f["provenance"] == "record" for f in facts)


def test_witness_keeps_sky_and_suffix_after_a_long_deity_clause(workings_dir):
    folio = working.run_working("x" * 400, "y" * 150, broadcast=False, deity="avalokiteshvara:thousand_armed")
    prompt = working.witness_prompt(folio)
    assert "thousand arms" in prompt
    assert prompt.endswith(NO_TEXT_SUFFIX)
    assert "Dedicated to" in prompt


def test_run_working_without_deity_is_unchanged(workings_dir):
    folio = working.run_working("peace for the river", broadcast=False)
    assert folio["deity"] is None
    assert "Manifestation" in folio["image_prompt"]
    assert not any(f["label"] == "Deity" for f in working.witness_caption_facts(folio))


def test_run_working_rejects_an_unknown_deity(workings_dir):
    with pytest.raises(ValueError, match="unknown deity"):
        working.run_working("peace", broadcast=False, deity="Zeus")
    assert list(workings_dir.glob("wrk_*.json")) == []


def test_llm_tool_drops_an_unknown_deity_and_says_so(workings_dir):
    from backend.core.llm_agent.tools import run_working as tool_run_working

    folio = tool_run_working("peace for the hills", broadcast=False, deity="Zeus")
    assert folio["deity"] is None and "Zeus" in folio["deity_note"]
    folio = tool_run_working("healing for the valley", broadcast=False, deity="medicine_buddha")
    assert folio["deity"]["id"] == "medicine_buddha"


def test_http_working_validates_the_deity(workings_dir):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.api.v1.endpoints.operator import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/operator")
    client = TestClient(app)
    bad = client.post("/api/v1/operator/working", json={"intention": "peace", "broadcast": False, "deity": "Zeus"})
    assert bad.status_code == 422
    ok = client.post("/api/v1/operator/working", json={"intention": "peace", "broadcast": False, "deity": "Green Tara"})
    assert ok.status_code == 200 and ok.json()["deity"]["id"] == "green_tara"


def test_outlook_illustration_adds_a_single_named_deity():
    from backend.app.api.v1.endpoints.outlook import illustration_request_facts

    narrative = "Under the Moon at 44% we invoke Green Tara, swift protectress, for all who travel in fear."
    prompt, facts = illustration_request_facts(narrative, "protection", None)
    assert "Green Tara" in prompt and "right leg extended" in prompt
    assert prompt.endswith(NO_TEXT_SUFFIX) and "44" not in prompt
    assert any(f["label"] == "Deity" for f in facts)

    prompt, facts = illustration_request_facts("Green Tara and Medicine Buddha bless the land.", "healing", None)
    assert "thangka" not in prompt and not any(f["label"] == "Deity" for f in facts)


def test_frontend_deity_options_resolve():
    source = (REPO_ROOT / "frontend" / "src" / "lib" / "iconographyDeities.ts").read_text(encoding="utf-8")
    values = re.findall(r"value: '([^']+)'", source)
    assert len(values) >= len(DATA["deities"])
    for value in values:
        assert iconography.resolve(value) is not None, value
    assert {iconography.resolve(v).id for v in values} == {entry["id"] for entry in DATA["deities"]}


def test_outlook_prompt_without_deity_is_unchanged():
    assert outlook_illustration_prompt("a quiet blessing for the land", "healing") == outlook_illustration_prompt(
        "a quiet blessing for the land", "healing", deity_clause=None
    )
