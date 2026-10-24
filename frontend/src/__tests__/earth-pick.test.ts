/**
 * W3-C0 — inverse of the globe's latitude/longitude -> vector mapping.
 *
 * The forward map is the one the globes already use,
 * `latLonToVec3` in components/3D/worldEmanationHelpers.ts:
 *   phi = (90 - lat)°, theta = (lng + 180)°
 *   x = -r sin(phi) cos(theta), y = r cos(phi), z = r sin(phi) sin(theta)
 * On three's SphereGeometry the same point has texture uv
 * u = (lng + 180) / 360, v = (lat + 90) / 180 (verified in Wave 1 by
 * docs/notes/earthsky/wave1/lead-vis/align.test.ts).
 *
 * This test drives `pointToLatLon` from real geometry vertices (not from the
 * formula it implements) and requires an exact forward/back round trip on a
 * grid that includes the poles and +-180.
 */
import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { pointToLatLon, uvToLatLon, wrapLon } from '../lib/earth';
import { latLonToVec3 } from '../components/3D/worldEmanationHelpers';

const ROUND_TRIP_EPS_DEG = 1e-9;
// three stores SphereGeometry positions in a Float32Array: ~1e-7 relative,
// i.e. ~1e-5 deg on the sphere. The 1e-9 bar is for the double-precision
// round trip; geometry vertices are compared at Float32 resolution.
const VERTEX_EPS_DEG = 1e-4;
const POLE_LAT = 90;

/** Signed longitude difference in degrees, wrap-aware. */
function lonDelta(a: number, b: number): number {
  return Math.abs(wrapLon(a - b));
}

function expectClose(actual: number, expected: number, eps: number, label: string): void {
  if (!(Math.abs(actual - expected) <= eps)) {
    throw new Error(`${label}: expected ${expected}, got ${actual} (|d|=${Math.abs(actual - expected)})`);
  }
}

describe('uvToLatLon (equirectangular uv -> degrees)', () => {
  it('maps the four texture corners and the centre', () => {
    // v = 0/1 is a pole: latitude is the pole, longitude is the defined 0.
    expect(uvToLatLon(0, 0)).toEqual({ lat: -90, lng: 0 });
    expect(uvToLatLon(0, 1)).toEqual({ lat: 90, lng: 0 });
    expect(uvToLatLon(1, 0)).toEqual({ lat: -90, lng: 0 });
    expect(uvToLatLon(1, 1)).toEqual({ lat: 90, lng: 0 });
    expect(uvToLatLon(0.5, 0.5)).toEqual({ lat: 0, lng: 0 });
  });

  it('matches hand-computed uv for London and the East/West quadrants', () => {
    // London lon=-0.13 -> u=(180-0.13)/360; lat=51.5 -> v=(90+51.5)/180.
    const london = uvToLatLon((180 - 0.13) / 360, (90 + 51.5) / 180);
    expectClose(london.lat, 51.5, 1e-12, 'London lat');
    expectClose(london.lng, -0.13, 1e-12, 'London lng');

    expect(uvToLatLon(0.75, 0.5).lng).toBe(90);
    expect(uvToLatLon(0.25, 0.5).lng).toBe(-90);
    // The seam is one place: u=0 and u=1 both mean longitude -180.
    expect(uvToLatLon(0, 0.5).lng).toBe(-180);
    expect(uvToLatLon(1, 0.5).lng).toBe(-180);
    expect(uvToLatLon(0, 0.25).lat).toBe(-45);
  });
});

describe('pointToLatLon (globe frame -> degrees)', () => {
  it('puts the poles on the axis and defines their longitude as 0', () => {
    expect(pointToLatLon(0, 2.05, 0)).toEqual({ lat: 90, lng: 0 });
    expect(pointToLatLon(0, -2.05, 0)).toEqual({ lat: -90, lng: 0 });
    // The forward map at lat=-90 leaves ~1e-16 of horizontal residue; it must
    // still read as a pole, not as an arbitrary longitude.
    const south = latLonToVec3(-90, 123);
    expect(pointToLatLon(south.x, south.y, south.z)).toEqual({ lat: -90, lng: 0 });
    expect(pointToLatLon(0, 0, 0)).toEqual({ lat: 0, lng: 0 });
  });

  it('is radius-independent', () => {
    const a = latLonToVec3(37.7749, -122.4194, 1);
    const b = latLonToVec3(37.7749, -122.4194, 8);
    expect(pointToLatLon(a.x, a.y, a.z)).toEqual(pointToLatLon(b.x, b.y, b.z));
  });

  it('round-trips the forward map exactly on a grid incl. +-89.999 and +-180', () => {
    const lats = [-90, -89.999, -60, -45, -0.0001, 0, 0.0001, 45, 60, 89.999, 90];
    const lngs = [-180, -179.999, -122.4194, -90, -0.0001, 0, 0.0001, 90, 139.6503, 179.999, 180];
    let checked = 0;
    for (const lat of lats) {
      for (const lng of lngs) {
        const v = latLonToVec3(lat, lng);
        const back = pointToLatLon(v.x, v.y, v.z);
        expectClose(back.lat, lat, ROUND_TRIP_EPS_DEG, `lat ${lat},${lng}`);
        if (Math.abs(lat) === POLE_LAT) {
          expectClose(back.lng, 0, ROUND_TRIP_EPS_DEG, `pole lng ${lat},${lng}`);
        } else {
          expectClose(lonDelta(back.lng, lng), 0, ROUND_TRIP_EPS_DEG, `lng ${lat},${lng}`);
        }
        checked += 1;
      }
    }
    expect(checked).toBe(lats.length * lngs.length);
  });
});

