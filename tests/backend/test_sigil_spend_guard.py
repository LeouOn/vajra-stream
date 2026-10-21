"""SB-1: sigil's PAID image branches must spend from the shared budget.

RED-first. At HEAD, sigil's two paid branches (OpenAI dall-e-3, OpenRouter) had
no cap, no hourly limit and no cost record at all -- verified with a faked
``requests.post``:

    SIGIL openai  8 concurrent -> paid_posts=8 images_returned=8
    budget state: has _daily_spend=False has _spend_lock=False has budget=False

The local (Stable Diffusion) and comfyui providers are free and must reserve
nothing. No network and no API key: ``requests.post`` and ``requests.get`` are
monkeypatched, and the budget is the module's real ``SpendBudget``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.core.services import sigil_service as sig
from backend.core.services.spend_budget import SpendBudget

OPENAI_ESTIMATE = sig.SIGIL_IMAGE_COST_ESTIMATE_USD["openai"]
OPENROUTER_ESTIMATE = sig.SIGIL_IMAGE_COST_ESTIMATE_USD["openrouter"]


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None, content: bytes = b"") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = content
        self.text = ""

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.fixture(autouse=True)
def fresh_budget(monkeypatch: pytest.MonkeyPatch) -> SpendBudget:
    """A FRESH budget per test -- the module's shared instance is replaced so no
    test can see another's spend, and the real one is never mutated."""
    budget = SpendBudget(daily_cost_cap_usd=100.0, max_per_hour=1000)
    monkeypatch.setattr(sig, "shared_image_budget", lambda: budget)
    return budget


@pytest.fixture
def sigil(tmp_path, monkeypatch: pytest.MonkeyPatch) -> sig.SigilService:
    """A SigilService configured for the PAID openai path.

    ``SigilService`` is a process-wide singleton (``__new__`` returns one
    instance and ``__init__`` is guarded by ``_initialized``), so constructing
    it per test does NOT re-read the environment. The provider fields are
    therefore set on the instance directly, and ``storage_dir`` is repointed at
    this test's tmp_path so nothing is written into the repo.
    """
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    service = sig.SigilService(storage_dir=str(tmp_path / "sigils"))
    service.storage_dir = tmp_path / "sigils"
    service.storage_dir.mkdir(parents=True, exist_ok=True)
    service.image_provider = "openai"
    service.openai_api_key = "fake-key"
    service.openrouter_api_key = "fake-key"
    return service


def install_openai_post(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any] | None = None, status_code: int = 200
) -> list[str]:
    """Fake ``requests.post``; returns the list of URLs it was called with."""
    calls: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append(url)
        body = payload if payload is not None else {"data": [{"b64_json": "aGk="}]}
        return FakeResponse(status_code=status_code, payload=body)

    monkeypatch.setattr(sig.requests, "post", fake_post)
    return calls


# ---------------------------------------------------------------------------
# a paid call reserves, and settles at the estimate when the provider is silent
# ---------------------------------------------------------------------------


def test_openai_paid_call_reserves_and_keeps_the_estimate(sigil, fresh_budget, monkeypatch) -> None:
    calls = install_openai_post(monkeypatch)

    image, skip = sigil._request_image("a sigil intention")

    assert skip is None
    assert image is not None and image.startswith("data:image/png;base64,")
    assert len(calls) == 1
    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(OPENAI_ESTIMATE)
    assert stats["hourly_calls"] == 1


def test_openrouter_paid_call_reserves(sigil, fresh_budget, monkeypatch) -> None:
    sigil.image_provider = "openrouter"
    sigil.openrouter_image_model = "some/model"

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse(payload={"data": [{"url": "https://example.invalid/i.png"}]})

    monkeypatch.setattr(sig.requests, "post", fake_post)
    monkeypatch.setattr(sig.requests, "get", lambda url, **kw: FakeResponse(content=b"bytes"))

    image, skip = sigil._request_image("a sigil intention")

    assert skip is None and image is not None
    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(OPENROUTER_ESTIMATE)


