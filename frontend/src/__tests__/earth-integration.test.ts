/**
 * W1-D1 additions to earth.ts. Literals for the sidereal step are the
 * contract rate 360.9856° per 86400 s. The island counts are the lead's
 * count of 50 m polygons whose longer bounding-box side is under 0.5°.
 */
import { describe, expect, it } from 'vitest';
import { extrapolateSubPoint, loadLand, smallIslandVertices, wrapLon } from '../lib/earth';

const DEG_PER_SEC = 360.9856 / 86400;

describe('extrapolateSubPoint', () => {
  it('returns the same latitude and longitude at 0 seconds', () => {
    expect(extrapolateSubPoint({ lat: 12.5, lon: 20 }, 0)).toEqual({ lat: 12.5, lon: 20 });
  });

  it('moves longitude west at 60 s and at 3600 s and leaves latitude unchanged', () => {
    const at60 = extrapolateSubPoint({ lat: 12.5, lon: 20 }, 60);
    expect(at60.lat).toBe(12.5);
    expect(at60.lon).toBeCloseTo(wrapLon(20 - DEG_PER_SEC * 60), 9);
    expect(at60.lon).toBeCloseTo(19.749315555555555, 9);

    const atHour = extrapolateSubPoint({ lat: 12.5, lon: 20 }, 3600);
    expect(atHour.lat).toBe(12.5);
    expect(atHour.lon).toBeCloseTo(wrapLon(20 - DEG_PER_SEC * 3600), 9);
    expect(atHour.lon).toBeCloseTo(4.958933333333333, 9);
  });

  it('wraps across ±180 when longitude decreases through the antimeridian', () => {
    const wrapped = extrapolateSubPoint({ lat: -4.175, lon: -179.9 }, 60);
    expect(wrapped.lat).toBe(-4.175);
    expect(wrapped.lon).toBeCloseTo(179.84931555555555, 9);
    expect(wrapped.lon).toBeGreaterThan(0);
    expect(wrapped.lon).toBeLessThan(180);
  });
});

describe('smallIslandVertices', () => {
  it('counts 913 polygons and 9152 outline vertices on the committed 50 m land', async () => {
    const land = await loadLand();
    const got = smallIslandVertices(land);
    expect(got.polygonCount).toBe(913);
    expect(got.vertexCount).toBe(9152);
    expect(got.rings).toHaveLength(913);
    const vertices = got.rings.reduce((sum, ring) => sum + ring.length / 2, 0);
    expect(vertices).toBe(9152);
  });
});
