/**
 * Earth & Sky wave 3 — the validated `/night-sky` client (row W3-D2a).
 *
 * The dome used to type-assert the response and then throw during render when
 * `moon.phase_name` or `planets.filter` was missing. This module validates the
 * whole shape the dome reads, names the first bad path, and never casts.
 * 422/503/other HTTP/network failures become typed `NightSkyError`s. A newer
 * call supersedes an older one (AbortController + generation), so a slow older
 * answer can never overwrite a newer place.
 */
import { apiUrl } from '../utils/api';
import { parseInstant } from './skyClock';

export type NightSkyErrorKind =
  | 'invalid-input'
  | 'invalid-response'
  | 'unavailable'
  | 'network'
  | 'http'
  | 'stale';

export class NightSkyError extends Error {
  readonly kind: NightSkyErrorKind;
  readonly status?: number;

  constructor(kind: NightSkyErrorKind, message: string, status?: number) {
    super(message);
    this.name = 'NightSkyError';
    this.kind = kind;
    this.status = status;
  }
}

export interface NightSkyObserver {
  latitude: number;
  longitude: number;
  local_sidereal_time_deg: number;
  local_sidereal_time_hms: string;
}

export interface NightSkyMoon {
  phase_name: string;
  illumination: number;
}

export interface NightSkyPlanet {
  id: string;
  name: string;
  glyph: string;
  altitude: number;
  azimuth: number;
  sign: string;
  sign_glyph: string;
  visible: boolean;
  color: string;
  esoteric_quality: string;
}

export interface NightSkyStar {
  id: string;
  name: string;
  altitude: number;
  azimuth: number;
  magnitude: number;
  visible: boolean;
  color: string;
  nakshatra: string;
  quality: string;
  /** J2000 catalogue position (degrees); absent until the backend adds it. */
  ra_j2000?: number;
  dec_j2000?: number;
}

/** Every field the dome reads; anything else in the JSON is ignored. */
export interface NightSky {
  timestamp_utc: string;
  observer: NightSkyObserver;
  moon: NightSkyMoon;
  planets: NightSkyPlanet[];
  visible_planets_count: number;
  sacred_stars: NightSkyStar[];
  visible_stars_count: number;
  provenance: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function invalid(path: string, detail: string): never {
  throw new NightSkyError('invalid-response', `night-sky ${path} ${detail}`);
}

function requireObject(value: unknown, path: string): Record<string, unknown> {
  if (!isRecord(value)) invalid(path, 'must be an object');
  return value;
}

function requireString(value: unknown, path: string): string {
  if (typeof value !== 'string' || value.length === 0) invalid(path, 'must be a non-empty string');
  return value;
}

function requireNumber(value: unknown, path: string, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    invalid(path, `must be a finite number in [${min}, ${max}]`);
  }
  return value;
}

function requireBoolean(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') invalid(path, 'must be a boolean');
  return value;
}

function requireCount(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) {
    invalid(path, 'must be a non-negative integer');
  }
  return value;
}

function decodeObserver(raw: unknown): NightSkyObserver {
  const record = requireObject(raw, 'observer');
  return {
    latitude: requireNumber(record.latitude, 'observer.latitude', -90, 90),
    longitude: requireNumber(record.longitude, 'observer.longitude', -180, 180),
    local_sidereal_time_deg: requireNumber(
      record.local_sidereal_time_deg,
      'observer.local_sidereal_time_deg',
      0,
      360,
    ),
    local_sidereal_time_hms: requireString(
      record.local_sidereal_time_hms,
      'observer.local_sidereal_time_hms',
    ),
  };
}

function decodeMoon(raw: unknown): NightSkyMoon {
  const record = requireObject(raw, 'moon');
  return {
    phase_name: requireString(record.phase_name, 'moon.phase_name'),
    illumination: requireNumber(record.illumination, 'moon.illumination', 0, 100),
  };
}

function decodePlanet(raw: unknown, index: number): NightSkyPlanet {
  const path = `planets[${index}]`;
  const record = requireObject(raw, path);
  return {
    id: requireString(record.id, `${path}.id`),
    name: requireString(record.name, `${path}.name`),
    glyph: requireString(record.glyph, `${path}.glyph`),
    altitude: requireNumber(record.altitude, `${path}.altitude`, -90, 90),
    azimuth: requireNumber(record.azimuth, `${path}.azimuth`, 0, 360),
    sign: requireString(record.sign, `${path}.sign`),
    sign_glyph: requireString(record.sign_glyph, `${path}.sign_glyph`),
    visible: requireBoolean(record.visible, `${path}.visible`),
    color: requireString(record.color, `${path}.color`),
    esoteric_quality: requireString(record.esoteric_quality, `${path}.esoteric_quality`),
  };
}

