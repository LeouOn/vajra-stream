"""A single working: intention → rates → folio → optional broadcast.

Command Center chat could already write prayers and cast I Ching, but it
could not close a radionics loop. ``run_working`` is the compound tool
that does: Losar-aware Saka Dawa stamp, 5-dial signature, library lookup,
Solfeggio carriers, a spoken charge, and a non-blocking broadcast.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import home_location, iconography, image_prompts, sky
from core.auspicious_timing import check_auspicious_window, check_saka_dawa
from core.context_builder import search_rates
from core.provenance import COMPUTED, DRAW, RECORD, with_provenance
from core.radionics_engine import SignatureCalculator
from core.rate_to_audio import map_rate_to_carriers

logger = logging.getLogger(__name__)

# A sealed folio is a record; the values sealed into it say how they were made.
# The dials are computed from the intention's text (SignatureCalculator "mixed"),
# the carriers from the dials, the calendar blocks from the sealing time, and a
# divination cast attached at sealing is a draw.
FOLIO_PROVENANCE: dict[str, str] = {
    "sealed_at": RECORD,
    "rate_values": COMPUTED,
    "dials": COMPUTED,
    "frequencies": COMPUTED,
    "solfeggio_names": COMPUTED,
    "amplitude": COMPUTED,
    "saka_dawa": COMPUTED,
    "timing": COMPUTED,
    "hour_stamp": COMPUTED,
    "broadcast": RECORD,
    "divination": DRAW,
    "deity": RECORD,
    "location": RECORD,
}

# Dials set by hand (PATCH /workings/{id}) are recorded as entered.
HAND_SET_DIALS_PROVENANCE: dict[str, str] = {"rate_values": RECORD, "dials": RECORD}

# The ledger row ``list_workings`` returns for each folio.
FOLIO_SUMMARY_PROVENANCE: dict[str, str] = {
    "sealed_at": RECORD,
    "rate_values": COMPUTED,
    "frequencies": COMPUTED,
    "solfeggio_names": COMPUTED,
    "saka_dawa_duchen": COMPUTED,
    "saka_dawa_multiplier": COMPUTED,
    "planetary_hour": COMPUTED,
    "moon_phase": COMPUTED,
}


def _label_folio(folio: dict[str, Any]) -> dict[str, Any]:
    """Attach the folio's provenance map (labels already stored on it win)."""
    with_provenance(folio, FOLIO_PROVENANCE)
    return folio


WORKINGS_DIR = Path(__file__).resolve().parent.parent / "generated" / "workings"

# Serializes the witness listener's read-modify-write of a folio (it can fire from
# the render worker while a request handler is also touching the same folio).
_witness_lock = threading.Lock()

_DIAL_NAMES = ("Physical", "Astral", "Mental", "Causal", "Spiritual")

# Same intention+target within this window is one sitting, not a new folio.
SITTING_WINDOW_SECONDS = 60


def _normalize_sitting_key(intention: str, target: str) -> tuple[str, str]:
    return (intention.lower().strip(), target.lower().strip())


def _sealed_at_utc(folio: dict[str, Any]) -> datetime | None:
    raw = folio.get("sealed_at")
    if not raw:
        return None
    try:
        stamped = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamped.tzinfo is None:
        stamped = stamped.replace(tzinfo=timezone.utc)
    return stamped.astimezone(timezone.utc)


