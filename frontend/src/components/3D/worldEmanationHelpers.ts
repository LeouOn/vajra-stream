/**
 * worldEmanationHelpers.ts — Pure geographic and 3D projection helpers
 * for Earth emanation, radionics globe, and target coordinate resolution.
 */
import { useEffect, useState } from 'react';
import * as THREE from 'three';
import {
  angularDistanceDeg,
  extrapolateSubPoint,
  loadLand,
  paintLand,
  smallIslandVertices,
  terminatorPoints,
  uvToLatLon,
  type EarthState,
  type LandData,
  type SubPoint,
} from '../../lib/earth';

export const COUNTRY_COORDS: Record<string, [number, number]> = {
  'japan': [36, 138], 'tokyo': [35.6762, 139.6503], 'osaka': [34.6937, 135.5023],
  'indonesia': [-2, 118], 'bali': [-8.4095, 115.1889], 'java': [-7.6145, 110.7122], 'sumatra': [-0.5897, 101.3431], 'sulawesi': [-1.4300, 121.4456], 'jakarta': [-6.2088, 106.8456],
  'philippines': [13, 122], 'manila': [14.5995, 120.9842], 'cebu': [10.3157, 123.8854],
  'china': [35, 105], 'beijing': [39.9042, 116.4074], 'shanghai': [31.2304, 121.4737], 'tibet': [31.6927, 88.0924], 'lhasa': [29.6525, 91.1721], 'sichuan': [30.6517, 104.0764],
  'india': [20, 78], 'dharamsala': [32.2190, 76.3234], 'bodh gaya': [24.6961, 84.9869], 'delhi': [28.6139, 77.2090], 'mumbai': [19.0760, 72.8777],
  'nepal': [28, 84], 'kathmandu': [27.7172, 85.3240], 'lumbini': [27.4842, 83.2760],
  'bhutan': [27.5142, 90.4336], 'thimphu': [27.4728, 89.6393],
  'turkey': [39, 35], 'istanbul': [41.0082, 28.9784], 'ankara': [39.9334, 32.8597],
  'iran': [32, 53], 'tehran': [35.6892, 51.3890], 'pakistan': [30, 70], 'islamabad': [33.6844, 73.0479],
  'mexico': [23, -102], 'mexico city': [19.4326, -99.1332], 'oaxaca': [17.0732, -96.7266],
  'united states': [38, -97], 'usa': [38, -97], 'us': [38, -97], 'california': [36.7783, -119.4179], 'los angeles': [34.0522, -118.2437], 'san francisco': [37.7749, -122.4194], 'new york': [40.7128, -74.0060], 'hawaii': [19.8968, -155.5828], 'alaska': [64.2008, -149.4937],
  'chile': [-35, -71], 'santiago': [-33.4489, -70.6693], 'peru': [-10, -76], 'lima': [-12.0464, -77.0428], 'ecuador': [-2, -77], 'quito': [-0.1807, -78.4678],
  'italy': [42, 13], 'rome': [41.9028, 12.4964],
  'greece': [39, 22], 'athens': [37.9838, 23.7275],
  'iceland': [65, -18], 'reykjavik': [64.1466, -21.9426],
  'new zealand': [-41, 174], 'auckland': [-36.8485, 174.7633],
  'papua new guinea': [-6, 144], 'solomon islands': [-9.6457, 160.1562], 'fiji': [-17.7134, 178.0650], 'tonga': [-21.1789, -175.1982], 'vanuatu': [-15.3767, 166.9592],
  'myanmar': [22, 96], 'yangon': [16.8661, 96.1951], 'bangladesh': [24, 90], 'dhaka': [23.8103, 90.4125],
  'thailand': [15, 101], 'bangkok': [13.7563, 100.5018], 'chiang mai': [18.7883, 98.9853],
  'vietnam': [14, 108], 'hanoi': [21.0285, 105.8542], 'afghanistan': [34, 67], 'kabul': [34.5553, 69.2075],
  'iraq': [33, 44], 'baghdad': [33.3152, 44.3661], 'syria': [35, 39], 'damascus': [33.5138, 36.2765],
  'yemen': [15, 48], 'sanaa': [15.3694, 44.1910], 'sudan': [15, 30], 'khartoum': [15.5007, 32.5599],
  'ethiopia': [9, 40], 'addis ababa': [9.0320, 38.7482], 'somalia': [6, 47], 'mogadishu': [2.0469, 45.3182],
  'congo': [-4, 22], 'drc': [-4.0383, 21.7587], 'democratic republic of the congo': [-4.0383, 21.7587],
  'rwanda': [-1.9403, 29.8739], 'kigali': [-1.9441, 30.0619],
  'nigeria': [9, 8], 'lagos': [6.5244, 3.3792],
  'ukraine': [49, 31], 'kyiv': [50.4501, 30.5234],
  'gaza': [31.5017, 34.4668], 'palestine': [31.9522, 35.2332], 'israel': [31.0461, 34.8516], 'jerusalem': [31.7683, 35.2137], 'lebanon': [33.8547, 35.8623], 'beirut': [33.8938, 35.5018],
  'haiti': [19, -72], 'port-au-prince': [18.5944, -72.3074],
  'colombia': [4, -72], 'bogota': [4.7110, -74.0721],
  'venezuela': [7, -66], 'caracas': [10.4806, -66.9036],
  'brazil': [-10, -55], 'rio de janeiro': [-22.9068, -43.1729], 'sao paulo': [-23.5505, -46.6333],
  'argentina': [-34, -64], 'buenos aires': [-34.6037, -58.3816],
  'australia': [-25, 135], 'sydney': [-33.8688, 151.2093], 'melbourne': [-37.8136, 144.9631],
  'france': [47, 2], 'paris': [48.8566, 2.3522],
  'germany': [51, 10], 'berlin': [52.5200, 13.4050],
  'spain': [40, -4], 'madrid': [40.4168, -3.7038], 'portugal': [39, -8], 'lisbon': [38.7223, -9.1393],
  'morocco': [32, -6], 'marrakech': [31.6295, -7.9811], 'algeria': [28, 3], 'algiers': [36.7538, 3.0588],
  'egypt': [27, 30], 'cairo': [30.0444, 31.2357],
  'south africa': [-29, 24], 'cape town': [-33.9249, 18.4241], 'kenya': [0, 38], 'nairobi': [-1.2921, 36.8219],
  'tanzania': [-6, 35], 'madagascar': [-20, 47], 'canada': [56, -106], 'vancouver': [49.2827, -123.1207], 'toronto': [43.6532, -79.3832],
  'russia': [61, 95], 'moscow': [55.7558, 37.6173],
  'south korea': [36, 128], 'seoul': [37.5665, 126.9780], 'north korea': [40, 127], 'pyongyang': [39.0392, 125.7625],
  'taiwan': [23.5, 121], 'taipei': [25.0330, 121.5654],
  'malaysia': [4, 102], 'kuala lumpur': [3.1390, 101.6869], 'singapore': [1.3521, 103.8198],
  'united kingdom': [55, -3], 'uk': [55, -3], 'london': [51.5074, -0.1278],
  'uae': [23.4241, 53.8478], 'dubai': [25.2048, 55.2708],
  'mongolia': [46.8625, 103.8467], 'sri lanka': [7.8731, 80.7718], 'colombo': [6.9271, 79.8612],
};

