"""Render engine primitives: presets, the job spec, the backend protocol, PNG checks.

A *render backend* is anything that can turn a :class:`RenderSpec` into PNG
bytes. ComfyUI running Qwen-Image 2.1 is the first one
(:mod:`backend.core.services.render.comfyui`); the protocol keeps it
replaceable. Backends never touch the operations ledger — the worker does.
"""

from __future__ import annotations

import struct
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Seeds travel as JSON numbers; above 2**53 - 1 JavaScript silently rounds them,
# so a displayed or re-submitted seed would no longer reproduce the image.
SEED_BITS = 53
MAX_SEED = 2**SEED_BITS - 1
MIN_SIDE = 256
MAX_SIDE = 2560
SIDE_MULTIPLE = 32


class RenderError(RuntimeError):
    """A render failed. The message is shown to the user, so it carries the backend's own words."""


class RenderTimeout(RenderError):
    """The backend did not finish within the configured timeout."""


@dataclass(frozen=True)
class Preset:
    """``width``/``height`` are what the model generates; ``export_*`` is the delivered PNG."""

    id: str
    width: int
    height: int
    export_width: int
    export_height: int
    label: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "export_width": self.export_width,
            "export_height": self.export_height,
            "label": self.label,
        }


# Wallpaper presets proven in the DataForge garden (athena-generator/src/local_render.py).
# s25 generates at a latent-aligned 6:13 size, then Lanczos-scales to the phone's 1080x2340.
PRESETS: dict[str, Preset] = {
    p.id: p
    for p in (
        Preset("square-1024", 1024, 1024, 1024, 1024, "Square 1024 x 1024"),
        Preset("desktop-19-10", 2432, 1280, 2432, 1280, "Desktop 19:10 (2432 x 1280)"),
        Preset("desktop-19-9", 2432, 1152, 2432, 1152, "Desktop 19:9 (2432 x 1152)"),
        Preset("s25", 1152, 2496, 1080, 2340, "Phone S25 (1080 x 2340)"),
    )
}


@dataclass(frozen=True)
class RenderSpec:
    """Everything a backend needs to render one image."""

    job_id: str
    prompt: str
    seed: int
    width: int
    height: int
    export_width: int
    export_height: int

    @classmethod
    def from_params(cls, job_id: str, params: dict[str, Any]) -> RenderSpec:
        """Rebuild the spec from an operation's normalized ``params`` (see ``jobs.normalize_request``)."""
        return cls(
            job_id=job_id,
            prompt=params["prompt"],
            seed=int(params["seed"]),
            width=int(params["generate_width"]),
            height=int(params["generate_height"]),
            export_width=int(params["width"]),
            export_height=int(params["height"]),
        )


@dataclass
class BackendJob:
    """What a backend reports once a job has finished on its side."""

    prompt_id: str
    image: bytes
    history: dict[str, Any]


QueueCallback = Callable[[int | None], Awaitable[None]]
StillWanted = Callable[[], bool]


@runtime_checkable
class RenderBackend(Protocol):
    """A render engine behind the job queue. Every network failure is raised as :class:`RenderError`."""

    name: str
    base_url: str

    def build_graph(self, spec: RenderSpec) -> dict[str, Any]:
        """The exact request the backend will execute (stored in the sidecar)."""
        ...

    async def submit(self, spec: RenderSpec) -> str:
        """Queue the job; return the backend's id for it."""
        ...

    async def locate(self, prompt_id: str) -> str:
        """``"done"`` (finished, history available), ``"pending"`` (queued/running) or ``"unknown"``."""
        ...

    async def wait(
        self,
        prompt_id: str,
        *,
        timeout: float,
        on_queue_position: QueueCallback | None = None,
        still_wanted: StillWanted | None = None,
    ) -> BackendJob | None:
        """Block until the job finishes and return its image, or ``None`` if ``still_wanted()`` turned false."""
        ...

    async def cancel(self, prompt_id: str) -> str:
        """Stop the job whether it is pending or executing; return what was done.

        Must not touch other clients' jobs (the GPU may be shared with other tools).
        """
        ...

    async def health(self) -> dict[str, Any]:
        """``{"backend", "reachable", "base_url", "detail", "queue_remaining"}``; never raises."""
        ...


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Validate the PNG signature and IHDR chunk; return ``(width, height)`` as stored in the file."""
    if len(data) < 24 or data[:8] != PNG_MAGIC:
        raise RenderError(f"backend returned an invalid PNG ({len(data)} bytes, bad signature)")
    if data[12:16] != b"IHDR":
        raise RenderError("backend returned an invalid PNG (first chunk is not IHDR)")
    width, height = struct.unpack(">II", data[16:24])
    if width == 0 or height == 0:
        raise RenderError(f"backend returned an invalid PNG ({width}x{height})")
    return width, height
