import { SUNRISE_ALTITUDE_DEG } from './earth';
import type { SubPoint } from './earth';

const RAD = Math.PI / 180;

export interface ProjectedPoint {
  x: number;
  y: number;
  visible: boolean;
}

/**
 * Orthographic projection of a sphere point onto a square canvas disc.
 *
 * Canvas coordinates: x grows right, y grows DOWN, origin at the canvas
 * top-left; the disc of `radiusPx` is centred at (radiusPx, radiusPx).
 * `visible` is true on the near hemisphere, including the exact limb
 * (angular distance 90 deg from the centre, cos c >= 0).
 *
 * Pure maths; no canvas dependency, so it is unit-testable headlessly.
 */
export function orthographicProject(
  point: SubPoint,
  centre: SubPoint,
  radiusPx: number,
): ProjectedPoint {
  const lat = point.lat * RAD;
  const lat0 = centre.lat * RAD;
  const dLon = (point.lon - centre.lon) * RAD;

  const cosC = Math.sin(lat0) * Math.sin(lat) + Math.cos(lat0) * Math.cos(lat) * Math.cos(dLon);

  // Standard orthographic (y up) …
  const xUp = radiusPx * Math.cos(lat) * Math.sin(dLon);
  const yUp =
    radiusPx * (Math.cos(lat0) * Math.sin(lat) - Math.sin(lat0) * Math.cos(lat) * Math.cos(dLon));

  // … flipped to canvas y-down, origin at the canvas corner.
  return {
    x: radiusPx + xUp,
    y: radiusPx - yUp,
    visible: cosC >= 0,
  };
}

/** Night-shading ramp bounds (degrees of Sun altitude at the pixel). */
export const NIGHT_RAMP_START_ALT_DEG = SUNRISE_ALTITUDE_DEG; // -0.8793
export const NIGHT_RAMP_END_ALT_DEG = -6; // full night by civil twilight
const SIN_START = Math.sin(NIGHT_RAMP_START_ALT_DEG * RAD);
const SIN_END = Math.sin(NIGHT_RAMP_END_ALT_DEG * RAD);

/**
 * Exact per-pixel night factor for the orthographic disc (W1-D2b).
 *
 * For pixel (x, y) inside the disc of `radiusPx` centred at (radiusPx,
 * radiusPx): invert the orthographic projection to the near-hemisphere
 * sphere point (z = sqrt(1 - p^2 - q^2)) and take the dot product with the
 * Sun's direction vector rotated into the same screen frame — sin(altitude)
 * directly, no per-pixel trig. Factor: 0 (no shade) at SUNRISE_ALTITUDE_DEG
 * and above; 1 (full 0.38 multiply) at -6 deg (civil twilight) and below;
 * linear in sin(altitude) between (equivalent to altitude-linear to within
 * 0.5% over the 5.1 deg ramp — inside every test tolerance). Returns 0 for
 * pixels outside the disc.
 */
export function nightFactorAt(
  centre: SubPoint,
  sun: SubPoint,
  radiusPx: number,
  x: number,
  y: number,
): number {
  const p = (x - radiusPx) / radiusPx;
  const q = (y - radiusPx) / radiusPx;
  const r2 = p * p + q * q;
  if (r2 > 1) return 0;
  const z = Math.sqrt(1 - r2);
  // Sun direction in the centre's screen frame (x east, y north, z to viewer).
  const lat0 = centre.lat * RAD;
  const latS = sun.lat * RAD;
  const dLon = (sun.lon - centre.lon) * RAD;
  const sX = Math.cos(latS) * Math.sin(dLon);
  const sY = Math.cos(lat0) * Math.sin(latS) - Math.sin(lat0) * Math.cos(latS) * Math.cos(dLon);
  const sZ = Math.sin(lat0) * Math.sin(latS) + Math.cos(lat0) * Math.cos(latS) * Math.cos(dLon);
  const sinAlt = p * sX - q * sY + z * sZ; // canvas y is down -> north is -q
  if (sinAlt >= SIN_START) return 0;
  if (sinAlt <= SIN_END) return 1;
  return (SIN_START - sinAlt) / (SIN_START - SIN_END);
}