const NON_GEOGRAPHIC_TARGETS = new Set([
  'all beings',
  'all sentient beings',
  'the field',
  'field',
  'world peace',
  'universe',
  'sentient beings',
  'cosmos',
  'earth',
]);

// Sorted keys by length descending to match most specific terms first (e.g. 'san francisco' before 'san')
const SORTED_GEO_KEYS = Object.keys(COUNTRY_COORDS).sort((a, b) => b.length - a.length);

/**
 * Resolves a target description string to approximate [latitude, longitude] coordinates.
 * Returns null if target is abstract, global ("all beings"), or not found.
 */
export function resolveTargetCoords(locationStr?: string | null): [number, number] | null {
  if (!locationStr) return null;
  const clean = locationStr.toLowerCase().replace(/[()[\]#\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!clean || NON_GEOGRAPHIC_TARGETS.has(clean)) return null;

  // Direct match
  if (COUNTRY_COORDS[clean]) {
    return COUNTRY_COORDS[clean];
  }

  // Segment by comma or semicolon if present (e.g. "East Java, Indonesia" -> checks "East Java" first)
  const segments = clean.split(/[,;]+/).map((s) => s.trim()).filter(Boolean);
  if (segments.length > 1) {
    for (const seg of segments) {
      if (COUNTRY_COORDS[seg]) {
        return COUNTRY_COORDS[seg];
      }
      for (const key of SORTED_GEO_KEYS) {
        const regex = new RegExp(`\\b${key}\\b`, 'i');
        if (regex.test(seg)) {
          return COUNTRY_COORDS[key];
        }
      }
    }
  }

  // Check longest match in sorted keys across entire string
  for (const key of SORTED_GEO_KEYS) {
    const regex = new RegExp(`\\b${key}\\b`, 'i');
    if (regex.test(clean)) {
      return COUNTRY_COORDS[key];
    }
  }

  // Tokenize by space
  const tokens = clean.split(/\s+/).filter((t) => t.length > 2);
  for (const token of tokens) {
    if (COUNTRY_COORDS[token]) {
      return COUNTRY_COORDS[token];
    }
  }

  return null;
}

/**
 * Converts spherical (lat, lon) coordinates to a 3D Cartesian vector on a sphere of radius R.
 */
/**
 * Globe picking (W3-C): a click is a pointer-down and pointer-up close in space
 * and time. Anything bigger is a drag (the user rotating the globe) and must
 * not move the observer. Thresholds are in CSS pixels and milliseconds.
 */
export const PICK_MAX_MOVE_PX = 5;
export const PICK_MAX_DURATION_MS = 500;

export interface GlobePickPoint {
  /** Pointer position in CSS pixels (clientX/clientY). */
  x: number;
  y: number;
  /** Event time in milliseconds (event.timeStamp). */
  t: number;
}

export interface GlobePickEvent extends GlobePickPoint {
  /** The surface UV from the r3f intersection; absent if there was no hit. */
  uv?: { x: number; y: number } | null;
}

export interface GlobePicker {
  onPointerDown(event: GlobePickPoint): void;
  /** Returns true when the gesture was a pick and `onPick` was called. */
  onPointerUp(event: GlobePickEvent): boolean;
  onPointerCancel(): void;
}

/**
 * A tiny gesture recognizer for the globe. `onPick` receives the latitude and
 * longitude resolved through `uvToLatLon` (the accepted W3-C0 inverse), never
 * a hand-rolled conversion. The returned handlers are stable; the component
 * owns one instance.
 */
export function createGlobePicker(onPick: (lat: number, lng: number) => void): GlobePicker {
  let down: GlobePickPoint | null = null;
  return {
    onPointerDown(event) {
      down = { x: event.x, y: event.y, t: event.t };
    },
    onPointerUp(event) {
      const start = down;
      down = null;
      if (start === null) return false;
      const moved = Math.hypot(event.x - start.x, event.y - start.y);
      const elapsed = event.t - start.t;
      if (moved > PICK_MAX_MOVE_PX || elapsed > PICK_MAX_DURATION_MS) return false;
      const uv = event.uv;
      if (!uv || !Number.isFinite(uv.x) || !Number.isFinite(uv.y)) return false;
      const { lat, lng } = uvToLatLon(uv.x, uv.y);
      onPick(lat, lng);
      return true;
    },
    onPointerCancel() {
      down = null;
    },
  };
}

export function latLonToVec3(lat: number, lon: number, radius = 2.05): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

/**
 * Old stylised rule, kept for the existing unit test and any caller that
 * still wants the decorative mapping. The globes do not use it.
 * Longitude is ecliptic longitude − 180. Latitude is 23.44°·sin(ecliptic longitude).
 * Real sub-points come from `useEarthState`.
 */
export function planetToLatLon(eclipticLongitude: number): [number, number] {
  const lon = eclipticLongitude - 180;
  const lat = 23.44 * Math.sin(eclipticLongitude * (Math.PI / 180));
  return [lat, lon];
}

/**
 * Builds a Quadratic Bezier arc between two 3D points on a sphere.
 */
export function createArcCurve(
  start: THREE.Vector3,
  end: THREE.Vector3,
  heightOffset = 0.4,
): THREE.QuadraticBezierCurve3 {
  const mid = new THREE.Vector3()
    .addVectors(start, end)
    .normalize()
    .multiplyScalar(2.05 + heightOffset);

  return new THREE.QuadraticBezierCurve3(
    start.clone().normalize().multiplyScalar(2.05),
    mid,
    end.clone().normalize().multiplyScalar(2.05),
  );
}

/**
 * Planet styling colors.
 */
export const PLANET_COLORS: Record<string, string> = {
  sun: '#fbbf24', moon: '#e2e8f0', mercury: '#94a3b8', venus: '#f472b6',
  mars: '#ef4444', jupiter: '#f59e0b', saturn: '#e2c97e',
  uranus: '#22d3ee', neptune: '#3b82f6', pluto: '#a78bfa',
  north_node: '#c084fc',
};

/**
 * Astrological aspect colors.
 */
export const ASPECT_COLORS: Record<string, string> = {
  Conjunction: '#ffd700', Trine: '#22d3ee', Sextile: '#a855f7',
  Square: '#ef4444', Opposition: '#f97316',
};

/**
 * Hue keyed to the dominant frequency in a broadcast's carrier list.
 *
 * The practitioner picks up a tonal accent on the World when they seal
 * a broadcast — pulses and arcs shift hue rather than always rendering
 * the same cyan. Buckets are inspired by the Solfeggio family (174→963 Hz)
 * so a 528 Hz "Mi" blessing glows green and a 741 Hz "Si" glows violet.
 *
 * Returns the canonical cyan fallback when no frequencies are provided.
 */
const TONE_BANDS: Array<[number, string]> = [
  [900, '#fbbf24'], // gold       — 963 Hz (Ut-high)
  [800, '#d946ef'], // magenta    — 852 Hz (Re-high)
  [700, '#8b5cf6'], // violet     — 741 Hz (Si)
  [580, '#22d3ee'], // cyan-blue  — 639 Hz (La)
  [450, '#22c55e'], // green      — 528 Hz (Mi / Sol)
  [400, '#6366f1'], // indigo     — 417 Hz (Fa)
  [300, '#818cf8'], // blue-violet — 396 Hz (Ut)
  [0, '#a78bfa'],   // violet     — 174/285 Hz (low)
];

const FALLBACK_TONE = '#38bdf8';

export function toneFromFrequencies(freqs: number[] | undefined): string {
  if (!freqs || freqs.length === 0) return FALLBACK_TONE;
  const max = freqs.reduce((a, b) => (b > a ? b : a));
  for (const [bound, color] of TONE_BANDS) {
    if (max >= bound) return color;
  }
  return FALLBACK_TONE;
}

/** Sphere radius shared by WorldEmanation and RadionicsGlobe. */
export const EARTH_SPHERE_RADIUS = 2;

/** Dawn line sits just above the sphere. */
export const DAWN_RADIUS = EARTH_SPHERE_RADIUS * 1.004;

/** Tiny-island outline sits just above the sphere, under the dawn line. */
export const ISLAND_RADIUS = EARTH_SPHERE_RADIUS * 1.003;

/** Rebuild the dawn line only after the sub-solar point moves at least this far. */
export const SUN_REBUILD_DEG = 0.05;

/**
 * Tiny-island outlines. Turn this off if a measurement crosses the Wave 0
 * thresholds (mount +100 ms, memory +50 MB, or steady frame +1 ms).
 * `?tinyIslands=0` or `?tinyIslands=1` overrides it for a screenshot.
 */
export const SHOW_TINY_ISLANDS = true;

const EARTH_TEX_W = 2048;
const EARTH_TEX_H = 1024;

/**
 * Navy ocean and green land, bright enough that a lit hemisphere stays
 * readable after MeshStandardMaterial shading. BT.709 luminance is about
 * 57 for the ocean and 180 for the land.
 */
export const EARTH_OCEAN = '#163e73';
export const EARTH_LAND = '#7dcc6a';

/** Ambient floor when the Sun is drawn. Night land stays faintly colored. */
export const EARTH_AMBIENT_LIT = 0.32;

let sharedTexture: THREE.CanvasTexture | null = null;
let textureRefs = 0;
let textureGeneration = 0;

function paintBlobEarth(ctx: CanvasRenderingContext2D): void {
  const sx = EARTH_TEX_W / 512;
  const sy = EARTH_TEX_H / 256;
  const grad = ctx.createLinearGradient(0, 0, 0, EARTH_TEX_H);
  grad.addColorStop(0, '#0e2a52');
  grad.addColorStop(0.3, '#123560');
  grad.addColorStop(0.5, EARTH_OCEAN);
  grad.addColorStop(0.7, '#123560');
  grad.addColorStop(1, '#0e2a52');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, EARTH_TEX_W, EARTH_TEX_H);

  ctx.fillStyle = EARTH_LAND;
  ctx.beginPath(); ctx.ellipse(100 * sx, 80 * sy, 110 * sx, 70 * sy, -0.2, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(130 * sx, 185 * sy, 35 * sx, 65 * sy, 0.1, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(260 * sx, 65 * sy, 55 * sx, 40 * sy, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(275 * sx, 160 * sy, 45 * sx, 90 * sy, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(370 * sx, 75 * sy, 120 * sx, 65 * sy, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(420 * sx, 200 * sy, 30 * sx, 22 * sy, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(430 * sx, 140 * sy, 18 * sx, 25 * sy, 0.3, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(455 * sx, 85 * sy, 8 * sx, 20 * sy, 0.2, 0, Math.PI * 2); ctx.fill();
}

function buildSharedTexture(): THREE.CanvasTexture {
  textureGeneration += 1;
  const generation = textureGeneration;
  const canvas = document.createElement('canvas');
  canvas.width = EARTH_TEX_W;
  canvas.height = EARTH_TEX_H;
  const ctx = canvas.getContext('2d');
  if (ctx) paintBlobEarth(ctx);
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  if (ctx) {
    void loadLand()
      .then((land) => {
        if (generation !== textureGeneration || sharedTexture !== tex) return;
        const paintCtx = canvas.getContext('2d');
        if (!paintCtx) return;
        paintLand(paintCtx, land, EARTH_TEX_W, EARTH_TEX_H, { ocean: EARTH_OCEAN, land: EARTH_LAND });
        tex.needsUpdate = true;
      })
      .catch(() => {
        /* Blob map stays. The land chunk can fail without blanking the globe. */
      });
  }
  return tex;
}

/** Retain the module-shared 2048×1024 Earth texture. Pair every call with releaseEarthTexture. */
export function retainEarthTexture(): THREE.CanvasTexture {
  if (!sharedTexture) sharedTexture = buildSharedTexture();
  textureRefs += 1;
  return sharedTexture;
}

/**
 * Same texture as retainEarthTexture. The name and the no-argument
 * CanvasTexture return are the existing call signature. This call retains;
 * the owner must release.
 */
export function createEarthTexture(): THREE.CanvasTexture {
  return retainEarthTexture();
}

type EarthTextureHold = {
  texture: THREE.CanvasTexture;
  live: boolean;
  counted: boolean;
};

/**
 * Development StrictMode renders a new function component twice and keeps
 * the second result. Each render retains. `mountedHolds` counts committed
 * holders; the microtask drops the retains whose render was discarded.
 */
let mountedHolds = 0;
let correctionScheduled = false;

function scheduleRetainCorrection(): void {
  if (correctionScheduled) return;
  correctionScheduled = true;
  queueMicrotask(() => {
    correctionScheduled = false;
    const extra = textureRefs - mountedHolds;
    for (let i = 0; i < extra; i += 1) releaseEarthTexture();
  });
}

/**
 * The shared Earth texture, retained before the first paint.
 * StrictMode runs the effect, its cleanup, then the effect again. The
 * cleanup only marks the hold; a microtask releases it if nothing remounted
 * that same hold. A later mount gets its own hold and its own retain.
 */
export function useSharedEarthTexture(): THREE.CanvasTexture {
  const [hold] = useState<EarthTextureHold>(() => ({
    texture: retainEarthTexture(),
    live: true,
    counted: false,
  }));
  useEffect(() => {
    if (!hold.counted) {
      hold.counted = true;
      mountedHolds += 1;
      scheduleRetainCorrection();
    }
    hold.live = true;
    return () => {
      hold.live = false;
      queueMicrotask(() => {
        if (hold.live) return;
        if (hold.counted) {
          hold.counted = false;
          mountedHolds -= 1;
        }
        releaseEarthTexture();
      });
    };
  }, [hold]);
  return hold.texture;
}

/** Material props that already include the map. Spread these on the first frame. */
export function earthSurfaceProps(map: THREE.CanvasTexture): {
  map: THREE.CanvasTexture;
  color: '#ffffff';
  roughness: 0.7;
  metalness: 0.1;
} {
  return { map, color: '#ffffff', roughness: 0.7, metalness: 0.1 };
}

/** A standard material whose map is attached at construction time. */
export function createEarthSurfaceMaterial(map: THREE.CanvasTexture): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial(earthSurfaceProps(map));
}

/** Drop one retain. At zero, dispose the texture and drop the canvas backing store. */
export function releaseEarthTexture(): void {
  if (textureRefs <= 0) return;
  textureRefs -= 1;
  if (textureRefs > 0 || !sharedTexture) return;
  const tex = sharedTexture;
  const canvas = tex.image instanceof HTMLCanvasElement ? tex.image : null;
  sharedTexture = null;
  textureGeneration += 1;
  tex.dispose();
  if (canvas) {
    canvas.width = 0;
    canvas.height = 0;
  }
}

export function sunMoved(prev: SubPoint | null, next: SubPoint): boolean {
  if (!prev) return true;
  return angularDistanceDeg(prev, next) >= SUN_REBUILD_DEG;
}

export function tinyIslandsEnabled(): boolean {
  if (typeof window !== 'undefined') {
    const flag = new URLSearchParams(window.location.search).get('tinyIslands');
    if (flag === '0') return false;
    if (flag === '1') return true;
  }
  return SHOW_TINY_ISLANDS;
}

export function buildTerminatorGeometry(sun: SubPoint, radius: number): THREE.BufferGeometry {
  const points = terminatorPoints(sun);
  const positions = new Float32Array(points.length * 3);
  const colors = new Float32Array(points.length * 3);
  const warm = new THREE.Color('#ffb15a');
  const dim = new THREE.Color('#5c6b86');
  for (let i = 0; i < points.length; i += 1) {
    const point = points[i];
    const vec = latLonToVec3(point.lat, point.lon, radius);
    positions[i * 3] = vec.x;
    positions[i * 3 + 1] = vec.y;
    positions[i * 3 + 2] = vec.z;
    const color = point.side === 'sunrise' ? warm : dim;
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  return geometry;
}

export function buildSmallIslandGeometry(land: LandData, radius: number): THREE.BufferGeometry {
  const { rings } = smallIslandVertices(land);
  const positions: number[] = [];
  for (const ring of rings) {
    const count = ring.length / 2;
    if (count < 2) continue;
    const closed = count > 2 && ring[0] === ring[ring.length - 2] && ring[1] === ring[ring.length - 1];
    const edges = closed ? count - 1 : count;
    for (let i = 0; i < edges; i += 1) {
      const j = (i + 1) % count;
      const a = latLonToVec3(ring[i * 2 + 1], ring[i * 2], radius);
      const b = latLonToVec3(ring[j * 2 + 1], ring[j * 2], radius);
      positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  return geometry;
}

export interface DrawnBody {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

export function drawnBodies(state: EarthState, fetchedAt: number, nowMs: number): DrawnBody[] {
  const dtSeconds = (nowMs - fetchedAt) / 1000;
  return [state.sun, state.moon, ...state.planets].map((body) => {
    const point = extrapolateSubPoint(body, dtSeconds);
    return { id: body.id, name: body.name, lat: point.lat, lon: point.lon };
  });
}

export function subPointMarker(body: DrawnBody): { position: THREE.Vector3; color: string; size: number } {
  return {
    position: latLonToVec3(body.lat, body.lon),
    color: PLANET_COLORS[body.id] || '#ffffff',
    size: body.id === 'sun' ? 0.08 : body.id === 'moon' ? 0.07 : 0.045,
  };
}

export function findDrawnBody(bodies: DrawnBody[], name: string): DrawnBody | null {
  const key = name.trim().toLowerCase();
  return bodies.find((body) => body.id === key || (body.name || '').toLowerCase() === key) ?? null;
}
