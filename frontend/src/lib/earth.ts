/**
 * Earth & Sky wave 1 — pure earth maths and land painting.
 *
 * No React, no three.js: this module is the shared library behind the dome
 * and the mini-globe. Conventions come from
 * docs/notes/earthsky/wave1/contract.md:
 *  - the sunrise/sunset convention is the Sun's centre at altitude
 *    -0.8793° (what swe.rise_trans fires at with default flags; the textbook
 *    -0.8333° is 12-24 s off at normal latitudes);
 *  - the terminator at altitude h0 is the small circle of angular radius
 *    90° - h0 around the sub-solar point;
 *  - points west of the sub-solar meridian are on the sunrise half.
 */

/**
 * The app's sunrise convention: the Sun-centre altitude at which
 * swe.rise_trans (default flags) reports rise/set. Measured by the lead
 * over 78 events: -0.8793° (sd 0.0036). The textbook -0.8333° (34' refraction
 * + 16' semi-diameter) differs by 12-24 s at normal latitudes; oracle rows
 * built at -0.8333° must pass that value explicitly.
 */
export const SUNRISE_ALTITUDE_DEG = -0.8793;

export interface SubPoint {
  lat: number;
  lon: number;
}

const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;

export function wrapLon(lon: number): number {
  const wrapped = ((((lon + 180) % 360) + 360) % 360) - 180;
  // wrapLon(180) === -180: the interval is [-180, 180).
  return wrapped === -180 ? -180 : wrapped;
}

export function angularDistanceDeg(a: SubPoint, b: SubPoint): number {
  const sinLatA = Math.sin(a.lat * RAD);
  const cosLatA = Math.cos(a.lat * RAD);
  const sinLatB = Math.sin(b.lat * RAD);
  const cosLatB = Math.cos(b.lat * RAD);
  const cosD =
    sinLatA * sinLatB + cosLatA * cosLatB * Math.cos((b.lon - a.lon) * RAD);
  // Clamp guards against floating-point excursions past |1| near 0° and 180°.
  const clamped = Math.min(1, Math.max(-1, cosD));
  return Math.acos(clamped) * DEG;
}

export function sunAltitudeDeg(sun: SubPoint, place: SubPoint): number {
  return 90 - angularDistanceDeg(sun, place);
}

export function sideOf(sun: SubPoint, place: SubPoint): 'sunrise' | 'sunset' {
  return wrapLon(place.lon - sun.lon) < 0 ? 'sunrise' : 'sunset';
}

export interface TerminatorPoint {
  lat: number;
  lon: number;
  side: 'sunrise' | 'sunset';
}

export function terminatorPoints(
  sun: SubPoint,
  altitudeDeg: number = SUNRISE_ALTITUDE_DEG,
  segments: number = 360,
): TerminatorPoint[] {
  const points: TerminatorPoint[] = [];
  if (segments < 1) return points;
  const angularRadius = (90 - altitudeDeg) * RAD;
  const latS = sun.lat * RAD;
  const lonS = sun.lon;
  const cosLatS = Math.cos(latS);
  const sinLatS = Math.sin(latS);
  const sinR = Math.sin(angularRadius);
  const cosR = Math.cos(angularRadius);

  for (let i = 0; i < segments; i += 1) {
    const bearingDeg = (360 * i) / segments;
    let lat: number;
    let lon: number;
    if (Math.abs(cosLatS) < 1e-12) {
      // Sub-solar point at a pole: the terminator is the parallel at
      // 90° - angularRadius (north) or -90° + angularRadius (south), swept
      // through every longitude. The general formula degenerates here
      // (atan2(0, 0)) and would emit NaN-free but identical longitudes.
      lat = latS > 0 ? 90 - angularRadius * DEG : -90 + angularRadius * DEG;
      lon = wrapLon(lonS + (latS > 0 ? bearingDeg : -bearingDeg));
    } else {
      const bearing = bearingDeg * RAD;
      const sinLat = sinLatS * cosR + cosLatS * sinR * Math.cos(bearing);
      lat = Math.asin(Math.min(1, Math.max(-1, sinLat))) * DEG;
      const dlon =
        Math.atan2(
          Math.sin(bearing) * sinR * cosLatS,
          cosR - sinLatS * sinLat,
        ) * DEG;
      lon = wrapLon(lonS + dlon);
    }
    points.push({ lat, lon, side: sideOf(sun, { lat, lon }) });
  }
  return points;
}

// ---------------------------------------------------------------------------
// Land data: integer rings, decoded to degrees
// ---------------------------------------------------------------------------