def test_local_provider_reserves_nothing(sigil, fresh_budget, monkeypatch) -> None:
    """The free local provider must not touch the budget at all."""
    sigil.image_provider = "local"

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse(payload={"images": ["aGk="]})

    monkeypatch.setattr(sig.requests, "post", fake_post)

    image, skip = sigil._request_image("a sigil intention")

    assert skip is None and image is not None
    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(0.0)
    assert stats["hourly_calls"] == 0


# ---------------------------------------------------------------------------
# reconcile to an ACTUAL cost when the provider reports one
# ---------------------------------------------------------------------------


def test_reported_actual_cost_replaces_the_estimate(sigil, fresh_budget, monkeypatch) -> None:
    install_openai_post(monkeypatch, payload={"data": [{"b64_json": "aGk="}], "usage": {"cost": 0.0123}})

    sigil._request_image("a sigil intention")

    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(0.0123)
    assert fresh_budget.stats()["hourly_calls"] == 1


def test_a_zero_cost_field_is_not_treated_as_free(sigil, fresh_budget, monkeypatch) -> None:
    """cost: 0 means "not reported here", not "this call was free"."""
    install_openai_post(monkeypatch, payload={"data": [{"b64_json": "aGk="}], "usage": {"cost": 0}})

    sigil._request_image("a sigil intention")

    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(OPENAI_ESTIMATE)


# ---------------------------------------------------------------------------
# release on failure
# ---------------------------------------------------------------------------


def test_failed_request_releases_the_reservation(sigil, fresh_budget, monkeypatch) -> None:
    install_openai_post(monkeypatch, status_code=500)

    image, skip = sigil._request_image("a sigil intention")

    assert image is None and skip is None, "a provider failure is not a budget skip"
    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(0.0)
    assert stats["hourly_calls"] == 0


# ---------------------------------------------------------------------------
# release vs keep: only a provider that definitely did NOT bill gets refunded
#
# Built the way requests builds them, so the shapes are real:
#   requests.ConnectionError(urllib3.exceptions.MaxRetryError(...,
#       reason=urllib3.exceptions.NewConnectionError(...)))   -> not sent
#   requests.ConnectionError(urllib3.exceptions.ProtocolError(...))          -> sent
# ---------------------------------------------------------------------------


def _new_connection_error() -> Exception:
    """requests' shape for "could not connect": nothing was sent."""
    import urllib3.exceptions

    return sig.requests.ConnectionError(
        urllib3.exceptions.MaxRetryError(
            None,
            "https://api.openai.com/v1/images/generations",
            reason=urllib3.exceptions.NewConnectionError(None, "Failed to establish a new connection"),
        )
    )


def _protocol_error() -> Exception:
    """requests' shape for a mid-response reset: the bytes WERE sent."""
    import urllib3.exceptions

    return sig.requests.ConnectionError(urllib3.exceptions.ProtocolError("Connection aborted.", ConnectionResetError))


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_connection_error_that_never_reached_the_provider_releases(sigil, fresh_budget, monkeypatch, provider) -> None:
    sigil.image_provider = provider
    install_openai_post(monkeypatch)

    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise _new_connection_error()

    monkeypatch.setattr(sig.requests, "post", boom)

    image, skip = sigil._request_image("a sigil intention")

    assert image is None and skip is None
    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(0.0), "nothing was sent, so nothing was billed"
    assert stats["hourly_calls"] == 0


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_connect_timeout_releases_the_reservation(sigil, fresh_budget, monkeypatch, provider) -> None:
    sigil.image_provider = provider
    install_openai_post(monkeypatch)

    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise sig.requests.ConnectTimeout("timed out before sending")

    monkeypatch.setattr(sig.requests, "post", boom)

    sigil._request_image("a sigil intention")

    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(0.0)


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_connection_error_wrapping_a_protocol_error_keeps_the_reservation(
    sigil, fresh_budget, monkeypatch, provider
) -> None:
    """A mid-response reset: the request bytes were written."""
    sigil.image_provider = provider
    install_openai_post(monkeypatch)

    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise _protocol_error()

    monkeypatch.setattr(sig.requests, "post", boom)

    sigil._request_image("a sigil intention")

    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(sig.SIGIL_IMAGE_COST_ESTIMATE_USD[provider])


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_ssl_error_keeps_the_reservation(sigil, fresh_budget, monkeypatch, provider) -> None:
    """SSLError is a ConnectionError SUBCLASS, so a naive handler refunds it."""
    sigil.image_provider = provider
    install_openai_post(monkeypatch)

    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise sig.requests.exceptions.SSLError("handshake failed")

    monkeypatch.setattr(sig.requests, "post", boom)

    sigil._request_image("a sigil intention")

    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(sig.SIGIL_IMAGE_COST_ESTIMATE_USD[provider])


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_read_timeout_keeps_the_reservation(sigil, fresh_budget, monkeypatch, provider) -> None:
    """The request WAS transmitted; the provider may have billed it."""
    sigil.image_provider = provider
    install_openai_post(monkeypatch)

    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise sig.requests.ReadTimeout("read timed out")

    monkeypatch.setattr(sig.requests, "post", boom)

    sigil._request_image("a sigil intention")

    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(sig.SIGIL_IMAGE_COST_ESTIMATE_USD[provider])


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
@pytest.mark.parametrize("status", [429, 500])
def test_non_2xx_generation_status_releases_the_reservation(sigil, fresh_budget, monkeypatch, provider, status) -> None:
    sigil.image_provider = provider
    install_openai_post(monkeypatch, status_code=status)

    sigil._request_image("a sigil intention")

    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(0.0)
    assert stats["hourly_calls"] == 0


