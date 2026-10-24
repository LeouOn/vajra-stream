/**
 * W2-A tests for frontend/src/lib/sky.ts.
 *
 * Hand-derived literal cases are shown inline (zenith/horizon dome points,
 * the meridian star, Polaris). The oracle literals come from
 * docs/notes/earthsky/wave2/oracle/oracle_stars.json variant B (copied, never
 * imported), with a negative control proving they catch the units bug.
 */

import { describe, expect, it } from 'vitest';
import {
  STAR_LIMIT_V,
  constellationSegments,
  decodeStars,
  domePoint,
  eclipticPoints,
  equatorialToHorizontal,
  gmstDeg,
  julianDay,
  precessJ2000,
  starAlpha,
  starRadiusPx,
  starRgb,
  type ConstellationLines,
  type Star,
} from '../lib/sky';

describe('starAlpha', () => {
  it('treats a non-finite magnitude as invisible instead of propagating NaN', () => {
    // A NaN/Infinity magnitude is not a measurement; returning NaN here would
    // reach ctx.arc/globalAlpha downstream (the canvas rejects it at draw time).
    expect(starAlpha(Number.NaN)).toBe(0);
    expect(starAlpha(Number.POSITIVE_INFINITY)).toBe(0);
  });

  it('is 1 up to V 6.0, strictly decreasing to 0 at 6.5, 0 above', () => {
    expect(STAR_LIMIT_V).toBe(6.5);
    expect(starAlpha(-1.46)).toBe(1);
    expect(starAlpha(6.0)).toBe(1);
    expect(starAlpha(6.25)).toBeCloseTo(0.5, 12);
    expect(starAlpha(6.4999)).toBeGreaterThan(0);
    expect(starAlpha(6.5)).toBe(0);
    expect(starAlpha(7.0)).toBe(0);
    for (let v = 6.0; v < 6.49; v += 0.01) {
      expect(starAlpha(v + 0.01)).toBeLessThan(starAlpha(v));
    }
  });
});

describe('starRadiusPx', () => {
  it('uses the faint floor for a non-finite magnitude (never NaN)', () => {
    expect(starRadiusPx(Number.NaN)).toBe(0.4);
    expect(Number.isFinite(starRadiusPx(Number.NaN))).toBe(true);
  });

  it('is monotone non-increasing and sub-pixel when faint', () => {
    let prev = starRadiusPx(-2);
    for (let v = -1.8; v <= 6.6; v += 0.05) {
      const r = starRadiusPx(v);
      expect(r).toBeLessThanOrEqual(prev + 1e-12);
      prev = r;
    }
    expect(starRadiusPx(6.4)).toBeLessThanOrEqual(0.45);
  });
});

describe('starRgb', () => {
  it('maps B-V blue-white -> white -> yellow -> orange-red, monotone-ish and clamped', () => {
    const blue = starRgb(-0.2);
    const white = starRgb(0.4);
    const yellow = starRgb(0.8);
    const red = starRgb(1.6);
    expect(blue[2]).toBeGreaterThan(blue[0]); // blue channel dominates hot stars
    expect(yellow[0]).toBeGreaterThan(blue[0]);
    expect(red[0]).toBeGreaterThanOrEqual(yellow[0]);
    expect(red[2]).toBeLessThan(yellow[2]); // red stars lose their blue
    expect(starRgb(null)).toEqual([255, 255, 255]);
    for (const bv of [-0.4, 0, 0.5, 1.0, 1.5, 2.0]) {
      const [r, g, b] = starRgb(bv);
      for (const channel of [r, g, b]) {
        expect(channel).toBeGreaterThanOrEqual(0);
        expect(channel).toBeLessThanOrEqual(255);
      }
    }
  });
});

