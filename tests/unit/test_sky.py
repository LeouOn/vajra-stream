"""The true sky on a witness: geometry, projection, drawing and the no-ephemeris fallback.

Nothing here contacts ComfyUI; render artifacts, the ledger and folios live in tmp dirs.
"""

from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

import core.working as working
from backend.core.services import gallery
from backend.core.services.render import jobs
from core import operations, sky, sky_composite
from core.sky import BELOW_HORIZON, DAYLIGHT, DRAWN, OUT_OF_FRAME, Camera


def has_swisseph() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    return True


needs_ephemeris = pytest.mark.skipif(not has_swisseph(), reason="pyswisseph not installed")


def fake_sky(
    *,
    moon_alt: float = 20.0,
    moon_az: float = 180.0,
    illumination: float = 40.0,
    limb: float = 270.0,
    sun_alt: float = -20.0,
    lat: float = 37.7749,
    planets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A hand-made ``compute_sky`` result, so drawing tests need no ephemeris."""
    return {
        "at": "2026-10-17T03:00:00+00:00",
        "ephemeris": "test",
        "observer": {"lat": lat, "lon": -122.4194},
        "local_sidereal_deg": 0.0,
        "sun": {"alt": sun_alt, "az": 250.0},
        "period": sky.sky_period(sun_alt),
        "moon": {
            "alt": moon_alt,
            "az": moon_az,
            "illumination": illumination,
            "phase_angle": 90.0,
            "elongation": 90.0,
            "waxing": True,
            "apparent_diameter_deg": 0.5,
            "bright_limb_position_angle": limb,
            "parallactic_angle": 0.0,
            "bright_limb_from_vertical": limb,
        },
        "planets": planets if planets is not None else [],
    }


# -- the drawn disk ----------------------------------------------------------------------


@pytest.mark.parametrize("illumination", [0.0, 5.0, 25.0, 33.0, 50.0, 70.0, 95.0, 100.0])
@pytest.mark.parametrize("limb", [0.0, 45.0, 137.0, 270.0, 316.9])
def test_lit_pixel_fraction_matches_the_illumination(illumination, limb):
    size = 400
    lit = sky_composite.moon_lit_mask(size, illumination, limb).sum()
    disk = sky_composite.moon_disk_mask(size).sum()
    assert lit / disk == pytest.approx(illumination / 100.0, abs=0.01)


@pytest.mark.parametrize("illumination", [10.0, 33.0, 60.0, 90.0])
@pytest.mark.parametrize("limb", [0.0, 90.0, 200.0, 290.0, 316.9])
def test_bright_limb_points_toward_the_given_angle(illumination, limb):
    size = 300
    mask = sky_composite.moon_lit_mask(size, illumination, limb)
    ys, xs = np.nonzero(mask)
    cx, cy = xs.mean() + 0.5 - size / 2, ys.mean() + 0.5 - size / 2
    measured = math.atan2(cy, cx)
    bx, by = sky.limb_unit_vector(limb)
    expected = math.atan2(by, bx)
    assert abs(sky.wrap180(math.degrees(measured - expected))) < 2.0


def test_limb_vector_convention_is_counter_clockwise_from_up():
    assert sky.limb_unit_vector(0.0) == pytest.approx((0.0, -1.0))  # up
    assert sky.limb_unit_vector(90.0) == pytest.approx((-1.0, 0.0))  # left (east, facing south)
    assert sky.limb_unit_vector(270.0) == pytest.approx((1.0, 0.0))  # right (west)
    assert sky.limb_direction_words(270.0) == "right"
    assert sky.limb_direction_words(225.0) == "lower right"


def test_drawn_moon_on_black_lights_the_illuminated_fraction():
    plan = sky.plan_sky(fake_sky(illumination=33.0, limb=300.0), 1024, 1024, moon_scale=20.0)
    assert plan["moon"]["drawn"]
    scene = Image.new("RGB", (1024, 1024), (0, 0, 0))
    out = np.asarray(sky_composite.draw_sky(scene, plan).convert("L"), dtype=np.float64)
    x, y, r = plan["moon"]["x"], plan["moon"]["y"], plan["moon"]["radius_px"]
    yy, xx = np.mgrid[0:1024, 0:1024]
    inside = (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= (r - 1.5) ** 2  # skip the antialiased rim
    bright = out[inside] > 128
    assert bright.mean() == pytest.approx(0.33, abs=0.03)
    # the lit side is to the right (and a little up) of the centre, as asked
    lit_x = (xx[inside][bright] + 0.5 - x).mean()
    assert lit_x > 0.2 * r


# -- projection --------------------------------------------------------------------------


def test_projection_maps_alt_az_linearly_around_the_camera():
    cam = Camera(azimuth=200.0, basis="test")
    w, h = 1024, 1024
    assert sky.project(0.0, 200.0, cam, w, h) == pytest.approx((512.0, 0.85 * h))
    x, y = sky.project(30.0, 215.0, cam, w, h)
    assert x == pytest.approx(512.0 + 15.0 * w / 60.0)
    assert y == pytest.approx(0.85 * h - 30.0 * w / 60.0)
    # the left edge is 30 degrees east of the camera azimuth
    assert sky.project(10.0, 170.0, cam, w, h)[0] == pytest.approx(0.0)


def test_projection_wraps_through_north():
    cam = Camera(azimuth=350.0, basis="test")
    assert sky.project(10.0, 10.0, cam, 1000, 1000)[0] == pytest.approx(500.0 + 20.0 * 1000 / 60.0)
    assert sky.project(10.0, 330.0, cam, 1000, 1000)[0] == pytest.approx(500.0 - 20.0 * 1000 / 60.0)


def test_classify_in_frame_out_of_frame_and_below_horizon():
    cam = Camera(azimuth=180.0, basis="test")
    w = h = 1024
    assert sky.classify(20.0, 190.0, cam, w, h) == DRAWN
    assert sky.classify(-0.5, 180.0, cam, w, h) == BELOW_HORIZON
    assert sky.classify(20.0, 215.0, cam, w, h) == OUT_OF_FRAME  # beyond the 30 degree half-width
    assert sky.classify(20.0, 0.0, cam, w, h) == OUT_OF_FRAME  # behind the camera
    assert sky.classify(60.0, 180.0, cam, w, h) == OUT_OF_FRAME  # above the top edge (51 degrees)
    assert sky.classify(50.0, 180.0, cam, w, h) == DRAWN
    assert sky.classify(50.0, 180.0, cam, w, h, margin=30.0) == OUT_OF_FRAME  # a disk must fit whole


def test_plan_faces_the_moon_and_lists_every_body():
    planets = [
        {"name": "Venus", "alt": 10.0, "az": 195.0, "magnitude": -4.0},
        {"name": "Jupiter", "alt": 30.0, "az": 90.0, "magnitude": -2.0},
        {"name": "Saturn", "alt": -5.0, "az": 180.0, "magnitude": 0.8},
    ]
    plan = sky.plan_sky(fake_sky(moon_az=200.0, planets=planets), 1024, 1024)
    assert plan["camera"]["azimuth"] == 200.0 and plan["camera"]["basis"] == "Moon"
    assert plan["moon"]["x"] == pytest.approx(512.0)
    status = {p["name"]: p["status"] for p in plan["planets"]}
    assert status == {"Venus": DRAWN, "Jupiter": OUT_OF_FRAME, "Saturn": BELOW_HORIZON}
    fact = sky.overlay_caption_fact(plan)
    assert fact["provenance"] == "computed"
    assert "Moon drawn at 5× apparent size" in fact["value"]
    assert "drawn: Moon, Venus" in fact["value"] and "out of frame: Jupiter" in fact["value"]


def test_planets_are_not_drawn_in_daylight_but_the_moon_is():
    planets = [{"name": "Venus", "alt": 20.0, "az": 185.0, "magnitude": -4.0}]
    plan = sky.plan_sky(fake_sky(sun_alt=30.0, planets=planets), 1024, 1024)
    assert plan["moon"]["drawn"] is True
    assert plan["planets"][0]["status"] == DAYLIGHT and plan["planets"][0]["drawn"] is False


def test_camera_without_a_moon_faces_the_brightest_planet_or_the_equator():
    planets = [
        {"name": "Mars", "alt": 20.0, "az": 100.0, "magnitude": 1.0},
        {"name": "Jupiter", "alt": 25.0, "az": 140.0, "magnitude": -2.2},
    ]
    assert sky.choose_camera(fake_sky(moon_alt=-10.0, planets=planets)).azimuth == 140.0
    assert sky.choose_camera(fake_sky(moon_alt=-10.0, planets=planets, sun_alt=10.0)).azimuth == 180.0
    assert sky.choose_camera(fake_sky(moon_alt=-10.0, lat=-33.9)).azimuth == 0.0


def test_below_horizon_moon_is_captioned_and_not_drawn():
    plan = sky.plan_sky(fake_sky(moon_alt=-3.0), 1024, 1024)
    assert plan["moon"]["status"] == BELOW_HORIZON and not plan["moon"]["drawn"]
    facts = {f["label"]: f["value"] for f in sky.sky_caption_facts(fake_sky(moon_alt=-3.0))}
    assert facts["Moon in the sky"].startswith("Moon below horizon at sealing")


def test_observer_is_the_folio_location_or_the_default():
    assert sky.observer_for({"location": {"lat": 27.7, "lon": 85.3}}) == (27.7, 85.3, "folio")
    assert sky.observer_for({"latitude": -33.9, "longitude": 151.2}) == (-33.9, 151.2, "folio")
    assert sky.observer_for({}) == (37.7749, -122.4194, "default")
    assert sky.observer_for({"location": {"lat": 200, "lon": 0}})[2] == "default"
    assert "default location" in sky.observer_fact(37.7749, -122.4194, "default")["value"]


# -- the ephemeris -------------------------------------------------------------------------


@needs_ephemeris
@pytest.mark.parametrize("lat,lon", [(37.7749, -122.4194), (-33.9, 151.2), (64.1, -21.9)])
def test_bright_limb_points_along_the_great_circle_to_the_sun(lat, lon):
    """Independent check in alt/az: the bearing of the Sun from the Moon, from the local vertical."""
    checked = 0
    for hour in range(0, 24 * 20, 7):
        computed = sky.compute_sky(f"2026-10-{1 + hour // 24:02d}T{hour % 24:02d}:00:00+00:00", lat, lon)
        assert computed is not None
        moon, sun = computed["moon"], computed["sun"]
        if not 3.0 < moon["illumination"] < 90.0 or moon["alt"] < 5.0:
            continue  # near new or full the direction is ill-conditioned; refraction bends the horizon
        a1, a2 = math.radians(moon["alt"]), math.radians(sun["alt"])
        d = math.radians(sun["az"] - moon["az"])
        bearing = math.degrees(
            math.atan2(
                math.sin(d) * math.cos(a2), math.cos(a1) * math.sin(a2) - math.sin(a1) * math.cos(a2) * math.cos(d)
            )
        )
        # bearing is clockwise (toward increasing azimuth = right); the limb angle is counter-clockwise
        # (within the Moon's ~1 degree parallax, which this alt/az check does not model)
        assert abs(sky.wrap180(-bearing - moon["bright_limb_from_vertical"])) < 3.0
        checked += 1
    assert checked > 10


@needs_ephemeris
def test_known_sky_evening_crescent_has_its_bright_limb_toward_the_set_sun():
    # 2026-10-17 02:00 UTC = 19:00 PDT: a waxing crescent low in the south-west after sunset
    computed = sky.compute_sky("2026-10-17T02:00:00+00:00", 37.7749, -122.4194)
    assert computed is not None
    moon = computed["moon"]
    assert moon["waxing"] and 30.0 < moon["illumination"] < 45.0
    assert moon["alt"] > 0 and 180.0 < moon["az"] < 260.0
    assert sky.limb_unit_vector(moon["bright_limb_from_vertical"])[0] > 0.3  # lit side to the right (west)
    assert computed["period"] in ("twilight", "night")


def test_missing_ephemeris_means_no_sky(monkeypatch):
    monkeypatch.setitem(sys.modules, "swisseph", None)  # import raises ImportError
    assert sky.compute_sky("2026-10-17T02:00:00+00:00", 37.7749, -122.4194) is None
    folio = {"working_id": "wrk_x", "sealed_at": "2026-10-17T02:00:00+00:00", "intention": "x"}
    facts = {f["label"]: f for f in working.witness_caption_facts(folio)}
    assert facts["Sky at sealing"]["value"].startswith("could not be computed")
    assert "Moon in the sky" not in facts
    assert "no moon" in working.witness_prompt(folio)


def test_composite_witness_without_ephemeris_keeps_the_scene(tmp_path):
    block = {"status": "ok", "image_url": "/api/v1/render/jobs/abc/image", "caption_facts": []}
    out = sky_composite.composite_witness(block, {"id": "abc"}, None)
    assert out["image_url"] == block["image_url"]
    assert "scene_image_url" not in out
    assert out["sky"]["computed"] is False and out["sky"]["composited"] is False
    assert [f["label"] for f in out["caption_facts"]] == ["Sky at sealing"]


# -- compositing a render --------------------------------------------------------------------


@pytest.fixture
def render_root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(operations, "get_db_path", lambda: str(tmp_path / "ops.db"))
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    return tmp_path


def finished_render(base: Path, size: tuple[int, int] = (256, 256)) -> dict[str, Any]:
    op = operations.create_operation("render", "w", params={"purpose": "witness", "prompt": "p"})
    operations.start_operation(op["id"])
    rel = jobs.artifact_relpath(op)
    (base / rel).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (20, 30, 60)).save(base / rel, format="PNG")
    return operations.complete_operation(
        op["id"],
        {
            "image_url": f"/api/v1/render/jobs/{op['id']}/image",
            "artifact_path": str(rel),
            "width": size[0],
            "height": size[1],
        },
    )


def test_composite_keeps_the_scene_and_writes_a_sidecar(render_root):
    op = finished_render(render_root)
    scene = jobs.image_file(op)
    assert scene is not None
    before = hashlib.sha256(scene.read_bytes()).hexdigest()
    block = {
        "status": "ok",
        "operation_id": op["id"],
        "image_url": op["result"]["image_url"],
        "width": 256,
        "height": 256,
        "caption_facts": [{"label": "Sealed", "value": "x", "provenance": "record"}],
    }
    out = sky_composite.composite_witness(block, op, fake_sky())
    assert hashlib.sha256(scene.read_bytes()).hexdigest() == before  # the scene is untouched
    composite, sidecar = sky_composite.composite_paths(scene)
    assert composite.is_file() and sidecar.is_file()
    assert out["image_url"] == f"/api/v1/gallery/sky/{op['id']}/image"
    assert out["scene_image_url"] == op["result"]["image_url"]
    assert out["sky"]["composited"] is True and out["sky"]["moon"]["drawn"] is True
    assert out["sky"]["moon_scale_note"] == "moon drawn at 5× apparent size"
    assert out["caption_facts"][-1]["label"] == "Sky overlay"
    with Image.open(composite) as drawn, Image.open(scene) as plain:
        assert drawn.size == plain.size
        assert np.asarray(drawn).max() > np.asarray(plain).max()  # something bright was drawn
    # deterministic: a repeat produces the same block and reuses the composite
    mtime = composite.stat().st_mtime_ns
    assert sky_composite.composite_witness(block, op, fake_sky()) == out
    assert composite.stat().st_mtime_ns == mtime


def test_gallery_lists_and_serves_the_composite(render_root):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.api.v1.endpoints import gallery as gallery_endpoint

    op = finished_render(render_root)
    plain = finished_render(render_root)
    block = {"status": "ok", "image_url": op["result"]["image_url"], "width": 256, "height": 256}
    sky_composite.composite_witness(block, op, fake_sky())

    listing = gallery.list_gallery(hosted_dir=None, workings_dir=render_root / "none")
    items = {item["links"]["operation_id"]: item for item in listing["items"]}
    assert items[op["id"]]["image_url"] == f"/api/v1/gallery/sky/{op['id']}/image"
    assert items[op["id"]]["scene_image_url"] == op["result"]["image_url"]
    assert items[op["id"]]["caption_facts"][-1]["label"] == "Sky overlay"
    assert items[plain["id"]]["image_url"] == plain["result"]["image_url"]
    assert "scene_image_url" not in items[plain["id"]]

    app = FastAPI()
    app.include_router(gallery_endpoint.router, prefix="/api/v1")
    client = TestClient(app)
    res = client.get(f"/api/v1/gallery/sky/{op['id']}/image")
    assert res.status_code == 200 and res.headers["content-type"] == "image/png"
    assert client.get(f"/api/v1/gallery/sky/{plain['id']}/image").status_code == 404
    assert client.get("/api/v1/gallery/sky/nope/image").status_code == 404


def test_composite_witness_with_a_skip_reason_keeps_the_scene(render_root):
    op = finished_render(render_root)
    block = {"status": "ok", "image_url": op["result"]["image_url"], "width": 256, "height": 256, "caption_facts": []}
    out = sky_composite.composite_witness(block, op, fake_sky(), skip_reason="no horizon")
    assert out["image_url"] == block["image_url"]
    assert out["sky"]["composited"] is False and out["sky"]["reason"] == "no horizon"
    assert out["caption_facts"] == [{"label": "Sky overlay", "value": "not drawn: no horizon", "provenance": "record"}]
    composite, _ = sky_composite.composite_paths(jobs.image_file(op))
    assert not composite.exists()


def test_a_deity_witness_is_not_composited(render_root, monkeypatch):
    monkeypatch.setattr(working, "WORKINGS_DIR", render_root / "workings")
    (render_root / "workings").mkdir()
    folio = working.run_working("May all beings find refuge", broadcast=False, deity="green_tara")
    assert "low horizon" not in folio["image_prompt"]
    assert sky.EMPTY_BACKGROUND_CLAUSE in folio["image_prompt"]

    op = operations.create_operation(
        "render", "w", params={"purpose": "witness", "prompt": "p", "working_id": folio["working_id"]}
    )
    operations.start_operation(op["id"])
    rel = jobs.artifact_relpath(op)
    (render_root / rel).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (256, 256), (20, 30, 60)).save(render_root / rel, format="PNG")
    done = operations.complete_operation(
        op["id"], {"image_url": f"/api/v1/render/jobs/{op['id']}/image", "artifact_path": str(rel)}
    )
    assert working.apply_witness_render(done) is True
    witness = working.load_working(folio["working_id"])["witness"]
    assert witness["image_url"] == f"/api/v1/render/jobs/{op['id']}/image"
    assert witness["sky"]["composited"] is False
    assert "devotional painting" in witness["sky"]["reason"]
