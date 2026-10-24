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
import { moonlightPenaltyMag } from '../moonlight';

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

// ---------------------------------------------------------------------------------------------------------
// W5-B — moonlight. The Moon is an OPTIONAL last argument; without it (or with the Moon at or below the
// horizon) every result must be byte-identical to what this file pinned before W5-B.
// ---------------------------------------------------------------------------------------------------------

// The values skyBrightness.ts returned BEFORE W5-B, captured from the unchanged file (docs/notes/earthsky/wave5/c1/):
// limits per Sun altitude, and starAlpha per (Sun altitude, magnitude); the 'x' rows are the see-through view.
// prettier-ignore
const BEFORE_W5B = {
  alts: [-30, -18, -15, -12, -9, -6, -4.5, -3, -1.5, 0, 2, 5, 10, 20],
  mags: [-1.5, 0, 1.5, 3, 4, 5, 6, 6.5],
  limits: [6.5, 6.5, 5.25, 4, 3, 2, 0.75, -0.5, -1.25, -2, -2.4, -3, -4, -4],
  alphas: {
    '0': [0, 0, 0, 0, 0, 0, 0, 0],
    '2': [0, 0, 0, 0, 0, 0, 0, 0],
    '5': [0, 0, 0, 0, 0, 0, 0, 0],
    '10': [0, 0, 0, 0, 0, 0, 0, 0],
    '20': [0, 0, 0, 0, 0, 0, 0, 0],
    '-30': [1, 1, 1, 1, 1, 1, 1, 0],
    '-30x': [1, 1, 1, 1, 1, 1, 1, 0.12],
    '-18': [1, 1, 1, 1, 1, 1, 1, 0],
    '-18x': [1, 1, 1, 1, 1, 1, 1, 0.12],
    '-15': [1, 1, 1, 1, 1, 0.5, 0, 0],
    '-15x': [1, 1, 1, 1, 1, 0.5, 0.134375, 0.12],
    '-12': [1, 1, 1, 1, 0, 0, 0, 0],
    '-12x': [1, 1, 1, 1, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '-9': [1, 1, 1, 0, 0, 0, 0, 0],
    '-9x': [1, 1, 1, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '-6': [1, 1, 1, 0, 0, 0, 0, 0],
    '-6x': [1, 1, 1, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '-4.5': [1, 1, 0, 0, 0, 0, 0, 0],
    '-4.5x': [1, 1, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '-3': [1, 0, 0, 0, 0, 0, 0, 0],
    '-3x': [1, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '-1.5': [0.5, 0, 0, 0, 0, 0, 0, 0],
    '-1.5x': [0.5, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '0x': [0.35, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '2x': [0.35, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '5x': [0.35, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '10x': [0.35, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
    '20x': [0.35, 0.306875, 0.26375000000000004, 0.22062500000000002, 0.19187500000000002, 0.163125, 0.134375, 0.12],
  } as Record<string, number[]>,
};

const HIGH_FULL = { altDeg: 60, illuminatedFraction: 1 };
const HIGH_QUARTER = { altDeg: 60, illuminatedFraction: 0.5 };
const HIGH_CRESCENT = { altDeg: 60, illuminatedFraction: 0.1 };
/** The see-through floor, as skyBrightness.ts documents it (0.35 at Sirius-class, 0.12 at the catalogue edge). */
const seeThroughFloor = (mag: number) => 0.12 + 0.23 * Math.max(0, Math.min(1, (6.5 - mag) / 8));

describe('W5-B: without a Moon nothing changes (byte-identical)', () => {
  it('limitingMagnitude equals the pre-change values, with the argument absent or undefined', () => {
    BEFORE_W5B.alts.forEach((alt, index) => {
      expect(limitingMagnitude(alt), `alt ${alt}`).toBe(BEFORE_W5B.limits[index]);
      expect(limitingMagnitude(alt, undefined), `alt ${alt}`).toBe(BEFORE_W5B.limits[index]);
    });
  });

  it('starAlpha equals the pre-change values over the whole captured grid, both views, with the argument absent or undefined', () => {
    for (const alt of BEFORE_W5B.alts) {
      BEFORE_W5B.mags.forEach((mag, index) => {
        expect(starAlpha(mag, alt, false), `alt ${alt} mag ${mag}`).toBe(BEFORE_W5B.alphas[`${alt}`][index]);
        expect(starAlpha(mag, alt, false, undefined), `alt ${alt} mag ${mag}`).toBe(BEFORE_W5B.alphas[`${alt}`][index]);
        expect(starAlpha(mag, alt, true), `alt ${alt} mag ${mag} x`).toBe(BEFORE_W5B.alphas[`${alt}x`][index]);
        expect(starAlpha(mag, alt, true, undefined), `alt ${alt} mag ${mag} x`).toBe(BEFORE_W5B.alphas[`${alt}x`][index]);
      });
    }
  });

  it('a Moon at or below the horizon, or a new Moon, changes nothing (Object.is) across a dense grid', () => {
    const moons = [
      { altDeg: -90, illuminatedFraction: 1 },
      { altDeg: -30, illuminatedFraction: 1 },
      { altDeg: -1, illuminatedFraction: 1 },
      { altDeg: -0.001, illuminatedFraction: 1 },
      { altDeg: 0, illuminatedFraction: 1 },
      { altDeg: 60, illuminatedFraction: 0 },
    ];
    for (const moon of moons) {
      for (let sun = -30; sun <= 20; sun += 0.25) {
        expect(Object.is(limitingMagnitude(sun, moon), limitingMagnitude(sun)), `limit sun ${sun} moon ${moon.altDeg}/${moon.illuminatedFraction}`).toBe(true);
        for (let mag = -2; mag <= 7; mag += 0.25) {
          for (const seeThrough of [false, true]) {
            expect(Object.is(starAlpha(mag, sun, seeThrough, moon), starAlpha(mag, sun, seeThrough)), `sun ${sun} mag ${mag}`).toBe(true);
          }
        }
      }
    }
  });
});

describe('W5-B: a Moon above the horizon washes out the faint stars', () => {
  it('a high full Moon in a dark sky: a mag 6 star is gone, a mag 3 star keeps alpha 1, Sirius is unchanged', () => {
    const penalty = moonlightPenaltyMag(60, 1);
    expect(penalty).toBeCloseTo(1.75, 2);
    expect(limitingMagnitude(-30, HIGH_FULL)).toBeCloseTo(6.5 - penalty, 12);
    expect(starAlpha(6, -30, false, HIGH_FULL)).toBe(0);
    expect(starAlpha(6.5, -30, false, HIGH_FULL)).toBe(0);
    expect(starAlpha(5, -30, false, HIGH_FULL)).toBe(0);
    expect(starAlpha(3, -30, false, HIGH_FULL)).toBe(1);
    expect(starAlpha(-1.46, -30, false, HIGH_FULL)).toBe(1); // Sirius
    expect(starAlpha(0.03, -30, false, HIGH_FULL)).toBe(1); // Vega
    // and the old, Moonless sky still shows the mag 6 star at full strength
    expect(starAlpha(6, -30, false)).toBe(1);
    // a star 0.25 mag inside the new limit is half faded (the same 0.5-mag band as everywhere)
    expect(starAlpha(6.5 - penalty - 0.25, -30, false, HIGH_FULL)).toBeCloseTo(0.5, 12);
  });

  it('a high quarter Moon takes ~0.8 mag: a mag 6 star is gone, a mag 5 star survives', () => {
    expect(limitingMagnitude(-30, HIGH_QUARTER)).toBeGreaterThan(5.5);
    expect(limitingMagnitude(-30, HIGH_QUARTER)).toBeLessThan(5.8);
    expect(starAlpha(6, -30, false, HIGH_QUARTER)).toBe(0);
    expect(starAlpha(5, -30, false, HIGH_QUARTER)).toBe(1);
  });

  it('a thin crescent barely matters: the limit falls under 0.2 mag, a mag 5.5 star is untouched, a mag 6 star keeps ~70 %', () => {
    expect(6.5 - limitingMagnitude(-30, HIGH_CRESCENT)).toBeLessThan(0.2);
    expect(starAlpha(5.5, -30, false, HIGH_CRESCENT)).toBe(1);
    expect(starAlpha(6, -30, false, HIGH_CRESCENT)).toBeGreaterThan(0.7);
    expect(starAlpha(6, -30, false, HIGH_CRESCENT)).toBeLessThan(1);
  });

  it('a Moon just above the horizon changes almost nothing (no pop at moonrise)', () => {
    const rising = { altDeg: 0.5, illuminatedFraction: 1 };
    expect(6.5 - limitingMagnitude(-30, rising)).toBeLessThan(0.02);
    expect(Math.abs(starAlpha(6, -30, false, rising) - starAlpha(6, -30, false))).toBeLessThan(0.05);
  });
});

describe('W5-B: moonlight and twilight combine sensibly', () => {
  const penalty = moonlightPenaltyMag(60, 1);

  it('the full penalty applies at astronomical night and fades as twilight already brightens the sky', () => {
    expect(6.5 - limitingMagnitude(-18, HIGH_FULL)).toBeCloseTo(penalty, 12);
    expect(6.5 - limitingMagnitude(-40, HIGH_FULL)).toBeCloseTo(penalty, 12);
    // nautical twilight, Sun-limited limit 4.0: darkness (4 - 2) / (6.5 - 2) of the penalty remains
    expect(4 - limitingMagnitude(-12, HIGH_FULL)).toBeCloseTo((penalty * 2) / 4.5, 12);
    // Sun-limited limit 3.0
    expect(3 - limitingMagnitude(-9, HIGH_FULL)).toBeCloseTo((penalty * 1) / 4.5, 12);
  });

  it('once the Sun-limited limit is 2 (civil twilight) or below, the Moon adds nothing at all', () => {
    for (const sun of [-6, -5, -4.5, -3, -1.5, 0, 2, 10, 40]) {
      expect(Object.is(limitingMagnitude(sun, HIGH_FULL), limitingMagnitude(sun)), `sun ${sun}`).toBe(true);
    }
  });

  it('never makes the sky brighter than the Moonless result, and a brighter Moon never raises the limit', () => {
    for (let sun = -30; sun <= 15; sun += 0.5) {
      const base = limitingMagnitude(sun);
      let previousByFraction = Number.POSITIVE_INFINITY;
      for (let k = 0; k <= 1.0001; k += 0.1) {
        const limit = limitingMagnitude(sun, { altDeg: 50, illuminatedFraction: k });
        expect(limit, `sun ${sun} k ${k}`).toBeLessThanOrEqual(base);
        expect(limit, `sun ${sun} k ${k}`).toBeLessThanOrEqual(previousByFraction + 1e-12);
        previousByFraction = limit;
      }
      let previousByAltitude = Number.POSITIVE_INFINITY;
      for (let alt = -5; alt <= 90; alt += 5) {
        const limit = limitingMagnitude(sun, { altDeg: alt, illuminatedFraction: 1 });
        expect(limit, `sun ${sun} alt ${alt}`).toBeLessThanOrEqual(previousByAltitude + 1e-12);
        previousByAltitude = limit;
      }
    }
  });

  it('star alpha is never higher with a Moon than without, anywhere on the grid', () => {
    for (let sun = -30; sun <= 15; sun += 0.5) {
      for (let mag = -2; mag <= 7; mag += 0.25) {
        expect(starAlpha(mag, sun, false, HIGH_FULL), `sun ${sun} mag ${mag}`).toBeLessThanOrEqual(starAlpha(mag, sun, false) + 1e-12);
      }
    }
  });

  it('stays continuous in the Sun altitude and in the Moon altitude with the Moon up', () => {
    for (let sun = -25; sun <= 5; sun += 0.05) {
      const step = Math.abs(limitingMagnitude(sun + 0.05, HIGH_FULL) - limitingMagnitude(sun, HIGH_FULL));
      expect(step, `sun ${sun}`).toBeLessThan(0.05);
    }
    for (let alt = -5; alt < 90; alt += 0.05) {
      const step = Math.abs(
        limitingMagnitude(-30, { altDeg: alt + 0.05, illuminatedFraction: 1 }) -
          limitingMagnitude(-30, { altDeg: alt, illuminatedFraction: 1 }),
      );
      expect(step, `moon alt ${alt}`).toBeLessThan(0.01);
    }
  });

  it('the see-through floor does not change: it is still the floor under a high full Moon, at any Sun altitude', () => {
    for (const sun of [-30, -18, -12, -6, 0, 40]) {
      for (const mag of [-1.5, 0, 1.5, 3, 4.5, 6, 6.5]) {
        const withMoon = starAlpha(mag, sun, false, HIGH_FULL);
        expect(starAlpha(mag, sun, true, HIGH_FULL), `sun ${sun} mag ${mag}`).toBeCloseTo(Math.max(withMoon, seeThroughFloor(mag)), 12);
      }
    }
    // the faint star the Moon removed comes back at exactly the pre-W5-B floor in the see-through view
    expect(starAlpha(6, -30, false, HIGH_FULL)).toBe(0);
    expect(starAlpha(6, -30, true, HIGH_FULL)).toBe(BEFORE_W5B.alphas['0x'][6]);
    expect(starAlpha(6, -30, true, HIGH_FULL)).toBeCloseTo(seeThroughFloor(6), 12);
    // and by day, where the Moon adds nothing, the x-ray view is the old one exactly
    expect(starAlpha(6, 40, true, HIGH_FULL)).toBe(starAlpha(6, 40, true));
  });
});
