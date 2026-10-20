"""Tests for /api/v1/blessings/generate-narrative options (ITEM 4).

Covers the truthful-options contract:
  * short/medium/long produce meaningfully different outputs,
  * every tradition advertised by /traditions has a distinct template
    (previously zen/yogic silently fell back to universal),
  * target/intention are interpolated,
  * dedication toggles,
  * metadata.generated_at is the real UTC generation time (injectable clock),
  * unsupported length/tradition values are rejected with 422,
  * the pre-existing universal/buddhist/tibetan medium texts are preserved.

Router-only test app: the blessings router is mounted on a bare FastAPI app;
no server, no LLM/TTS/network, no hardware. The endpoint renders only the
deterministic inline templates; the never-importable optional core generators
are not used (their vestigial HAS_BLESSING_MODULES gate was removed — it had
made every request return 501).
"""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import blessings as blessings_endpoint
from backend.app.api.v1.endpoints.blessings import (
    SUPPORTED_LENGTHS,
    SUPPORTED_TRADITIONS,
)


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(blessings_endpoint.router)
    return TestClient(app)


def request_body(**overrides):
    base = {
        "target_name": "Alex",
        "target_type": "person",
        "intention": "ease and clarity",
        "tradition": "universal",
        "length": "medium",
        "include_dedication": True,
    }
    base.update(overrides)
    return base


def generate(client: TestClient, **overrides):
    response = client.post("/generate-narrative", json=request_body(**overrides))
    assert response.status_code == 200, response.text
    return response.json()


class TestLengthOptions:
    def test_short_medium_long_produce_different_texts_of_increasing_length(self, client):
        texts = {length: generate(client, length=length)["blessing_text"] for length in SUPPORTED_LENGTHS}
        # Actually different content, not just whitespace.
        assert len({texts["short"], texts["medium"], texts["long"]}) == 3
        # Meaningfully different lengths: short < medium < long.
        assert len(texts["short"]) < len(texts["medium"]) < len(texts["long"])
        # Long extends the medium text rather than replacing it.
        assert texts["long"].startswith(texts["medium"])

    def test_length_is_echoed_in_metadata(self, client):
        for length in SUPPORTED_LENGTHS:
            body = generate(client, length=length)
            assert body["metadata"]["length"] == length

    @pytest.mark.parametrize("tradition", SUPPORTED_TRADITIONS)
    def test_every_tradition_has_all_three_lengths(self, client, tradition):
        sizes = [
            len(generate(client, tradition=tradition, length=length)["blessing_text"]) for length in SUPPORTED_LENGTHS
        ]
        assert sizes[0] < sizes[1] < sizes[2]


class TestTraditionTemplates:
    def test_advertised_traditions_produce_distinct_texts(self, client):
        texts = {
            tradition: generate(client, tradition=tradition)["blessing_text"] for tradition in SUPPORTED_TRADITIONS
        }
        assert len(set(texts.values())) == len(SUPPORTED_TRADITIONS)
        # The old bug: zen/yogic fell back to the universal template.
        assert texts["zen"] != texts["universal"]
        assert texts["yogic"] != texts["universal"]

    def test_existing_tradition_texts_are_preserved_at_medium(self, client):
        universal = generate(client, tradition="universal")["blessing_text"]
        assert "May Alex be filled with loving-kindness." in universal
        assert "May all beings everywhere share in these blessings." in universal

        buddhist = generate(client, tradition="buddhist")["blessing_text"]
        assert "May Alex be free from suffering and the causes of suffering." in buddhist
        assert "Om Mani Padme Hum" in buddhist

        tibetan = generate(client, tradition="tibetan")["blessing_text"]
        assert "In the vast expanse of the primordial ground" in tibetan
        assert "Om Ah Hum Vajra Guru Padma Siddhi Hum" in tibetan

    def test_target_and_intention_are_interpolated(self, client):
        body = generate(
            client,
            target_name="Marta",
            intention="steadiness in a hard week",
        )
        assert "Marta" in body["blessing_text"]
        assert "steadiness in a hard week" in body["blessing_text"]
        assert body["recipients"] == ["Marta"]
        assert body["metadata"]["intention"] == "steadiness in a hard week"

    def test_tradition_mantras_match_catalog_register(self, client):
        # zen keeps the Heart Sutra mantra this endpoint already used; yogic
        # mirrors the /traditions catalog value.
        assert "Gate Gate Paragate Parasamgate Bodhi Svaha" in generate(client, tradition="zen")["blessing_text"]
        assert "Om Namah Shivaya" in generate(client, tradition="yogic")["blessing_text"]


