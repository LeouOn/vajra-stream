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
        rates = tuple(int(v) for v in (data.get("rate_values") or []) if isinstance(v, (int, float)))
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
    return data if isinstance(data, dict) else None


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
        has_image = bool(witness.get("image_data_url"))
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

    existing = find_recent_working(intention, target)
    if existing:
        reused = dict(existing)
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
