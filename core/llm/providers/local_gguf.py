# core/llm/providers/local_gguf.py
"""Local GGUF model provider using llama-cpp-python.

``llama-cpp-python`` is an optional, heavy native dependency that is NOT
installed by default. To keep this module importable without it, the
``llama_cpp`` import is deferred until ``_load_model()`` is first called.
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

from core.llm.models import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    HealthStatus,
    ModelInfo,
)

logger = logging.getLogger(__name__)


class LocalGGUFProvider:
    """Provider for locally-hosted GGUF models via llama-cpp-python.

    Scans ``models_dir`` for ``*.gguf`` files, preferring filenames that
    contain "instruct" or "chat" (which indicates a chat-tuned model).
    Generation runs in a thread executor to avoid blocking the event loop.
    """

    def __init__(
        self,
        models_dir: str = "./models",
        default_model: str | None = None,
        priority: int = 30,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
    ) -> None:
        self.name = "local"
        self.priority = priority
        self.models_dir = models_dir
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self._loaded_model = None
        self._loaded_path: str | None = None
        # Discover available models at construction time (cheap filesystem op).
        self.default_model = default_model or self._scan_for_default_model()

    def _scan_for_default_model(self) -> str:
        """Return the best GGUF filename in models_dir, or 'unknown'."""
        models = self._list_gguf_files()
        if not models:
            return "unknown"
        # Prefer chat/instruct-tuned models.
        preferred = [
            m for m in models if "instruct" in m.lower() or "chat" in m.lower()
        ]
        chosen = preferred[0] if preferred else models[0]
        return os.path.basename(chosen)

    def _list_gguf_files(self) -> list[str]:
        """Return full paths of *.gguf files in models_dir, sorted."""
        d = Path(self.models_dir)
        if not d.is_dir():
            return []
        return sorted(str(p) for p in d.glob("*.gguf"))

    def _resolve_model_path(self) -> str | None:
        """Resolve the path of the model to load (default_model if present)."""
        models = self._list_gguf_files()
        if not models:
            return None
        for m in models:
            if os.path.basename(m) == self.default_model:
                return m
        return models[0]

    def _build_prompt(self, request: ChatRequest) -> str:
        """Build an Alpaca-format prompt from the chat request."""
        system = request.system_prompt or ""
        parts: list[str] = []
        for m in request.messages:
            tag = "User"
            if m.role == "system":
                continue
            if m.role == "assistant":
                tag = "Assistant"
            parts.append(f"### {tag}:\n{m.content}")
        body = "\n\n".join(parts)
        prompt = f"### System:\n{system}\n\n{body}\n\n### Assistant:\n"
        return prompt

    def _load_model_sync(self, model_path: str):  # type: ignore[no-untyped-def]
        """Synchronously load the llama-cpp model (runs in executor).

        The ``llama_cpp`` import is intentionally deferred to here so the
        module can be imported without the optional dependency installed.
        """
        # --- lazy import: only required when actually loading a model ---
        from llama_cpp import Llama

        logger.info(f"Loading local GGUF model: {model_path}")
        return Llama(
            model_path=model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
        )

    async def _ensure_model(self) -> None:
        """Load (or reload) the model in an executor if needed."""
        model_path = self._resolve_model_path()
        if model_path is None:
            raise RuntimeError(
                f"No GGUF models found in {self.models_dir}"
            )
        if self._loaded_model is not None and self._loaded_path == model_path:
            return
        loop = asyncio.get_running_loop()
        self._loaded_model = await loop.run_in_executor(
            None, self._load_model_sync, model_path
        )
        self._loaded_path = model_path

    def _call_model_sync(self, prompt: str, max_tokens: int) -> str:
        """Synchronous generation call (runs in executor)."""
        assert self._loaded_model is not None
        result = self._loaded_model(
            prompt,
            max_tokens=max_tokens,
            stop=["### System:", "### User:"],
            echo=False,
        )
        # llama-cpp returns an OpenAI-like dict with "choices".
        choices = result.get("choices", []) if isinstance(result, dict) else []
        if choices:
            return choices[0].get("text", "")
        return ""

    async def health_check(self) -> HealthStatus:
        models = self._list_gguf_files()
        healthy = len(models) > 0
        return HealthStatus(
            provider=self.name,
            healthy=healthy,
            models_available=len(models),
            error=None if healthy else f"No GGUF models in {self.models_dir}",
        )

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=os.path.basename(m),
                provider=self.name,
                supports_streaming=False,
            )
            for m in self._list_gguf_files()
        ]

    async def generate(self, request: ChatRequest) -> ChatResponse:
        model_name = request.model or self.default_model
        await self._ensure_model()
        prompt = self._build_prompt(request)
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(
            None, self._call_model_sync, prompt, request.max_tokens
        )
        return ChatResponse(
            content=content,
            provider=self.name,
            model=model_name,
            finish_reason="stop",
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        # llama-cpp-python does not stream usefully; fall back to a single
        # chunk from the non-streaming generate path.
        response = await self.generate(request)
        yield ChatChunk(
            content=response.content,
            done=False,
            provider=self.name,
            model=response.model,
        )
        yield ChatChunk(content="", done=True, provider=self.name, model=response.model)

    async def close(self) -> None:
        # llama-cpp models hold native resources; drop our reference so GC
        # can reclaim them. There is no explicit close() on the Llama object.
        self._loaded_model = None
        self._loaded_path = None
