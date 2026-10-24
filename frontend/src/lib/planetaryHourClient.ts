/**
 * Earth & Sky wave 3 — the planetary-hour client (row W3-J).
 *
 * One validated read of `GET /astrology/planetary-hour`: which planetary hour it is at a place and instant (ruler,
 * day or night hour, its bounds and the time left). The response is checked, never cast. Where no sunrise-to-sunrise
 * day brackets the instant (polar day or night) the backend answers `hour: null` with a reason; that is a valid
 * answer here, and an hour is never invented. A payload that is not labelled `computed` is refused as invalid, so an
 * estimate can never be shown as an hour.
 *
 * 422, 503, other HTTP failures and network failures become typed `PlanetaryHourError`s. A newer call supersedes an
 * older one (the older is aborted; whatever it was doing it ends as `stale`, never as a real error), a request that
 * has not finished within 15 s is abandoned as a `network` failure, and `cancelPlanetaryHourRequest()` stops the
 * one in flight (unmount). Single-flight by design: exactly one readout is expected to be mounted.
 */
import { apiUrl } from '../utils/api';
import { wrapLon } from './earth';
import { parseInstant } from './skyClock';

export type PlanetaryHourErrorKind =
  | 'invalid-input'
  | 'invalid-response'
  | 'unavailable'
  | 'network'
  | 'http'
  | 'stale';

export class PlanetaryHourError extends Error {
  readonly kind: PlanetaryHourErrorKind;
  readonly status?: number;

  constructor(kind: PlanetaryHourErrorKind, message: string, status?: number) {
    super(message);
    this.name = 'PlanetaryHourError';
    this.kind = kind;
    this.status = status;
  }
}

export const PLANETARY_RULERS = ['Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus', 'Mercury', 'Moon'] as const;
export type PlanetaryRuler = (typeof PLANETARY_RULERS)[number];

export interface PlanetaryHourSolarDay {
  sunrise: string;
  sunset: string;
  nextSunrise: string;
  /** The ruler of the weekday of the local mean solar date of the sunrise that began this solar day. */
  dayRuler: PlanetaryRuler;
}

export interface PlanetaryHourDetail {
  ruler: PlanetaryRuler;
  isDaytime: boolean;
  /** 1-12 within the day or the night part. */
  index: number;
  startsAt: string;
  endsAt: string;
  startsAtMs: number;
  endsAtMs: number;
  lengthSeconds: number;
  /** At the instant asked for; the readout recomputes it against the shown instant as time passes. */
  timeRemainingSeconds: number;
}

/** The validated backend payload. `hour` and `solarDay` are both null where there is no sunrise-to-sunrise day. */
export interface PlanetaryHour {
  at: string;
  atMs: number;
  latitude: number;
  longitude: number;
  solarDay: PlanetaryHourSolarDay | null;
  hour: PlanetaryHourDetail | null;
  /** Why there is no hour; null when there is one. */
  reason: string | null;
  provenance: Record<string, unknown>;
}

/** Slack for the millisecond rounding of the boundaries the backend prints. */
const MS_SLACK = 2;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function invalidResponse(detail: string): PlanetaryHourError {
  return new PlanetaryHourError('invalid-response', `The planetary-hour response was not valid: ${detail}.`);
}

function requireInstant(value: unknown, field: string): { text: string; ms: number } {
  if (typeof value !== 'string') throw invalidResponse(`${field} must be a string`);
  try {
    return { text: value, ms: parseInstant(value) };
  } catch {
    throw invalidResponse(`${field} is not an ISO-8601 instant with a zone`);
  }
}

function requireNumber(value: unknown, field: string, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw invalidResponse(`${field} must be a finite number in [${min}, ${max}]`);
  }
  return value;
}

function requireRuler(value: unknown, field: string): PlanetaryRuler {
  if (typeof value !== 'string' || !(PLANETARY_RULERS as readonly string[]).includes(value)) {
    throw invalidResponse(`${field} must be one of ${PLANETARY_RULERS.join(', ')}`);
  }
  return value as PlanetaryRuler;
}

