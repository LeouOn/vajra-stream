/**
 * W1-B tests for frontend/src/lib/earth.ts — terminator maths and land painter.
 *
 * The property tests are hand-derived from the wave-1 contract:
 *  - the terminator at altitude h0 is the small circle of angular radius
 *    90° − h0 around the sub-solar point, so every point on it has
 *    sunAltitudeDeg = h0 (tolerance 1e-9°);
 *  - points west of the sub-solar meridian are on the sunrise half;
 *  - Sun altitude at P is 90° − (angular distance P to sub-solar point).
 *
 * The painter is tested against a recording stub of CanvasRenderingContext2D
 * (the vitest environment is node; there is no canvas).
 */

import { beforeAll, describe, expect, it } from 'vitest';
import {
  SUNRISE_ALTITUDE_DEG,
  angularDistanceDeg,
  decodeLand,
  landRings,
  paintLand,
  sideOf,
  sunAltitudeDeg,
  terminatorPoints,
  wrapLon,
  type LandData,
  type SubPoint,
} from '../lib/earth';

const sub = (lat: number, lon: number): SubPoint => ({ lat, lon });

describe('wrapLon', () => {
  it('maps to [-180, 180)', () => {
    expect(wrapLon(0)).toBe(0);
    expect(wrapLon(180)).toBe(-180);
    expect(wrapLon(-180)).toBe(-180);
    expect(wrapLon(360)).toBe(0);
    expect(wrapLon(181)).toBe(-179);
    expect(wrapLon(-181)).toBe(179);
    expect(wrapLon(540)).toBe(-180); // 540 -> -180
  });
});

describe('angularDistanceDeg / sunAltitudeDeg', () => {
  it('hand-derived spherical distances', () => {
    expect(angularDistanceDeg(sub(0, 0), sub(0, 0))).toBeCloseTo(0, 9);
    expect(angularDistanceDeg(sub(0, 0), sub(0, 90))).toBeCloseTo(90, 9);
    expect(angularDistanceDeg(sub(0, 0), sub(0, 180))).toBeCloseTo(180, 9);
    expect(angularDistanceDeg(sub(0, 0), sub(90, 0))).toBeCloseTo(90, 9);
    // diagonal: cos d = sin0 sin45 + cos0 cos45 cos90 = 0 -> d = 90
    expect(angularDistanceDeg(sub(0, 0), sub(45, 90))).toBeCloseTo(90, 9);
    // same latitude, 60 deg apart in longitude at lat 60: cos d = sin²60 + cos²60·cos60
    expect(angularDistanceDeg(sub(60, 0), sub(60, 60))).toBeCloseTo(
      (Math.acos(Math.sin((60 * Math.PI) / 180) ** 2 + Math.cos((60 * Math.PI) / 180) ** 2 * 0.5) * 180) / Math.PI,
      9,
    );
  });

  it('altitude is 90 minus distance to the sub-solar point', () => {
    expect(sunAltitudeDeg(sub(0, 0), sub(0, 0))).toBeCloseTo(90, 9);
    expect(sunAltitudeDeg(sub(0, 0), sub(0, 180))).toBeCloseTo(-90, 9);
    expect(sunAltitudeDeg(sub(10, 20), sub(20, 20))).toBeCloseTo(80, 9);
    expect(sunAltitudeDeg(sub(-11.1549, 12.3456), sub(-11.1549, 12.3456))).toBeCloseTo(90, 9);
  });

  it('never returns NaN at antipodes and poles', () => {
    const bad = [
      sunAltitudeDeg(sub(90, 0), sub(-90, 0)),
      sunAltitudeDeg(sub(-90, 45), sub(90, -45)),
      sunAltitudeDeg(sub(23.44, -180), sub(-23.44, 180)),
    ];
    for (const value of bad) expect(Number.isNaN(value)).toBe(false);
  });
});

