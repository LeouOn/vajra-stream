/**
 * worldEmanationHelpers.ts — Pure geographic and 3D projection helpers
 * for Earth emanation, radionics globe, and target coordinate resolution.
 */
import * as THREE from 'three';

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
 * Ecliptic longitude → sub-planetary point on globe.
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

/**
 * Procedural Earth texture generation.
 */
export function createEarthTexture(): THREE.CanvasTexture {
  const size = 512;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size / 2;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new THREE.CanvasTexture(canvas);

  // Ocean gradient
  const grad = ctx.createLinearGradient(0, 0, 0, size / 2);
  grad.addColorStop(0, '#0a1628');
  grad.addColorStop(0.3, '#0d2137');
  grad.addColorStop(0.5, '#0f2b45');
  grad.addColorStop(0.7, '#0d2137');
  grad.addColorStop(1, '#0a1628');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size / 2);

  // Simplified continent blobs
  ctx.fillStyle = '#1a3a2a';
  // North America
  ctx.beginPath(); ctx.ellipse(100, 80, 110, 70, -0.2, 0, Math.PI * 2); ctx.fill();
  // South America
  ctx.beginPath(); ctx.ellipse(130, 185, 35, 65, 0.1, 0, Math.PI * 2); ctx.fill();
  // Europe
  ctx.beginPath(); ctx.ellipse(260, 65, 55, 40, 0, 0, Math.PI * 2); ctx.fill();
  // Africa
  ctx.beginPath(); ctx.ellipse(275, 160, 45, 90, 0, 0, Math.PI * 2); ctx.fill();
  // Asia
  ctx.beginPath(); ctx.ellipse(370, 75, 120, 65, 0, 0, Math.PI * 2); ctx.fill();
  // Australia
  ctx.beginPath(); ctx.ellipse(420, 200, 30, 22, 0, 0, Math.PI * 2); ctx.fill();
  // Southeast Asia islands
  ctx.beginPath(); ctx.ellipse(430, 140, 18, 25, 0.3, 0, Math.PI * 2); ctx.fill();
  // Japan
  ctx.beginPath(); ctx.ellipse(455, 85, 8, 20, 0.2, 0, Math.PI * 2); ctx.fill();

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  return tex;
}