function decodeSolarDay(raw: unknown): PlanetaryHourSolarDay {
  if (!isRecord(raw)) throw invalidResponse('solar_day must be an object or null');
  const sunrise = requireInstant(raw.sunrise, 'solar_day.sunrise');
  const sunset = requireInstant(raw.sunset, 'solar_day.sunset');
  const nextSunrise = requireInstant(raw.next_sunrise, 'solar_day.next_sunrise');
  if (!(sunrise.ms < sunset.ms && sunset.ms < nextSunrise.ms)) {
    throw invalidResponse('solar_day must run sunrise, then sunset, then the next sunrise');
  }
  return {
    sunrise: sunrise.text,
    sunset: sunset.text,
    nextSunrise: nextSunrise.text,
    dayRuler: requireRuler(raw.day_ruler, 'solar_day.day_ruler'),
  };
}

function decodeHour(raw: unknown, atMs: number): PlanetaryHourDetail {
  if (!isRecord(raw)) throw invalidResponse('hour must be an object or null');
  const startsAt = requireInstant(raw.starts_at, 'hour.starts_at');
  const endsAt = requireInstant(raw.ends_at, 'hour.ends_at');
  if (!(startsAt.ms < endsAt.ms)) throw invalidResponse('hour.ends_at must be after hour.starts_at');
  if (atMs < startsAt.ms - MS_SLACK || atMs > endsAt.ms + MS_SLACK) {
    throw invalidResponse('hour does not contain the instant that was asked for');
  }
  if (typeof raw.is_daytime !== 'boolean') throw invalidResponse('hour.is_daytime must be a boolean');
  const index = raw.index;
  if (typeof index !== 'number' || !Number.isInteger(index) || index < 1 || index > 12) {
    throw invalidResponse('hour.index must be an integer in [1, 12]');
  }
  const lengthSeconds = requireNumber(raw.length_seconds, 'hour.length_seconds', 0, 86_400);
  if (lengthSeconds <= 0) throw invalidResponse('hour.length_seconds must be positive');
  const timeRemainingSeconds = requireNumber(raw.time_remaining_seconds, 'hour.time_remaining_seconds', 0, 86_400);
  if (timeRemainingSeconds > lengthSeconds + MS_SLACK / 1000) {
    throw invalidResponse('hour.time_remaining_seconds must not exceed hour.length_seconds');
  }
  return {
    ruler: requireRuler(raw.ruler, 'hour.ruler'),
    isDaytime: raw.is_daytime,
    index,
    startsAt: startsAt.text,
    endsAt: endsAt.text,
    startsAtMs: startsAt.ms,
    endsAtMs: endsAt.ms,
    lengthSeconds,
    timeRemainingSeconds,
  };
}

