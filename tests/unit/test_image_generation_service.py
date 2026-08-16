"""Tests for the modular ImageGenerationService.

These tests intentionally exercise the service as a standalone module —
no Vajra.Stream container, event bus, settings, or DB is required. This
is the proof that the service can be extracted to a standalone repo by
copying ``backend/core/services/image_generation_service.py`` plus
``pip install httpx``.
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.services.image_generation_service import (
    DEFAULT_CONFIG,
    MODEL_COST_USD,
    ImageGenerationService,
    MiniMaxProvider,
    OpenRouterProvider,
    PermanentProviderError,
    create_service_from_env,
)

FAKE_B64 = base64.b64encode(b"\x89PNG_FAKE_BYTES").decode("ascii")


def _response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


def _patched_client(post_response: MagicMock):
    """Return a configured ``httpx.AsyncClient`` mock with the given response wired to ``.post()``.

    Uses MagicMock for the client (not AsyncMock) so attribute access returns
    regular mocks instead of auto-generated AsyncMocks. ``__aenter__`` /
    ``__aexit__`` are explicitly set as AsyncMocks.
    """
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=post_response)
    return client


# ── Construction & config ───────────────────────────────────────────────


def test_default_config_has_safe_defaults():
    assert DEFAULT_CONFIG["enabled"] is False
    assert DEFAULT_CONFIG["daily_cost_cap_usd"] == 0.50
    assert DEFAULT_CONFIG["max_per_hour"] == 10
    assert DEFAULT_CONFIG["max_prompt_tokens"] == 1000


def test_constructor_with_no_args_uses_defaults():
    service = ImageGenerationService()
    assert service.config == DEFAULT_CONFIG


def test_constructor_overrides_config():
    service = ImageGenerationService({"enabled": True, "daily_cost_cap_usd": 1.0, "default_model": "image-01"})
    assert service.config["enabled"] is True
    assert service.config["daily_cost_cap_usd"] == 1.0
    assert service.config["default_model"] == "image-01"
    assert service.config["max_per_hour"] == DEFAULT_CONFIG["max_per_hour"]


def test_update_config_rejects_unknown_keys():
    service = ImageGenerationService()
    with pytest.raises(ValueError, match="unknown config key"):
        service.update_config({"nonsense_key": "value"})


def test_update_config_preserves_other_keys():
    service = ImageGenerationService({"enabled": True, "daily_cost_cap_usd": 0.25})
    service.update_config({"daily_cost_cap_usd": 0.75})
    assert service.config["enabled"] is True
    assert service.config["daily_cost_cap_usd"] == 0.75


# ── Prompt validation ───────────────────────────────────────────────────


def test_validate_prompt_short_ok():
    service = ImageGenerationService()
    result = service.validate_prompt("A heart chakra mandala")
    assert result["ok"] is True
    assert result["estimated_tokens"] > 0


def test_validate_prompt_too_long_suggests_truncation():
    service = ImageGenerationService({"max_prompt_tokens": 10})
    long_prompt = " ".join(["lotus"] * 50)
    result = service.validate_prompt(long_prompt)
    assert result["ok"] is False
    assert "tokens" in result["error"]
    assert "suggestion" in result
    assert len(result["suggestion"].split()) <= 60


def test_validate_prompt_counts_cjk_characters():
    service = ImageGenerationService()
    result = service.validate_prompt("觀世音菩薩" * 100)
    assert result["estimated_tokens"] > 0


# ── Cost & rate tracking ────────────────────────────────────────────────


def test_cost_stats_initial_zero():
    service = ImageGenerationService()
    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.0
    assert stats["hourly_calls"] == 0
    assert stats["cache_entries"] == 0


def test_cost_stats_reflects_cache_size():
    service = ImageGenerationService()
    from backend.core.services.image_generation_service import ProviderResult

    fake = ProviderResult(
        image_data_url="data:image/png;base64,abc",
        model="test-model",
        cost_usd=0.01,
        provider="openrouter",
    )
    service._cache["k1"] = (1e18, fake)
    service._cache["k2"] = (1e18, fake)
    assert service.get_cost_stats()["cache_entries"] == 2


# ── Provider selection & guards ─────────────────────────────────────────


def test_get_provider_unknown_raises():
    service = ImageGenerationService({"openrouter_api_key": "sk-test"})
    with pytest.raises(ValueError, match="Unknown image provider"):
        service._get_provider("does-not-exist")


def test_openrouter_provider_requires_key_at_construction():
    with pytest.raises(RuntimeError, match="OpenRouter API key not configured"):
        OpenRouterProvider(api_key="")


def test_minimax_provider_requires_key_at_construction():
    with pytest.raises(RuntimeError, match="MiniMax API key not configured"):
        MiniMaxProvider(api_key="")


# ── End-to-end generate() with mocked HTTP ──────────────────────────────


@pytest.mark.asyncio
async def test_generate_openrouter_success():
    service = ImageGenerationService(
        {"enabled": True, "openrouter_api_key": "sk-or-test", "default_provider": "openrouter"}
    )
    client = _patched_client(_response(json_data={"images": [{"b64_json": FAKE_B64, "revised_prompt": "vivid"}]}))
    with patch("httpx.AsyncClient", return_value=client):
        result = await service.generate(prompt="heart chakra mandala, golden")

    assert result["image_data_url"].startswith("data:image/png;base64,")
    assert result["model"] == DEFAULT_CONFIG["default_model"]
    assert result["provider_used"] == "openrouter"
    assert result["cached"] is False
    assert result["revised_prompt"] == "vivid"


@pytest.mark.asyncio
async def test_generate_minimax_with_aspect_ratio():
    """Supported ratios pass through verbatim; unsupported ones fall back to 1:1."""
    service = ImageGenerationService({"enabled": True, "minimax_api_key": "sk-mm-test", "default_provider": "minimax"})
    client = _patched_client(_response(json_data={"data": {"image_base64": [FAKE_B64]}}))
    with patch("httpx.AsyncClient", return_value=client):
        result = await service.generate(
            prompt="green tara portrait",
            provider="minimax",
            model="image-01",
            aspect_ratio="3:4",
        )

    body = client.post.call_args.kwargs["json"]
    assert body["aspect_ratio"] == "3:4"
    assert "size" not in body
    assert result["provider_used"] == "minimax"


@pytest.mark.asyncio
async def test_generate_minimax_unsupported_aspect_ratio_falls_back():
    """image-01 supports only 1:1/16:9/9:16/4:3/3:4 — anything else degrades to 1:1."""
    service = ImageGenerationService({"enabled": True, "minimax_api_key": "sk-mm-test", "default_provider": "minimax"})
    client = _patched_client(_response(json_data={"data": {"image_base64": [FAKE_B64]}}))
    with patch("httpx.AsyncClient", return_value=client):
        await service.generate(
            prompt="green tara portrait",
            provider="minimax",
            model="image-01",
            aspect_ratio="4:5",
        )

    body = client.post.call_args.kwargs["json"]
    assert body["aspect_ratio"] == "1:1"


@pytest.mark.asyncio
async def test_generate_disabled_raises():
    service = ImageGenerationService({"enabled": False})
    with pytest.raises(RuntimeError, match="disabled"):
        await service.generate(prompt="anything")


@pytest.mark.asyncio
async def test_generate_prompt_over_limit_raises():
    service = ImageGenerationService({"enabled": True, "max_prompt_tokens": 5})
    with pytest.raises(ValueError, match="tokens"):
        await service.generate(prompt="word " * 50)


@pytest.mark.asyncio
async def test_generate_daily_cost_cap_enforced():
    service = ImageGenerationService(
        {
            "enabled": True,
            "openrouter_api_key": "sk-or-test",
            "daily_cost_cap_usd": 0.05,
            "default_model": "google/gemini-3.1-flash-lite-image",
        }
    )
    client = _patched_client(_response(json_data={"images": [{"b64_json": FAKE_B64}]}))
    with patch("httpx.AsyncClient", return_value=client):
        await service.generate(prompt="first image")

    with pytest.raises(RuntimeError, match="daily cost cap"):
        await service.generate(prompt="second image")


@pytest.mark.asyncio
async def test_generate_caches_result():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test"})
    client = _patched_client(_response(json_data={"images": [{"b64_json": FAKE_B64}]}))
    with patch("httpx.AsyncClient", return_value=client):
        first = await service.generate(prompt="same prompt")
        second = await service.generate(prompt="same prompt")

    assert first["cached"] is False
    assert second["cached"] is True
    assert client.post.call_count == 1


@pytest.mark.asyncio
async def test_generate_n_greater_than_1_clamps_to_1():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test", "max_images_per_call": 3})
    client = _patched_client(_response(json_data={"images": [{"b64_json": FAKE_B64}]}))
    with patch("httpx.AsyncClient", return_value=client):
        result = await service.generate(prompt="mandala", n=3)

    body = client.post.call_args.kwargs["json"]
    assert body["n"] == 1
    assert result["cost_usd"] == MODEL_COST_USD[DEFAULT_CONFIG["default_model"]]


@pytest.mark.asyncio
async def test_generate_4xx_does_not_retry_raises_permanent():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test"})
    client = _patched_client(_response(status_code=402, text="insufficient credits"))
    with patch("httpx.AsyncClient", return_value=client):
        with pytest.raises(PermanentProviderError, match="OpenRouter image API error 402"):
            await service.generate(prompt="x")
    assert client.post.call_count == 1


@pytest.mark.asyncio
async def test_generate_empty_response_retries_then_wraps():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test"})
    client = _patched_client(_response(json_data={"images": []}))
    with patch("httpx.AsyncClient", return_value=client):
        with pytest.raises(RuntimeError, match="failed after 2 tries"):
            await service.generate(prompt="x")
    assert client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_5xx_retries_then_wraps():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test"})
    client = _patched_client(_response(status_code=503, text="upstream down"))
    with patch("httpx.AsyncClient", return_value=client):
        with pytest.raises(RuntimeError, match="failed after 2 tries"):
            await service.generate(prompt="x")
    assert client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_succeeds_on_second_try():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test"})
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(
        side_effect=[
            _response(status_code=503, text="transient"),
            _response(json_data={"images": [{"b64_json": FAKE_B64}]}),
        ]
    )
    with patch("httpx.AsyncClient", return_value=client):
        result = await service.generate(prompt="mandala")
    assert client.post.call_count == 2
    assert result["image_data_url"].startswith("data:image/png;base64,")
    assert result["cached"] is False


@pytest.mark.asyncio
async def test_generate_openrouter_url_response_fetches_and_converts():
    service = ImageGenerationService({"enabled": True, "openrouter_api_key": "sk-or-test"})
    img_bytes = b"\x89PNG\r\n\x1a\n fake image data"
    img_resp = MagicMock()
    img_resp.content = img_bytes
    img_resp.headers = {"content-type": "image/png"}
    img_resp.raise_for_status = MagicMock()

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=_response(json_data={"images": [{"url": "https://cdn.example.com/img.png"}]}))
    client.get = AsyncMock(return_value=img_resp)

    with patch("httpx.AsyncClient", return_value=client):
        result = await service.generate(prompt="test")
    assert result["image_data_url"].startswith("data:image/png;base64,")
    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_generate_minimax_image_urls_shape():
    service = ImageGenerationService({"enabled": True, "minimax_api_key": "sk-mm-test", "default_provider": "minimax"})
    client = _patched_client(_response(json_data={"data": {"image_urls": ["https://cdn.example.com/img.png"]}}))
    with patch("httpx.AsyncClient", return_value=client):
        result = await service.generate(prompt="tara portrait", model="image-01")
    assert result["image_data_url"] == "https://cdn.example.com/img.png"
    assert result["provider_used"] == "minimax"


# ── Env factory ─────────────────────────────────────────────────────────


def test_create_service_from_env_reads_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-from-env")
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-mm-from-env")
    service = create_service_from_env()
    assert service._config["openrouter_api_key"] == "sk-or-from-env"
    assert service._config["minimax_api_key"] == "sk-mm-from-env"


def test_create_service_from_env_overrides_take_precedence(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-from-env")
    service = create_service_from_env({"openrouter_api_key": "sk-or-override"})
    assert service._config["openrouter_api_key"] == "sk-or-override"


# ── Extractability proof ────────────────────────────────────────────────


def test_service_module_has_no_project_imports():
    """Importing the service must not pull in any Vajra.Stream package.

    Uses ``ast.parse`` to walk every ``Import`` / ``ImportFrom`` node,
    catching all forms: ``import backend``, ``from backend import x``,
    relative imports, and ``__import__`` / ``importlib.import_module`` calls
    that reference project packages.
    """
    import ast
    import importlib

    mod = importlib.import_module("backend.core.services.image_generation_service")
    src_path = mod.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        source = f.read()

    FORBIDDEN_ROOTS = {"backend", "core", "container", "config", "modules", "infrastructure"}
    tree = ast.parse(source, filename=src_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in FORBIDDEN_ROOTS, (
                    f"image_generation_service.py line {node.lineno}: import {alias.name} breaks standalone extraction."
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                assert root not in FORBIDDEN_ROOTS, (
                    f"image_generation_service.py line {node.lineno}: "
                    f"from {node.module} import ... breaks standalone extraction."
                )
            elif node.level and node.level > 0:
                raise AssertionError(
                    f"image_generation_service.py line {node.lineno}: "
                    f"relative import (level={node.level}) breaks standalone extraction."
                )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            if node.args and isinstance(node.args[0], ast.Constant):
                root = str(node.args[0].value).split(".")[0]
                assert root not in FORBIDDEN_ROOTS, (
                    f"image_generation_service.py line {node.lineno}: "
                    f"__import__({node.args[0].value!r}) breaks standalone extraction."
                )
