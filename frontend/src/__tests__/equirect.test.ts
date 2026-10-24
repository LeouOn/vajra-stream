// @vitest-environment happy-dom
/**
 * W3-E — flat equirectangular world strip: pure maths tests.
 *
 * The Wave 1 lesson (W1-D2): shading is physics. A night mask drawn as an
 * approximate polygon passed every structural test while shading five of
 * eight visible places wrong. So the core of this file checks the per-pixel
 * factor at many places x several sun positions against an INDEPENDENTLY
 * written solar-altitude formula (hour-angle form, not the library's
 * acos-distance form), and pins that a binary alt<0 polygon mask CANNOT
 * satisfy these expectations.
 */
import { describe, expect, test } from 'vitest';

import {
  SUNRISE_ALTITUDE_DEG,
  decodeLand,
  sunAltitudeDeg,
  wrapLon,
  type LandData,
  type SubPoint,
} from '../lib/earth';
import { NIGHT_RAMP_END_ALT_DEG, NIGHT_RAMP_START_ALT_DEG } from '../lib/orthographic';
import {
  dawnPaths,
  drawWorldStrip,
  latLonToXY,
  nightFactorAt,
  nightFactorMask,
  nightOverlay,
  xyToLatLon,
} from '../lib/equirect';

const W = 720;
const H = 360;
const RAD = Math.PI / 180;

/* Independent solar altitude: sin(alt) = sin(lat)sin(dec) + cos(lat)cos(dec)cos(H),
 * with declination = sub-solar latitude and hour angle H = lng - sun.lng.
 * Written fresh here; it shares no code path with lib/equirect or the
 * angularDistanceDeg-based sunAltitudeDeg. */
function sinAltIndependent(sun: SubPoint, lat: number, lng: number): number {
  return (
    Math.sin(lat * RAD) * Math.sin(sun.lat * RAD) +
    Math.cos(lat * RAD) * Math.cos(sun.lat * RAD) * Math.cos((lng - sun.lon) * RAD)
  );
}

/* The same ramp semantics as the globes' mask (lib/orthographic): 0 at and
 * above SUNRISE_ALTITUDE_DEG, 1 at and below -6 deg, linear in sin(altitude)
 * between. Ramp bounds imported; the altitude path above is independent. */
const SIN_START = Math.sin(NIGHT_RAMP_START_ALT_DEG * RAD);
const SIN_END = Math.sin(NIGHT_RAMP_END_ALT_DEG * RAD);

function expectedFactor(sun: SubPoint, lat: number, lng: number): number {
  const sinAlt = sinAltIndependent(sun, lat, lng);
  if (sinAlt >= SIN_START) return 0;
  if (sinAlt <= SIN_END) return 1;
  return (SIN_START - sinAlt) / (SIN_START - SIN_END);
}

/* The naive mask this row must be better than: "night" as a boolean
 * half-plane of solar altitude below 0 deg (what a coarse polygon fill of
 * an alt<0 terminator computes), ignoring both the sunrise constant and
 * the twilight ramp. */
function legacyBinaryNight(sun: SubPoint, lat: number, lng: number): boolean {
  return sinAltIndependent(sun, lat, lng) < 0;
}

const SUNS: SubPoint[] = [
  { lat: 0, lon: 0 }, // equinox, sub-solar on the prime meridian
  { lat: 23.44, lon: 146.1 }, // June solstice, Sun over the Pacific
  { lat: -23.44, lon: -93.9 }, // December solstice, Sun over the Americas
  { lat: -11.1, lon: 86.1 }, // the W1-C 02:00 UTC case (Sun over Asia)
  { lat: 90, lon: 20 }, // Sun at the pole: polar day north of the terminator
];

const PLACES: Array<{ name: string; lat: number; lng: number }> = [
  { name: 'New York', lat: 40.71, lng: -74.01 },
  { name: 'Miami', lat: 25.76, lng: -80.19 },
  { name: 'Denver', lat: 39.74, lng: -104.99 },
  { name: 'Mexico City', lat: 19.43, lng: -99.13 },
  { name: 'Bogota', lat: 4.71, lng: -74.07 },
  { name: 'Los Angeles', lat: 34.05, lng: -118.24 },
  { name: 'London', lat: 51.51, lng: -0.13 },
  { name: 'Sydney', lat: -33.87, lng: 151.21 },
  { name: 'Tokyo', lat: 35.68, lng: 139.69 },
  { name: 'Cape Town', lat: -33.92, lng: 18.42 },
  { name: 'Reykjavik', lat: 64.15, lng: -21.94 },
  { name: 'near South Pole', lat: -89.9, lng: 0 },
];

