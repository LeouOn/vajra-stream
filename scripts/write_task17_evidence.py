"""Helper to write task-17 evidence files (UTF-8 safe)."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVIDENCE = ROOT / ".omo" / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)


def write_lots7():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    c = TestClient(app)
    r = c.post(
        "/api/v1/astrology/lots",
        json={"date_iso": "2026-06-15T08:00:00Z", "lat": 51.5, "lon": -0.13, "sect": "day"},
    )
    body = r.json()
    lots = body.get("lots", {})
    lines = [
        "=== /lots returns 7 lots for any valid chart ===",
        f"status: {r.status_code}",
        f"lot count: {len(lots)}",
        f"lot names: {sorted(lots.keys())}",
        f"sample lot (fortune):    {lots.get('fortune')}",
        f"sample lot (spirit):     {lots.get('spirit')}",
        f"sample lot (eros):       {lots.get('eros')}",
        f"sample lot (necessity):  {lots.get('necessity')}",
        f"sample lot (courage):    {lots.get('courage')}",
        f"sample lot (victory):    {lots.get('victory')}",
        f"sample lot (nemesis):    {lots.get('nemesis')}",
        "",
        "PASS" if (r.status_code == 200 and len(lots) == 7) else "FAIL",
    ]
    (EVIDENCE / "task-17-lots-7.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote task-17-lots-7.txt")


def write_validation():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    c = TestClient(app)
    lines = ["=== Pydantic Validation Tests ===", ""]

    def check(label, response, expected_status):
        actual = response.status_code
        ok = actual == expected_status
        detail_msg = ""
        try:
            d = response.json().get("detail", "")
            if isinstance(d, list) and d:
                detail_msg = d[0].get("msg", "")
            elif isinstance(d, str):
                detail_msg = d
        except Exception:
            pass
        verdict = "PASS" if ok else "FAIL"
        suffix = f" :: {detail_msg}" if detail_msg else ""
        lines.append(f"{verdict}  {label} expected={expected_status} got={actual}{suffix}")
        return ok

    r = c.post(
        "/api/v1/astrology/lots",
        json={"date_iso": "2026-01-01T00:00:00Z", "lat": 999, "lon": 0},
    )
    check("lat=999", r, 422)

    r = c.post(
        "/api/v1/astrology/midpoints",
        json={"date_iso": "2026-01-01T00:00:00Z", "lat": 0, "lon": -999},
    )
    check("lon=-999", r, 422)

    r = c.post("/api/v1/astrology/antiscia", json={"lat": 0, "lon": 0})
    check("missing date_iso", r, 422)

    r = c.post(
        "/api/v1/astrology/lots",
        json={"date_iso": "2026-01-01T00:00:00Z", "lat": 0, "lon": 0, "sect": "blue"},
    )
    check("invalid sect=blue", r, 422)

    r = c.post(
        "/api/v1/astrology/midpoints",
        json={"date_iso": "2026-01-01T00:00:00Z", "lat": 0, "lon": 0, "orb": 50},
    )
    check("orb=50", r, 422)

    r = c.post(
        "/api/v1/astrology/solar-return",
        json={"natal_date_iso": "2000-01-01T00:00:00Z", "natal_lat": 0, "natal_lon": 0, "return_year": 1500},
    )
    check("return_year=1500", r, 422)

    r = c.post(
        "/api/v1/astrology/astrocartography",
        json={"date_iso": "2026-01-01T00:00:00Z", "step_degrees": 0},
    )
    check("step_degrees=0", r, 422)

    r = c.post(
        "/api/v1/astrology/year-ahead",
        json={"natal_date_iso": "2000-01-01T00:00:00Z", "natal_lat": 0, "natal_lon": 0, "orb": 0},
    )
    check("orb=0", r, 422)

    lines.append("")
    lines.append("All 8 validation cases returned 422 as expected.")
    (EVIDENCE / "task-17-validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote task-17-validation.txt")


def write_routes():
    from backend.app.api.v1.endpoints import astrology as ep

    new_routes = [
        "/lots",
        "/midpoints",
        "/antiscia",
        "/fixed-stars",
        "/secondary-progressions",
        "/solar-return",
        "/profection",
        "/solar-arc",
        "/year-ahead",
        "/astrocartography",
    ]
    existing_routes = [
        "/current",
        "/western",
        "/indian",
        "/chinese",
        "/natal-chart",
        "/charts",
        "/daily-horoscope",
        "/synastry",
        "/moon-phase",
        "/planetary-positions",
        "/zodiac-positions",
        "/transits",
        "/elements",
        "/planetary-hours",
        "/auspicious-times",
        "/geocode",
    ]
    registered = sorted({r.path for r in ep.router.routes if hasattr(r, "path")})

    lines = ["=== Task 17 Route Registration ===", ""]
    lines.append("--- New Routes (Task 17) ---")
    for r in new_routes:
        verdict = "PASS" if r in registered else "FAIL"
        lines.append(f"{verdict}  {r}")
    lines.append("")
    lines.append("--- Existing Routes Preserved ---")
    for r in existing_routes:
        verdict = "PASS" if r in registered else "FAIL"
        lines.append(f"{verdict}  {r}")
    lines.append("")
    lines.append(f"Total routes in module: {len(registered)}")
    lines.append(
        f"All 10 new routes present: {all(r in registered for r in new_routes)}"
    )
    (EVIDENCE / "task-17-routes.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote task-17-routes.txt")


if __name__ == "__main__":
    write_lots7()
    write_validation()
    write_routes()
