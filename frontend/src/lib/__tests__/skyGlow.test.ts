import { describe, expect, it } from 'vitest';
import {
  GLOW_WIDTH_DEG,
  HALO_ALPHA,
  TWILIGHT_GLOW_ENABLED,
  angularGlowProfile,
  twilightGlow,
} from '../skyGlow';

describe('twilightGlow', () => {
  it('is absent at night and has literal anchors through twilight', () => {
    expect(TWILIGHT_GLOW_ENABLED).toBe(true);
    expect(twilightGlow(-40, 90).kind).toBe('none');
    expect(twilightGlow(-20, 90).kind).toBe('none');

    expect(twilightGlow(-18, 90)).toMatchObject({ kind: 'horizon', alpha: 0, azimuthDeg: 90 });
    expect(twilightGlow(-10, 90).alpha).toBeCloseTo(0.5, 12);
    expect(twilightGlow(-2, 90).alpha).toBe(1);
    expect(twilightGlow(0, 90).alpha).toBe(1);
    expect(twilightGlow(2, 90).alpha).toBe(1);
    expect(twilightGlow(4, 90).alpha).toBeCloseTo(0.5, 12);
    expect(twilightGlow(6, 90)).toMatchObject({ kind: 'horizon', alpha: 0 });
    expect(twilightGlow(10, 90)).toMatchObject({ kind: 'halo', alpha: HALO_ALPHA });
    expect(GLOW_WIDTH_DEG).toBe(70);
  });

  it('keeps a flat plateau to 12 deg, then feathers: literals, symmetry, monotone, 0 at 35', () => {
    // W5-L: the raised cosine over +-35 put almost all its energy in +-15 and
    // made the strongest twilight case too faint. 1 on +-12, then a raised
    // cosine from 12 to 35 (zero slope at both ends).
    expect(angularGlowProfile(0)).toBeCloseTo(1, 12);
    expect(angularGlowProfile(6)).toBeCloseTo(1, 12);
    expect(angularGlowProfile(12)).toBeCloseTo(1, 12);
    expect(angularGlowProfile(20)).toBeCloseTo(0.7300325, 6);
    expect(angularGlowProfile(30)).toBeCloseTo(0.1121444, 6);
    expect(angularGlowProfile(35)).toBe(0);
    expect(angularGlowProfile(40)).toBe(0);
    expect(angularGlowProfile(-6)).toBeCloseTo(1, 12);
    expect(angularGlowProfile(-20)).toBeCloseTo(angularGlowProfile(20), 12);
    expect(angularGlowProfile(-35)).toBe(0);
    let previous = 1;
    for (let offset = 0; offset <= 35; offset += 0.1) {
      const value = angularGlowProfile(offset);
      expect(value).toBeLessThanOrEqual(previous + 1e-12);
      previous = value;
    }
    for (let offset = 0; offset < 35; offset += 0.1) {
      expect(Math.abs(angularGlowProfile(offset + 0.1) - angularGlowProfile(offset))).toBeLessThan(0.02);
    }
  });

  it('is continuous through the twilight band and wraps the azimuth', () => {
    for (let alt = -18; alt < 5.9; alt += 0.05) {
      const a = twilightGlow(alt, 0).alpha;
      const b = twilightGlow(alt + 0.05, 0).alpha;
      expect(Math.abs(b - a)).toBeLessThan(0.02);
    }
    expect(twilightGlow(-5, 370).azimuthDeg).toBe(10);
    expect(twilightGlow(-5, -10).azimuthDeg).toBe(350);
  });
});
