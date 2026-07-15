# core/llm/legacy_adapter.py
"""Sync compatibility adapter over the async :class:`ProviderRegistry`.

This module provides a drop-in replacement for the deprecated
:class:`~core.llm_integration.LLMIntegration` and
:class:`~core.llm_integration.DharmaLLM` classes. It exposes the *exact
same synchronous API* (``generate()``, ``list_available_models()``,
``get_usage_summary()``, ``get_active_provider()``, the five DharmaLLM
methods) but routes every call through the new async provider layer
(:mod:`core.llm.registry`, :mod:`core.llm.providers`).

The sync→async bridge uses a **persistent daemon-thread event loop**
rather than ``asyncio.run()`` per call. This is critical for two reasons:

1. ``asyncio.run()`` creates and tears down a fresh event loop each call,
   which means the ``AsyncOpenAI`` / ``AsyncAnthropic`` clients (and their
   underlying ``httpx`` connection pools) would be recreated every time —
   expensive and leak-prone.
2. ``asyncio.run()`` raises ``RuntimeError: This event loop is already
   running`` when invoked from inside an already-running loop (e.g. a
   FastAPI request handler that calls legacy sync code). The background
   loop sidesteps this entirely.

KNOWN LIMITATIONS
-----------------
- ``.client``: The new providers use ``AsyncOpenAI`` / ``AsyncAnthropic``.
  For backward compatibility with code that reaches through to
  ``.client.chat.completions.create()`` (e.g.
  ``modules/radionics_operator.py`` lines 1506-1543) or
  ``.client.messages.create()``, this adapter lazily reconstructs a
  **synchronous** client from the first healthy provider's credentials.
  Only ONE of the two reach-through patterns will work depending on
  whether the active provider is OpenAI-compatible or Anthropic. New code
  should use the registry directly.
- ``.local_model``: Always ``None``. Local GGUF generation is delegated
  to :class:`~core.llm.providers.local_gguf.LocalGGUFProvider`.
- ``prefix routing``: ``model="provider:model_name"`` is supported
  (e.g. ``"deepseek:deepseek-chat"``, ``"anthropic:claude-3-5-sonnet"``,
  ``"local:my-model.gguf"``). Name-based auto-detection (no prefix) is
  also supported. Unrecognised prefixes fall back to the registry's
  best provider.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any

from core.llm.base import strip_thinking
from core.llm.models import ChatMessage, ChatRequest, ChatResponse
from core.llm.registry import ProviderRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Usage tracking (optional — import lazily so the adapter works without it)
# ---------------------------------------------------------------------------
try:
    from core.llm.usage import LLMUsageTracker, UsageRecord

    _HAS_USAGE_TRACKER = True
except ImportError:  # pragma: no cover - usage tracker is part of the repo
    _HAS_USAGE_TRACKER = False
    LLMUsageTracker = None  # type: ignore[assignment]
    UsageRecord = None  # type: ignore[assignment]


# ===========================================================================
# Persistent background event loop (sync→async bridge)
# ===========================================================================

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_lock = threading.Lock()


def _get_bg_loop() -> asyncio.AbstractEventLoop:
    """Return the process-wide persistent background event loop.

    Lazily starts a daemon thread running ``loop.run_forever()`` on first
    call. The loop (and any ``AsyncOpenAI`` / ``AsyncAnthropic`` clients
    created inside it) persists for the process lifetime, so clients are
    reused across calls instead of being recreated per ``generate()``.

    Thread-safe via a module-level lock.
    """
    global _bg_loop, _bg_thread
    # Fast path: already initialised and alive.
    if _bg_loop is not None and not _bg_loop.is_closed():
        return _bg_loop
    with _bg_lock:
        # Double-checked locking.
        if _bg_loop is not None and not _bg_loop.is_closed():
            return _bg_loop
        loop = asyncio.new_event_loop()

        def _runner() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        t = threading.Thread(
            target=_runner, name="llm-legacy-adapter-bg-loop", daemon=True
        )
        t.start()
        _bg_loop = loop
        _bg_thread = t
        logger.debug("Started persistent background event loop: %r", loop)
    return _bg_loop


def _in_running_loop() -> bool:
    """Return True if the calling thread currently has a running event loop.

    Uses ``asyncio.get_running_loop()`` (the non-deprecated form in
    Python 3.12+) wrapped in try/except. We never call
    ``asyncio.get_event_loop()`` because it is deprecated and emits a
    DeprecationWarning when there is no current loop.
    """
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def run_async(coro: Any) -> Any:
    """Run a coroutine from synchronous code and return its result.

    Always offloads to the persistent background loop (see
    :func:`_get_bg_loop`) so that async clients are reused. This is safe
    to call from:

    - Plain synchronous code (no running loop).
    - Inside a running event loop (FastAPI request handlers, async tests).
      ``asyncio.run_coroutine_threadsafe`` submits the coroutine to a
      *different* thread's loop, avoiding the "event loop already running"
      deadlock that ``asyncio.run`` would hit.

    Args:
        coro: A coroutine (or awaitable) to execute.

    Returns:
        The coroutine's return value.

    Raises:
        Whatever the coroutine raises (re-raised on the calling thread).
    """
    loop = _get_bg_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()  # blocks until the coroutine completes; re-raises


# ===========================================================================
# Provider-name → legacy model_type mapping
# ===========================================================================

_PROVIDER_TO_MODEL_TYPE: dict[str, str] = {
    "openrouter": "openrouter",
    "lm_studio": "lm_studio",
    "deepseek": "deepseek",
    "z_ai": "z_ai",
    "anthropic": "anthropic",
    "openai": "openai",
    "minimax": "minimax",
    "local": "local",
}


def _parse_model_spec(model: str | None) -> tuple[str | None, str | None]:
    """Parse a legacy model spec into ``(provider_name, model_name)``.

    Supports the same prefix routing as the old ``LLMIntegration.generate``:

    - ``"deepseek:deepseek-chat"`` → ``("deepseek", "deepseek-v4-flash")``
    - ``"anthropic:claude-3-5-sonnet"`` → ``("anthropic", "claude-3-5-sonnet")``
    - ``"lm-studio:foo"`` → ``("lm_studio", "foo")`` (hyphen normalised)
    - ``"gpt-4o-mini"`` → name-based detection returns ``(None, "gpt-4o-mini")``
      and the caller decides the provider.

    Returns:
        ``(provider_name, model_name)``. Either element may be ``None``:
        ``provider_name`` is ``None`` when no prefix was supplied;
        ``model_name`` is the trailing value (or the whole string when
        no prefix is present).
    """
    if not model:
        return None, None
    model_str = model.strip()
    if model_str.lower() == "auto":
        return None, None
    if ":" in model_str:
        prefix, _, rest = model_str.partition(":")
        pref = prefix.strip().lower().replace("-", "_")
        # Only treat as a provider prefix if we recognise it; otherwise
        # the colon may be part of a model id (rare, but safe).
        if pref in _PROVIDER_TO_MODEL_TYPE.values() or pref in {
            "openrouter",
            "lm_studio",
            "deepseek",
            "z_ai",
            "zai",
            "anthropic",
            "openai",
            "minimax",
            "local",
        }:
            # Normalise zai → z_ai
            if pref == "zai":
                pref = "z_ai"
            return pref, rest.strip() or None
    return None, model_str


def _detect_provider_from_name(model_name: str) -> str | None:
    """Guess a provider key from a bare model name (no prefix).

    Mirrors the legacy name-based detection in
    :meth:`LLMIntegration.generate`: GGUF → local, "deepseek" → deepseek,
    "claude"/"haiku"/"sonnet" → anthropic, "glm" → z_ai, "gpt-" → openai.
    Returns ``None`` if no heuristic matches.
    """
    if not model_name:
        return None
    lower = model_name.lower()
    if lower.endswith(".gguf") or "gguf" in lower:
        return "local"
    if "deepseek" in lower:
        return "deepseek"
    if "glm-" in lower or "glm" in lower:
        return "z_ai"
    if "claude" in lower or "haiku" in lower or "sonnet" in lower:
        return "anthropic"
    if "gpt-" in lower:
        return "openai"
    return None


# ===========================================================================
# LegacyLLMIntegration
# ===========================================================================


class LegacyLLMIntegration:
    """Synchronous adapter that mimics :class:`LLMIntegration` over a registry.

    Construct with no arguments to auto-build a registry from environment
    variables (via :func:`~core.llm.bootstrap.build_default_registry`),
    or pass an existing ``ProviderRegistry`` (e.g. ``app.state.llm_registry``)
    to share providers with the FastAPI app.

    Example::

        from core.llm.legacy_adapter import LegacyLLMIntegration

        llm = LegacyLLMIntegration()
        print(llm.generate("Reply with PONG", max_tokens=50))
    """

    def __init__(
        self,
        model_type: str = "auto",
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        local_models_dir: str = "./models",
        registry: ProviderRegistry | None = None,
    ) -> None:
        """Initialize the legacy adapter.

        Args:
            model_type: Accepted for API compatibility. ``"auto"`` (default)
                uses the registry's priority-ordered providers. Any other
                value is recorded on ``self.model_type`` but does not change
                routing (the registry already encodes priorities).
            model_name: Optional default model override.
            api_key: Accepted for compatibility; ignored (credentials live
                on the providers).
            base_url: Accepted for compatibility; ignored.
            local_models_dir: Directory to scan for GGUF models in
                :meth:`list_available_models`.
            registry: An existing :class:`ProviderRegistry`. If ``None``,
                one is built from env vars via
                :func:`~core.llm.bootstrap.build_default_registry`.
        """
        # Public attributes (for backward-compat reach-through).
        # NOTE: ``client`` is exposed as a *property* below (lazily-built sync
        # client); do NOT set ``self.client`` here.
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.local_models_dir = local_models_dir
        self.provider_key = "unknown"
        self.local_model: Any = None  # always None (delegated to provider)

        # Usage tracker singleton.
        self._tracker = LLMUsageTracker.get() if _HAS_USAGE_TRACKER else None

        # Registry: use the provided one, or build from env.
        if registry is not None:
            self._registry: ProviderRegistry = registry
            self._owns_registry = False
        else:
            # Imported here to avoid a circular import at module load
            # (bootstrap imports providers, which import base/models).
            from core.llm.bootstrap import build_default_registry

            self._registry = build_default_registry()
            self._owns_registry = True

        # Resolve a "primary" provider for attribute setup (no health check;
        # the actual generate() path uses pick_best() which does health-check).
        self._primary_provider = self._pick_primary_provider()
        self._sync_client_cache: Any = None
        self._apply_primary_attributes(self._primary_provider)

    # ------------------------------------------------------------------
    # Internal: provider resolution & attribute setup
    # ------------------------------------------------------------------

    def _pick_primary_provider(self) -> Any:
        """Return the highest-priority registered provider (no health check).

        Used to set ``model_type`` / ``model_name`` / ``base_url`` for
        backward-compat attribute access. Returns ``None`` if the registry
        is empty.
        """
        providers = self._registry.providers  # sorted by priority desc
        return providers[0] if providers else None

    def _apply_primary_attributes(
        self, provider: Any, force: bool = False
    ) -> None:
        """Populate ``model_type``/``model_name``/``provider_key`` from a provider.

        Args:
            provider: The provider to source attributes from.
            force: When ``True`` (used after :meth:`generate`), always
                overwrite ``model_name`` with the provider's default — so
                ``current_model`` reflects the provider actually used rather
                than a stale initial value. When ``False`` (used during
                ``__init__``), a user-supplied ``model_name`` is preserved.
        """
        if provider is None:
            return
        name = getattr(provider, "name", None)
        self.provider_key = name or "unknown"
        self.model_type = _PROVIDER_TO_MODEL_TYPE.get(name or "", name or "auto")
        default_model = getattr(provider, "default_model", None)
        if force or not self.model_name:
            self.model_name = default_model
        if not self.base_url:
            client = getattr(provider, "_client", None)
            if client is not None and hasattr(client, "base_url"):
                self.base_url = str(client.base_url)

    def _find_provider(self, name: str) -> Any:
        """Find a registered provider by name (case-insensitive).

        Returns the provider instance or ``None``.
        """
        target = name.lower().replace("-", "_")
        for p in self._registry.providers:
            if getattr(p, "name", "").lower().replace("-", "_") == target:
                return p
        return None

    def _build_sync_client(self, provider: Any) -> Any:
        """Reconstruct a SYNC client from a provider's async credentials.

        Supports OpenAI-compatible providers (returns ``openai.OpenAI``)
        and Anthropic / Z.AI providers (returns ``anthropic.Anthropic``).
        Returns ``None`` if the provider is unknown or the SDK is missing.

        This is a **known limitation**: only the reach-through pattern
        matching the active provider's family (``.chat.completions.create``
        for OpenAI-compatible, ``.messages.create`` for Anthropic) will
        work. New code should use the registry directly.
        """
        if provider is None:
            return None
        async_client = getattr(provider, "_client", None)
        if async_client is None:
            return None

        # OpenAI-compatible (AsyncOpenAI)
        try:
            from openai import AsyncOpenAI

            if isinstance(async_client, AsyncOpenAI):
                from openai import OpenAI

                return OpenAI(
                    api_key=async_client.api_key,
                    base_url=str(async_client.base_url),
                )
        except ImportError:
            logger.debug("openai SDK not available for sync client reconstruction")

        # Anthropic / Z.AI (AsyncAnthropic)
        try:
            from anthropic import AsyncAnthropic

            if isinstance(async_client, AsyncAnthropic):
                from anthropic import Anthropic

                return Anthropic(
                    api_key=async_client.api_key,
                    base_url=str(async_client.base_url),
                )
        except ImportError:
            logger.debug("anthropic SDK not available for sync client reconstruction")

        return None

    # ------------------------------------------------------------------
    # Public API (matches core.llm_integration.LLMIntegration)
    # ------------------------------------------------------------------

    @property
    def registry(self) -> ProviderRegistry:
        """The underlying :class:`ProviderRegistry` (for advanced callers)."""
        return self._registry

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str:
        """Generate text from a prompt (synchronous).

        Drop-in replacement for :meth:`LLMIntegration.generate`. Supports
        ``model="provider:name"`` prefix routing and bare-name
        auto-detection, exactly like the legacy implementation.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instructions.
            max_tokens: Maximum response length.
            temperature: Sampling temperature (0.0–2.0).
            model: Optional model spec. May be ``"provider:model_name"``
                (e.g. ``"deepseek:deepseek-chat"``) or a bare model name
                (auto-detected). ``None`` or ``"auto"`` uses the registry's
                best provider.

        Returns:
            The generated text. On failure, returns a human-readable error
            string (matching the legacy contract — does not raise).
        """
        try:
            return run_async(
                self._generate_async(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model,
                )
            )
        except Exception as e:
            # Last-resort guard so legacy callers that don't catch exceptions
            # still get a usable string. (The inner method already converts
            # most errors to strings; this catches unexpected bridge errors.)
            logger.exception("LegacyLLMIntegration.generate failed: %s", e)
            return f"LLM generation failed: {e}"

    async def _generate_async(
        self,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
        model: str | None,
    ) -> str:
        """Async implementation of :meth:`generate`."""
        provider: Any = None
        target_model: str | None = None

        provider_hint, model_part = _parse_model_spec(model)

        if provider_hint is not None:
            # Explicit prefix: locate that provider in the registry.
            provider = self._find_provider(provider_hint)
            if provider is None:
                return (
                    f"Provider '{provider_hint}' is not registered. "
                    f"Available: {[p.name for p in self._registry.providers]}"
                )
            target_model = model_part  # may be None → provider default

        if provider is None and model_part is not None:
            # No prefix but a name was given → name-based detection.
            detected = _detect_provider_from_name(model_part)
            if detected is not None:
                provider = self._find_provider(detected)
                target_model = model_part
            # else fall through to pick_best()

        if provider is None:
            # No hint and no name match → let the registry pick the best
            # healthy provider.
            provider = await self._registry.pick_best()
            if provider is None:
                return (
                    "No healthy LLM provider available. Configure an API key "
                    "(OPENROUTER_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY, "
                    "ANTHROPIC_API_KEY) or add a local model."
                )
            # If a bare name was supplied, honour it; else provider default.
            target_model = model_part

        # Build the ChatRequest and call the provider.
        request = ChatRequest(
            messages=[ChatMessage(role="user", content=prompt)],
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            model=target_model,
        )

        start = time.time()
        success = True
        try:
            response: ChatResponse = await provider.generate(request)
        except Exception as e:
            success = False
            logger.warning(
                "generate via %s failed: %s", getattr(provider, "name", "?"), e
            )
            return f"{getattr(provider, 'name', 'unknown')} generation failed: {e}"

        latency_ms = (time.time() - start) * 1000.0

        # Refresh primary attributes so .client / .model_type track the
        # provider actually used. ``force=True`` updates model_name to the
        # used provider's default so current_model is accurate.
        self._primary_provider = provider
        self._sync_client_cache = None  # invalidate; rebuilt on next access
        self._apply_primary_attributes(provider, force=True)

        # Record usage (best-effort; never blocks generation).
        self._record_usage(provider, response, latency_ms, success)

        clean_content, _ = strip_thinking(response.content)
        return clean_content

    def _record_usage(
        self,
        provider: Any,
        response: ChatResponse,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record a usage entry in the shared :class:`LLMUsageTracker`."""
        if not (_HAS_USAGE_TRACKER and self._tracker):
            return
        try:
            provider_name = getattr(provider, "name", "unknown")
            prompt_tokens = getattr(response, "input_tokens", 0) or 0
            completion_tokens = getattr(response, "output_tokens", 0) or 0
            cost = self._tracker.estimate_cost(
                provider_name, response.model, prompt_tokens, completion_tokens
            )
            self._tracker.record(
                UsageRecord(
                    provider=provider_name,
                    model=response.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    endpoint="chat",
                    success=success,
                )
            )
        except Exception:
            logger.debug("usage recording failed (ignored)", exc_info=True)

    def list_available_models(self) -> dict[str, list[str]]:
        """List all available models across registered providers.

        Returns a dict with the same shape as the legacy
        :meth:`LLMIntegration.list_available_models`:

        - ``"local"``: list of local GGUF model basenames.
        - ``"api"``: list of ``"ProviderName (default_model)"`` labels.
        - ``"current_provider"``: single-element list with the active provider key.
        - ``"current_model"``: single-element list with the active model name.
        """
        available: dict[str, list[str]] = {"local": [], "api": []}

        for p in self._registry.providers:
            name = getattr(p, "name", "unknown")
            if name == "local":
                # Enumerate GGUF files via the provider's scanner.
                files = p._list_gguf_files() if hasattr(p, "_list_gguf_files") else []
                available["local"].extend(os.path.basename(f) for f in files)
            else:
                default_model = getattr(p, "default_model", "unknown")
                available["api"].append(f"{name} ({default_model})")

        available["current_provider"] = [self.provider_key]
        available["current_model"] = [self.model_name or "unknown"]
        return available

    def get_usage_summary(self) -> dict:
        """Return the usage tracker summary, or ``{}`` if tracking is off."""
        if self._tracker:
            return self._tracker.get_summary()
        return {}

    def get_active_provider(self) -> dict:
        """Return info about the currently active provider.

        Returns a dict with ``provider``, ``model``, ``base_url``, and
        ``model_type`` keys — matching the legacy shape.
        """
        return {
            "provider": self.provider_key,
            "model": self.model_name,
            "base_url": getattr(self, "base_url", None),
            "model_type": self.model_type,
        }

    # ------------------------------------------------------------------
    # Lazy sync client (backward-compat reach-through)
    # ------------------------------------------------------------------

    @property
    def client(self) -> Any:
        """Lazily-built synchronous client for backward-compat reach-through.

        The new provider layer uses ``AsyncOpenAI`` / ``AsyncAnthropic``.
        This property reconstructs a **synchronous** client from the
        primary provider's credentials so that legacy code reaching
        through to ``.client.chat.completions.create()`` (OpenAI family)
        or ``.client.messages.create()`` (Anthropic family) continues to
        work.

        **Known limitation**: only the reach-through pattern matching the
        active provider's family will work. New code should use the
        registry directly. Returns ``None`` if the primary provider is
        unknown or the relevant SDK is not installed.
        """
        return self._get_sync_client()

    def _get_sync_client(self) -> Any:
        """Build and cache the sync client for the primary provider."""
        if self._sync_client_cache is not None:
            return self._sync_client_cache
        client = self._build_sync_client(self._primary_provider)
        self._sync_client_cache = client
        return client


