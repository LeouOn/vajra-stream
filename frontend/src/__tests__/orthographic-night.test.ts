import { describe, expect, test } from 'vitest';

import { SUNRISE_ALTITUDE_DEG, sunAltitudeDeg, type SubPoint } from '../lib/earth';
import {
  NIGHT_RAMP_END_ALT_DEG,
  NIGHT_RAMP_START_ALT_DEG,
  nightFactorAt,
  nightFactorMask,
  orthographicProject,
} from '../lib/orthographic';

/* Legacy polygon shading (copy of W1-D2's nightBoundary fill, unchanged) —
 * kept ONLY to demonstrate that these tests fail on the old approach. */

function legacyNightPolygonContains(
  centre: SubPoint,
  sun: SubPoint,
  radiusPx: number,
  x: number,
  y: number,
): boolean {
  const RAD = Math.PI / 180;
  const antiSolar: SubPoint = { lat: -sun.lat, lon: (((sun.lon + 180 + 540) % 360) - 180) };
  const segments = 128;
  const pts: { x: number; y: number }[] = [];
  const latS = antiSolar.lat * RAD;
  const lonS = antiSolar.lon * RAD;
  for (let i = 0; i < segments; i += 1) {
    const bearing = (i / segments) * 2 * Math.PI;
    const lat = Math.asin(-Math.cos(bearing) * Math.cos(latS));
    const lon =
      (((lonS + Math.atan2(Math.sin(bearing) * Math.cos(latS), -Math.cos(bearing) * Math.sin(latS)) +
        Math.PI) %
        (2 * Math.PI)) -
        Math.PI) *
      (180 / Math.PI);
    pts.push(orthographicProject({ lat: (lat * 180) / Math.PI, lon }, centre, radiusPx));
  }
  // Even-odd point-in-polygon on the FULL projected ring (the old bug: the
  // ring is a closed curve regardless of the far half).
  let inside = false;
  for (let i = 0, j = segments - 1; i < segments; j = i++) {
    const a = pts[i];
    const b = pts[j];
    if (a.y > y !== b.y > y && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
  }
  return inside;
}

/** Expected night factor derived from the COMMITTED sunAltitudeDeg. */
function expectedFactor(sun: SubPoint, place: SubPoint): number {
  const alt = sunAltitudeDeg(sun, place);
  if (alt >= NIGHT_RAMP_START_ALT_DEG) return 0;
  if (alt <= NIGHT_RAMP_END_ALT_DEG) return 1;
  return (NIGHT_RAMP_START_ALT_DEG - alt) / (NIGHT_RAMP_START_ALT_DEG - NIGHT_RAMP_END_ALT_DEG);
}

const CENTRES: SubPoint[] = [
  { lat: 20, lon: -122.4194 }, // the app centre (lead's measured case)
  { lat: 0, lon: 0 }, // equator/prime
  { lat: 65, lon: 20 }, // poles-side (Reykjavik-ish view)
];

const SUNS: SubPoint[] = [
  { lat: -11.1, lon: 146.1 }, // Sun over the Pacific (the W1-C 02:00Z case)
  { lat: -11.2, lon: -93.9 }, // Sun over the Americas (90W payload)
  { lat: -11.1, lon: 86.1 }, // Sun over Asia (90E payload)
];

const PLACES: SubPoint[] = [
  { lat: 40.71, lon: -74.01 }, // New York
  { lat: 25.76, lon: -80.19 }, // Miami
  { lat: 39.74, lon: -104.99 }, // Denver
  { lat: 19.43, lon: -99.13 }, // Mexico City
  { lat: 4.71, lon: -74.07 }, // Bogota
  { lat: 34.05, lon: -118.24 }, // Los Angeles
  { lat: 51.51, lon: -0.13 }, // London
  { lat: -33.87, lon: 151.21 }, // Sydney
];

describe('nightFactorAt — exact per-pixel mask (W1-D2b)', () => {
  for (const centre of CENTRES) {
    for (const sun of SUNS) {
      test(`centre (${centre.lat},${centre.lon}) sun lon ${sun.lon}: 8 places match sunAltitudeDeg-derived factors`, () => {
        for (const place of PLACES) {
          const proj = orthographicProject(place, centre, 100);
          if (!proj.visible) continue;
          const factor = nightFactorAt(centre, sun, 100, proj.x, proj.y);
          const expected = expectedFactor(sun, place);
          // The projected pixel is within ~1.5 px of the place's true
          // pixel, so allow the factor tolerance of a 1.5 px altitude shift.
          expect(Math.abs(factor - expected)).toBeLessThanOrEqual(0.06);
        }
      });
    }
  }

  test('the lead-measured case: 02:00 UTC, centre (20,-122.4): east-coast night places get factor 1', () => {
    const centre = CENTRES[0];
    const sun = SUNS[0]; // Sun over 146E -> Americas in night
    const nightPlaces = PLACES.slice(0, 5); // NY, Miami, Denver, Mexico City, Bogota
    for (const place of nightPlaces) {
      const proj = orthographicProject(place, centre, 100);
      if (!proj.visible) continue;
      expect(sunAltitudeDeg(sun, place)).toBeLessThan(NIGHT_RAMP_END_ALT_DEG); // really night
      expect(nightFactorAt(centre, sun, 100, proj.x, proj.y)).toBe(1);
    }
  });

  test('monotone between the ramp bounds along a meridian through the terminator', () => {
    const centre = { lat: 0, lon: 0 };
    const sun = { lat: 0, lon: 90 };
    // Sample the equator eastward from the sub-solar point: altitudes fall
    // from 90 through 0 to -90; the factor must never decrease.
    let previous = -1;
    for (let lon = 90; lon >= -90; lon -= 1) {
      const proj = orthographicProject({ lat: 0, lon }, centre, 100);
      if (!proj.visible) continue;
      const f = nightFactorAt(centre, sun, 100, proj.x, proj.y);
      expect(f).toBeGreaterThanOrEqual(previous - 1e-9);
      previous = f;
    }
    expect(previous).toBe(1);
  });

  test('RED demo: the legacy polygon shades the east coast BRIGHT at 02:00 UTC (the defect)', () => {
    const centre = CENTRES[0];
    const sun = SUNS[0];
    const place = PLACES[0]; // New York: real night, factor must be 1
    const proj = orthographicProject(place, centre, 100);
    const legacy = legacyNightPolygonContains(centre, sun, 100, proj.x, proj.y);
    // The defect, PINNED: the polygon does NOT contain New York's pixel
    // although the Sun altitude there is well past -6 deg. (Before the fix
    // this assertion was written the honest way — expect(legacy).toBe(true)
    // — and it FAILED, which was the RED run demonstrating the defect; see
    // the W1-D2b handoff. Now we pin both facts green.)
    expect(legacy).toBe(false);
    expect(expectedFactor(sun, place)).toBe(1);
    expect(nightFactorAt(centre, sun, 100, proj.x, proj.y)).toBe(1);
  });

  test('nightFactorMask covers the full canvas and matches nightFactorAt', () => {
    const centre = { lat: 10, lon: -30 };
    const sun = { lat: -11, lon: 40 };
    const mask = nightFactorMask(centre, sun, 8);
    expect(mask.length).toBe(256);
    for (let y = 0; y < 16; y += 1) {
      for (let x = 0; x < 16; x += 1) {
        expect(mask[y * 16 + x]).toBeCloseTo(nightFactorAt(centre, sun, 8, x + 0.5, y + 0.5), 6); // Float32 mask
      }
    }
  });

  test('ramp constants come from the contract', () => {
    expect(NIGHT_RAMP_START_ALT_DEG).toBe(SUNRISE_ALTITUDE_DEG);
    expect(NIGHT_RAMP_END_ALT_DEG).toBe(-6);
  });
});
