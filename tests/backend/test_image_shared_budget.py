"""SB-1: images and sigils really do share ONE dollar budget.

Exercised through the REAL composition: the endpoint's service singleton (built
the way ``endpoints/image_generation.py`` builds it, with the DB loaders stubbed
so nothing touches the database) plus a real ``SigilService``, both pointed at
``shared_image_budget()``.

No network and no provider key: ``requests.post`` / ``requests.get`` and the
image provider seam are fakes.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from backend.app.api.v1.endpoints import image_generation as image_endpoint
from backend.core.services import sigil_service as sig
from backend.core.services import spend_budget as sb
from backend.core.services.image_generation_service import (
    DEFAULT_CONFIG,
    ImageGenerationService,
    ProviderResult,
)

OPENAI_ESTIMATE = sig.SIGIL_IMAGE_COST_ESTIMATE_USD["openai"]
IMAGE_ESTIMATE = 0.034  # the default model's listed cost


@pytest.fixture(autouse=True)
def fresh_shared_budget(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Replace the process-wide budget with a fresh one for every test.

    The real instance is module state, so leaving it dirty would let one test's
    spend refuse the next. Restored by monkeypatch; the original is never spent.
    """
    budget = sb.SpendBudget(daily_cost_cap_usd=100.0, max_per_hour=1000)
    monkeypatch.setattr(sb, "_shared_budget", budget)
    return budget


@pytest.fixture
def endpoint_service(monkeypatch: pytest.MonkeyPatch, tmp_path) -> ImageGenerationService:
    """The endpoint's service, built the real way minus the database.

    ``get_service`` normally pulls persisted config from the DB. That is stubbed
    out so this test cannot open vajra_stream.db.
    """
    monkeypatch.setattr(image_endpoint, "_load_config_from_db", lambda service: None)
    monkeypatch.setattr(image_endpoint, "_inject_fallback_keys", lambda service: None)
    monkeypatch.setattr(image_endpoint, "_anchor_output_dir", lambda service: None)
    monkeypatch.setattr(image_endpoint, "_service", None)
    service = image_endpoint.get_service()
    service.update_config({"enabled": True, "image_output_dir": str(tmp_path)})
    return service


@pytest.fixture
def sigil(tmp_path, monkeypatch: pytest.MonkeyPatch) -> sig.SigilService:
    service = sig.SigilService(storage_dir=str(tmp_path / "sigils"))
    service.storage_dir = tmp_path / "sigils"
    service.storage_dir.mkdir(parents=True, exist_ok=True)
    service.image_provider = "openai"
    service.openai_api_key = "fake-key"
    service.openrouter_api_key = "fake-key"
    return service


def install_sigil_post(monkeypatch: pytest.MonkeyPatch, calls: list[str] | None = None) -> list[str]:
    posted: list[str] = calls if calls is not None else []

    class Resp:
        status_code = 200
        content = b""
        text = ""

        def json(self) -> dict[str, Any]:
            return {"data": [{"b64_json": "aGk="}]}

    def fake_post(url: str, **kwargs: Any) -> Resp:
        posted.append(url)
        return Resp()

    monkeypatch.setattr(sig.requests, "post", fake_post)
    return posted


def install_image_provider(
    service: ImageGenerationService, monkeypatch: pytest.MonkeyPatch, calls: list[int] | None = None
) -> list[int]:
    counter = calls if calls is not None else []
    monkeypatch.setattr(
        service,
        "_get_provider",
        lambda name: _FakeProvider(counter),
    )
    return counter


class _FakeProvider:
    def __init__(self, counter: list[int]) -> None:
        self.counter = counter

    async def generate(self, **kwargs: Any) -> ProviderResult:
        self.counter.append(1)
        await asyncio.sleep(0.02)  # a real await, so callers genuinely overlap
        return ProviderResult(
            image_data_url="not-a-data-url",
            model=kwargs.get("model", "m"),
            cost_usd=IMAGE_ESTIMATE,
            provider="fake",
        )