describe('domePoint (hand-derived literals)', () => {
  const cx = 200;
  const cy = 150;
  const radius = 100;

  it('zenith maps to the centre', () => {
    const { x, y } = domePoint(90, 0, radius, cx, cy);
    expect(x).toBeCloseTo(cx, 9);
    expect(y).toBeCloseTo(cy, 9);
  });

  it('horizon north maps to the top (az 0, alt 0)', () => {
    const { x, y } = domePoint(0, 0, radius, cx, cy);
    expect(x).toBeCloseTo(cx, 9); // cx - r*sin(0)
    expect(y).toBeCloseTo(cy - radius, 9); // cy - r*cos(0)
  });

  it('horizon east maps to the LEFT (az 90, alt 0)', () => {
    const { x, y } = domePoint(0, 90, radius, cx, cy);
    expect(x).toBeCloseTo(cx - radius, 9); // cx - r*sin(90)
    expect(y).toBeCloseTo(cy, 9); // cy - r*cos(90)
  });

  it('horizon south to the bottom, horizon west to the right', () => {
    const south = domePoint(0, 180, radius, cx, cy);
    expect(south.x).toBeCloseTo(cx, 9);
    expect(south.y).toBeCloseTo(cy + radius, 9);
    const west = domePoint(0, 270, radius, cx, cy);
    expect(west.x).toBeCloseTo(cx + radius, 9);
    expect(west.y).toBeCloseTo(cy, 9);
  });

  it('45 deg altitude halves the radius', () => {
    const { x, y } = domePoint(45, 0, radius, cx, cy);
    expect(y).toBeCloseTo(cy - radius / 2, 9);
    expect(x).toBeCloseTo(cx, 9);
  });
});

describe('precession (IAU 1976)', () => {
  it('is the identity at J2000', () => {
    for (const [ra, dec] of [[0, 0], [101.287, -16.716], [279.234, 38.784], [37.95, 89.264]]) {
      const out = precessJ2000(ra, dec, 2451545.0);
      expect(out.ra).toBeCloseTo(ra, 9);
      expect(out.dec).toBeCloseTo(dec, 9);
    }
  });

  it('is stable (deterministic) and moves Polaris measurably by 2100', () => {
    const jd2100 = 2451545.0 + 75 * 365.25;
    const fwd = precessJ2000(37.95, 89.264, jd2100);
    expect(precessJ2000(37.95, 89.264, jd2100)).toEqual(fwd);
    // A ~75-year precession shifts a mid-sky star by a few tenths of a
    // degree and keeps Polaris within ~2 deg of the pole.
    expect(Math.abs(fwd.ra - 37.95)).toBeGreaterThan(0.05);
    expect(fwd.dec).toBeGreaterThan(89.264 - 2.0);
    expect(fwd.dec).toBeLessThan(90.0001);
  });
});

describe('gmstDeg (IAU 1982)', () => {
  it('matches a hand-checked value at J2000.0 noon', () => {
    // 2000-01-01T12:00:00Z is JD 2451545.0; GMST(UT) there is
    // 18h 41m 50.548s = 280.460618... deg (well-known constant).
    expect(gmstDeg(2451545.0)).toBeCloseTo(280.46062, 4);
  });

  it('advances ~360.9856 deg per solar day', () => {
    const g0 = gmstDeg(2451545.0);
    const g1 = gmstDeg(2451545.0 + 1);
    expect(((g1 - g0) % 360)).toBeCloseTo(0.9856, 3);
  });
});