def find_recent_working(
    intention: str,
    target: str = "all beings",
    window_seconds: int = SITTING_WINDOW_SECONDS,
) -> dict[str, Any] | None:
    """Return the newest matching folio sealed inside ``window_seconds``, or None."""
    if not WORKINGS_DIR.is_dir():
        return None
    key = _normalize_sitting_key(intention, target)
    now = datetime.now(timezone.utc)
    files = sorted(WORKINGS_DIR.glob("wrk_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or data.get("hidden"):
            continue
        sealed = _sealed_at_utc(data)
        if sealed is None:
            continue
        age = (now - sealed).total_seconds()
        if age > window_seconds:
            # Newest-first: older files cannot match the window.
            break
        stored_key = _normalize_sitting_key(str(data.get("intention") or ""), str(data.get("target") or "all beings"))
        if stored_key == key:
            return data
    return None


def collapse_duplicate_workings() -> dict[str, Any]:
    """Hide redundant folios: same intention + target + rate signature keeps only the newest.

    The pre-idempotency ledger minted one folio per auto-chain retry, so a
    single sitting can appear many times. Duplicates are hidden (not deleted)
    and stamped ``duplicate_of`` so the newest folio remains the one sitting.
    """
    if not WORKINGS_DIR.is_dir():
        return {"status": "success", "unique_sittings": 0, "hidden": [], "kept": []}

    entries: list[tuple[datetime, dict[str, Any]]] = []
    for path in WORKINGS_DIR.glob("wrk_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        sealed = _sealed_at_utc(data) or datetime.min.replace(tzinfo=timezone.utc)
        entries.append((sealed, data))
    # Folio-internal timestamps, not filesystem mtimes: rapid writes can
    # share an mtime and make "newest" nondeterministic.
    entries.sort(key=lambda item: item[0], reverse=True)

    groups: dict[tuple[str, str, tuple[int, ...]], list[dict[str, Any]]] = {}
    order: list[tuple[str, str, tuple[int, ...]]] = []
    for _, data in entries:
        rates = tuple(int(v) for v in (data.get("rate_values") or []) if isinstance(v, int | float))
        key = (
            *_normalize_sitting_key(str(data.get("intention") or ""), str(data.get("target") or "all beings")),
            rates,
        )
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(data)

    kept: list[str] = []
    hidden: list[str] = []
    for key in order:
        folios = groups[key]
        keeper = next((f for f in folios if not f.get("hidden")), folios[0])
        keeper_id = str(keeper.get("working_id") or "")
        if keeper_id:
            kept.append(keeper_id)
        for dup in folios:
            if dup is keeper:
                continue
            if dup.get("hidden") and dup.get("duplicate_of") == keeper_id:
                continue
            dup["hidden"] = True
            dup["duplicate_of"] = keeper_id
            try:
                _persist(dup, index=False)
                hidden.append(str(dup.get("working_id") or ""))
            except OSError:
                continue

    return {"status": "success", "unique_sittings": len(kept), "hidden": hidden, "kept": kept}


def _persist(folio: dict[str, Any], *, index: bool = True) -> None:
    WORKINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = WORKINGS_DIR / f"{folio['working_id']}.json"
    path.write_text(json.dumps(folio, indent=2, default=str), encoding="utf-8")
    if not index:
        return
    idx = WORKINGS_DIR / "index.jsonl"
    with idx.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "working_id": folio["working_id"],
                    "intention": folio["intention"],
                    "at": folio["sealed_at"],
                }
            )
            + "\n"
        )


def load_working(working_id: str) -> dict[str, Any] | None:
    """Load a sealed folio by id, or None if it is not on disk."""
    safe = "".join(ch for ch in working_id if ch.isalnum() or ch == "_")
    path = WORKINGS_DIR / f"{safe}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _label_folio(data) if isinstance(data, dict) else None