describe('latLonToXY / xyToLatLon — equirectangular mapping', () => {
  test('round trip exact on a grid including the corners', () => {
    for (let lat = -90; lat <= 90; lat += 15) {
      for (let lng = -180; lng < 180; lng += 15) {
        const { x, y } = latLonToXY(lat, lng, W, H);
        const back = xyToLatLon(x, y, W, H);
        expect(Math.abs(back.lat - lat)).toBeLessThan(1e-9);
        expect(Math.abs(wrapLon(back.lng - lng))).toBeLessThan(1e-9);
      }
    }
  });

  test('corners: (90,-180) top-left, (-90,180) bottom-right edge', () => {
    expect(latLonToXY(90, -180, W, H)).toEqual({ x: 0, y: 0 });
    const bottomRight = latLonToXY(-90, 179.5, W, H);
    expect(bottomRight.x).toBeCloseTo(W - 1, 6);
    expect(bottomRight.y).toBeCloseTo(H, 6);
  });

  test('wrap-aware: the right edge maps to lng -180', () => {
    const atRightEdge = xyToLatLon(W, H / 2, W, H);
    expect(atRightEdge.lng).toBe(-180);
    // A click half a pixel past the edge wraps instead of exceeding 180.
    const past = xyToLatLon(W + 1.2, H / 2, W, H);
    expect(past.lng).toBeGreaterThanOrEqual(-180);
    expect(past.lng).toBeLessThan(0);
  });

  test('out-of-vertical clicks clamp to the poles', () => {
    expect(xyToLatLon(W / 2, -5, W, H).lat).toBe(90);
    expect(xyToLatLon(W / 2, H + 5, W, H).lat).toBe(-90);
  });
});

describe('nightFactorAt — exact per-pixel mask (the Wave 1 lesson)', () => {
  for (const sun of SUNS) {
    test(`sun (${sun.lat},${sun.lon}): 12 places match the independent formula`, () => {
      for (const place of PLACES) {
        const { x, y } = latLonToXY(place.lat, place.lng, W, H);
        const factor = nightFactorAt(sun, W, H, x, y);
        const expected = expectedFactor(sun, place.lat, place.lng);
        // The pixel centre IS the place (exact inverse), so agreement is to
        // floating-point precision, not a polygon-scale tolerance.
        expect(factor).toBeCloseTo(expected, 9);
      }
    });
  }

  test('agrees with the committed sunAltitudeDeg over the whole grid', () => {
    const sun = SUNS[1];
    for (let lat = -88; lat <= 88; lat += 11) {
      for (let lng = -175; lng <= 175; lng += 23) {
        const { x, y } = latLonToXY(lat, lng, W, H);
        const sinAlt = Math.sin(sunAltitudeDeg(sun, { lat, lon: lng }) * RAD);
        const expected =
          sinAlt >= SIN_START ? 0 : sinAlt <= SIN_END ? 1 : (SIN_START - sinAlt) / (SIN_START - SIN_END);
        expect(nightFactorAt(sun, W, H, x, y)).toBeCloseTo(expected, 9);
      }
    }
  });

  test('twilight ramp: hand-derived mid-ramp factors on the equator, sun (0,0)', () => {
    // On the equator with the Sun at (0,0): alt = 90 - |lng|, sin(alt) = cos(lng).
    // Ramp (linear in sin(alt), SUNRISE_ALTITUDE_DEG=-0.8793 to -6 deg):
    //   lng 90.4 -> alt -0.4  (above the constant: still day, factor 0)
    //   lng 91.0 -> alt -1.0  -> (cos91-sin(-.8793))/(sin(-.8793)-sin(-6)) = 0.0236182
    //   lng 93.5 -> alt -3.5  -> 0.5124606
    //   lng 95.0 -> alt -5.0  -> 0.8052001
    //   lng 97.0 -> alt -7.0  -> past the ramp end, 1.0
    const sun = SUNS[0];
    const cases: Array<[number, number]> = [
      [90.4, 0],
      [91.0, 0.0236182],
      [93.5, 0.5124606],
      [95.0, 0.8052001],
      [97.0, 1.0],
      [-93.5, 0.5124606],
    ];
    for (const [lng, expected] of cases) {
      const { x, y } = latLonToXY(0, lng, W, H);
      expect(nightFactorAt(sun, W, H, x, y)).toBeCloseTo(expected, 6);
    }
  });

  test('polar day and night at the June solstice', () => {
    const sun = SUNS[1]; // Sun over 23.44 N
    // North pole: polar day, factor 0. South pole: polar night, factor 1.
    const np = latLonToXY(89.9, 0, W, H);
    expect(nightFactorAt(sun, W, H, np.x, np.y)).toBe(0);
    const sp = latLonToXY(-89.9, 0, W, H);
    expect(nightFactorAt(sun, W, H, sp.x, sp.y)).toBe(1);
  });

  test('RED pin: a binary alt<0 polygon mask cannot satisfy the ramp', () => {
    const sun = SUNS[0];
    // Mid-ramp places on both sides of the anti-solar meridian.
    for (const lng of [91.0, 93.5, 95.0, -91.0, -93.5, -95.0]) {
      const { x, y } = latLonToXY(0, lng, W, H);
      const exact = nightFactorAt(sun, W, H, x, y);
      const expected = expectedFactor(sun, 0, lng);
      const legacy = legacyBinaryNight(sun, 0, lng) ? 1 : 0;
      expect(exact).toBeCloseTo(expected, 9);
      // The exact value is strictly between 0 and 1 where the ramp lives:
      // no boolean mask (any polygon of any fineness) can produce it.
      expect(exact).toBeGreaterThan(0.02);
      expect(exact).toBeLessThan(0.95);
      expect(Math.abs(legacy - exact)).toBeGreaterThan(0.04);
    }
  });

  test('RED pin: the sunrise constant, not 0 deg, starts the ramp', () => {
    const sun = SUNS[0];
    // alt = -0.5 (lng 90.5) is BELOW 0 but ABOVE SUNRISE_ALTITUDE_DEG:
    // the exact mask still says day (factor 0), a 0-deg polygon says night.
    const day = latLonToXY(0, 90.5, W, H);
    expect(nightFactorAt(sun, W, H, day.x, day.y)).toBe(0);
    expect(legacyBinaryNight(sun, 0, 90.5)).toBe(true);
    // alt = -1.0 (lng 91.0): the ramp has just begun — 0.0236, not 1.
    const p2 = latLonToXY(0, 91.0, W, H);
    expect(nightFactorAt(sun, W, H, p2.x, p2.y)).toBeCloseTo(0.0236182, 6);
    expect(legacyBinaryNight(sun, 0, 91.0) ? 1 : 0).toBe(1);
  });
});