describe('sideOf', () => {
  it('west of the sub-solar meridian is sunrise', () => {
    expect(sideOf(sub(0, 0), sub(0, -1))).toBe('sunrise');
    expect(sideOf(sub(0, 0), sub(0, 1))).toBe('sunset');
    expect(sideOf(sub(0, 100), sub(0, 99))).toBe('sunrise');
    // across the antimeridian: 179 is WEST of -179 (wrapLon(179-(-179)) = -2)
    expect(sideOf(sub(0, -179), sub(0, 179))).toBe('sunrise');
    // the sub-solar meridian itself is sunset by contract (not < 0)
    expect(sideOf(sub(0, 0), sub(0, 0))).toBe('sunset');
  });
});

describe('terminatorPoints properties (40 sub-solar positions)', () => {
  const positions: SubPoint[] = [
    sub(90, 0),
    sub(-90, 0),
    sub(90, 123),
    sub(-90, -77),
    sub(0, 0),
    sub(0, 180),
    sub(0, -180),
    sub(23.44, 0),
    sub(-23.44, 0),
    sub(23.44, 180),
    sub(-23.44, -180),
    sub(66.5, 45),
    sub(-66.5, -45),
    sub(89.9, 10),
    sub(-89.9, 10),
    sub(45, 90),
    sub(-45, -90),
    sub(11.15, 12.35),
    sub(-11.15, -12.35),
    sub(5, 175),
    sub(-5, -175),
    sub(30, -30),
    sub(-30, 30),
    sub(60, 120),
    sub(-60, -120),
    sub(80, -1),
    sub(-80, 1),
    sub(15, 15),
    sub(-15, -15),
    sub(22, 22),
    sub(-22, -22),
    sub(1, 90),
    sub(-1, -90),
    sub(70, 170),
    sub(-70, -170),
    sub(40, -140),
    sub(-40, 140),
    sub(90 - 0.8333, 0),
    sub(-90 + 0.8333, 0),
    sub(0.8333, 180),
  ];

  it.each(positions.map((p) => [p.lat, p.lon]))('sub-solar (%s, %s)', (lat, lon) => {
    const sun = sub(lat as number, lon as number);
    const points = terminatorPoints(sun);
    expect(points).toHaveLength(360);
    let sunrise = 0;
    for (const point of points) {
      expect(Number.isNaN(point.lat)).toBe(false);
      expect(Number.isNaN(point.lon)).toBe(false);
      expect(point.lat).toBeGreaterThanOrEqual(-90);
      expect(point.lat).toBeLessThanOrEqual(90);
      expect(point.lon).toBeGreaterThanOrEqual(-180);
      expect(point.lon).toBeLessThan(180);
      expect(Math.abs(sunAltitudeDeg(sun, point) - SUNRISE_ALTITUDE_DEG)).toBeLessThan(1e-9);
      if (point.side === 'sunrise') sunrise += 1;
      // the tag must agree with sideOf itself
      expect(point.side).toBe(sideOf(sun, point));
    }
    expect(Math.abs(sunrise - 180)).toBeLessThanOrEqual(2);
  });

  it('loop is closed: first-to-last spacing matches neighbour spacing', () => {
    const sun = sub(11.15, 12.35);
    const points = terminatorPoints(sun);
    const gaps: number[] = [];
    for (let i = 0; i < points.length; i += 1) {
      const a = points[i];
      const b = points[(i + 1) % points.length];
      gaps.push(angularDistanceDeg(sub(a.lat, a.lon), sub(b.lat, b.lon)));
    }
    const max = Math.max(...gaps);
    const min = Math.min(...gaps);
    expect(min).toBeGreaterThan(0);
    expect(max / min).toBeLessThan(1.5);
  });

  it('sideOf one degree west of the sub-solar meridian on the equator is sunrise', () => {
    for (const lon of [0, 45, 179, -179, -1, 90, -90]) {
      expect(sideOf(sub(0, lon), sub(0, lon - 1))).toBe('sunrise');
    }
  });

  it('custom altitude and segment count are honoured', () => {
    const sun = sub(20, -40);
    const points = terminatorPoints(sun, 10, 24);
    expect(points).toHaveLength(24);
    for (const point of points) {
      expect(Math.abs(sunAltitudeDeg(sun, point) - 10)).toBeLessThan(1e-9);
    }
  });
});