def list_workings(limit: int = 20, *, include_hidden: bool = False) -> list[dict[str, Any]]:
    """Newest sealed workings, without image payloads."""
    if not WORKINGS_DIR.is_dir():
        return []
    files = sorted(WORKINGS_DIR.glob("wrk_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for path in files:
        if len(out) >= max(1, min(limit, 50)):
            break
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        hidden = bool(data.get("hidden"))
        if hidden and not include_hidden:
            continue
        witness = data.get("witness") if isinstance(data.get("witness"), dict) else {}
        saka = data.get("saka_dawa") if isinstance(data.get("saka_dawa"), dict) else {}
        # Hosted witnesses carry an inline data URL; local renders an image_url.
        has_image = bool(witness.get("image_data_url") or witness.get("image_url"))
        stored = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
        row_provenance = dict(FOLIO_SUMMARY_PROVENANCE)
        if stored.get("rate_values") in (RECORD, COMPUTED):
            row_provenance["rate_values"] = stored["rate_values"]
        out.append(
            {
                "working_id": data.get("working_id"),
                "intention": data.get("intention"),
                "target": data.get("target"),
                "sealed_at": data.get("sealed_at"),
                "rate_values": data.get("rate_values"),
                "frequencies": data.get("frequencies"),
                "solfeggio_names": data.get("solfeggio_names"),
                "source": data.get("source"),
                "hidden": hidden,
                "has_witness": has_image,
                "has_manifestation": has_image,
                "saka_dawa_duchen": saka.get("saka_dawa_duchen"),
                "planetary_hour": (data.get("hour_stamp") or {}).get("planetary_hour"),
                "moon_phase": (data.get("hour_stamp") or {}).get("moon_phase"),
                "saka_dawa_multiplier": saka.get("multiplier", 1),
                "duplicate_of": data.get("duplicate_of"),
                "provenance": row_provenance,
            }
        )
    return out


def delete_working(working_id: str) -> bool:
    """Remove a folio and its charge audio from disk."""
    folio = load_working(working_id)
    if folio is None:
        return False
    safe = "".join(ch for ch in working_id if ch.isalnum() or ch == "_")
    path = WORKINGS_DIR / f"{safe}.json"
    try:
        path.unlink()
        charge = charge_audio_path(working_id)
        if charge.is_file():
            charge.unlink()
        return True
    except OSError:
        return False


def set_working_hidden(working_id: str, hidden: bool) -> dict[str, Any] | None:
    folio = load_working(working_id)
    if folio is None:
        return None
    folio["hidden"] = bool(hidden)
    try:
        _persist(folio, index=False)
        folio["saved"] = True
    except OSError as exc:
        folio["saved"] = False
        folio["save_error"] = str(exc)[:200]
    return folio


def update_working_rates(working_id: str, rate_values: list[int]) -> dict[str, Any] | None:
    folio = load_working(working_id)
    if folio is None:
        return None
    values = [max(0, min(100, int(v))) for v in (rate_values or [])[:5]]
    if len(values) < 2:
        return folio
    carriers = map_rate_to_carriers(values)
    folio["rate_values"] = values
    folio["provenance"] = {**(folio.get("provenance") or {}), **HAND_SET_DIALS_PROVENANCE}
    folio["dials"] = [
        {"name": _DIAL_NAMES[i] if i < len(_DIAL_NAMES) else f"D{i + 1}", "value": values[i]}
        for i in range(len(values))
    ]
    folio["frequencies"] = list(carriers.frequencies)
    folio["solfeggio_names"] = list(carriers.solfeggio_names)
    folio["amplitude"] = carriers.amplitude
    try:
        _persist(folio, index=False)
        folio["saved"] = True
    except OSError as exc:
        folio["saved"] = False
        folio["save_error"] = str(exc)[:200]
    return folio


def _folio_sky(folio: dict[str, Any]) -> dict[str, Any] | None:
    """The true sky at the folio's ``sealed_at`` and place (core/sky.py), or ``None``.

    ``observer.source`` says whether the folio's own location or the default was
    used. The sky is computed at the exact place; the returned record (stored on
    the witness and shown in captions) carries the place rounded, with its label
    (:func:`core.sky.public_sky`).
    """
    lat, lon, source = sky.observer_for(folio)
    computed = sky.compute_sky(folio.get("sealed_at"), lat, lon)
    if computed is None:
        return None
    return sky.public_sky(computed, source, sky.observer_label(folio) if source == "folio" else None)


def _saka_block(folio: dict[str, Any]) -> dict[str, Any]:
    saka = folio.get("saka_dawa")
    return saka if isinstance(saka, dict) else {}


def witness_prompt(folio: dict[str, Any]) -> str:
    """The folio's witness image prompt, always rebuilt from its facts.

    A stored ``image_prompt`` is not reused: folios sealed before
    :mod:`core.image_prompts` stored prompts with dates and a "full moon"
    taken from a future festival, which models paint as text and false sky.
    """
    computed = _folio_sky(folio)
    return _image_prompt(
        str(folio.get("intention") or ""),
        str(folio.get("target") or "all beings"),
        sky_period=computed["period"] if computed else None,
        saka_dawa=_saka_block(folio),
        deity_clause=_deity_clause(folio),
    )


def _deity_clause(folio: dict[str, Any]) -> str:
    """The curated iconography clause for the folio's deity (core/iconography.py), or ""."""
    ref = iconography.folio_deity(folio)
    return iconography.ref_prompt_clause(ref) if ref is not None else ""


def witness_caption_facts(folio: dict[str, Any]) -> list[dict[str, str]]:
    """The real values a witness image is captioned with (never painted into it)."""
    facts: list[dict[str, str]] = []
    if folio.get("sealed_at"):
        facts.append(image_prompts.caption_fact("Sealed", folio["sealed_at"], "record"))
    computed = _folio_sky(folio)
    hour = folio.get("hour_stamp") if isinstance(folio.get("hour_stamp"), dict) else {}
    if computed is not None:
        facts.extend(sky.sky_caption_facts(computed))
        facts.append(sky.observer_fact(**computed["observer"]))
    else:
        facts.append(sky.unavailable_fact())
        if hour.get("moon_phase"):
            facts.append(image_prompts.caption_fact("Moon phase", hour["moon_phase"], "computed"))
    if hour.get("planetary_hour"):
        facts.append(image_prompts.caption_fact("Planetary hour", hour["planetary_hour"], "computed"))
    saka = _saka_block(folio)
    if saka.get("saka_dawa_duchen"):
        facts.append(image_prompts.caption_fact("Saka Dawa Duchen", saka["saka_dawa_duchen"], "computed"))
    multiplier = int(saka.get("multiplier") or 1)
    if multiplier > 1:
        facts.append(image_prompts.caption_fact("Merit multiplier", f"×{multiplier:,}", "computed"))
    deity = iconography.folio_deity(folio)
    if deity is not None:
        facts.extend(iconography.deity_caption_facts(deity.entry, deity.form))
    return facts


def submit_witness_render(working_id: str) -> dict[str, Any] | None:
    """Queue a local render of the folio's witness (spec Contract W2-2); never blocks.

    Returns ``{"working_id", "operation"}``, or ``None`` if the folio does not exist.
    The folio itself is left untouched until the render finishes: then
    :func:`apply_witness_render` (an operations listener) writes its ``witness``.
    """
    folio = load_working(working_id)
    if folio is None:
        return None
    from backend.core.services.render.jobs import RenderJobRequest, submit_job

    install_witness_listener()
    op = submit_job(
        RenderJobRequest(
            prompt=witness_prompt(folio),
            working_id=working_id,
            purpose="witness",
            caption_facts=witness_caption_facts(folio),
            reference_id=_deity_reference_id(folio),
        )
    )
    return {"working_id": working_id, "operation": op}


def _deity_reference_id(folio: dict[str, Any]) -> str | None:
    """The user's thangka reference image for the folio's deity, if one is set."""
    ref = iconography.folio_deity(folio)
    if ref is None:
        return None
    # Function-level: the render engine lives in backend (core must not import it at module level).
    from backend.core.services.render.deity_references import reference_for

    return reference_for(ref.id)


def witness_block_for(op: dict[str, Any]) -> dict[str, Any] | None:
    """The folio ``witness`` a finished witness render produces, or ``None`` if it produces none."""
    if op.get("kind") != "render":
        return None
    params = op.get("params") or {}
    if params.get("purpose") != "witness":
        return None
    if op.get("status") == "success":
        result = op.get("result") or {}
        return {
            "status": "ok",
            "source": "local-render",
            "operation_id": op["id"],
            "image_url": result.get("image_url"),
            "seed": result.get("seed", params.get("seed")),
            "seed_provenance": (op.get("provenance") or {}).get("seed"),
            "width": result.get("width"),
            "height": result.get("height"),
            "prompt": params.get("prompt"),
            "caption_facts": params.get("caption_facts") or [],
        }
    if op.get("status") == "error":
        return {"status": "error", "operation_id": op["id"], "error": op.get("error") or "render failed"}
    return None  # queued / running / cancelled leave the folio as it is


def _superseded_by(current: Any, op: dict[str, Any]) -> bool:
    """True if the folio already shows the outcome of a *newer* witness render than ``op``."""
    if not isinstance(current, dict):
        return False
    other_id = current.get("operation_id")
    if not other_id or other_id == op["id"]:
        return False
    from core import operations

    other = operations.get_operation(str(other_id))
    return other is not None and str(other.get("created_at")) > str(op.get("created_at"))


def apply_witness_render(op: dict[str, Any]) -> bool:
    """Operations listener: write a finished witness render into its folio. Returns True if written.

    Idempotent (a repeat notification writes nothing), and an older render
    finishing late never replaces a newer one's witness. Only the ``witness``
    and ``manifestation`` keys of a freshly loaded folio are changed.
    """
    block = witness_block_for(op)
    working_id = op.get("working_id") or (op.get("params") or {}).get("working_id")
    if block is None or not working_id:
        return False
    with _witness_lock:
        folio = load_working(str(working_id))
        if folio is None:
            logger.warning("witness render %s finished for missing folio %s", op.get("id"), working_id)
            return False
        current = folio.get("witness")
        if _superseded_by(current, op):
            return False
        if block.get("status") == "ok":
            # Draw the true sky onto the empty-sky scene (deterministic, so a repeat stays a no-op).
            from core.sky_composite import composite_witness

            # A deity's devotional painting has no horizon: its sky stays in the caption.
            no_horizon = "the witness is a devotional painting of a deity" if folio.get("deity") else None
            block = composite_witness(block, op, _folio_sky(folio), skip_reason=no_horizon)
        if current == block:
            return False
        folio["witness"] = block
        folio["manifestation"] = block
        try:
            _persist(folio, index=False)
        except OSError:
            logger.exception("could not write witness of render %s into folio %s", op.get("id"), working_id)
            return False
    return True


def witness_listener(op: dict[str, Any]) -> None:
    """The registered operations listener (``apply_witness_render`` without its return value)."""
    apply_witness_render(op)


def install_witness_listener() -> None:
    """Register :func:`witness_listener` with the operations ledger (repeat calls are no-ops)."""
    from core import operations

    operations.add_listener(witness_listener)


def attach_witness_image(working_id: str) -> dict[str, Any]:
    """Generate a witness image from the folio prompt and persist it."""
    folio = load_working(working_id)
    if folio is None:
        return {"error": "working_not_found", "working_id": working_id}

    prompt = witness_prompt(folio)
    facts = witness_caption_facts(folio)
    try:
        from backend.core.llm_agent.tools import generate_image

        img = generate_image(prompt)
        visual = {
            "status": "ok",
            "image_data_url": img.get("image_data_url"),
            "model": img.get("model"),
            "cost_usd": img.get("cost_usd"),
            "provider_used": img.get("provider_used"),
            "prompt": prompt,
            "caption_facts": facts,
        }
        folio["witness"] = visual
        folio["manifestation"] = visual
    except Exception as exc:
        err = {"status": "error", "error": str(exc)[:300], "prompt": prompt}
        folio["witness"] = err
        folio["manifestation"] = err

    try:
        _persist(folio, index=False)
        folio["saved"] = True
    except OSError as exc:
        folio["saved"] = False
        folio["save_error"] = str(exc)[:200]
    return folio


async def local_render_health() -> dict[str, Any]:
    """``/render/health`` of the default local backend; never raises."""
    from backend.core.services.render import jobs

    try:
        return await jobs.get_backend(jobs.DEFAULT_BACKEND).health()
    except Exception as exc:  # health never raises, but the backend lookup could
        return {"reachable": False, "detail": str(exc) or type(exc).__name__}


@dataclass(frozen=True)
class WitnessOutcome:
    """What :func:`forge_witness` did: queued a local render, or ran the hosted path."""

    queued: bool
    # queued: ``{"working_id", "operation"}``; hosted: the updated folio
    # (plus ``witness_fallback`` when local was preferred but unreachable).
    body: dict[str, Any]


async def forge_witness(working_id: str, backend: str | None = None) -> WitnessOutcome | None:
    """Witness image for a folio, preferring the local render engine (spec Contract W2-2).

    The one policy behind both ``POST /operator/workings/{id}/witness`` and the
    ``forge_witness`` LLM tools, so they cannot drift:

    - ``backend="local"`` queues a render job and returns at once (``queued``).
    - ``backend="hosted"`` runs the synchronous hosted generator in a worker
      thread, so the event loop is never blocked.
    - ``backend=None`` renders locally when the engine is reachable, else
      falls back to hosted and says so in ``body["witness_fallback"]``.

    Returns ``None`` if the folio does not exist.
    """
    if load_working(working_id) is None:
        return None
    fallback = None
    if backend is None:
        health = await local_render_health()
        if health.get("reachable"):
            backend = "local"
        else:
            backend = "hosted"
            fallback = {
                "requested": "local",
                "used": "hosted",
                "reason": f"local render backend unreachable: {health.get('detail') or 'no detail'}",
            }
    if backend == "local":
        submitted = submit_witness_render(working_id)
        return None if submitted is None else WitnessOutcome(queued=True, body=submitted)
    folio = await asyncio.to_thread(attach_witness_image, working_id)
    if fallback is not None:
        folio["witness_fallback"] = fallback
    return WitnessOutcome(queued=False, body=folio)


async def forge_witness_for_tool(working_id: str) -> dict[str, Any]:
    """:func:`forge_witness` shaped for an LLM tool result.

    A queued local render answers with its ``operation_id`` (the folio's
    ``witness`` is written when the render finishes); the hosted path answers
    with the updated folio, as it always has.
    """
    outcome = await forge_witness(working_id)
    if outcome is None:
        return {"error": "working_not_found", "working_id": working_id}
    if not outcome.queued:
        return outcome.body
    op = outcome.body["operation"]
    return {
        "working_id": working_id,
        "status": "queued",
        "backend": "local",
        "operation_id": op["id"],
        "operation": op,
        "message": (
            "Witness render queued on the local engine. It takes a few minutes; "
            "the folio's witness is filled in when the render finishes "
            f"(track it with operation {op['id']})."
        ),
    }


def charge_audio_path(working_id: str) -> Path:
    safe = "".join(ch for ch in working_id if ch.isalnum() or ch == "_")
    return WORKINGS_DIR / f"{safe}_charge.mp3"


def record_spoken(working_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    folio = load_working(working_id)
    if folio is None:
        return {"error": "working_not_found", "working_id": working_id}
    folio["spoken"] = payload
    try:
        _persist(folio, index=False)
        folio["saved"] = True
    except OSError as exc:
        folio["saved"] = False
        folio["save_error"] = str(exc)[:200]
    return folio


def video_prompt_for(folio: dict[str, Any]) -> str:
    """Build a MiniMax-length prompt from the sealed folio."""
    intention = str(folio.get("intention") or "a blessing")
    target = str(folio.get("target") or "all beings")
    charge = str(folio.get("spoken_charge") or "")
    still = str(folio.get("image_prompt") or "")
    # Video models paint numbers as text just like image models ("Merit ×100,000").
    return image_prompts.finalize_image_prompt(
        f"{still} Slow cinematic push-in, seamless loop, prayer-bowl glow, "
        f"dedication of merit for {target}. {charge} Theme: {intention}.",
        max_chars=1800,
    )


def record_video(working_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    folio = load_working(working_id)
    if folio is None:
        return {"error": "working_not_found", "working_id": working_id}
    folio["video"] = payload
    try:
        _persist(folio, index=False)
        folio["saved"] = True
    except OSError as exc:
        folio["saved"] = False
        folio["save_error"] = str(exc)[:200]
    return folio


def _image_prompt(
    intention: str,
    target: str,
    *,
    sky_period: str | None = None,
    saka_dawa: dict[str, Any] | None = None,
    deity_clause: str = "",
) -> str:
    """The witness image prompt: imagery only, under an empty sky.

    The model never paints the Moon or planets: the scene asks for a clear,
    empty sky (day, twilight or night as computed at sealing) and the true sky
    is drawn onto the render afterwards (:func:`apply_witness_render`,
    core/sky_composite.py). Saka Dawa is named only when the sitting fell in
    it; its date belongs in the caption, not here.
    A ``deity_clause`` (core/iconography.py) makes the still a devotional
    painting of that deity, the clause first so clipping never cuts it. A
    devotional painting has no horizon to draw the sky against, so its
    background is simply left empty and the sky goes in the caption only.
    """
    sky_line = f" {sky.empty_sky_clause(sky_period)}"
    saka = saka_dawa or {}
    if saka.get("is_duchen"):
        season = " Saka Dawa Duchen offerings: rows of butter lamps and white scarves."
    elif saka.get("is_saka_dawa"):
        season = " The Saka Dawa month: butter lamps glowing in the dusk."
    else:
        season = ""
    if deity_clause:
        return image_prompts.finalize_image_prompt(
            f"{deity_clause} Offered for the intention: {intention[:200]}. Dedicated to {target}. "
            f"{sky.EMPTY_BACKGROUND_CLAUSE}{season}",
            max_chars=iconography.DEITY_PROMPT_MAX_CHARS,
        )
    return image_prompts.finalize_image_prompt(
        f"Manifestation still of the fulfilled intention: {intention[:200]}. "
        f"Dedicated to {target}. Sacred cinematic lighting, brass singing bowls "
        f"at the edge of frame, amber and indigo, photographic, no real people."
        f"{sky_line}{season}"
    )


def _spoken_charge(intention: str, target: str, multiplier: int) -> str:
    merit = f" Merit ×{multiplier:,}." if multiplier > 1 else ""
    return (
        f"For {target}: {intention.strip().rstrip('.')}. "
        f"May this rate hold until the work is done.{merit} "
        "I dedicate the merit to all beings."
    )


def run_working(
    intention: str,
    target: str | None = None,
    broadcast: bool = True,
    duration_minutes: int = 5,
    source: str | None = None,
    chart_name: str | None = None,
    planetary_hour: str | None = None,
    moon_phase: str | None = None,
    divination: dict[str, Any] | None = None,
    deity: str | None = None,
    location: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Seal one working and optionally start a non-blocking broadcast.

    ``location`` (``{latitude, longitude, label?, source?}``) is where the
    working is sealed, so its witness shows the sky from there. Without one the
    home location (core/home_location.py) is used; with neither the folio has
    no location and its sky falls back to the configured default. An invalid
    location raises ``ValueError`` before anything is sealed.

    ``deity`` (an id, alias or form alias from ``knowledge/iconography.json``,
    e.g. ``green_tara`` or ``thousand-armed Chenrezig``) is sealed on the folio
    and paints its witness with that deity's curated iconography. An unknown
    deity raises ``ValueError`` before anything is sealed.
    """
    deity_ref = iconography.resolve(deity) if deity and deity.strip() else None
    if deity and deity.strip() and deity_ref is None:
        raise ValueError(f"unknown deity {deity!r}; see knowledge/iconography.json")
    sealed_location = home_location.folio_location(location)
    intention = (intention or "").strip() or "May all beings be free from suffering"
    target = (target or "all beings").strip() or "all beings"
    duration_minutes = max(1, min(int(duration_minutes or 5), 30))

    existing = find_recent_working(intention, target)
    if existing:
        reused = _label_folio(dict(existing))
        reused["reused"] = True
        return reused

    saka = check_saka_dawa()
    timing = check_auspicious_window("healing")
    rate = SignatureCalculator().text_to_rate(f"{intention} :: {target}", num_dials=5, algorithm="mixed")
    values = [int(v) for v in rate.values]
    carriers = map_rate_to_carriers(values)
    library = search_rates(intention)[:3]

    folio: dict[str, Any] = {
        "working_id": f"wrk_{uuid.uuid4().hex[:12]}",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "intention": intention,
        "target": target,
        "rate_values": values,
        "dials": [
            {"name": _DIAL_NAMES[i] if i < len(_DIAL_NAMES) else f"D{i + 1}", "value": values[i]}
            for i in range(len(values))
        ],
        "frequencies": list(carriers.frequencies),
        "solfeggio_names": list(carriers.solfeggio_names),
        "amplitude": carriers.amplitude,
        "library_hits": [
            {"name": hit.get("name"), "values": hit.get("values"), "category": hit.get("category")} for hit in library
        ],
        "saka_dawa": {
            "is_saka_dawa": saka.get("is_saka_dawa"),
            "is_duchen": saka.get("is_duchen"),
            "multiplier": saka.get("multiplier", 1),
            "losar": saka.get("losar"),
            "saka_dawa_duchen": saka.get("saka_dawa_duchen"),
            "days_until_duchen": saka.get("days_until_duchen"),
        },
        "timing": {
            "quality": timing.quality,
            "planetary_hour": timing.planetary_hour,
            "recommended_approach": timing.recommended_approach,
        },
        "image_prompt": "",  # filled in below from the sealed facts (witness_prompt)
        "spoken_charge": _spoken_charge(intention, target, int(saka.get("multiplier") or 1)),
        "broadcast": None,
        "source": source or "command-center",
        "chart_name": chart_name,
        "hour_stamp": {
            "planetary_hour": planetary_hour or timing.planetary_hour,
            "moon_phase": moon_phase,
        },
        "divination": divination,
        "deity": deity_ref.record() if deity_ref is not None else None,
        "location": sealed_location,
        "provenance": dict(FOLIO_PROVENANCE),
    }
    folio["image_prompt"] = witness_prompt(folio)

    if broadcast:
        try:
            from container import container

            folio["broadcast"] = container.radionics.broadcast_healing(
                target_name=target,
                duration_minutes=duration_minutes,
                intensity=0.8,
                rate_values=values,
            )
        except Exception as exc:
            folio["broadcast"] = {"status": "skipped", "error": str(exc)[:300]}

    try:
        _persist(folio)
        folio["saved"] = True
    except OSError as exc:
        folio["saved"] = False
        folio["save_error"] = str(exc)[:200]

    return folio