describe('nightFactorMask / nightOverlay', () => {
  test('mask covers the canvas and equals per-pixel evaluation at pixel centres', () => {
    const sun = SUNS[3];
    const mask = nightFactorMask(sun, 64, 32);
    expect(mask.length).toBe(64 * 32);
    for (let y = 0; y < 32; y += 1) {
      for (let x = 0; x < 64; x += 1) {
        expect(mask[y * 64 + x]).toBeCloseTo(nightFactorAt(sun, 64, 32, x + 0.5, y + 0.5), 5);
      }
    }
  });

  test('mask is continuous: neighbouring pixels differ by the ramp slope at most', () => {
    const sun = SUNS[1];
    const mask = nightFactorMask(sun, 96, 48);
    // One longitude pixel = 3.75 deg of altitude on the equator: the full
    // ramp (5.12 deg) spans ~1.4 px, so neighbours can differ by at most 1.
    for (let y = 0; y < 48; y += 1) {
      for (let x = 1; x < 96; x += 1) {
        const d = Math.abs(mask[y * 96 + x] - mask[y * 96 + x - 1]);
        expect(d).toBeLessThanOrEqual(1.0001);
      }
    }
  });

  test('overlay: rgb 97,97,112 with alpha = round(255*factor); alpha 0 in day', () => {
    const sun = SUNS[0];
    const overlay = nightOverlay(sun, 64, 32);
    expect(overlay.width).toBe(64);
    expect(overlay.height).toBe(32);
    expect(overlay.data.length).toBe(64 * 32 * 4);
    for (let y = 0; y < 32; y += 1) {
      for (let x = 0; x < 64; x += 1) {
        const i = y * 64 + x;
        const o = i * 4;
        const factor = nightFactorAt(sun, 64, 32, x + 0.5, y + 0.5);
        expect(overlay.data[o + 3]).toBe(Math.round(255 * factor));
        if (factor > 0) {
          expect(overlay.data[o]).toBe(97);
          expect(overlay.data[o + 1]).toBe(97);
          expect(overlay.data[o + 2]).toBe(112);
        } else {
          expect(overlay.data[o + 3]).toBe(0);
        }
      }
    }
  });
});