@pytest.mark.parametrize("status", [404, 500])
def test_openrouter_failed_image_download_keeps_the_reservation(sigil, fresh_budget, monkeypatch, status) -> None:
    """The GENERATION succeeded and was billed; only the download failed."""
    sigil.image_provider = "openrouter"
    sigil.openrouter_image_model = "some/model"

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse(payload={"data": [{"url": "https://example.invalid/i.png"}]})

    monkeypatch.setattr(sig.requests, "post", fake_post)
    monkeypatch.setattr(sig.requests, "get", lambda url, **kw: FakeResponse(status_code=status))

    image, skip = sigil._request_image("a sigil intention")

    assert image is None and skip is None
    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(OPENROUTER_ESTIMATE)
    assert stats["hourly_calls"] == 1


@pytest.mark.parametrize("exc_name", ["ConnectionError", "ConnectTimeout", "ReadTimeout"])
def test_openrouter_download_exceptions_keep_the_reservation(sigil, fresh_budget, monkeypatch, exc_name) -> None:
    """The download sits in the same try as the POST; it must not refund it."""
    sigil.image_provider = "openrouter"
    sigil.openrouter_image_model = "some/model"

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse(payload={"data": [{"url": "https://example.invalid/i.png"}]})

    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise getattr(sig.requests, exc_name)("download failed")

    monkeypatch.setattr(sig.requests, "post", fake_post)
    monkeypatch.setattr(sig.requests, "get", boom)

    image, skip = sigil._request_image("a sigil intention")

    assert image is None and skip is None
    stats = fresh_budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(
        OPENROUTER_ESTIMATE
    ), f"a download {exc_name} must not refund a billed generation"


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_malformed_success_body_keeps_the_reservation(sigil, fresh_budget, monkeypatch, provider) -> None:
    """HTTP 2xx means the image WAS generated, even if we cannot read the body."""
    sigil.image_provider = provider
    install_openai_post(monkeypatch, payload={"unexpected": "shape"})

    image, skip = sigil._request_image("a sigil intention")

    assert image is None and skip is None
    assert fresh_budget.stats()["daily_spend_usd"] == pytest.approx(sig.SIGIL_IMAGE_COST_ESTIMATE_USD[provider])


def test_kept_reservation_logs_exactly_one_warning(sigil, fresh_budget, monkeypatch, caplog) -> None:
    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise sig.requests.ReadTimeout("read timed out")

    monkeypatch.setattr(sig.requests, "post", boom)

    with caplog.at_level("WARNING"):
        sigil._request_image("a sigil intention")

    keeps = [r for r in caplog.records if "keeping the budget reservation" in r.getMessage()]
    assert len(keeps) == 1, f"expected one keep-warning, got {len(keeps)}"