/** Full mask of night factors for the square (2*radiusPx) canvas.
 * factor 0 outside the disc; Float32Array of length (2R)^2, row-major. */
export function nightFactorMask(centre: SubPoint, sun: SubPoint, radiusPx: number): Float32Array {
  const size = radiusPx * 2;
  const mask = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      mask[y * size + x] = nightFactorAt(centre, sun, radiusPx, x + 0.5, y + 0.5);
    }
  }
  return mask;
}

/** A drawing command emitted by ring clipping: move/line in canvas pixels,
 * or an arc along the disc's limb (angles in canvas atan2 space around the
 * disc centre, sweep < pi — the short way through the hidden span). */
export type RingCommand =
  | { op: 'M'; x: number; y: number }
  | { op: 'L'; x: number; y: number }
  | { op: 'A'; a0: number; a1: number };

interface FrameVec {
  x: number;
  y: number;
  z: number;
}

function toFrame(point: SubPoint, centre: SubPoint): FrameVec {
  const lat = point.lat * RAD;
  const lon = point.lon * RAD;
  const lat0 = centre.lat * RAD;
  const lon0 = centre.lon * RAD;
  const sinLat = Math.sin(lat);
  const cosLat = Math.cos(lat);
  const dLon = lon - lon0;
  return {
    x: cosLat * Math.sin(dLon),
    y: Math.cos(lat0) * sinLat - Math.sin(lat0) * cosLat * Math.cos(dLon),
    z: Math.sin(lat0) * sinLat + Math.cos(lat0) * cosLat * Math.cos(dLon),
  };
}

function frameToScreen(v: FrameVec, radiusPx: number): { x: number; y: number } {
  return { x: radiusPx + v.x * radiusPx, y: radiusPx - v.y * radiusPx };
}

/** Crossing of the great-circle arc between two frame vectors where z=0
 * (the limb), by bisection on the slerp parameter. Both endpoints must be
 * on opposite sides (z signs differ). */
function limbCrossing(a: FrameVec, b: FrameVec): FrameVec {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 40; i += 1) {
    const t = (lo + hi) / 2;
    const x = a.x + (b.x - a.x) * t;
    const y = a.y + (b.y - a.y) * t;
    const z = a.z + (b.z - a.z) * t;
    const len = Math.hypot(x, y, z);
    const zc = z / len;
    if ((a.z >= 0) === zc >= 0) lo = t;
    else hi = t;
  }
  const t = (lo + hi) / 2;
  const x = a.x + (b.x - a.x) * t;
  const y = a.y + (b.y - a.y) * t;
  const z = a.z + (b.z - a.z) * t;
  const len = Math.hypot(x, y, z);
  return { x: x / len, y: y / len, z: z / len };
}

/**
 * Clip a closed ring (lon/lat degrees) to the visible orthographic disc
 * (W1-D2c). Edges are first refined near the limb (a long edge whose both
 * endpoints are visible can dip behind the horizon and back); where an
 * edge crosses the horizon the crossing point on the great-circle arc
 * between the two vertices (frame z = 0) is inserted; each visible run is
 * closed ALONG THE LIMB to the next entry crossing in +angle order
 * (crossings of a simple ring alternate around the limb). Entirely hidden
 * rings emit nothing; entirely visible rings emit plain M/L unchanged.
 */