describe('dawnPaths — the sunrise/sunset boundary in strip pixels', () => {
  for (const sun of [SUNS[0], SUNS[1], SUNS[2], SUNS[3], SUNS[4]]) {
    test(`sun (${sun.lat},${sun.lon}): two continuous side-split paths on the terminator`, () => {
      const paths = dawnPaths(sun, W, H, 180);
      expect(paths.map((p) => p.side).sort()).toEqual(['sunrise', 'sunset']);
      for (const path of paths) {
        expect(path.points.length).toBeGreaterThan(50);
        for (let i = 0; i < path.points.length; i += 1) {
          const pt = path.points[i];
          expect(pt.x).toBeGreaterThanOrEqual(-W - 1);
          expect(pt.x).toBeLessThanOrEqual(2 * W + 1);
          expect(pt.y).toBeGreaterThanOrEqual(-1);
          expect(pt.y).toBeLessThanOrEqual(H + 1);
          if (i > 0) {
            const prev = path.points[i - 1];
            // Continuity: no antimeridian jump left inside a path (x), and
            // y steps stay within the poleward steepness of a 2-deg bearing
            // step at 180 segments (~4.6 deg of latitude -> ~10 px at H=360).
            expect(Math.abs(pt.x - prev.x)).toBeLessThanOrEqual(W / 2 + 1);
            expect(Math.abs(pt.y - prev.y)).toBeLessThanOrEqual(12);
          }
          // Physics: the pixel converts back to a place ON the terminator.
          const back = xyToLatLon(((pt.x % W) + W) % W, pt.y, W, H);
          const alt = Math.asin(Math.min(1, Math.max(-1, sinAltIndependent(sun, back.lat, back.lng)))) / RAD;
          expect(Math.abs(alt - SUNRISE_ALTITUDE_DEG)).toBeLessThanOrEqual(0.02);
          // Side: sunrise half is west of the sub-solar meridian. The two
          // arc-split points themselves (dlon ~0 south extreme, |dlon| ~180
          // north fold) belong to both halves' closures and are excluded.
          const dLon = wrapLon(back.lng - sun.lon);
          if (Math.abs(dLon) > 0.5 && Math.abs(dLon) < 178) {
            expect(dLon < 0).toBe(path.side === 'sunrise');
          }
        }
      }
    });
  }
});