def test_released_reservation_logs_no_keep_warning(sigil, fresh_budget, monkeypatch, caplog) -> None:
    def boom(url: str, **kwargs: Any) -> FakeResponse:
        raise _new_connection_error()

    monkeypatch.setattr(sig.requests, "post", boom)

    with caplog.at_level("WARNING"):
        sigil._request_image("a sigil intention")

    assert not [r for r in caplog.records if "keeping the budget reservation" in r.getMessage()]


# ---------------------------------------------------------------------------
# refusal: warn, return None, never raise
# ---------------------------------------------------------------------------


def test_refusal_warns_once_and_returns_the_budget_skip_reason(sigil, fresh_budget, monkeypatch, caplog) -> None:
    fresh_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE / 2, max_per_hour=100)
    calls = install_openai_post(monkeypatch)

    with caplog.at_level("WARNING"):
        image, skip = sigil._request_image("a sigil intention")

    assert image is None
    assert skip == "budget"
    assert calls == [], "a refused call must not reach the provider"
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1, f"expected exactly one warning, got {len(warnings)}"
    assert "budget" in warnings[0].getMessage().lower()


def test_refusal_does_not_raise_into_generate_ai_image(sigil, fresh_budget, monkeypatch) -> None:
    fresh_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE / 2, max_per_hour=100)
    install_openai_post(monkeypatch)

    result = asyncio_run(sigil.generate_ai_image("a sigil intention"))

    assert result["ai_image"] is None
    assert result["ai_image_render"] is None
    assert result["ai_image_skipped"] == "budget"


def test_no_skip_key_on_the_normal_path(sigil, fresh_budget, monkeypatch) -> None:
    """Additive means additive: the normal shape must be unchanged."""
    install_openai_post(monkeypatch)

    result = asyncio_run(sigil.generate_ai_image("a sigil intention"))

    assert set(result) == {"ai_image", "ai_image_render"}


def test_hourly_limit_also_refuses_a_sigil(sigil, fresh_budget, monkeypatch) -> None:
    fresh_budget.configure(daily_cost_cap_usd=100.0, max_per_hour=1)
    install_openai_post(monkeypatch)

    first, first_skip = sigil._request_image("one")
    second, second_skip = sigil._request_image("two")

    assert first_skip is None and first is not None
    assert second_skip == "budget" and second is None


def test_sigil_spend_reduces_the_room_left_for_images(sigil, fresh_budget, monkeypatch) -> None:
    """One shared dollar cap: a sigil's spend is visible to the next caller."""
    fresh_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE * 2, max_per_hour=100)
    install_openai_post(monkeypatch)

    sigil._request_image("one")
    remaining = fresh_budget.stats()["daily_spend_usd"]

    # A hypothetical image call of the same price now has room for exactly one more.
    assert remaining == pytest.approx(OPENAI_ESTIMATE)
    reservation = fresh_budget.try_reserve(OPENAI_ESTIMATE)
    assert reservation is not None
    assert fresh_budget.try_reserve(OPENAI_ESTIMATE) is None, "the cap must now be full"


def test_stored_sigil_records_the_skip_reason(sigil, fresh_budget, monkeypatch, tmp_path) -> None:
    """The stored sigil shows WHY there is no AI image, not just that it is None."""
    fresh_budget.configure(daily_cost_cap_usd=OPENAI_ESTIMATE / 2, max_per_hour=100)
    install_openai_post(monkeypatch)

    data = asyncio_run(sigil.forge_sigil("a sigil intention", kamea_name="saturn"))

    assert data["ai_image"] is None
    assert data["ai_image_skipped"] == "budget"
    stored = json.loads(next(iter(sorted(tmp_path.rglob("*.json")))).read_text(encoding="utf-8"))
    assert stored["ai_image_skipped"] == "budget"


def asyncio_run(coro):
    """Run a coroutine without importing asyncio at module scope in the tests."""
    import asyncio

    return asyncio.run(coro)