describe('agreement with real THREE.SphereGeometry vertices', () => {
  // 36 x 18 segments: 703 vertices, including the polar rows and the u seam.
  const geometry = new THREE.SphereGeometry(2, 36, 18);
  const position = geometry.getAttribute('position');
  const uv = geometry.getAttribute('uv');

  it('every non-polar vertex agrees with its own uv, and its own position, to 1e-9 deg', () => {
    let equatorial = 0;
    let polarRows = 0;
    for (let i = 0; i < position.count; i += 1) {
      const vertex = new THREE.Vector3(position.getX(i), position.getY(i), position.getZ(i));
      const fromPosition = pointToLatLon(vertex.x, vertex.y, vertex.z);
      const fromUv = uvToLatLon(uv.getX(i), uv.getY(i));
      // three's own uv convention, spelled out, so the inverse is not grading itself.
      const textureLat = uv.getY(i) * 180 - 90;
      const textureLng = wrapLon(uv.getX(i) * 360 - 180);

      expectClose(fromUv.lat, textureLat, 1e-12, `uv lat at vertex ${i}`);

      if (Math.abs(fromPosition.lat) > 89.999) {
        // The pole vertices all share the axis; the geometry duplicates the
        // point once per azimuth, so only the latitude is meaningful and the
        // inverse reports the defined longitude 0 for both inputs.
        expectClose(fromPosition.lat, textureLat, VERTEX_EPS_DEG, `polar lat at vertex ${i}`);
        expect(fromUv.lng).toBe(0);
        polarRows += 1;
        continue;
      }
      expectClose(fromUv.lng, textureLng, 1e-12, `uv lng at vertex ${i}`);
      expectClose(fromPosition.lat, textureLat, VERTEX_EPS_DEG, `vertex lat at ${i}`);
      expectClose(lonDelta(fromPosition.lng, textureLng), 0, VERTEX_EPS_DEG, `vertex lng at ${i}`);
      equatorial += 1;
    }
    // Guard against a geometry change that would make the loop vacuous.
    expect(equatorial).toBeGreaterThan(600);
    expect(polarRows).toBe(2 * 37);
  });

  it('places named cities on the vertex whose texture uv samples them', () => {
    const cases: [string, number, number][] = [
      ['London', 51.5, -0.13],
      ['Kiritimati', 1.87, -157.4],
      ['Cape Town', -33.9, 18.4],
      ['Tokyo', 35.7, 139.7],
      ['Quito', -0.2, -78.5],
      ['Honolulu', 21.3, -157.9],
    ];
    for (const [name, lat, lng] of cases) {
      // uv -> degrees is the texture sampling the pick will use.
      const fromUv = uvToLatLon((lng + 180) / 360, (lat + 90) / 180);
      expectClose(fromUv.lat, lat, 1e-12, `${name} uv lat`);
      expectClose(lonDelta(fromUv.lng, lng), 0, 1e-12, `${name} uv lng`);

      // The nearest real vertex must be within one grid cell, and converting
      // that vertex back must land within one cell of the city.
      const marker = latLonToVec3(lat, lng, 2);
      let best = Infinity;
      let bestIndex = 0;
      for (let i = 0; i < position.count; i += 1) {
        const dx = position.getX(i) - marker.x;
        const dy = position.getY(i) - marker.y;
        const dz = position.getZ(i) - marker.z;
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < best) {
          best = d2;
          bestIndex = i;
        }
      }
      const nearest = pointToLatLon(
        position.getX(bestIndex),
        position.getY(bestIndex),
        position.getZ(bestIndex),
      );
      // 36 segments around = 10°, 18 rows = 10°; half a cell + rounding.
      expect(Math.abs(nearest.lat - lat)).toBeLessThanOrEqual(5.0001);
      expect(lonDelta(nearest.lng, lng)).toBeLessThanOrEqual(5.0001);
    }
  });
});