describe('gmstDeg against the oracle (IAU 1982)', () => {
  // Literals from docs/notes/earthsky/wave2/oracle/oracle_stars.json
  // (sha256 1670d52b14ff35db25f311ba192c1a8adad75e3a80ad466728b73f9bafb565d1),
  // field gmst_deg: one value per instant. Copied, never imported.
  //
  // Tolerance: 0.002 deg for 2026/2199, where the oracle's UT1 vs UTC
  // agreement is ~0.0002-0.0007 deg and the old T^4 typo shows up as 0.0054
  // deg at 2199. 0.004 deg for 1800/1900: delta-T (UT1-UTC) ambiguity there is
  // ~0.0035 deg for BOTH the old and the corrected polynomial, so a tighter
  // bar would test the oracle, not this code.
  const CASES: Array<[string, number, number]> = [
    ['1800-01-01T00:00:00Z', 100.40406, 0.004],
    ['1900-06-15T12:00:00Z', 83.31187, 0.004],
    ['2026-01-01T00:00:00Z', 100.66115, 0.002],
    ['2026-03-20T14:46:00Z', 39.64802, 0.002],
    ['2026-06-21T08:24:00Z', 35.55157, 0.002],
    ['2026-07-15T12:00:00Z', 113.35495, 0.002],
    ['2026-09-23T00:05:00Z', 3.11076, 0.002],
    ['2026-10-22T02:00:00Z', 60.52311, 0.002],
    ['2026-12-21T20:50:00Z', 42.93514, 0.002],
    ['2199-12-31T23:59:00Z', 100.27242, 0.002],
  ];

  it('has all 10 oracle instants with a spread of dates', () => {
    expect(CASES).toHaveLength(10);
    expect(new Set(CASES.map((c) => c[0])).size).toBe(10);
  });

  it('matches every oracle instant within its tolerance', () => {
    for (const [instant, expected, tolerance] of CASES) {
      const jd = julianDay(new Date(instant));
      const got = gmstDeg(jd);
      const diff = Math.abs((((got - expected) % 360) + 540) % 360 - 180);
      expect(diff, `${instant}: ${got} vs ${expected}`).toBeLessThan(tolerance);
    }
  });
});

describe('equatorialToHorizontal (hand-derived)', () => {
  const SF_LAT = 37.7749;

  it('Polaris altitude is within 1 deg of the latitude', () => {
    for (const lst of [0, 45, 100, 200, 300]) {
      const { alt } = equatorialToHorizontal(37.954, 89.264, lst, SF_LAT);
      expect(Math.abs(alt - SF_LAT)).toBeLessThanOrEqual(1.0);
    }
  });

  it('a star on the meridian (H=0) sits due south (az 180) at the derived altitude', () => {
    // LST == RA: hour angle 0. Star dec 20 deg at latitude 37.7749:
    // alt = 90 - |lat - dec| = 72.2251 deg; az = 180 (south of zenith).
    const { alt, az } = equatorialToHorizontal(150.0, 20.0, 150.0, SF_LAT);
    expect(alt).toBeCloseTo(90 - Math.abs(SF_LAT - 20.0), 6);
    expect(az).toBeCloseTo(180, 6);
  });

  it('a star north of zenith on the meridian has az 0', () => {
    // dec 50 deg > latitude 37.77: still on the meridian, but north.
    const { alt, az } = equatorialToHorizontal(150.0, 50.0, 150.0, SF_LAT);
    expect(alt).toBeCloseTo(90 - Math.abs(SF_LAT - 50.0), 6);
    expect(az).toBeCloseTo(0, 6);
  });
});

describe('eclipticPoints', () => {
  it('intersects the celestial equator at RA 0 and 180 with dec 0', () => {
    const jd = julianDay(new Date('2026-10-22T00:00:00Z'));
    const points = eclipticPoints(jd, 360);
    const zero = points[0];
    expect(zero.ra).toBeCloseTo(0, 6);
    expect(zero.dec).toBeCloseTo(0, 6);
    const half = points[180];
    expect(half.ra).toBeCloseTo(180, 6);
    expect(half.dec).toBeCloseTo(0, 6);
  });

  it('peaks at declination ~ the obliquity at RA 90', () => {
    const jd = julianDay(new Date('2026-10-22T00:00:00Z'));
    const points = eclipticPoints(jd, 360);
    expect(points[90].dec).toBeCloseTo(23.436, 1);
  });
});

