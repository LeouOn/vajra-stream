"""Task 17 — smoke test for the 10 per-calc endpoints.

Hits all 10 new endpoints via FastAPI's TestClient and prints a one-line
result per endpoint. Saves a transcript for evidence.

Expected: all 200, with non-empty JSON bodies.
"""

from __future__ import annotations

import json

# Ensure the project root is on sys.path so `from backend.app.main import app`
# works no matter how this script is invoked.
import pathlib
import sys
from datetime import datetime, timezone

from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.main import app  # noqa: E402

client = TestClient(app)

NATAL = "2000-01-01T12:00:00Z"
TARGET = "2025-01-01T12:00:00Z"
SNAPSHOT = "2026-01-01T12:00:00Z"
LAT, LON = 0.0, 0.0

ENDPOINTS = [
    (
        "/api/v1/astrology/lots",
        {"date_iso": SNAPSHOT, "lat": LAT, "lon": LON, "sect": "day"},
        lambda body: (
            isinstance(body, dict)
            and body.get("status") == "success"
            and isinstance(body.get("lots"), dict)
            and len(body["lots"]) == 7
        ),
        "7 lots returned",
    ),
    (
        "/api/v1/astrology/midpoints",
        {"date_iso": SNAPSHOT, "lat": LAT, "lon": LON, "orb": 1.5},
        lambda body: (
            body.get("status") == "success" and body.get("count") == 45 and isinstance(body.get("midpoints"), dict)
        ),
        "45 midpoints returned",
    ),
    (
        "/api/v1/astrology/antiscia",
        {"date_iso": SNAPSHOT, "lat": LAT, "lon": LON},
        lambda body: body.get("status") == "success" and "antiscia" in body and len(body["antiscia"]) == 10,
        "10 planets antiscia",
    ),
    (
        "/api/v1/astrology/fixed-stars",
        {"date_iso": SNAPSHOT, "lat": LAT, "lon": LON, "orb": 1.0},
        lambda body: body.get("status") == "success" and "stars" in body and len(body["stars"]) == 7,
        "7 fixed stars",
    ),
    (
        "/api/v1/astrology/secondary-progressions",
        {
            "natal_date_iso": NATAL,
            "natal_lat": LAT,
            "natal_lon": LON,
            "target_date_iso": TARGET,
        },
        lambda body: (
            body.get("status") == "success" and "progressions" in body and len(body["progressions"]["positions"]) == 10
        ),
        "10 planet progressions + angles",
    ),
    (
        "/api/v1/astrology/solar-return",
        {
            "natal_date_iso": NATAL,
            "natal_lat": LAT,
            "natal_lon": LON,
            "return_year": 2026,
        },
        lambda body: (
            body.get("status") == "success"
            and "solar_return" in body
            and "exact_moment" in body["solar_return"]
            and "positions" in body["solar_return"]
        ),
        "solar return has exact_moment + positions",
    ),
    (
        "/api/v1/astrology/profection",
        {"natal_date_iso": NATAL, "target_year": 2025},
        lambda body: (
            body.get("status") == "success"
            and "profection" in body
            and "profected_asc_sign" in body["profection"]
            and "profection_lord" in body["profection"]
        ),
        "profection has sign + lord",
    ),
    (
        "/api/v1/astrology/solar-arc",
        {
            "natal_date_iso": NATAL,
            "natal_lat": LAT,
            "natal_lon": LON,
            "target_date_iso": TARGET,
        },
        lambda body: (
            body.get("status") == "success"
            and "solar_arc" in body
            and "solar_arc_degrees" in body["solar_arc"]
            and "directed" in body["solar_arc"]
        ),
        "solar arc has degrees + directed",
    ),
    (
        "/api/v1/astrology/year-ahead",
        {
            "natal_date_iso": NATAL,
            "natal_lat": LAT,
            "natal_lon": LON,
        },
        lambda body: body.get("status") == "success" and "year_ahead" in body and "events" in body["year_ahead"],
        "year-ahead has events list",
    ),
    (
        "/api/v1/astrology/astrocartography",
        {"date_iso": SNAPSHOT, "step_degrees": 5.0},
        lambda body: body.get("status") == "success" and "lines" in body and len(body["lines"]) == 10,
        "10 planets astrocartography",
    ),
]


def main() -> int:
    transcript: list[str] = []
    passed = 0
    failed = 0
    for path, body, check, description in ENDPOINTS:
        r = client.post(path, json=body)
        ok_status = r.status_code == 200
        try:
            payload = r.json()
        except Exception:
            payload = {}
        ok_shape = bool(check(payload)) if ok_status else False
        verdict = "PASS" if (ok_status and ok_shape) else "FAIL"
        if verdict == "PASS":
            passed += 1
        else:
            failed += 1
        line = f"{verdict}  {r.status_code:>3}  {path}  :: {description}  :: {json.dumps(payload, default=str)[:200]}"
        print(line)
        transcript.append(line)

    # Also test pydantic validation: lat=999 should return 422.
    validation_line = ""
    r = client.post(
        "/api/v1/astrology/lots",
        json={"date_iso": SNAPSHOT, "lat": 999.0, "lon": 0.0},
    )
    val_ok = r.status_code == 422
    validation_line = (
        f"{'PASS' if val_ok else 'FAIL'}  {r.status_code}  /api/v1/astrology/lots  :: lat=999 rejected by Pydantic"
    )
    print(validation_line)
    transcript.append(validation_line)
    if val_ok:
        passed += 1
    else:
        failed += 1

    summary = f"\n{passed} passed, {failed} failed"
    print(summary)
    transcript.append(summary)

    out = pathlib.Path(__file__).resolve().parent.parent / ".omo" / "evidence" / "task-17-endpoints.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(transcript) + "\n", encoding="utf-8")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