describe('decodeLand', () => {
  const valid = {
    v: 1,
    kind: 'land',
    decimals: 2,
    polys: [
      { o: [0, 0, 1000, 0, 1000, 1000, 0, 1000], h: [] },
      { o: [-500, -500, 500, -500, 0, 500], h: [[-100, -100, 100, -100, 0, 100]] },
    ],
  };

  it('decodes a valid payload and scales integers to degrees', () => {
    const land = decodeLand(valid);
    expect(land.decimals).toBe(2);
    const rings = landRings(land);
    expect(rings).toHaveLength(3); // two outer rings plus one hole
    expect(rings[0]).toEqual([0, 0, 10, 0, 10, 10, 0, 10]);
  });

  it('rejects malformed payloads', () => {
    expect(() => decodeLand(null)).toThrow();
    expect(() => decodeLand({})).toThrow();
    expect(() => decodeLand({ v: 2, kind: 'land', decimals: 2, polys: [] })).toThrow();
    expect(() => decodeLand({ v: 1, kind: 'coastline', decimals: 2, polys: [] })).toThrow();
    expect(() => decodeLand({ v: 1, kind: 'land', decimals: 2 })).toThrow();
    expect(() => decodeLand({ v: 1, kind: 'land', decimals: 2, polys: [{ o: [1, 2, 3], h: [] }] })).toThrow();
    expect(() => decodeLand({ v: 1, kind: 'land', decimals: 2, polys: [{ o: [1, 'x', 2, 3], h: [] }] })).toThrow();
  });
});

// ---------------------------------------------------------------------------
// Literals copied from docs/notes/earthsky/wave1/oracle/oracle_cases.json
// (row W1-C, generated 2026-10-22; sunrise = Sun centre at -0.8333° via
// NOAA-formula bisection to <1 s). The oracle is NEVER imported: these are
// copies. The sub-solar point at each event instant is derived in-test with
// the same NOAA solar-position formulas the oracle's meta cites
// (hand-derived and shown, independent of the module under test).
// ---------------------------------------------------------------------------

interface CityEvent {
  place: string;
  lat: number;
  lon: number;
  rise: string;
  set: string;
}