describe('constellationSegments', () => {
  const lines: ConstellationLines = {
    crosswalk: 'test',
    tolerance_arcsec: 180,
    constellations: {
      Ori: [[24436, 2712, 26311], [99999, 1713]],
      And: [[3094]],
    },
  };
  const stars: Star[] = [
    { hr: 3094, ra: 2.1, dec: 42.3, v: 2.1, bv: null },
    { hr: 2712, ra: 88.8, dec: 7.4, v: 0.5, bv: 1.85 },
    { hr: 24436, ra: 81.3, dec: -0.3, v: 1.7, bv: -0.2 },
    { hr: 26311, ra: 84.0, dec: -1.2, v: 0.2, bv: -0.6 },
    { hr: 1713, ra: 85.2, dec: -1.9, v: 1.7, bv: -0.1 },
  ];

  it('resolves polylines, drops and counts unresolved HR ids, keeps only >=2-star polylines', () => {
    const groups = constellationSegments(lines, new Map(stars.map((s) => [s.hr, s] as const)));
    const byName = new Map(groups.map((g) => [g.name, g]));
    expect(byName.get('And')!.polylines).toHaveLength(0); // 1-vertex polyline dropped
    const ori = byName.get('Ori')!;
    expect(ori.polylines).toHaveLength(1); // [99999, 1713] reduces to 1 star -> dropped
    expect(ori.polylines[0]).toHaveLength(3);
    expect(ori.droppedHr).toBe(1); // HR 99999 unresolved
    expect(groups.map((g) => g.name)).toEqual(['And', 'Ori']); // sorted
  });
});

describe('decodeStars', () => {
  it('rejects malformed rows', () => {
    expect(() => decodeStars(null)).toThrow(TypeError);
    expect(() => decodeStars([[1, 2, 3]])).toThrow(TypeError); // too short
    expect(() => decodeStars([['x', 1, 2, 3, null]])).toThrow(TypeError);
    expect(() => decodeStars([[1, 1, 1, 1, 'bad']])).toThrow(TypeError);
    expect(() => decodeStars([[1.5, 1, 1, 1, null]])).toThrow(TypeError); // non-integer hr
  });

  it('rejects the dev-check-g probe row (values out of range on every field)', () => {
    // Confirmed probe: this used to decode happily though nothing in the row
    // is a real sky position or magnitude.
    expect(() => decodeStars([[1, -5, 200, -100, null]])).toThrow(TypeError);
  });

  it('range-checks RA [0, 360), Dec [-90, 90] and V [-2, 6.5], naming the field', () => {
    const bad: Array<[Array<number | null>, string]> = [
      [[1, -0.001, 0, 3, null], 'ra'],
      [[1, 360, 0, 3, null], 'ra'],
      [[1, Number.NaN, 0, 3, null], 'ra'],
      [[1, 0, -90.001, 3, null], 'dec'],
      [[1, 0, 90.001, 3, null], 'dec'],
      [[1, 0, Number.POSITIVE_INFINITY, 3, null], 'dec'],
      [[1, 0, 0, -2.01, null], 'v'],
      [[1, 0, 0, 6.51, null], 'v'],
      [[1, 0, 0, Number.NaN, null], 'v'],
    ];
    for (const [row, field] of bad) {
      for (const index of [0, 3]) {
        const filler = [1, 0, 0, 3, null];
        const payload = index === 0 ? [row] : [filler, filler, filler, row];
        expect(() => decodeStars(payload), `${field} @ ${index}: ${row.join(',')}`).toThrow(
          new RegExp(`stars\\[${index}\\].*${field}`),
        );
      }
    }
  });

  it('rejects a non-finite B-V (null stays the missing-B-V sentinel)', () => {
    expect(() => decodeStars([[1, 0, 0, 3, Number.NaN]])).toThrow(TypeError);
    expect(() => decodeStars([[1, 0, 0, 3, Number.POSITIVE_INFINITY]])).toThrow(TypeError);
    expect(decodeStars([[1, 0, 0, 3, null]])[0].bv).toBeNull();
  });

  it('accepts the inclusive boundaries of the shipped catalogue', () => {
    const stars = decodeStars([
      [1, 0, -90, -1.46, null],
      [2, 359.999, 90, 6.5, 3.9],
    ]);
    expect(stars).toHaveLength(2);
    expect(stars[0]).toEqual({ hr: 1, ra: 0, dec: -90, v: -1.46, bv: null });
    expect(stars[1].ra).toBe(359.999);
  });
});