class TestDedication:
    def test_dedication_included_by_default(self, client):
        body = generate(client)
        assert body["dedication"] is not None
        assert "merit" in body["dedication"].lower()

    def test_dedication_omitted_when_disabled(self, client):
        body = generate(client, include_dedication=False)
        assert body["dedication"] is None


class TestTimestamp:
    def test_generated_at_is_the_real_utc_time(self, client):
        before = datetime.now(timezone.utc)
        stamp = generate(client)["metadata"]["generated_at"]
        after = datetime.now(timezone.utc)
        parsed = datetime.fromisoformat(stamp)
        assert parsed.tzinfo is not None
        assert before <= parsed <= after
        # The old hardcoded placeholder is gone.
        assert stamp != "2025-11-16"

    def test_generated_at_is_injectable_for_deterministic_checks(self, client, monkeypatch):
        frozen = "2030-01-02T03:04:05+00:00"
        monkeypatch.setattr(blessings_endpoint, "_utc_now_iso", lambda: frozen)
        assert generate(client)["metadata"]["generated_at"] == frozen


class TestIntentionWording:
    """NEW short/long wording must QUOTE the intention, not assert it.

    A clause-shaped intention (e.g. "Alex is cured of her cancer") used to
    produce ungrammatical outcome-assertions like "May Alex is cured of her
    cancer be fulfilled...". The new scaffolds place the intention after
    "With the intention of"; the pre-existing medium pattern (which asserts)
    is preserved byte-identically and is not covered by this rule.
    """

    CLAUSE_INTENTION = "Alex is cured of her cancer"

    def test_short_quotes_clause_intention_instead_of_asserting_it(self, client):
        text = generate(client, length="short", intention=self.CLAUSE_INTENTION)["blessing_text"]
        assert f"With the intention of {self.CLAUSE_INTENTION}" in text
        assert f"May {self.CLAUSE_INTENTION}" not in text

    def test_long_closing_quotes_clause_intention_instead_of_asserting_it(self, client):
        text = generate(client, length="long", intention=self.CLAUSE_INTENTION)["blessing_text"]
        # The NEW wording is the closing after the (pre-existing, asserting)
        # medium body; scope the assertion to it.
        closing = text[text.index("In every moment and in every place") :]
        assert f"With the intention of {self.CLAUSE_INTENTION}" in closing
        assert f"May {self.CLAUSE_INTENTION}" not in closing
        assert f"May {self.CLAUSE_INTENTION}" in text  # medium body keeps its line

    def test_short_and_long_still_work_with_noun_phrase_intentions(self, client):
        noun = "ease and clarity"
        for length in ("short", "long"):
            text = generate(client, length=length, intention=noun)["blessing_text"]
            assert f"With the intention of {noun}" in text

    def test_medium_keeps_its_pre_existing_intention_line_unchanged(self, client):
        text = generate(client, length="medium", intention=self.CLAUSE_INTENTION)["blessing_text"]
        # Pre-existing (asserting) pattern, required to stay byte-identical:
        assert f"May {self.CLAUSE_INTENTION} be fulfilled for the highest good of all." in text


class TestValidation:
    def test_unsupported_length_is_rejected_with_422_listing_values(self, client):
        response = client.post("/generate-narrative", json=request_body(length="epic"))
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "epic" in detail
        for length in SUPPORTED_LENGTHS:
            assert length in detail

    def test_unsupported_tradition_is_rejected_with_422_listing_values(self, client):
        response = client.post("/generate-narrative", json=request_body(tradition="norse"))
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "norse" in detail
        for tradition in SUPPORTED_TRADITIONS:
            assert tradition in detail

    def test_validation_errors_are_not_masked_as_500(self, client):
        # Regression guard: HTTPException raised inside the handler's try block
        # must pass through, not be converted by the generic except.
        response = client.post("/generate-narrative", json=request_body(length="epic"))
        assert response.status_code == 422

    @pytest.mark.parametrize("tradition", SUPPORTED_TRADITIONS)
    @pytest.mark.parametrize("length", SUPPORTED_LENGTHS)
    def test_supported_combinations_all_succeed(self, client, tradition, length):
        body = generate(client, tradition=tradition, length=length)
        assert body["status"] == "success"
        assert body["tradition"] == tradition