/** Validate an unknown payload; throws PlanetaryHourError rather than casting. */
export function validatePlanetaryHour(raw: unknown): PlanetaryHour {
  if (!isRecord(raw)) throw invalidResponse('expected an object');
  const at = requireInstant(raw.at, 'at');
  const latitude = requireNumber(raw.latitude, 'latitude', -90, 90);
  const longitude = requireNumber(raw.longitude, 'longitude', -180, 180);

  const provenance = raw.provenance;
  if (!isRecord(provenance)) throw invalidResponse('missing provenance');
  for (const field of ['at', 'solar_day', 'hour']) {
    if (provenance[field] !== 'computed') {
      throw invalidResponse(`provenance.${field} must be "computed" (an estimate is never shown as an hour)`);
    }
  }

  const hasHour = raw.hour !== null && raw.hour !== undefined;
  const hasDay = raw.solar_day !== null && raw.solar_day !== undefined;
  if (raw.hour === undefined || raw.solar_day === undefined || raw.reason === undefined) {
    throw invalidResponse('hour, solar_day and reason must all be present');
  }
  if (hasHour !== hasDay) throw invalidResponse('hour and solar_day must both be present or both null');
  if (hasHour) {
    if (raw.reason !== null) throw invalidResponse('reason must be null when there is an hour');
    return {
      at: at.text,
      atMs: at.ms,
      latitude,
      longitude,
      solarDay: decodeSolarDay(raw.solar_day),
      hour: decodeHour(raw.hour, at.ms),
      reason: null,
      provenance,
    };
  }
  if (typeof raw.reason !== 'string' || raw.reason.trim().length === 0) {
    throw invalidResponse('reason must say why there is no hour');
  }
  return {
    at: at.text,
    atMs: at.ms,
    latitude,
    longitude,
    solarDay: null,
    hour: null,
    reason: raw.reason,
    provenance,
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

/** A request that has not finished (headers and body) by now is abandoned as a `network` failure. */
const REQUEST_TIMEOUT_MS = 15_000;

/** Monotonic request generation: a newer call makes every older one stale. */
let generation = 0;
let activeController: AbortController | null = null;

/** Abort the in-flight request and make it stale (readout unmount). */
export function cancelPlanetaryHourRequest(): void {
  generation += 1;
  activeController?.abort();
  activeController = null;
}

/**
 * Fetch and validate the planetary hour for an observer at an instant.
 *
 * @param lat latitude in degrees [-90, 90]
 * @param lng longitude in degrees, any finite value: wrapped into [-180, 180) before the request (the route
 *   refuses a longitude outside that range); an in-range value is sent unchanged
 * @param atIso ISO-8601 instant with an explicit zone
 */
export async function fetchPlanetaryHour(lat: number, lng: number, atIso: string): Promise<PlanetaryHour> {
  if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
    throw new PlanetaryHourError('invalid-input', 'The observer latitude must be between -90 and 90.');
  }
  if (!Number.isFinite(lng)) {
    throw new PlanetaryHourError('invalid-input', 'The observer longitude must be a finite number.');
  }
  let atMs: number;
  try {
    atMs = parseInstant(atIso);
  } catch {
    throw new PlanetaryHourError('invalid-input', 'The time must be ISO-8601 with an explicit zone (Z or +hh:mm).');
  }

  const sentLng = lng >= -180 && lng < 180 ? lng : wrapLon(lng);
  const query = new URLSearchParams({
    latitude: String(lat),
    longitude: String(sentLng),
    datetime_str: new Date(atMs).toISOString(),
  });

  const myGeneration = (generation += 1);
  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  // Why this request must stop being acted on, or null if it is still the live one. A newer call or a cancel
  // makes it stale (checked first, so a superseded request that also timed out is still just stale).
  const interrupted = (): PlanetaryHourError | null => {
    if (myGeneration !== generation) {
      return new PlanetaryHourError('stale', 'A newer planetary-hour request replaced this one.');
    }
    if (timedOut) {
      return new PlanetaryHourError(
        'network',
        `The planetary-hour request timed out after ${REQUEST_TIMEOUT_MS / 1000} s.`,
      );
    }
    if (controller.signal.aborted) {
      return new PlanetaryHourError('stale', 'A newer planetary-hour request replaced this one.');
    }
    return null;
  };

  try {
    let response: Response;
    try {
      response = await fetch(`${apiUrl('/astrology/planetary-hour')}?${query.toString()}`, {
        signal: controller.signal,
      });
    } catch {
      throw interrupted() ?? new PlanetaryHourError('network', 'Could not reach the server for the planetary hour.');
    }
    const afterHeaders = interrupted();
    if (afterHeaders) throw afterHeaders;

    if (!response.ok) {
      const detail = await detailOf(response);
      // The error body is read after the last check above: a request superseded (or timed out) meanwhile must
      // not be reported as unavailable/http/invalid-input.
      const afterErrorBody = interrupted();
      if (afterErrorBody) throw afterErrorBody;
      if (response.status === 422) {
        throw new PlanetaryHourError('invalid-input', detail ?? 'The server rejected the request (422).', 422);
      }
      if (response.status === 503) {
        throw new PlanetaryHourError('unavailable', detail ?? 'Ephemeris unavailable (503).', 503);
      }
      throw new PlanetaryHourError(
        'http',
        detail ?? `The planetary-hour request failed (HTTP ${response.status}).`,
        response.status,
      );
    }

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      // An aborted body read rejects too: say why, instead of calling it "not JSON".
      throw interrupted() ?? invalidResponse('body is not JSON');
    }
    const afterBody = interrupted();
    if (afterBody) throw afterBody;
    return validatePlanetaryHour(body);
  } finally {
    clearTimeout(timer);
  }
}
