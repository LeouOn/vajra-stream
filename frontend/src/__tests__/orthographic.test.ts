import { describe, expect, test } from 'vitest';

import { orthographicProject } from '../lib/orthographic';

const R = 100;

describe('orthographicProject literal cases (hand-derived, shown)', () => {
  // Centre (0,0), radius 100. Canvas coords: x right, y DOWN, origin at the
  // canvas top-left; the disc centre sits at (R, R).
  test('centre on (0,0): the centre point maps to the disc centre', () => {
    const p = orthographicProject({ lat: 0, lon: 0 }, { lat: 0, lon: 0 }, R);
    expect(p.x).toBeCloseTo(100, 9);
    expect(p.y).toBeCloseTo(100, 9);
    expect(p.visible).toBe(true);
  });

  test('(0, 90) maps to the right edge and is visible', () => {
    const p = orthographicProject({ lat: 0, lon: 90 }, { lat: 0, lon: 0 }, R);
    expect(p.x).toBeCloseTo(200, 9);
    expect(p.y).toBeCloseTo(100, 9);
    expect(p.visible).toBe(true);
  });

  test('(0, 180) is the antipode: not visible', () => {
    const p = orthographicProject({ lat: 0, lon: 180 }, { lat: 0, lon: 0 }, R);
    expect(p.visible).toBe(false);
  });

  test('north pole (90, 0) maps to the top of the disc', () => {
    const p = orthographicProject({ lat: 90, lon: 0 }, { lat: 0, lon: 0 }, R);
    expect(p.x).toBeCloseTo(100, 9);
    expect(p.y).toBeCloseTo(0, 9);
    expect(p.visible).toBe(true);
  });

  test('south pole (-90, 0) maps to the bottom of the disc', () => {
    const p = orthographicProject({ lat: -90, lon: 0 }, { lat: 0, lon: 0 }, R);
    expect(p.x).toBeCloseTo(100, 9);
    expect(p.y).toBeCloseTo(200, 9);
    expect(p.visible).toBe(true);
  });

  // Tilted centre (45, -100). Hand derivation for (45, -10):
  //   dx = lon diff = +90deg -> x = R*cos(45)*sin(90) = 70.7107 to the RIGHT;
  //   y_up = R*(cos45*sin45 - sin45*cos45*cos90) = R*0.5 = 50 -> canvas y = 50;
  //   cos c = sin45*sin45 + cos45*cos45*cos90 = 0.5 -> visible, on the limb half.
  test('tilted centre (45,-100): the centre point maps to the disc centre', () => {
    const p = orthographicProject({ lat: 45, lon: -100 }, { lat: 45, lon: -100 }, R);
    expect(p.x).toBeCloseTo(100, 9);
    expect(p.y).toBeCloseTo(100, 9);
    expect(p.visible).toBe(true);
  });

  test('tilted centre (45,-100): (45,-10) hand-derived', () => {
    const p = orthographicProject({ lat: 45, lon: -10 }, { lat: 45, lon: -100 }, R);
    expect(p.x).toBeCloseTo(170.710678, 6);
    expect(p.y).toBeCloseTo(50, 6);
    expect(p.visible).toBe(true);
  });

  test('tilted centre (45,-100): equator (0,-100) hand-derived', () => {
    // x = R*cos(0)*sin(0) = 0; y_up = R*(cos45*0 - sin45*1) = -70.7107 ->
    // canvas y = 100 + 70.7107 = 170.7107; cos c = cos45 -> visible.
    const p = orthographicProject({ lat: 0, lon: -100 }, { lat: 45, lon: -100 }, R);
    expect(p.x).toBeCloseTo(100, 6);
    expect(p.y).toBeCloseTo(170.710678, 6);
    expect(p.visible).toBe(true);
  });

  test('tilted centre (45,-100): the antipode (-45, 80) is not visible', () => {
    const p = orthographicProject({ lat: -45, lon: 80 }, { lat: 45, lon: -100 }, R);
    expect(p.visible).toBe(false);
  });
});

describe('orthographicProject property: visible points lie within the disc', () => {
  // Deterministic LCG — Math.random is forbidden by the repo guard.
  let seed = 20261022;
  const next = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  test('1000 seeded points: every visible projection lies inside the disc', () => {
    for (let i = 0; i < 1000; i += 1) {
      const centre = { lat: next() * 180 - 90, lon: next() * 360 - 180 };
      const point = { lat: next() * 180 - 90, lon: next() * 360 - 180 };
      const radius = 40 + next() * 120;
      const p = orthographicProject(point, centre, radius);
      if (p.visible) {
        const dx = p.x - radius;
        const dy = p.y - radius;
        expect(dx * dx + dy * dy).toBeLessThanOrEqual(radius * radius + 1e-6);
      }
    }
  });
});