// ---------------------------------------------------------------------------
// Oracle literals: docs/notes/earthsky/wave2/oracle/oracle_stars.json
// sha256 1670d52b14ff35db25f311ba192c1a8adad75e3a80ad466728b73f9bafb565d1
// (row W2-C, astropy; variant B = precession-only, the client's model).
// Copied as literals on 2026-10-24; never imported.
// ---------------------------------------------------------------------------

const RAD = Math.PI / 180;

const ORACLE_STARS: { hr: number; name: string; ra: number; dec: number }[] = [
  { hr: 2491, name: 'Sirius', ra: 101.28708, dec: -16.71611 },
  { hr: 2326, name: 'Canopus', ra: 95.98792, dec: -52.69583 },
  { hr: 5340, name: 'Arcturus', ra: 213.91542, dec: 19.1825 },
  { hr: 7001, name: 'Vega', ra: 279.23458, dec: 38.78361 },
  { hr: 1708, name: 'Capella', ra: 79.1725, dec: 45.99806 },
  { hr: 1713, name: 'Rigel', ra: 78.63458, dec: -8.20167 },
  { hr: 2943, name: 'Procyon', ra: 114.82542, dec: 5.225 },
  { hr: 472, name: 'Achernar', ra: 24.42875, dec: -57.23667 },
  { hr: 2061, name: 'Betelgeuse', ra: 88.79292, dec: 7.40694 },
  { hr: 5459, name: 'Rigil', ra: 219.89958, dec: -60.83528 },
  { hr: 424, name: 'Polaris', ra: 37.95292, dec: 89.26417 },
  { hr: 361, name: 'Revati', ra: 18.43292, dec: 7.57528 },
  { hr: 6134, name: 'Antares', ra: 247.35167, dec: -26.43194 },
  { hr: 5056, name: 'Spica', ra: 201.29833, dec: -11.16139 },
  { hr: 681, name: 'Mira', ra: 34.83625, dec: -2.9775 },
];