export interface LandPolygon {
  /** Outer ring, flat [lon0, lat0, lon1, lat1, ...] in degrees. */
  o: number[];
  /** Hole rings, each flat [lon0, lat0, ...] in degrees. */
  h: number[][];
}

export interface LandData {
  v: number;
  kind: 'land';
  decimals: number;
  polys: LandPolygon[];
}

function decodeRing(ring: unknown, scale: number, what: string): number[] {
  if (!Array.isArray(ring) || ring.length < 4 || ring.length % 2 !== 0) {
    throw new TypeError(`${what}: ring must be a flat even-length array of >= 4 numbers`);
  }
  const out: number[] = [];
  for (const value of ring) {
    if (typeof value !== 'number' || !Number.isFinite(value) || !Number.isInteger(value)) {
      throw new TypeError(`${what}: coordinates must be integers`);
    }
    out.push(value * scale);
  }
  return out;
}

export function decodeLand(raw: unknown): LandData {
  if (typeof raw !== 'object' || raw === null) {
    throw new TypeError('land data: payload must be an object');
  }
  const rec = raw as Record<string, unknown>;
  if (rec.v !== 1) throw new TypeError('land data: unsupported version');
  if (rec.kind !== 'land') throw new TypeError('land data: kind must be "land"');
  if (
    typeof rec.decimals !== 'number' ||
    !Number.isInteger(rec.decimals) ||
    rec.decimals < 0 ||
    rec.decimals > 6
  ) {
    throw new TypeError('land data: decimals must be an integer in [0, 6]');
  }
  if (!Array.isArray(rec.polys)) {
    throw new TypeError('land data: polys must be an array');
  }
  const scale = 10 ** -rec.decimals;
  const polys: LandPolygon[] = rec.polys.map((poly, index) => {
    if (typeof poly !== 'object' || poly === null || !Array.isArray((poly as Record<string, unknown>).o)) {
      throw new TypeError(`land data: polys[${index}].o must be an array`);
    }
    const p = poly as Record<string, unknown>;
    const holes = Array.isArray(p.h) ? p.h : [];
    return {
      o: decodeRing(p.o, scale, `polys[${index}].o`),
      h: holes.map((h, hi) => decodeRing(h, scale, `polys[${index}].h[${hi}]`)),
    };
  });
  return { v: 1, kind: 'land', decimals: rec.decimals, polys };
}

export function landRings(land: LandData): number[][] {
  const rings: number[][] = [];
  for (const poly of land.polys) {
    rings.push(poly.o);
    for (const hole of poly.h) rings.push(hole);
  }
  return rings;
}

/**
 * Paint the land equirectangular onto `width x height` pixels.
 *
 * The ocean is painted first, then every outer ring and hole ring is added
 * as one sub-path and filled once with the even-odd rule, so holes (the
 * Caspian Sea) subtract. Antarctica's ring includes the run along latitude
 * -90 (sampled at sub-1.5° steps in this dataset), so the fill reaches the
 * bottom edge of the map without drawing a line across it and without any
 * antimeridian seam jump.
 */