# ---------------------------------------------------------------------------
# the placeholders are the shipped defaults
# ---------------------------------------------------------------------------


def test_shared_budget_placeholders_equal_the_image_service_defaults() -> None:
    """A sigil forged before any image request must not spend against a third
    set of numbers."""
    monkey = sb.SpendBudget(daily_cost_cap_usd=0.50, max_per_hour=10)
    stats = monkey.stats()
    assert stats["daily_cost_cap_usd"] == DEFAULT_CONFIG["daily_cost_cap_usd"]
    assert stats["max_per_hour"] == DEFAULT_CONFIG["max_per_hour"]


def test_a_fresh_shared_budget_uses_the_shipped_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sb, "_shared_budget", None)
    stats = sb.shared_image_budget().stats()
    assert stats["daily_cost_cap_usd"] == DEFAULT_CONFIG["daily_cost_cap_usd"]
    assert stats["max_per_hour"] == DEFAULT_CONFIG["max_per_hour"]


# ---------------------------------------------------------------------------
# the endpoint's service uses the shared budget
# ---------------------------------------------------------------------------


def test_endpoint_service_uses_the_shared_budget(endpoint_service) -> None:
    assert endpoint_service._budget is sb.shared_image_budget()


def test_service_without_injection_keeps_a_private_budget() -> None:
    private = ImageGenerationService()
    assert private._budget is not sb.shared_image_budget()


# ---------------------------------------------------------------------------
# both directions of sharing
# ---------------------------------------------------------------------------


def test_a_sigil_spend_reduces_the_room_left_for_an_image(
    endpoint_service, sigil, fresh_shared_budget, monkeypatch
) -> None:
    fresh_shared_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE + IMAGE_ESTIMATE, max_per_hour=100)
    install_sigil_post(monkeypatch)
    image_calls = install_image_provider(endpoint_service, monkeypatch)

    sigil._request_image("one")
    assert fresh_shared_budget.stats()["daily_spend_usd"] == pytest.approx(OPENAI_ESTIMATE)

    result = asyncio.run(endpoint_service.generate("an image prompt"))
    assert result["cached"] is False
    assert len(image_calls) == 1
    assert fresh_shared_budget.stats()["daily_spend_usd"] == pytest.approx(OPENAI_ESTIMATE + IMAGE_ESTIMATE)


def test_an_image_spend_reduces_the_room_left_for_a_sigil(
    endpoint_service, sigil, fresh_shared_budget, monkeypatch
) -> None:
    fresh_shared_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE + IMAGE_ESTIMATE, max_per_hour=100)
    posts = install_sigil_post(monkeypatch)
    install_image_provider(endpoint_service, monkeypatch)

    asyncio.run(endpoint_service.generate("an image prompt"))

    image, skip = sigil._request_image("one")
    assert image is not None and skip is None
    assert len(posts) == 1


def test_a_sigil_can_be_refused_once_images_spent_the_cap(
    endpoint_service, sigil, fresh_shared_budget, monkeypatch
) -> None:
    """The product trade-off, stated as a test rather than a caveat."""
    fresh_shared_budget.configure(daily_cost_cap_usd=IMAGE_ESTIMATE, max_per_hour=100)
    install_sigil_post(monkeypatch)
    install_image_provider(endpoint_service, monkeypatch)

    asyncio.run(endpoint_service.generate("an image prompt"))

    image, skip = sigil._request_image("one")
    assert image is None
    assert skip == "budget"


def test_changing_the_image_settings_changes_the_limit_the_sigil_sees(
    endpoint_service, sigil, fresh_shared_budget, monkeypatch
) -> None:
    posts = install_sigil_post(monkeypatch)

    fresh_shared_budget.configure(daily_cost_cap_usd=0.10, max_per_hour=100)
    endpoint_service.update_config({"daily_cost_cap_usd": 0.10})
    sigil._request_image("one")
    assert len(posts) == 1

    fresh_shared_budget.configure(daily_cost_cap_usd=10.0, max_per_hour=100)
    endpoint_service.update_config({"daily_cost_cap_usd": 10.0})
    sigil._request_image("two")
    assert len(posts) == 2, "the raised image cap must apply to sigils too"

    # And lowering it refuses the next sigil.
    endpoint_service.update_config({"daily_cost_cap_usd": 0.0001})
    _image, skip = sigil._request_image("three")
    assert skip == "budget"


