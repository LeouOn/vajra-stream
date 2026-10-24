/**
 * W4-D1 — daytime sky brightness (pure).
 *
 * The anchors are an APPROXIMATION from standard twilight sightings, not a
 * radiative-transfer model. Literals are hand-derived from the piecewise
 * limits documented in skyBrightness.ts.
 */
import { describe, expect, it } from 'vitest';
import {
  limitingMagnitude,
  skyBackground,
  starAlpha,
} from '../skyBrightness';

const NIGHT = { core: '#0f172a', mid: '#090d16', edge: '#020617' };

describe('limitingMagnitude', () => {
  it('hits the documented anchors and clamps outside them', () => {
    expect(limitingMagnitude(-40)).toBe(6.5);
    expect(limitingMagnitude(-18)).toBe(6.5);
    expect(limitingMagnitude(-12)).toBe(4);
    expect(limitingMagnitude(-6)).toBe(2);
    expect(limitingMagnitude(-3)).toBe(-0.5);
    expect(limitingMagnitude(0)).toBe(-2);
    expect(limitingMagnitude(10)).toBe(-4);
    expect(limitingMagnitude(40)).toBe(-4);
  });

  it('is continuous and never increases as the Sun rises', () => {
    for (let alt = -30; alt <= 20; alt += 0.05) {
      const current = limitingMagnitude(alt);
      const next = limitingMagnitude(alt + 0.05);
      expect(next).toBeLessThanOrEqual(current + 1e-12);
      expect(current - next).toBeLessThan(0.05);
    }
  });
});

describe('starAlpha', () => {
  it('matches the anchor grid for the naked-eye view', () => {
    const cases: [number, [number, number][]][] = [
      [-18, [[-1.5, 1], [0, 1], [1.5, 1], [3, 1], [6, 1], [6.5, 0]]],
      [-12, [[-1.5, 1], [0, 1], [1.5, 1], [3, 1], [3.5, 1], [4, 0], [6, 0]]],
      [-6, [[-1.5, 1], [0, 1], [1.5, 1], [2, 0], [3, 0]]],
      [-3, [[-1.5, 1], [-0.5, 0], [0, 0]]],
      [0, [[-1.5, 0], [0, 0], [1.5, 0]]],
      [10, [[-1.5, 0], [0, 0], [6, 0]]],
      [40, [[-1.5, 0], [0, 0], [6, 0]]],
    ];
    for (const [sunAlt, rows] of cases) {
      for (const [mag, expected] of rows) {
        expect(starAlpha(mag, sunAlt, false), `alt ${sunAlt} mag ${mag}`).toBeCloseTo(expected, 12);
      }
    }
  });

  it('is monotone: never brighter as the Sun rises or the star fades', () => {
    let previous = 2;
    for (let alt = -25; alt <= 15; alt += 0.25) {
      const value = starAlpha(1.5, alt, false);
      expect(value).toBeLessThanOrEqual(previous + 1e-12);
      previous = value;
    }
    previous = 2;
    for (let mag = -2; mag <= 7; mag += 0.05) {
      const value = starAlpha(mag, -6, false);
      expect(value).toBeLessThanOrEqual(previous + 1e-12);
      previous = value;
    }
  });

  it('is continuous in Sun altitude', () => {
    for (const mag of [-1.5, 0, 1.5, 3, 6]) {
      for (let alt = -20; alt <= 12; alt += 0.05) {
        const delta = Math.abs(starAlpha(mag, alt + 0.05, false) - starAlpha(mag, alt, false));
        expect(delta, `mag ${mag} alt ${alt}`).toBeLessThan(0.1);
      }
    }
  });

  it('see-through is a faint floor, never below the real alpha when that is higher', () => {
    const floor = (mag: number) => 0.12 + 0.23 * Math.max(0, Math.min(1, (6.5 - mag) / 8));
    for (const alt of [-20, -12, -6, 0, 40]) {
      for (const mag of [-1.5, 0, 1.5, 3, 6, 6.5]) {
        const normal = starAlpha(mag, alt, false);
        const xray = starAlpha(mag, alt, true);
        expect(xray).toBeCloseTo(Math.max(normal, floor(mag)), 12);
        expect(floor(mag)).toBeGreaterThanOrEqual(0.12 - 1e-12);
        expect(floor(mag)).toBeLessThanOrEqual(0.35 + 1e-12);
        // The floor lifts dim stars only; a bright star keeps its real alpha.
        if (normal < 0.12) expect(xray).toBeGreaterThanOrEqual(0.12 - 1e-12);
      }
    }
    // The floor is brighter for brighter stars and dims toward the limit.
    expect(starAlpha(-1.5, 40, true)).toBeGreaterThan(starAlpha(3, 40, true));
    expect(starAlpha(3, 40, true)).toBeGreaterThan(starAlpha(6.5, 40, true));
  });
});

describe('skyBackground', () => {
  it('is exactly the current night fill at <= -18 deg', () => {
    expect(skyBackground(-18)).toEqual(NIGHT);
    expect(skyBackground(-40)).toEqual(NIGHT);
  });

  it('is a calm day blue by +10 deg and interpolates continuously', () => {
    expect(skyBackground(10)).toEqual({ core: '#3c5573', mid: '#314a66', edge: '#263c52' });
    expect(skyBackground(40)).toEqual(skyBackground(10));
    const channel = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
    for (let alt = -18; alt <= 10; alt += 0.1) {
      const a = skyBackground(alt);
      const b = skyBackground(alt + 0.1);
      for (const key of ['core', 'mid', 'edge'] as const) {
        for (let i = 0; i < 3; i += 1) {
          expect(Math.abs(channel(a[key], i) - channel(b[key], i)), `${key} ${alt}`).toBeLessThanOrEqual(4);
        }
      }
    }
  });
});