// One place per instant (10 instants, 10 distinct places: polar north
// Tromso, polar south McMurdo, and southern sites Sydney/Cape Town), all 15
// named stars per place. Expected alt/az are variant B literals.
const ORACLE_CASES: { instant: string; place: string; lat: number; lst: number; stars: [number, number, number][] }[] = [
  { instant: '1800-01-01T00:00:00Z', place: 'Tromso', lat: 69.65, lst: 119.361888, stars: [
    [2491, 2.6412, 199.4571],
    [2326, -33.5364, 197.58],
    [5340, 18.0549, 80.7068],
    [7001, 19.448, 17.9251],
    [1708, 57.8395, 245.2914],
    [1713, 6.5095, 222.8922],
    [2943, 25.8455, 187.9599],
    [472, -54.9827, 245.5593],
    [2061, 24.105, 216.5916],
    [5459, -56.3201, 116.2999],
    [424, 69.0942, 355.2591],
    [361, 1.46, 284.9193],
    [6134, -36.1321, 65.862],
    [5056, -5.8036, 103.5077],
    [681, -2.6366, 265.8762],
  ] },
  { instant: '1900-06-15T12:00:00Z', place: 'Sydney', lat: -33.87, lst: 234.526003, stars: [
    [2491, -23.382, 228.2906],
    [2326, 3.5664, 203.463],
    [5340, 32.6014, 335.4952],
    [7001, 6.8164, 33.0075],
    [1708, -68.8898, 311.4705],
    [1713, -42.5428, 211.5242],
    [2943, -28.6159, 256.3584],
    [472, 5.2512, 163.9668],
    [2061, -49.7175, 236.4679],
    [5459, 61.3709, 197.0438],
    [424, -34.8843, 0.8295],
    [361, -46.3101, 119.2559],
    [6134, 77.592, 54.893],
    [5056, 50.8146, 298.1238],
    [681, -47.7855, 147.9186],
  ] },
  { instant: '2026-01-01T00:00:00Z', place: 'San Francisco', lat: 37.7749, lst: 338.243133, stars: [
    [2491, -36.3292, 83.2554],
    [2326, -45.3442, 130.3716],
    [5340, -12.5883, 306.6151],
    [7001, 44.6729, 290.4113],
    [1708, 19.4054, 46.1884],
    [1713, -13.4389, 89.9856],
    [2943, -31.3268, 52.7717],
    [472, -12.6178, 156.2214],
    [2061, -11.5747, 71.0184],
    [5459, -45.6233, 217.8792],
    [424, 38.0058, 0.7405],
    [361, 42.6528, 118.8879],
    [6134, -16.2168, 248.7625],
    [5056, -43.0922, 292.6847],
    [681, 23.5974, 114.0415],
  ] },
  { instant: '2026-03-20T14:46:00Z', place: 'McMurdo', lat: -77.85, lst: 206.319608, stars: [
    [2491, 13.3195, 252.1166],
    [2326, 47.2034, 236.8191],
    [5340, -7.0207, 7.5242],
    [7001, -34.408, 64.6747],
    [1708, -52.2586, 245.4989],
    [1713, 0.7182, 231.8805],
    [2943, -5.2886, 269.9692],
    [472, 44.9578, 178.7345],
    [2061, -12.7903, 244.7775],
    [5459, 72.5015, 23.1439],
    [424, -78.4368, 358.9178],
    [361, -19.7536, 172.0538],
    [6134, 35.2569, 46.4984],
    [5056, 23.4043, 355.004],
    [681, -9.1468, 188.9519],
  ] },
  { instant: '2026-06-21T08:24:00Z', place: 'Reykjavik', lat: 64.15, lst: 13.613557, stars: [
    [2491, -14.1519, 99.2678],
    [2326, -42.9691, 124.8242],
    [5340, -5.2695, 340.4788],
    [7001, 32.6407, 292.6356],
    [1708, 50.4025, 84.5894],
    [1713, 2.9887, 115.7379],
    [2943, -0.3474, 77.3557],
    [472, -31.5479, 172.9776],
    [2061, 12.9465, 99.8456],
    [5459, -77.3439, 272.3361],
    [424, 64.6732, 0.7983],
    [361, 33.4444, 173.8629],
    [6134, -39.0476, 290.9214],
    [5056, -36.8474, 350.1379],
    [681, 21.11, 156.8351],
  ] },
  { instant: '2026-07-15T12:00:00Z', place: 'Quito', lat: -0.18, lst: 34.887294, stars: [
    [2491, 22.3171, 108.0689],
    [2326, 17.0925, 146.2425],
    [5340, -71.1087, 1.9287],
    [7001, -19.6689, 311.6378],
    [1708, 29.382, 34.1417],
    [1713, 45.3717, 101.4892],
    [2943, 9.6535, 84.7323],
    [472, 32.4911, 186.5564],
    [2061, 35.363, 80.7717],
    [5459, -28.7244, 183.0552],
    [424, 0.4331, 0.1278],
    [361, 72.1041, 296.527],
    [6134, -48.6173, 227.2937],
    [5056, -72.5425, 131.5356],
    [681, 87.3084, 173.9351],
  ] },
  { instant: '2026-09-23T00:05:00Z', place: 'Cape Town', lat: -33.92, lst: 21.533044, stars: [
    [2491, 17.3405, 98.8454],
    [2326, 35.2711, 134.3229],
    [5340, -71.3295, 220.4587],
    [7001, -29.0116, 299.3841],
    [1708, -5.5895, 36.335],
    [1713, 31.4392, 77.8587],
    [2943, -5.8992, 87.7352],
    [472, 66.7202, 175.6796],
    [2061, 13.9648, 70.8907],
    [5459, 6.117, 189.0932],
    [424, -33.3536, 0.3189],
    [361, 48.282, 355.9011],
    [6134, -15.3602, 222.0865],
    [5056, -44.78, 180.1638],
    [681, 56.4298, 25.2128],
  ] },
  { instant: '2026-10-22T02:00:00Z', place: 'Delhi', lat: 28.61, lst: 137.735177, stars: [
    [2491, 32.7426, 222.1886],
    [2326, 0.9604, 203.7202],
    [5340, 20.4961, 78.8603],
    [7001, -13.7068, 29.792],
    [1708, 41.8367, 307.7296],
    [1713, 22.4805, 246.3619],
    [2943, 58.2716, 226.5837],
    [472, -36.0734, 218.1933],
    [2061, 39.6209, 254.879],
    [5459, -21.3641, 148.8578],
    [424, 28.5976, 359.2879],
    [361, -20.9057, 291.8437],
    [6134, -28.8608, 106.2302],
    [5056, 16.5391, 113.2541],
    [681, -12.3876, 273.5377],
  ] },
  { instant: '2026-12-21T20:50:00Z', place: 'Tokyo', lat: 35.68, lst: 182.627621, stars: [
    [2491, -2.688, 251.2529],
    [2326, -25.716, 222.157],
    [5340, 57.6018, 112.4132],
    [7001, 16.8712, 53.951],
    [1708, 17.0547, 314.9451],
    [1713, -15.8376, 271.2483],
    [2943, 21.2715, 260.753],
    [472, -63.982, 207.7016],
    [2061, 1.5168, 278.0367],
    [5459, -11.4311, 162.3275],
    [424, 35.2311, 359.4668],
    [361, -44.0121, 337.4541],
    [6134, 2.608, 125.6181],
    [5056, 39.6964, 155.4497],
    [681, -45.4708, 309.9798],
  ] },
  { instant: '2199-12-31T23:59:00Z', place: 'Kiritimati', lat: 1.87, lst: 302.875243, stars: [
    [2491, -65.7161, 129.577],
    [2326, -34.7404, 161.3491],
    [5340, 3.8018, 288.1928],
    [7001, 47.8271, 334.3409],
    [1708, -30.4432, 31.0832],
    [1713, -47.9008, 99.887],
    [2943, -81.4726, 39.2244],
    [472, 2.1097, 146.4594],
    [2061, -57.3534, 73.1438],
    [5459, 3.5157, 207.8325],
    [424, 1.1891, 359.7814],
    [361, 11.9695, 81.5805],
    [6134, 31.9345, 236.46],
    [5056, -9.1167, 257.9535],
    [681, -4.5586, 91.9368],
  ] },
];