# ===========================================================================
# LegacyDharmaLLM
# ===========================================================================

# Imported here (not at module top) to avoid an import cycle:
# dharma.py imports only registry/models, but keeping it lazy is safer.
def _load_async_dharma():
    from core.llm.dharma import DHARMA_SYSTEM_PROMPT, AsyncDharmaLLM

    return AsyncDharmaLLM, DHARMA_SYSTEM_PROMPT


class LegacyDharmaLLM:
    """Synchronous adapter that mimics :class:`DharmaLLM` over a registry.

    Construct with a :class:`LegacyLLMIntegration` (mirroring the legacy
    ``DharmaLLM(llm)`` signature) or directly with a
    :class:`ProviderRegistry`. Internally delegates to
    :class:`~core.llm.dharma.AsyncDharmaLLM` via :func:`run_async`, so the
    prompt templates are shared with the native async implementation (no
    duplication).

    Example::

        from core.llm.legacy_adapter import LegacyLLMIntegration, LegacyDharmaLLM

        llm = LegacyLLMIntegration()
        dharma = LegacyDharmaLLM(llm)
        print(dharma.generate_prayer("peace and healing for all beings"))
    """

    def __init__(self, llm: LegacyLLMIntegration | ProviderRegistry) -> None:
        """Initialize the dharma adapter.

        Args:
            llm: Either a :class:`LegacyLLMIntegration` (its ``.registry``
                is used) or a bare :class:`ProviderRegistry`.
        """
        AsyncDharmaLLM, DHARMA_SYSTEM_PROMPT = _load_async_dharma()

        # Mirror the legacy attribute name (.llm) for backward compat.
        self.llm = llm

        # Extract a registry from whichever form we were given.
        if isinstance(llm, ProviderRegistry):
            registry = llm
        elif hasattr(llm, "registry") and isinstance(llm.registry, ProviderRegistry):
            registry = llm.registry
        else:
            raise TypeError(
                "LegacyDharmaLLM requires a LegacyLLMIntegration or "
                f"ProviderRegistry, got {type(llm).__name__}"
            )

        self._async_dharma = AsyncDharmaLLM(registry)
        self.dharma_system = DHARMA_SYSTEM_PROMPT

    def generate_prayer(self, intention: str, tradition: str = "universal") -> str:
        """Generate a prayer / aspiration (synchronous)."""
        return run_async(self._async_dharma.generate_prayer(intention, tradition))

    def generate_teaching(self, topic: str, length: str = "short") -> str:
        """Generate a dharma teaching (synchronous)."""
        return run_async(self._async_dharma.generate_teaching(topic, length))

    def generate_meditation_instruction(self, practice: str) -> str:
        """Generate meditation instructions (synchronous)."""
        return run_async(self._async_dharma.generate_meditation_instruction(practice))

    def generate_dedication(self) -> str:
        """Generate a dedication of merit (synchronous)."""
        return run_async(self._async_dharma.generate_dedication())

    def generate_contemplation(self, theme: str) -> str:
        """Generate a contemplation exercise (synchronous)."""
        return run_async(self._async_dharma.generate_contemplation(theme))


__all__ = [
    "LegacyLLMIntegration",
    "LegacyDharmaLLM",
    "run_async",
]
