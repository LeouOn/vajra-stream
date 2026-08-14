"""A single working: intention → rates → folio → optional broadcast.

Command Center chat could already write prayers and cast I Ching, but it
could not close a radionics loop. ``run_working`` is the compound tool
that does: Losar-aware Saka Dawa stamp, 5-dial signature, library lookup,
Solfeggio carriers, a spoken charge, and a non-blocking broadcast.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.auspicious_timing import check_auspicious_window, check_saka_dawa
from core.context_builder import search_rates
from core.radionics_engine import SignatureCalculator
from core.rate_to_audio import map_rate_to_carriers

WORKINGS_DIR = Path(__file__).resolve().parent.parent / "generated" / "workings"

_DIAL_NAMES = ("Physical", "Astral", "Mental", "Causal", "Spiritual")


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
    return data if isinstance(data, dict) else None


def list_workings(limit: int = 20) -> list[dict[str, Any]]:
    """Newest sealed workings, without image payloads."""
    if not WORKINGS_DIR.is_dir():
        return []
    files = sorted(WORKINGS_DIR.glob("wrk_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for path in files[: max(1, min(limit, 50))]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        witness = data.get("witness") if isinstance(data.get("witness"), dict) else {}
        saka = data.get("saka_dawa") if isinstance(data.get("saka_dawa"), dict) else {}
        has_image = bool(witness.get("image_data_url"))
        out.append(
            {
                "working_id": data.get("working_id"),
                "intention": data.get("intention"),
                "target": data.get("target"),
                "sealed_at": data.get("sealed_at"),
                "rate_values": data.get("rate_values"),
                "has_witness": has_image,
                "has_manifestation": has_image,
                "saka_dawa_duchen": saka.get("saka_dawa_duchen"),
            }
        )
    return out


def attach_witness_image(working_id: str) -> dict[str, Any]:
    """Generate a witness image from the folio prompt and persist it."""
    folio = load_working(working_id)
    if folio is None:
        return {"error": "working_not_found", "working_id": working_id}

    prompt = folio.get("image_prompt") or _image_prompt(
        str(folio.get("intention") or ""),
        str(folio.get("target") or "all beings"),
        (folio.get("saka_dawa") or {}).get("saka_dawa_duchen") if isinstance(folio.get("saka_dawa"), dict) else None,
    )
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
    return (
        f"{still} Slow cinematic push-in, seamless loop, prayer-bowl glow, "
        f"dedication of merit for {target}. {charge} Theme: {intention}."
    )[:1800]


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


def _image_prompt(intention: str, target: str, duchen: str | None) -> str:
    moon = f" Pale full moon for Saka Dawa Duchen {duchen}." if duchen else ""
    return (
        f"Manifestation still of the fulfilled intention: {intention[:200]}. "
        f"Dedicated to {target}. Sacred cinematic lighting, brass singing bowls "
        f"at the edge of frame, amber and indigo, photographic, no readable text, "
        f"no real people.{moon}"
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
) -> dict[str, Any]:
    """Seal one working and optionally start a non-blocking broadcast."""
    intention = (intention or "").strip() or "May all beings be free from suffering"
    target = (target or "all beings").strip() or "all beings"
    duration_minutes = max(1, min(int(duration_minutes or 5), 30))

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
        "image_prompt": _image_prompt(intention, target, saka.get("saka_dawa_duchen")),
        "spoken_charge": _spoken_charge(intention, target, int(saka.get("multiplier") or 1)),
        "broadcast": None,
        "source": source or "command-center",
        "chart_name": chart_name,
        "hour_stamp": {
            "planetary_hour": planetary_hour or timing.planetary_hour,
            "moon_phase": moon_phase,
        },
        "divination": divination,
    }

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