const CITY_EVENTS: CityEvent[] = [
  { place: 'Kiritimati', lat: 1.87, lon: -157.4, rise: '2026-03-20T16:33:39Z', set: '2026-03-21T04:40:12Z' },
  { place: 'Kiritimati', lat: 1.87, lon: -157.4, rise: '2026-06-21T16:24:35Z', set: '2026-06-22T04:38:27Z' },
  { place: 'Kiritimati', lat: 1.87, lon: -157.4, rise: '2026-12-21T16:27:21Z', set: '2026-12-22T04:28:23Z' },
  { place: 'Honolulu', lat: 21.31, lon: -157.86, rise: '2026-03-20T16:35:12Z', set: '2026-03-21T04:42:37Z' },
  { place: 'Honolulu', lat: 21.31, lon: -157.86, rise: '2026-06-21T15:50:24Z', set: '2026-06-22T05:16:19Z' },
  { place: 'Honolulu', lat: 21.31, lon: -157.86, rise: '2026-12-21T17:04:36Z', set: '2026-12-22T03:54:50Z' },
  { place: 'San Francisco', lat: 37.77, lon: -122.42, rise: '2026-03-20T14:12:54Z', set: '2026-03-21T02:21:46Z' },
  { place: 'San Francisco', lat: 37.77, lon: -122.42, rise: '2026-06-21T12:48:05Z', set: '2026-06-22T03:35:03Z' },
  { place: 'San Francisco', lat: 37.77, lon: -122.42, rise: '2026-12-21T15:21:28Z', set: '2026-12-22T00:54:21Z' },
  { place: 'Fairbanks', lat: 64.84, lon: -147.72, rise: '2026-03-20T15:50:16Z', set: '2026-03-21T04:07:52Z' },
  { place: 'Fairbanks', lat: 64.84, lon: -147.72, rise: '2026-06-21T10:57:31Z', set: '2026-06-22T08:47:55Z' },
  { place: 'Fairbanks', lat: 64.84, lon: -147.72, rise: '2026-12-21T19:58:26Z', set: '2026-12-21T23:39:51Z' },
  { place: 'Reykjavik', lat: 64.15, lon: -21.94, rise: '2026-03-20T07:28:36Z', set: '2026-03-20T19:43:27Z' },
  { place: 'Reykjavik', lat: 64.15, lon: -21.94, rise: '2026-06-21T02:55:03Z', set: '2026-06-22T00:04:07Z' },
  { place: 'Reykjavik', lat: 64.15, lon: -21.94, rise: '2026-12-21T11:22:22Z', set: '2026-12-21T15:29:20Z' },
  { place: 'London', lat: 51.51, lon: -0.13, rise: '2026-03-20T06:03:24Z', set: '2026-03-20T18:13:33Z' },
  { place: 'London', lat: 51.51, lon: -0.13, rise: '2026-06-21T03:43:04Z', set: '2026-06-21T20:21:37Z' },
  { place: 'London', lat: 51.51, lon: -0.13, rise: '2026-12-21T08:03:45Z', set: '2026-12-21T15:53:24Z' },
  { place: 'Cairo', lat: 30.04, lon: 31.24, rise: '2026-03-20T03:59:09Z', set: '2026-03-20T16:06:21Z' },
  { place: 'Cairo', lat: 30.04, lon: 31.24, rise: '2026-06-21T02:54:21Z', set: '2026-06-21T16:59:20Z' },
  { place: 'Cairo', lat: 30.04, lon: 31.24, rise: '2026-12-21T04:46:42Z', set: '2026-12-21T14:59:24Z' },
  { place: 'Nairobi', lat: -1.29, lon: 36.82, rise: '2026-03-20T03:36:55Z', set: '2026-03-20T15:43:28Z' },
  { place: 'Nairobi', lat: -1.29, lon: 36.82, rise: '2026-06-21T03:33:04Z', set: '2026-06-21T15:35:58Z' },
  { place: 'Nairobi', lat: -1.29, lon: 36.82, rise: '2026-12-21T03:24:44Z', set: '2026-12-21T15:36:44Z' },
  { place: 'Cape Town', lat: -33.92, lon: 18.42, rise: '2026-03-20T04:49:25Z', set: '2026-03-20T16:57:38Z' },
  { place: 'Cape Town', lat: -33.92, lon: 18.42, rise: '2026-06-21T05:51:19Z', set: '2026-06-21T15:44:57Z' },
  { place: 'Cape Town', lat: -33.92, lon: 18.42, rise: '2026-12-21T03:31:49Z', set: '2026-12-21T17:56:53Z' },
  { place: 'Delhi', lat: 28.61, lon: 77.21, rise: '2026-03-20T00:55:26Z', set: '2026-03-20T13:02:20Z' },
  { place: 'Delhi', lat: 28.61, lon: 77.21, rise: '2026-06-20T23:53:53Z', set: '2026-06-21T13:51:59Z' },
  { place: 'Delhi', lat: 28.61, lon: 77.21, rise: '2026-12-21T01:39:28Z', set: '2026-12-21T11:58:45Z' },
  { place: 'Bangkok', lat: 13.76, lon: 100.5, rise: '2026-03-19T23:22:25Z', set: '2026-03-20T11:28:50Z' },
  { place: 'Bangkok', lat: 13.76, lon: 100.5, rise: '2026-06-20T22:51:34Z', set: '2026-06-21T11:47:57Z' },
  { place: 'Bangkok', lat: 13.76, lon: 100.5, rise: '2026-12-20T23:36:25Z', set: '2026-12-21T10:55:26Z' },
  { place: 'Tokyo', lat: 35.68, lon: 139.69, rise: '2026-03-19T20:45:37Z', set: '2026-03-20T08:52:34Z' },
  { place: 'Tokyo', lat: 35.68, lon: 139.69, rise: '2026-06-20T19:25:39Z', set: '2026-06-21T10:00:19Z' },
  { place: 'Tokyo', lat: 35.68, lon: 139.69, rise: '2026-12-20T21:46:51Z', set: '2026-12-21T07:31:21Z' },
  { place: 'Sydney', lat: -33.87, lon: 151.21, rise: '2026-03-19T19:57:58Z', set: '2026-03-20T08:06:57Z' },
  { place: 'Sydney', lat: -33.87, lon: 151.21, rise: '2026-06-20T20:59:57Z', set: '2026-06-21T06:53:50Z' },
  { place: 'Sydney', lat: -33.87, lon: 151.21, rise: '2026-12-20T18:40:37Z', set: '2026-12-21T09:05:25Z' },
  { place: 'Auckland', lat: -36.85, lon: 174.76, rise: '2026-03-19T18:23:27Z', set: '2026-03-20T06:33:03Z' },
  { place: 'Auckland', lat: -36.85, lon: 174.76, rise: '2026-06-20T19:33:41Z', set: '2026-06-21T05:11:40Z' },
  { place: 'Auckland', lat: -36.85, lon: 174.76, rise: '2026-12-20T16:57:59Z', set: '2026-12-21T07:39:35Z' },
  { place: 'Sao Paulo', lat: -23.55, lon: -46.63, rise: '2026-03-20T09:10:13Z', set: '2026-03-20T21:17:18Z' },
  { place: 'Sao Paulo', lat: -23.55, lon: -46.63, rise: '2026-06-21T09:47:52Z', set: '2026-06-21T20:28:53Z' },
  { place: 'Sao Paulo', lat: -23.55, lon: -46.63, rise: '2026-12-21T08:16:54Z', set: '2026-12-21T21:52:24Z' },
];

