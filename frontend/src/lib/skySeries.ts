/**
 * Earth & Sky wave 3 — the pure series maths behind scrubbing (row W3-D1).
 *
 * The backend ships sub-points, not RA/Dec: for a body at an instant,
 *   Dec = lat,  RA = wrap360(lon + gast_deg)
 * with the GAST apparent. Positions are geocentric (the same convention the
 * live `/night-sky` path uses), so the client only has to interpolate and
 * rotate. Longitudes and GAST wrap at +-180 / 360; interpolation is width-aware
 * (`wrap180(b - a)`), never raw subtraction.
 *
 * No React, no network, no timers: `earthSeriesClient.ts` owns the request.
 */
import { equatorialToHorizontal } from './sky';
import { wrapLon } from './earth';
import { parseInstant } from './skyClock';

const EXPECTED_PLANET_IDS = [
  'mercury',
  'venus',
  'mars',
  'jupiter',
  'saturn',
  'uranus',
  'neptune',
  'pluto',
] as const;

const MIN_STEP_SECONDS = 60;
const MAX_STEP_SECONDS = 3600;
const MAX_SAMPLES = 288;

export interface SeriesBody {
  id: string;
  lat: number;
  lon: number;
}

export interface SeriesSample {
  /** The instant as sent, e.g. "...Z" or "...+00:00". */
  at: string;
  /** `parseInstant(at)`, so callers never re-parse per frame. */
  atMs: number;
  gast: number;
  sun: SeriesBody;
  moon: SeriesBody;
  planets: SeriesBody[];
}

export interface SkySeries {
  ephemeris: string;
  siderealTime: 'apparent';
  start: string;
  end: string;
  stepSeconds: number;
  count: number;
  samples: SeriesSample[];
  provenance: Record<string, unknown>;
}

export interface InterpolatedBody {
  id: string;
  lat: number;
  lon: number;
  ra: number;
  dec: number;
}

function wrap360(deg: number): number {
  const wrapped = deg % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function fail(path: string, detail: string): never {
  throw new TypeError(`skySeries: ${path} ${detail}`);
}

function requireRecord(value: unknown, path: string): Record<string, unknown> {
  if (!isRecord(value)) fail(path, 'must be an object');
  return value;
}

function requireString(value: unknown, path: string, allowEmpty = false): string {
  if (typeof value !== 'string') fail(path, 'must be a string');
  if (!allowEmpty && value.length === 0) fail(path, 'must not be empty');
  return value;
}

function requireFinite(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) fail(path, 'must be a finite number');
  return value;
}

function requireIntegerInRange(value: unknown, path: string, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < min || value > max) {
    fail(path, `must be an integer in [${min}, ${max}]`);
  }
  return value;
}

function decodeBody(value: unknown, path: string, expectedId?: string): SeriesBody {
  const record = requireRecord(value, path);
  const id = requireString(record.id, `${path}.id`);
  if (expectedId !== undefined && id !== expectedId) fail(`${path}.id`, `must be "${expectedId}"`);
  const lat = requireFinite(record.lat, `${path}.lat`);
  if (lat < -90 || lat > 90) fail(`${path}.lat`, 'must be in [-90, 90]');
  const lon = requireFinite(record.lon, `${path}.lon`);
  if (lon < -180 || lon > 180) fail(`${path}.lon`, 'must be in [-180, 180]');
  return { id, lat, lon };
}

/**
 * Validate an unknown `/astrology/earth-state/series` payload.
 *
 * Throws `TypeError` naming the path of the first bad field; never casts.
 * Requires an apparent-GAST series, 60..3600 s steps, 2..288 samples at exactly
 * that uniform spacing, and the Sun, Moon and the eight planets in every sample
 * (same order throughout).
 */
