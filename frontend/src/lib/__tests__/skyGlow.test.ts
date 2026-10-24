import { describe, expect, it } from 'vitest';
import { GLOW_WIDTH_DEG, HALO_ALPHA, TWILIGHT_GLOW_ENABLED, twilightGlow } from '../skyGlow';

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