describe('drawWorldStrip — deterministic pure render onto a context', () => {
  const TINY_LAND: LandData = {
    v: 1,
    kind: 'land',
    decimals: 0,
    polys: [{ o: [0, 0, 10, 0, 10, 10, 0, 10], h: [] }],
  };

  interface Recorded {
    fills: string[];
    evenOddFills: number;
    arcs: Array<{ x: number; y: number; r: number }>;
    strokes: number;
    strokeRects: number;
    putImages: number[];
    drawnImages: number[];
    compositeOps: string[];
  }

  // Return type inferred on purpose: the harness object also exposes the
  // injected offscreen canvas, which three tests use.
  function makeCtx() {
    const recorded: Recorded = {
      fills: [],
      evenOddFills: 0,
      arcs: [],
      strokes: 0,
      strokeRects: 0,
      putImages: [],
      drawnImages: [],
      compositeOps: [],
    };
    const images: Array<{ width: number; height: number; data: Uint8ClampedArray }> = [];
    const offCtx = {
      putImageData: (img: { width: number; height: number }) => {
        recorded.putImages.push(img.width * 10000 + img.height);
      },
    };
    const offscreen = {
      width: 0,
      height: 0,
      getContext: () => offCtx,
    };
    const ctx = {
      _images: images,
      _offscreen: offscreen,
      fillStyle: '',
      strokeStyle: '',
      lineWidth: 0,
      globalCompositeOperation: 'source-over',
      globalAlpha: 1,
      fillRect: (_x: number, _y: number, w: number, _h: number) => {
        recorded.fills.push(`rect:${w}`);
      },
      strokeRect: () => {
        recorded.strokeRects += 1;
      },
      beginPath: () => undefined,
      moveTo: () => undefined,
      lineTo: () => undefined,
      closePath: () => undefined,
      arc: (x: number, y: number, r: number) => {
        recorded.arcs.push({ x, y, r });
      },
      stroke: () => {
        recorded.strokes += 1;
      },
      fill: (rule?: string) => {
        if (rule === 'evenodd') recorded.evenOddFills += 1;
      },
      createImageData: (w: number, h: number) => {
        const img = { width: w, height: h, data: new Uint8ClampedArray(w * h * 4) };
        images.push(img);
        return img;
      },
      drawImage: (_source: unknown, _a: number, _b: number, c: number, d: number) => {
        recorded.drawnImages.push(c * 10000 + d);
      },
      save: () => undefined,
      restore: () => undefined,
    };
    return { ctx: ctx as unknown as CanvasRenderingContext2D, recorded, offscreen };
  }

  test('ocean first, land second (evenodd), then mask, dawn lines, markers', () => {
    const { ctx, recorded, offscreen } = makeCtx();
    const sun: SubPoint = { lat: 5, lon: 5 };
    drawWorldStrip(
      ctx as CanvasRenderingContext2D,
      {
        width: 200,
        height: 100,
        land: TINY_LAND,
        sun,
        observer: { lat: -30, lng: 120 },
      },
      () => offscreen as unknown as HTMLCanvasElement,
    );
    // Ocean painted as a full-canvas rect before the land fill.
    expect(recorded.fills[0]).toBe('rect:200');
    expect(recorded.evenOddFills).toBe(1);
    // Night mask at full resolution: 200x100 offscreen, drawn back 1:1.
    expect(recorded.putImages).toEqual([200 * 10000 + 100]);
    expect(recorded.drawnImages).toEqual([200 * 10000 + 100]);
    // Dawn: sunrise + sunset strokes, each painted 3 times (wrapped -W, 0,
    // +W), plus the observer ring stroke = 7 strokes in total.
    expect(recorded.strokes).toBe(7);
    // One frame stroke around the strip.
    expect(recorded.strokeRects).toBe(1);
    // Markers: sun (2 arcs) + observer (2 arcs).
    expect(recorded.arcs.length).toBe(4);
    const sunPx = latLonToXY(5, 5, 200, 100);
    expect(recorded.arcs[0].x).toBeCloseTo(sunPx.x, 6);
    expect(recorded.arcs[0].y).toBeCloseTo(sunPx.y, 6);
    const obsPx = latLonToXY(-30, 120, 200, 100);
    expect(recorded.arcs[2].x).toBeCloseTo(obsPx.x, 6);
    expect(recorded.arcs[2].y).toBeCloseTo(obsPx.y, 6);
  });

  test('the mask pixels handed to the context equal nightOverlay exactly', () => {
    const { ctx, offscreen } = makeCtx();
    const sun: SubPoint = { lat: -11.1, lon: 86.1 };
    drawWorldStrip(
      ctx,
      { width: 100, height: 50, land: TINY_LAND, sun, observer: null },
      () => offscreen as unknown as HTMLCanvasElement,
    );
    const images = (ctx as unknown as { _images: Array<{ width: number; data: Uint8ClampedArray }> })._images;
    expect(images.length).toBe(1);
    const expected = nightOverlay(sun, 100, 50);
    expect(images[0].width).toBe(100);
    expect(Array.from(images[0].data)).toEqual(Array.from(expected.data));
  });

  test('sun null: land and frame only — no mask, no dawn, no markers', () => {
    const { ctx, recorded } = makeCtx();
    drawWorldStrip(ctx, { width: 100, height: 50, land: TINY_LAND, sun: null, observer: null });
    expect(recorded.fills[0]).toBe('rect:100');
    expect(recorded.evenOddFills).toBe(1);
    expect(recorded.putImages).toEqual([]);
    expect(recorded.drawnImages).toEqual([]);
    expect(recorded.strokes).toBe(0);
    expect(recorded.arcs.length).toBe(0);
  });

  test('decodes integer land through decodeLand-compatible rings (Caspian hole subtracts)', () => {
    // 3-decimal integer encoding, as the real 110 m file ships.
    const raw = {
      v: 1,
      kind: 'land',
      decimals: 3,
      polys: [
        {
          o: [-90000, -10000, 90000, -10000, 90000, 10000, -90000, 10000],
          h: [[10000, -2000, 14000, -2000, 14000, 2000, 10000, 2000]],
        },
      ],
    };
    expect(() => decodeLand(raw)).not.toThrow();
    const land = decodeLand(raw);
    const { ctx, recorded } = makeCtx();
    drawWorldStrip(ctx, { width: 100, height: 50, land, sun: null, observer: null });
    expect(recorded.evenOddFills).toBe(1);
  });
});