export function decodeSeries(raw: unknown): SkySeries {
  const record = requireRecord(raw, 'response');
  const ephemeris = requireString(record.ephemeris, 'ephemeris');
  if (record.sidereal_time !== 'apparent') fail('sidereal_time', 'must be "apparent"');

  const start = requireString(record.start, 'start');
  const end = requireString(record.end, 'end');
  let startMs: number;
  let endMs: number;
  try {
    startMs = parseInstant(start);
  } catch {
    fail('start', 'must be an ISO-8601 instant with an explicit zone');
  }
  try {
    endMs = parseInstant(end);
  } catch {
    fail('end', 'must be an ISO-8601 instant with an explicit zone');
  }
  if (startMs > endMs) fail('end', 'must not be before start');

  const stepSeconds = requireIntegerInRange(
    record.step_seconds,
    'step_seconds',
    MIN_STEP_SECONDS,
    MAX_STEP_SECONDS,
  );
  const count = requireIntegerInRange(record.count, 'count', 2, MAX_SAMPLES);
  if (!Array.isArray(record.samples)) fail('samples', 'must be an array');
  const rawSamples = record.samples;
  if (rawSamples.length !== count) fail('count', `must equal samples.length (${rawSamples.length})`);
  if (!isRecord(record.provenance)) fail('provenance', 'must be an object');

  const stepMs = stepSeconds * 1000;
  const expectedPlanets = new Set<string>(EXPECTED_PLANET_IDS);
  const samples: SeriesSample[] = [];
  let planetOrder: string[] | null = null;
  let previousMs = Number.NaN;

  for (let index = 0; index < rawSamples.length; index += 1) {
    const path = `samples[${index}]`;
    const sample = requireRecord(rawSamples[index], path);
    const at = requireString(sample.at, `${path}.at`);
    let atMs: number;
    try {
      atMs = parseInstant(at);
    } catch {
      fail(`${path}.at`, 'must be an ISO-8601 instant with an explicit zone');
    }
    if (index === 0) {
      if (startMs > atMs) fail(`${path}.at`, 'must not be before start');
    } else {
      if (atMs <= previousMs) fail(`${path}.at`, 'must be strictly increasing');
      if (atMs - previousMs !== stepMs) {
        fail(`${path}.at`, `must be exactly ${stepSeconds} s after the previous sample`);
      }
    }
    if (index === rawSamples.length - 1 && atMs > endMs) fail(`${path}.at`, 'must not be after end');
    previousMs = atMs;

    const gast = requireFinite(sample.gast_deg, `${path}.gast_deg`);
    if (gast < 0 || gast >= 360) fail(`${path}.gast_deg`, 'must be in [0, 360)');

    const sun = decodeBody(sample.sun, `${path}.sun`, 'sun');
    const moon = decodeBody(sample.moon, `${path}.moon`, 'moon');

    if (!Array.isArray(sample.planets)) fail(`${path}.planets`, 'must be an array');
    if (sample.planets.length !== EXPECTED_PLANET_IDS.length) {
      fail(`${path}.planets`, `must contain exactly ${EXPECTED_PLANET_IDS.length} planets`);
    }
    const planets = sample.planets.map((planet, planetIndex) => {
      const decoded = decodeBody(planet, `${path}.planets[${planetIndex}]`);
      if (!expectedPlanets.has(decoded.id)) fail(`${path}.planets`, `unknown planet id "${decoded.id}"`);
      return decoded;
    });
    const ids = planets.map((planet) => planet.id);
    if (new Set(ids).size !== ids.length) fail(`${path}.planets`, 'must not repeat a planet id');
    if (planetOrder === null) planetOrder = ids;
    else if (ids.some((id, planetIndex) => id !== planetOrder?.[planetIndex])) {
      fail(`${path}.planets`, 'must use the same planet order as samples[0]');
    }

    samples.push({ at, atMs, gast, sun, moon, planets });
  }

  return {
    ephemeris,
    siderealTime: 'apparent',
    start,
    end,
    stepSeconds,
    count,
    samples,
    provenance: record.provenance,
  };
}

/** Width-aware interpolation of an angle that wraps at 360 (GAST). */
function interpolateAngle(a: number, b: number, t: number): number {
  return wrap360(a + wrapLon(b - a) * t);
}

/** Width-aware interpolation of a longitude in [-180, 180). */
function interpolateLon(a: number, b: number, t: number): number {
  return wrapLon(a + wrapLon(b - a) * t);
}

function reconstruct(id: string, lat: number, lon: number, gast: number): InterpolatedBody {
  return { id, lat, lon, ra: wrap360(lon + gast), dec: lat };
}

/**
 * The bodies at `instantMs`, linearly interpolated between the two bracketing
 * samples. Returns the Sun, the Moon and the eight planets. `RangeError` when
 * the instant is outside [first, last]; `TypeError` for a non-finite instant.
 */
export function bodiesAt(series: SkySeries, instantMs: number): InterpolatedBody[] {
  if (!Number.isFinite(instantMs)) fail('instantMs', 'must be a finite epoch-millisecond number');
  const { samples } = series;
  if (instantMs < samples[0].atMs || instantMs > samples[samples.length - 1].atMs) {
    throw new RangeError('skySeries: instant is outside the series window');
  }

  // Greatest index whose instant is <= the requested instant.
  let low = 0;
  let high = samples.length - 1;
  while (low < high) {
    const middle = (low + high + 1) >> 1;
    if (samples[middle].atMs <= instantMs) low = middle;
    else high = middle - 1;
  }
  const before = samples[low];
  const after = low + 1 < samples.length ? samples[low + 1] : before;
  const t = before === after ? 0 : (instantMs - before.atMs) / (after.atMs - before.atMs);
  const gast = interpolateAngle(before.gast, after.gast, t);

  const bodies: InterpolatedBody[] = [];
  const pairs: [SeriesBody, SeriesBody][] = [
    [before.sun, after.sun],
    [before.moon, after.moon],
    ...before.planets.map((planet, index) => [planet, after.planets[index]] as [SeriesBody, SeriesBody]),
  ];
  for (const [a, b] of pairs) {
    const lat = a.lat + (b.lat - a.lat) * t;
    const lon = interpolateLon(a.lon, b.lon, t);
    bodies.push(reconstruct(a.id, lat, lon, gast));
  }
  return bodies;
}

/**
 * Alt/az for a body as seen from (observerLat, observerLng), using the same
 * spherical trigonometry as `core/celestial_sky.py` and the live dome path.
 * LST = GAST + observer longitude (east positive); az is North 0, East 90.
 */
export function horizontalOf(
  body: InterpolatedBody,
  gast: number,
  observerLat: number,
  observerLng: number,
): { alt: number; az: number } {
  const lst = wrap360(gast + observerLng);
  return equatorialToHorizontal(body.ra, body.dec, lst, observerLat);
}