/** Wrap-aware absolute difference of two azimuths in degrees. */
const azDiff = (a: number, b: number): number => Math.abs((((a - b) % 360) + 540) % 360 - 180);

const ORACLE_TOLERANCE_DEG = 0.05;

describe('oracle star literals (variant B, 0.05 deg)', () => {
  it('has the intended coverage: 10 instants, 10 places, 15 named stars', () => {
    expect(ORACLE_CASES).toHaveLength(10);
    expect(new Set(ORACLE_CASES.map((c) => c.instant)).size).toBe(10);
    expect(new Set(ORACLE_CASES.map((c) => c.place)).size).toBe(10);
    expect(ORACLE_STARS).toHaveLength(15);
    // The far ends of the contract's 1800-2200 range must be present.
    expect(ORACLE_CASES.map((c) => c.instant)).toContain('1800-01-01T00:00:00Z');
    expect(ORACLE_CASES.map((c) => c.instant)).toContain('2199-12-31T23:59:00Z');
    // A polar site (both hemispheres) and the faint mansion star are included.
    expect(ORACLE_CASES.map((c) => c.place)).toEqual(
      expect.arrayContaining(['Tromso', 'McMurdo']),
    );
    expect(ORACLE_STARS.map((s) => s.hr)).toContain(361); // Revati, V 5.24
    expect(ORACLE_STARS.map((s) => s.hr)).toContain(424); // Polaris
  });

  it('sky.ts matches every literal within 0.05 deg in altitude and azimuth', () => {
    const byHr = new Map(ORACLE_STARS.map((s) => [s.hr, s] as const));
    let worstAlt = 0;
    let worstAz = 0;
    let worstCase = '';
    for (const c of ORACLE_CASES) {
      const jd = julianDay(new Date(c.instant));
      for (const [hr, altExpected, azExpected] of c.stars) {
        const star = byHr.get(hr);
        expect(star, `HR ${hr}`).toBeDefined();
        const precessed = precessJ2000(star!.ra, star!.dec, jd);
        const { alt, az } = equatorialToHorizontal(precessed.ra, precessed.dec, c.lst, c.lat);
        const dAlt = Math.abs(alt - altExpected);
        const dAz = azDiff(az, azExpected);
        if (dAlt > worstAlt) worstAlt = dAlt;
        if (dAz > worstAz) worstAz = dAz;
        worstCase = `${c.instant} ${c.place} ${star!.name}`;
        expect(dAlt, `${worstCase} alt ${alt} vs ${altExpected}`).toBeLessThan(
          ORACLE_TOLERANCE_DEG,
        );
        expect(dAz, `${worstCase} az ${az} vs ${azExpected}`).toBeLessThan(
          ORACLE_TOLERANCE_DEG,
        );
      }
    }
    // Guard against a silently narrowed tolerance: the worst values are tiny
    // (measured 0.00019 deg alt / 0.00077 deg az with the correct units).
    expect(worstAlt).toBeLessThan(0.01);
    expect(worstAz).toBeLessThan(0.01);
  });

  it('negative control: the radians/degrees mix fails this test', () => {
    // The bug this row fixes: zeta and z are arcsec-to-RADIANS values added
    // to RA in DEGREES. Reproduced here so the literals cannot be made to pass
    // by a tolerance that is too loose.
    const J2000 = 2451545.0;
    const precessUnitMix = (ra: number, dec: number, jd: number) => {
      const t = (jd - J2000) / 36525.0;
      const zeta = ((2306.2181 * t + 0.30188 * t * t + 0.017998 * t * t * t) / 3600) * RAD;
      const z = ((2306.2181 * t + 1.09468 * t * t + 0.018203 * t * t * t) / 3600) * RAD;
      const theta = ((2004.3109 * t - 0.42665 * t * t - 0.041833 * t * t * t) / 3600) * RAD;
      const a = (ra + zeta) * RAD;
      const d = dec * RAD;
      const sinDec = Math.sin(d) * Math.cos(theta) + Math.cos(d) * Math.sin(theta) * Math.cos(a);
      const decOut = Math.asin(Math.min(1, Math.max(-1, sinDec)));
      const numerator = Math.cos(d) * Math.sin(a);
      const denominator = Math.cos(theta) * Math.cos(d) * Math.cos(a) - Math.sin(theta) * Math.sin(d);
      const raOut = z + Math.atan2(numerator, denominator) * (180 / Math.PI);
      return { ra: ((raOut % 360) + 360) % 360, dec: decOut * (180 / Math.PI) };
    };

    // Mira at Quito, 2199-12-31T23:59:00Z: variant B expects alt 74.3224,
    // az 97.0662; the unit mix gives about alt 76.82, az 98.31 (>2.5 deg).
    const mira = { ra: 34.83625, dec: -2.9775 };
    const jd = julianDay(new Date('2199-12-31T23:59:00Z'));
    const bad = precessUnitMix(mira.ra, mira.dec, jd);
    const { alt, az } = equatorialToHorizontal(bad.ra, bad.dec, 21.805243, -0.18);
    const dAlt = Math.abs(alt - 74.3224);
    const dAz = azDiff(az, 97.0662);
    expect(Math.max(dAlt, dAz)).toBeGreaterThan(ORACLE_TOLERANCE_DEG);
  });
});
