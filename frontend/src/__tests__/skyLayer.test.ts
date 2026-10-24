/**
 * W2-B skyLayer. Positions below are hand-derived, not copied from the
 * layer. J2000 (jd 2451545.0) makes precessJ2000 the identity.
 *
 * Zenith fixture: lat 45°, dec 45°, ra 0°, lst 0°, hour angle 0.
 * sin(alt) = sin45·sin45 + cos45·cos45·cos0 = 0.5 + 0.5 = 1, so alt = 90°.
 * Azimuth atan2(0, 0) = 0. dome radius term (90-alt)/90 = 0, so the point
 * is the centre (size/2, size/2). size 201 → centre (100.5, 100.5), which
 * is the centre of pixel (100, 100).
 *
 * Horizon fixture: lat 0°, dec 0°, ra 0°, lst 90° (hour angle 90°).
 * sin(alt) = cos90 = 0, so alt = 0. The layer draws only alt > 0.
 *
 * A real-sky count uses the published 8,404-star file. About half are
 * above a mid-latitude horizon. Each paints one to a few pixels (radius
 * ≤ 1.6). On a 401² grid that is 2,000–20,000 lit pixels: fewer means the
 * stamp or the horizon cut dropped stars; more means a fill or a radius bug.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { decodeStars, equatorialToHorizontal, starAlpha, type ConstellationLines, type Star } from '../lib/sky';
import { buildSkyLayer } from '../lib/skyLayer';

const J2000 = 2451545.0;
const EMPTY_LINES: ConstellationLines = {
  crosswalk: 'test',
  tolerance_arcsec: 180,
  constellations: {},
};

function zenithStar(v: number, bv: number | null = null, hr = 1): Star {
  return { hr, ra: 0, dec: 45, v, bv };
}

function layer(stars: readonly Star[], extra: Partial<Parameters<typeof buildSkyLayer>[0]> = {}) {
  return buildSkyLayer({
    stars,
    lines: EMPTY_LINES,
    lstDeg: 0,
    latDeg: 45,
    jd: J2000,
    size: 201,
    showCatalogue: true,
    showFigures: false,
    showEcliptic: false,
    ...extra,
  });
}

function pixel(buf: Uint8ClampedArray, size: number, x: number, y: number): [number, number, number, number] {
  const i = (y * size + x) * 4;
  return [buf[i], buf[i + 1], buf[i + 2], buf[i + 3]];
}

function luma(sample: [number, number, number, number]): number {
  return 0.2126 * sample[0] + 0.7152 * sample[1] + 0.0722 * sample[2];
}

/** Straight-alpha composite over black: what drawImage does with this buffer. */
function shownLuma(sample: [number, number, number, number]): number {
  return luma(sample) * (sample[3] / 255);
}

function litCount(buf: Uint8ClampedArray): number {
  let n = 0;
  for (let i = 3; i < buf.length; i += 4) {
    if (buf[i] > 0) n += 1;
  }
  return n;
}