function decodeStar(raw: unknown, index: number): NightSkyStar {
  const path = `sacred_stars[${index}]`;
  const record = requireObject(raw, path);
  const star: NightSkyStar = {
    id: requireString(record.id, `${path}.id`),
    name: requireString(record.name, `${path}.name`),
    altitude: requireNumber(record.altitude, `${path}.altitude`, -90, 90),
    azimuth: requireNumber(record.azimuth, `${path}.azimuth`, 0, 360),
    magnitude: requireNumber(record.magnitude, `${path}.magnitude`, -20, 30),
    visible: requireBoolean(record.visible, `${path}.visible`),
    color: requireString(record.color, `${path}.color`),
    nakshatra: requireString(record.nakshatra, `${path}.nakshatra`),
    quality: requireString(record.quality, `${path}.quality`),
  };
  // Additive in W3-D2b: optional J2000 position, validated when present. The
  // whole pair is optional so a backend that has not added it yet still works.
  if (record.ra_j2000 !== undefined) {
    star.ra_j2000 = requireNumber(record.ra_j2000, `${path}.ra_j2000`, 0, 360);
  }
  if (record.dec_j2000 !== undefined) {
    star.dec_j2000 = requireNumber(record.dec_j2000, `${path}.dec_j2000`, -90, 90);
  }
  return star;
}

/** Validate an unknown `/night-sky` payload; throws NightSkyError with a path. */
export function decodeNightSky(raw: unknown): NightSky {
  const record = requireObject(raw, 'response');
  const timestamp_utc = requireString(record.timestamp_utc, 'timestamp_utc');
  try {
    parseInstant(timestamp_utc);
  } catch {
    invalid('timestamp_utc', 'must be an ISO-8601 instant with an explicit zone');
  }

  const observer = decodeObserver(record.observer);
  const moon = decodeMoon(record.moon);

  if (!Array.isArray(record.planets)) invalid('planets', 'must be an array');
  const planets = record.planets.map((planet, index) => decodePlanet(planet, index));

  if (!Array.isArray(record.sacred_stars)) invalid('sacred_stars', 'must be an array');
  const sacred_stars = record.sacred_stars.map((star, index) => decodeStar(star, index));

  if (!isRecord(record.provenance)) invalid('provenance', 'must be an object');

  return {
    timestamp_utc,
    observer,
    moon,
    planets,
    visible_planets_count: requireCount(record.visible_planets_count, 'visible_planets_count'),
    sacred_stars,
    visible_stars_count: requireCount(record.visible_stars_count, 'visible_stars_count'),
    provenance: record.provenance,
  };
}

async function detailOf(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (isRecord(body) && typeof body.detail === 'string' && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    /* a non-JSON error body is fine; use the status message */
  }
  return null;
}

let generation = 0;
let activeController: AbortController | null = null;

/** Abort the in-flight request and make it stale (dome unmount / place change). */
export function cancelNightSkyRequest(): void {
  generation += 1;
  activeController?.abort();
  activeController = null;
}

/**
 * Fetch and validate the geocentric sky for an observer.
 *
 * @param lat latitude in degrees [-90, 90]
 * @param lng longitude in degrees (finite)
 * @param atIso optional ISO-8601 instant with an explicit zone (live if absent)
 */
export async function fetchNightSky(lat: number, lng: number, atIso?: string): Promise<NightSky> {
  if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
    throw new NightSkyError('invalid-input', 'The observer latitude must be between -90 and 90.');
  }
  if (!Number.isFinite(lng)) {
    throw new NightSkyError('invalid-input', 'The observer longitude must be a finite number.');
  }

  const query = new URLSearchParams({ latitude: String(lat), longitude: String(lng) });
  if (atIso !== undefined) {
    let atMs: number;
    try {
      atMs = parseInstant(atIso);
    } catch {
      throw new NightSkyError(
        'invalid-input',
        'The sky time must be ISO-8601 with an explicit zone (Z or +hh:mm).',
      );
    }
    query.set('datetime_str', new Date(atMs).toISOString());
  }

  const myGeneration = (generation += 1);
  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;

  let response: Response;
  try {
    response = await fetch(`${apiUrl('/astrology/night-sky')}?${query.toString()}`, {
      signal: controller.signal,
    });
  } catch {
    if (myGeneration !== generation || controller.signal.aborted) {
      throw new NightSkyError('stale', 'A newer night-sky request replaced this one.');
    }
    throw new NightSkyError('network', 'Could not reach the server for the night sky.');
  }
  if (myGeneration !== generation) {
    throw new NightSkyError('stale', 'A newer night-sky request replaced this one.');
  }

  if (!response.ok) {
    const detail = await detailOf(response);
    if (response.status === 422) {
      throw new NightSkyError(
        'invalid-input',
        detail ?? 'The server rejected the night-sky request (422).',
        422,
      );
    }
    if (response.status === 503) {
      throw new NightSkyError(
        'unavailable',
        detail ?? 'The ephemeris is unavailable (503).',
        503,
      );
    }
    throw new NightSkyError(
      'http',
      detail ?? `The night-sky request failed (HTTP ${response.status}).`,
      response.status,
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new NightSkyError('invalid-response', 'The night-sky response body was not JSON.');
  }
  if (myGeneration !== generation) {
    throw new NightSkyError('stale', 'A newer night-sky request replaced this one.');
  }

  try {
    return decodeNightSky(body);
  } catch (error) {
    if (error instanceof NightSkyError) throw error;
    const detail = error instanceof Error ? error.message : String(error);
    throw new NightSkyError('invalid-response', `The night-sky response was not valid: ${detail}.`);
  }
}