export function paintLand(
  ctx: CanvasRenderingContext2D,
  land: LandData,
  width: number,
  height: number,
  colors: { ocean: string; land: string },
): void {
  ctx.fillStyle = colors.ocean;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = colors.land;
  ctx.beginPath();
  for (const ring of landRings(land)) {
    for (let i = 0; i < ring.length; i += 2) {
      const x = ((ring[i] + 180) / 360) * width;
      const y = ((90 - ring[i + 1]) / 180) * height;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
  }
  ctx.fill('evenodd');
}

export async function loadLand(): Promise<LandData> {
  // Dynamic import so Vite splits the 688 KB data file into its own chunk,
  // fetched only when the dome mounts (spec: +0 KB initial bundle).
  const mod = (await import('../data/land-50m.json')) as unknown as {
    default?: unknown;
  };
  return decodeLand(mod.default ?? mod);
}

// ---------------------------------------------------------------------------
// Endpoint shape (row W1-A builds the backend; this row only mirrors the type)
// ---------------------------------------------------------------------------

export interface BodySubPoint {
  id: string;
  name: string;
  ra_deg: number;
  dec_deg: number;
  lat: number;
  lon: number;
}

export interface EarthState {
  at: string;
  ephemeris: string;
  gast_deg: number;
  sun: BodySubPoint;
  moon: BodySubPoint;
  planets: BodySubPoint[];
  provenance: Record<string, string>;
}

/** Sidereal Earth rotation used between earth-state polls. The body's own RA drift is ignored. */
const EARTH_ROTATION_DEG_PER_SEC = 360.9856 / 86400;

/**
 * Advance a sub-point by Earth's rotation. Longitude decreases (west) by
 * 360.9856°/86400 s. Latitude is unchanged. Longitude stays in [-180, 180).
 */
export function extrapolateSubPoint(p: SubPoint, dtSeconds: number): SubPoint {
  return {
    lat: p.lat,
    lon: wrapLon(p.lon - EARTH_ROTATION_DEG_PER_SEC * dtSeconds),
  };
}

/**
 * Outer rings of polygons whose longer bounding-box side is under `maxSpanDeg`.
 * Vertex count is every lon/lat pair in those rings, including a repeated closing point.
 * Holes are not outlined. The committed 50 m file yields 913 polygons and 9152 vertices at 0.5°.
 */
export function smallIslandVertices(
  land: LandData,
  maxSpanDeg = 0.5,
): { rings: number[][]; polygonCount: number; vertexCount: number } {
  const rings: number[][] = [];
  let vertexCount = 0;
  for (const poly of land.polys) {
    const ring = poly.o;
    if (ring.length < 4) continue;
    let minLon = Infinity;
    let maxLon = -Infinity;
    let minLat = Infinity;
    let maxLat = -Infinity;
    for (let i = 0; i < ring.length; i += 2) {
      const lon = ring[i];
      const lat = ring[i + 1];
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    }
    const longer = Math.max(maxLon - minLon, maxLat - minLat);
    if (longer < maxSpanDeg) {
      rings.push(ring);
      vertexCount += ring.length / 2;
    }
  }
  return { rings, polygonCount: rings.length, vertexCount };
}

// ---------------------------------------------------------------------------
// Globe picking: the inverse of the lat/lon -> vector mapping (row W3-C0)
// ---------------------------------------------------------------------------

export interface LatLng {
  lat: number;
  lng: number;
}

/**
 * Below this horizontal radius (relative to the point's radius) a cartesian
 * point is treated as a pole. `latLonToVec3` is exact at +90 (sin(0) = 0) but
 * at -90 `sin(180°)` rounds to ~1.2e-16, which would otherwise turn into an
 * arbitrary longitude. 89.999° has a horizontal radius of ~1.7e-5, far above
 * the threshold.
 */
const POLE_HORIZONTAL_EPS = 1e-12;

/**
 * `uvToLatLon` — the equirectangular texture coordinate on three's
 * `SphereGeometry` -> degrees. This is what a raycast `intersection.uv`
 * carries when the globe material samples `land`/earth textures:
 *   u = (lng + 180) / 360, v = (lat + 90) / 180
 * (the Wave 1 check against SphereGeometry vertices lives in
 * docs/notes/earthsky/wave1/lead-vis/align.test.ts).
 * Longitude is wrapped into [-180, 180), so the seam (u = 0 or 1) is -180
 * away from the poles. A pole has no longitude of its own, so v = 0 and v = 1
 * report 0 — the same defined value `pointToLatLon` uses.
 */
export function uvToLatLon(u: number, v: number): LatLng {
  const lat = v * 180 - 90;
  if (v <= 0 || v >= 1) return { lat, lng: 0 };
  return { lat, lng: wrapLon(u * 360 - 180) };
}

/**
 * `pointToLatLon` — a point on the globe in the same local frame as the
 * forward mapping the globes already use (`latLonToVec3` in
 * components/3D/worldEmanationHelpers.ts):
 *   phi = (90 - lat)°, theta = (lng + 180)°
 *   x = -r sin(phi) cos(theta), y = r cos(phi), z = r sin(phi) sin(theta)
 * The radius does not matter. Longitude is wrapped into [-180, 180); the
 * poles have no longitude of their own, so they return 0 (a defined value)
 * and the degenerate zero vector returns 0, 0.
 */
export function pointToLatLon(x: number, y: number, z: number): LatLng {
  const radius = Math.hypot(x, y, z);
  if (!(radius > 0)) return { lat: 0, lng: 0 };
  const lat = Math.asin(Math.min(1, Math.max(-1, y / radius))) * DEG;
  const horizontal = Math.hypot(x, z);
  if (horizontal <= POLE_HORIZONTAL_EPS * radius) return { lat, lng: 0 };
  // x = -r sin(phi) cos(theta), z = r sin(phi) sin(theta), so
  // theta = atan2(z, -x) and lng = theta - 180, wrapped.
  return { lat, lng: wrapLon(Math.atan2(z, -x) * DEG - 180) };
}