describe('buildSkyLayer', () => {
  it('writes no pixels for a star below the horizon', () => {
    // Hour angle 90° is the mathematical horizon, but cos(π/2) is a tiny
    // positive in IEEE math, so that fixture sits a hair above alt 0.
    // 91° is unambiguously below. The layer draws only alt > 0.
    const justBelow = equatorialToHorizontal(0, 0, 91, 0);
    expect(justBelow.alt).toBeLessThan(0);
    const painted = layer([{ hr: 9, ra: 0, dec: 0, v: 1, bv: null }], {
      lstDeg: 91,
      latDeg: 0,
    });
    expect(litCount(painted.stars)).toBe(0);

    const below = equatorialToHorizontal(0, -80, 0, 45);
    expect(below.alt).toBeLessThan(0);
    const hidden = layer([{ hr: 8, ra: 0, dec: -80, v: 1, bv: null }]);
    expect(litCount(hidden.stars)).toBe(0);
  });

  it('puts a bright pixel on a V 4 zenith star and paints V 6.4 dimmer than V 5.0', () => {
    const bright = layer([zenithStar(4)]);
    const core = pixel(bright.stars, 201, 100, 100);
    expect(luma(core)).toBeGreaterThan(200);

    const mag5 = shownLuma(pixel(layer([zenithStar(5)]).stars, 201, 100, 100));
    const mag64 = shownLuma(pixel(layer([zenithStar(6.4)]).stars, 201, 100, 100));
    expect(mag5).toBeGreaterThan(200);
    expect(mag64).toBeGreaterThan(0);
    expect(mag64).toBeLessThan(mag5);
  });

  it('never darkens a pixel when stars overlap, in either order', () => {
    const bright: Star = zenithStar(1, null, 1);
    const dim: Star = zenithStar(6.4, 1.6, 2);
    const aloneBright = pixel(layer([bright]).stars, 201, 100, 100);
    const aloneDim = pixel(layer([dim]).stars, 201, 100, 100);
    for (const order of [[bright, dim], [dim, bright]] as const) {
      const mixed = pixel(layer(order).stars, 201, 100, 100);
      for (let channel = 0; channel < 4; channel += 1) {
        expect(mixed[channel]).toBeGreaterThanOrEqual(aloneBright[channel]);
        expect(mixed[channel]).toBeGreaterThanOrEqual(aloneDim[channel]);
      }
    }
  });

  it('supports an optional per-star alpha hook; the default equals sky.ts starAlpha', () => {
    const stars = [zenithStar(4), zenithStar(6.4, null, 2)];
    const byDefault = layer(stars).stars;
    const explicit = layer(stars, { starAlphaFor: (star) => starAlpha(star.v) }).stars;
    expect(Array.from(explicit)).toEqual(Array.from(byDefault));

    const zeroed = layer(stars, { starAlphaFor: () => 0 }).stars;
    expect(Array.from(zeroed).every((value) => value === 0)).toBe(true);

    const half = layer(stars, { starAlphaFor: () => 0.5 }).stars;
    let foundHalf = false;
    for (let i = 3; i < half.length; i += 4) if (half[i] === 128) foundHalf = true;
    expect(foundHalf).toBe(true);
  });

  it('is deterministic for the same input', () => {
    const stars = [zenithStar(3, 0.2, 1), zenithStar(5.5, null, 2)];
    const a = layer(stars);
    const b = layer(stars);
    expect(Array.from(a.stars)).toEqual(Array.from(b.stars));
    expect(a.figures).toEqual(b.figures);
    expect(a.ecliptic).toEqual(b.ecliptic);
  });

  it('skips figure segments that are not entirely above the horizon', () => {
    const lines: ConstellationLines = {
      crosswalk: 'test',
      tolerance_arcsec: 180,
      constellations: { Tst: [[1, 2], [3, 4]] },
    };
    const stars: Star[] = [
      { hr: 1, ra: 0, dec: 45, v: 2, bv: null },
      { hr: 2, ra: 0, dec: -80, v: 2, bv: null },
      { hr: 3, ra: 0, dec: 45, v: 2, bv: null },
      { hr: 4, ra: 0, dec: 20, v: 2, bv: null },
    ];
    const below = equatorialToHorizontal(0, -80, 0, 45);
    const high = equatorialToHorizontal(0, 20, 0, 45);
    expect(below.alt).toBeLessThanOrEqual(0);
    expect(high.alt).toBeGreaterThan(0);
    const painted = layer(stars, { lines, showFigures: true, showCatalogue: false });
    expect(painted.figures).toHaveLength(1);
    expect(painted.figures[0].x1).toBeCloseTo(100.5, 6);
    expect(painted.figures[0].y1).toBeCloseTo(100.5, 6);
  });

  it('keeps ecliptic segments inside the horizon disc', () => {
    const painted = layer([], {
      showEcliptic: true,
      latDeg: 37.7749,
      lstDeg: 298.105777,
    });
    expect(painted.ecliptic.length).toBeGreaterThan(10);
    const radius = 201 * 0.42;
    for (const seg of painted.ecliptic) {
      for (const point of [
        [seg.x1, seg.y1],
        [seg.x2, seg.y2],
      ] as const) {
        expect(Math.hypot(point[0] - 100.5, point[1] - 100.5)).toBeLessThanOrEqual(radius + 1e-6);
      }
    }
  });

  it('lights a plausible number of pixels for the real 8404-star catalogue', () => {
    const raw: unknown = JSON.parse(
      readFileSync(path.resolve(__dirname, '../data/stars-v65.json'), 'utf8'),
    );
    const stars = decodeStars(raw);
    expect(stars).toHaveLength(8404);
    const painted = layer(stars, {
      size: 401,
      latDeg: 37.7749,
      lstDeg: 298.105777,
      jd: Date.parse('2026-10-22T02:00:00Z') / 86_400_000 + 2440587.5,
    });
    const lit = litCount(painted.stars);
    expect(lit).toBeGreaterThanOrEqual(2000);
    expect(lit).toBeLessThanOrEqual(20000);
  });
});