/**
 * Sub-solar point from the low-order Meeus solar coordinates used by the
 * NOAA Solar Calculator (the source the oracle's meta cites for its
 * sunrise bisection): ecliptic longitude from the mean longitude and mean
 * anomaly, declination and right ascension from the obliquity, subsolar
 * longitude from local apparent solar time = 12 h with EoT = L − RA.
 * Hand-derived; shares nothing with lib/earth.ts (the code under test).
 * Validated in-session against the oracle's own 42 astropy sun positions:
 * worst-case error 0.0103° (the cruder fractional-year Fourier fit measured
 * 0.44° and was discarded).
 */
function noaaSubsolar(instant: string): SubPoint {
  const date = new Date(instant);
  const n = date.getTime() / 86_400_000 + 2440587.5 - 2451545.0; // days since J2000
  const meanLon = (280.46 + 0.9856474 * n) % 360;
  const meanAnom = ((357.528 + 0.9856003 * n) % 360) * (Math.PI / 180);
  const eclLon =
    (meanLon + 1.915 * Math.sin(meanAnom) + 0.02 * Math.sin(2 * meanAnom)) *
    (Math.PI / 180);
  const obliquity = (23.439 - 0.0000004 * n) * (Math.PI / 180);
  const decl = Math.asin(Math.sin(obliquity) * Math.sin(eclLon)) * (180 / Math.PI);
  const raDeg =
    (Math.atan2(Math.cos(obliquity) * Math.sin(eclLon), Math.cos(eclLon)) * 180) /
    Math.PI;
  const ra = (raDeg + 360) % 360;
  let eqTimeDeg = (meanLon - ra + 360) % 360;
  if (eqTimeDeg > 180) eqTimeDeg -= 360;
  const hours =
    date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600;
  const subsolarLon = -15 * (hours - 12) - eqTimeDeg;
  return { lat: decl, lon: wrapLon(subsolarLon) };
}

describe('oracle city sunrise/sunset literals (45 events)', () => {
  // Contract addendum 2026-10-22: these oracle rows are defined at the
  // TEXTBOOK -0.8333° (not the app's -0.8793° default), so the comparison
  // altitude is the explicit literal below. Tolerance 0.02° (lead correction).
  const EVENT_ALTITUDE_DEG = -0.8333;
  const ALTITUDE_TOLERANCE_DEG = 0.02;

  it.each(CITY_EVENTS.map((e, i) => [e.place, i] as const))(
    '%s event %d (rise): altitude ≈ -0.8333° and side agrees',
    (_place, i) => {
      const event = CITY_EVENTS[i];
      const sun = noaaSubsolar(event.rise);
      const city = sub(event.lat, event.lon);
      expect(Math.abs(sunAltitudeDeg(sun, city) - EVENT_ALTITUDE_DEG)).toBeLessThanOrEqual(
        ALTITUDE_TOLERANCE_DEG,
      );
      expect(sideOf(sun, city)).toBe('sunrise');
    },
  );

  it.each(CITY_EVENTS.map((e, i) => [e.place, i] as const))(
    '%s event %d (set): altitude ≈ -0.8333° and side agrees',
    (_place, i) => {
      const event = CITY_EVENTS[i];
      const sun = noaaSubsolar(event.set);
      const city = sub(event.lat, event.lon);
      expect(Math.abs(sunAltitudeDeg(sun, city) - EVENT_ALTITUDE_DEG)).toBeLessThanOrEqual(
        ALTITUDE_TOLERANCE_DEG,
      );
      expect(sideOf(sun, city)).toBe('sunset');
    },
  );
});

