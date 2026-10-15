"""Local render engine: render jobs are operations (``kind="render"``) run one at a time.

Contract: docs/specs/2026-10-14-operations-and-local-render.md ("Render contract").

* :mod:`.base` — presets, :class:`RenderSpec`, the :class:`RenderBackend` protocol, PNG checks
* :mod:`.comfyui` — ComfyUI + Qwen-Image 2.1 Turbo adapter (graph ported from the DataForge garden)
* :mod:`.jobs` — request validation, submit / cancel, artifact paths, backend registry
* :mod:`.worker` — the single asyncio worker started from ``backend/app/main.py``
"""

from backend.core.services.render.base import PRESETS, Preset, RenderBackend, RenderError, RenderSpec
from backend.core.services.render.comfyui import ComfyUIQwenImage21Adapter, build_graph
from backend.core.services.render.jobs import RenderJobRequest, cancel_job, get_backend, submit_job
from backend.core.services.render.worker import RenderWorker, get_render_worker

__all__ = [
    "PRESETS",
    "ComfyUIQwenImage21Adapter",
    "Preset",
    "RenderBackend",
    "RenderError",
    "RenderJobRequest",
    "RenderSpec",
    "RenderWorker",
    "build_graph",
    "cancel_job",
    "get_backend",
    "get_render_worker",
    "submit_job",
]