# ---------------------------------------------------------------------------
# the thread proof the row asked for: real asyncio.to_thread workers
# ---------------------------------------------------------------------------


def test_eight_concurrent_sigil_forges_pay_exactly_once(sigil, fresh_shared_budget, monkeypatch) -> None:
    """8 concurrent generate_ai_image calls through asyncio.to_thread workers.

    ``_generate_sync_image`` dispatches to a worker THREAD, so these run on eight
    different OS threads against one shared budget. With room for exactly one,
    exactly one may reach the paid provider.
    """
    fresh_shared_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE, max_per_hour=100)
    posts = install_sigil_post(monkeypatch)

    async def main() -> list[dict[str, Any]]:
        return await asyncio.gather(*[sigil.generate_ai_image(f"intention {i}") for i in range(8)])

    results = asyncio.run(main())

    assert len(posts) == 1, f"exactly one paid POST, got {len(posts)}"
    skipped = [r for r in results if r.get("ai_image_skipped") == "budget"]
    assert len(skipped) == 7, f"the other seven must be skipped, got {len(skipped)}"
    assert sum(1 for r in results if r["ai_image"] is not None) == 1
    stats = fresh_shared_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(OPENAI_ESTIMATE)
    assert stats["hourly_calls"] == 1


def test_stored_sigil_records_the_shared_budget_skip(sigil, fresh_shared_budget, monkeypatch, tmp_path) -> None:
    fresh_shared_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE / 2, max_per_hour=100)
    install_sigil_post(monkeypatch)

    data = asyncio.run(sigil.forge_sigil("an intention", kamea_name="saturn"))

    assert data["ai_image_skipped"] == "budget"
    stored = json.loads(next(iter(sorted(tmp_path.rglob("*.json")))).read_text(encoding="utf-8"))
    assert stored["ai_image_skipped"] == "budget"


# ---------------------------------------------------------------------------
# REWORK 2 (3): the published cap must be the ENFORCED cap
# ---------------------------------------------------------------------------


def test_cost_stats_publishes_the_budgets_enforced_cap(endpoint_service, fresh_shared_budget) -> None:
    """The budget is what enforces the limit, so the budget is what is published.

    The endpoint's service configures the shared budget, so in the normal case
    the two agree -- but the published value must come from the budget, so that
    a last-writer configure() cannot leave the UI announcing a limit that is not
    the one in force.
    """
    # Configure the BUDGET to values the service's own config does NOT have, so
    # publishing the service's config would give the wrong answer.
    fresh_shared_budget.configure(daily_cost_cap_usd=7.5, max_per_hour=3)
    assert endpoint_service.config["daily_cost_cap_usd"] != 7.5

    stats = endpoint_service.get_cost_stats()

    assert stats["daily_cost_cap_usd"] == 7.5, "the published cap must be the ENFORCED one"
    assert stats["max_per_hour"] == 3


def test_cost_stats_keys_and_types_are_unchanged(endpoint_service) -> None:
    stats = endpoint_service.get_cost_stats()
    assert list(stats.keys()) == [
        "daily_spend_usd",
        "daily_cost_cap_usd",
        "hourly_calls",
        "max_per_hour",
        "cache_entries",
    ]
    assert isinstance(stats["daily_spend_usd"], float)
    assert isinstance(stats["daily_cost_cap_usd"], float)
    assert isinstance(stats["hourly_calls"], int)
    assert isinstance(stats["max_per_hour"], int)
    assert isinstance(stats["cache_entries"], int)