/** Recording stub: captures the 2D-context calls paintLand makes. */
class RecordingContext {
  fillStyle = '';
  readonly calls: Array<{ op: string; args: number[] | string[] }> = [];
  private rec(op: string, ...args: number[] | string[]): void {
    this.calls.push({ op, args });
  }
  fillRect(x: number, y: number, w: number, h: number): void {
    this.rec('fillRect', x, y, w, h);
  }
  beginPath(): void {
    this.rec('beginPath');
  }
  moveTo(x: number, y: number): void {
    this.rec('moveTo', x, y);
  }
  lineTo(x: number, y: number): void {
    this.rec('lineTo', x, y);
  }
  closePath(): void {
    this.rec('closePath');
  }
  fill(rule: string): void {
    this.rec('fill', rule);
  }
}

const WIDTH = 360;
const HEIGHT = 180;

function recordedPaint(land: LandData) {
  const ctx = new RecordingContext();
  paintLand(ctx as unknown as CanvasRenderingContext2D, land, WIDTH, HEIGHT, { ocean: '#000022', land: '#22cc66' });
  return ctx;
}

describe('paintLand against the real data shape', () => {
  // The full data assertions live in earth-data.test.ts; here we exercise the
  // painter with the real file through the same decode path.
  let land: LandData;
  beforeAll(async () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const raw = await import('../data/land-50m.json');
    land = decodeLand(raw.default ?? raw);
  });

  it('paints the ocean first, then one even-odd fill', () => {
    const ctx = recordedPaint(land);
    expect(ctx.calls[0]).toEqual({ op: 'fillRect', args: [0, 0, WIDTH, HEIGHT] });
    const fills = ctx.calls.filter((c) => c.op === 'fill');
    expect(fills).toHaveLength(1);
    expect(fills[0].args).toEqual(['evenodd']);
  });

  it('opens exactly 1,422 sub-paths (1,421 outer rings plus 1 hole) and closes them all', () => {
    const ctx = recordedPaint(land);
    const moveTos = ctx.calls.filter((c) => c.op === 'moveTo');
    const closePaths = ctx.calls.filter((c) => c.op === 'closePath');
    expect(moveTos).toHaveLength(1422);
    expect(closePaths).toHaveLength(1422);
  });

  it('never emits NaN and never crosses more than 180 degrees of longitude in one step', () => {
    const ctx = recordedPaint(land);
    let previous: { x: number; y: number } | null = null;
    let maxLonStep = 0;
    let reachedBottom = false;
    for (const call of ctx.calls) {
      if (call.op !== 'moveTo' && call.op !== 'lineTo') continue;
      const [x, y] = call.args as number[];
      expect(Number.isNaN(x)).toBe(false);
      expect(Number.isNaN(y)).toBe(false);
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(WIDTH);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(HEIGHT);
      if (y >= HEIGHT - 0.5) reachedBottom = true;
      if (previous && call.op === 'lineTo') {
        const lonStep = (Math.abs(x - previous.x) / WIDTH) * 360;
        if (lonStep > maxLonStep) maxLonStep = lonStep;
      }
      previous = { x, y };
    }
    // The Antarctica ring's pole edge is sampled at sub-1.5° steps in this
    // dataset, so even the "pole seam" never jumps 180° in one lineTo.
    expect(maxLonStep).toBeLessThanOrEqual(180);
    expect(reachedBottom).toBe(true);
  });
});