export function clipRingToDisc(
  ring: SubPoint[],
  centre: SubPoint,
  radiusPx: number,
): RingCommand[] {
  if (ring.length < 3) return [];
  const n = ring.length;
  let vecs = ring.map((point) => toFrame(point, centre));

  // Refinement: split edges whose lowest-z endpoint is near the limb, twice,
  // so an edge that dips behind the horizon produces real sign changes.
  for (let pass = 0; pass < 2; pass += 1) {
    const refined: FrameVec[] = [];
    for (let k = 0; k < vecs.length; k += 1) {
      const a = vecs[k];
      const b = vecs[(k + 1) % vecs.length];
      refined.push(a);
      if (Math.min(a.z, b.z) < 0.06 && a.z >= 0 === b.z >= 0) {
        for (const t of [0.25, 0.5, 0.75]) {
          const x = a.x + (b.x - a.x) * t;
          const y = a.y + (b.y - a.y) * t;
          const z = a.z + (b.z - a.z) * t;
          const len = Math.hypot(x, y, z);
          refined.push({ x: x / len, y: y / len, z: z / len });
        }
      }
    }
    vecs = refined;
  }

  const m = vecs.length;
  const visible = vecs.map((v) => v.z >= 0);
  if (visible.every((v) => v)) {
    const commands: RingCommand[] = [];
    vecs.forEach((v, idx) => {
      const scr = frameToScreen(v, radiusPx);
      commands.push({ op: idx === 0 ? ('M' as const) : ('L' as const), x: scr.x, y: scr.y });
    });
    return commands;
  }
  if (!visible.some((v) => v)) return [];

  const angleOf = (v: FrameVec) => Math.atan2(-v.y, v.x);
  const TAU = 2 * Math.PI;
  const norm = (a: number) => ((a % TAU) + TAU) % TAU;

  interface RunInfo {
    commands: RingCommand[];
    exitScreen: { x: number; y: number };
    exitAngle: number;
    entryAngle: number; // of THIS run (its own entry crossing)
    hiddenAzimuths: number[]; // of the span AFTER this run's exit
  }
  const runs: RunInfo[] = [];

  let i = 0;
  let guard = 0;
  while (!(visible[i % m] && !visible[(i - 1 + m) % m])) {
    i += 1;
    guard += 1;
    if (guard > m) return [];
  }
  const start = i % m;
  while (true) {
    let first = true;
    const runCommands: RingCommand[] = [];
    let entryAngle = 0;
    while (visible[i % m]) {
      const v = vecs[i % m];
      const scr = frameToScreen(v, radiusPx);
      if (first) {
        const cross = limbCrossing(vecs[(i - 1 + m) % m], v);
        const cs = frameToScreen(cross, radiusPx);
        entryAngle = angleOf(cross);
        runCommands.push({ op: 'M', x: cs.x, y: cs.y });
        runCommands.push({ op: 'L', x: scr.x, y: scr.y });
        first = false;
      } else {
        runCommands.push({ op: 'L', x: scr.x, y: scr.y });
      }
      i += 1;
      guard += 1;
      if (guard > 8 * m) return [];
    }
    const exitCross = limbCrossing(vecs[(i - 1 + m) % m], vecs[i % m]);
    const hiddenAzimuths: number[] = [];
    while (!visible[i % m]) {
      const hv = vecs[i % m];
      hiddenAzimuths.push(angleOf(hv));
      i += 1;
      guard += 1;
      if (guard > 8 * m) return [];
    }
    runs.push({
      commands: runCommands,
      exitScreen: frameToScreen(exitCross, radiusPx),
      exitAngle: angleOf(exitCross),
      entryAngle,
      hiddenAzimuths,
    });
    if (i % m === start) break;
  }

  // Close each run from its exit to the next ENTRY in +angle order (limb
  // crossings of a simple ring alternate around the limb). Cases where two
  // crossings nearly coincide (a concave coastline grazing the limb) can
  // break strict alternation; the spike filter below removes the degenerate
  // ones and the accuracy of the remaining pairing is pinned by the tests.
  const out: RingCommand[] = [];
  const entryAngles = runs.map((r) => r.entryAngle);
  for (let r = 0; r < runs.length; r += 1) {
    const run = runs[r];
    let delta = Infinity;
    for (const e of entryAngles) {
      const d = norm(e - run.exitAngle);
      if (d > 1e-9 && d < delta) delta = d;
    }
    if (!Number.isFinite(delta)) delta = TAU;
    const visibleVertices = run.commands.filter((c) => c.op === 'L').length - 1;
    if (delta < 0.5 * (Math.PI / 180) && visibleVertices <= 2) continue; // spike
    out.push(...run.commands);
    out.push({ op: 'L', x: run.exitScreen.x, y: run.exitScreen.y });
    out.push({ op: 'A', a0: run.exitAngle, a1: run.exitAngle + delta });
  }
  return out;
}
