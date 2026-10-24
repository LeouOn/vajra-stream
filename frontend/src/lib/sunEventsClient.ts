/**
 * Earth & Sky wave 3 — the sun-events client.
 *
 * One validated read of `GET /astrology/sun-events`. The backend returns six
 * event instants that may be `null` at polar day/night (never a fake time); a
 * missing/ill-typed/unparsable field is an error here, not a cast. 422, 503,
 * other HTTP failures and network failures become typed, readable
 * `SunEventsError`s. A newer call supersedes an older one: the older request
 * is aborted and, even if its answer still arrives, it rejects as `stale`
 * instead of being returned — so a slow older answer can never win.
 *
 * Uses the shared zone-explicit parser (`parseInstant`), so an instant without
 * an explicit zone is rejected before it reaches the backend.
 */
import { apiUrl } from '../utils/api';
import { parseInstant } from './skyClock';

export type SunEventsErrorKind =
  | 'invalid-input'
  | 'invalid-response'
  | 'unavailable'
  | 'network'
  | 'http'
  | 'stale';

export class SunEventsError extends Error {
  readonly kind: SunEventsErrorKind;
  readonly status?: number;

  constructor(kind: SunEventsErrorKind, message: string, status?: number) {
    super(message);
    this.name = 'SunEventsError';
    this.kind = kind;
    this.status = status;
  }
}

/** The validated backend payload. Events are ISO instants ending in Z or null. */
export interface SunEvents {
  at: string;
  latitude: number;
  longitude: number;
  previous_sunrise: string | null;
  sunset: string | null;
  next_sunrise: string | null;
  previous_sunset: string | null;
  next_sunset: string | null;
  provenance: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function invalidResponse(detail: string): SunEventsError {
  return new SunEventsError('invalid-response', `The sun-events response was not valid: ${detail}.`);
}

function requireInstant(value: unknown, field: string): string {
  if (typeof value !== 'string') {
    throw invalidResponse(`${field} must be a string`);
  }
  try {
    parseInstant(value);
  } catch {
    throw invalidResponse(`${field} is not an ISO-8601 instant with a zone`);
  }
  return value;
}

function requireEvent(value: unknown, field: string): string | null {
  if (value === null) return null;
  return requireInstant(value, field);
}

function requireNumber(value: unknown, field: string, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw invalidResponse(`${field} must be a finite number in [${min}, ${max}]`);
  }
  return value;
}

/** Validate an unknown payload; throws SunEventsError rather than casting. */
export function validateSunEvents(raw: unknown): SunEvents {
  if (!isRecord(raw)) throw invalidResponse('expected an object');
  const at = requireInstant(raw.at, 'at');
  const latitude = requireNumber(raw.latitude, 'latitude', -90, 90);
  const longitude = requireNumber(raw.longitude, 'longitude', -180, 180);
  const previous_sunrise = requireEvent(raw.previous_sunrise, 'previous_sunrise');
  const sunset = requireEvent(raw.sunset, 'sunset');
  const next_sunrise = requireEvent(raw.next_sunrise, 'next_sunrise');
  const previous_sunset = requireEvent(raw.previous_sunset, 'previous_sunset');
  const next_sunset = requireEvent(raw.next_sunset, 'next_sunset');
  if (!isRecord(raw.provenance)) throw invalidResponse('missing provenance');
  return {
    at,
    latitude,
    longitude,
    previous_sunrise,
    sunset,
    next_sunrise,
    previous_sunset,
    next_sunset,
    provenance: raw.provenance,
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

/**
 * Abort the in-flight request and make it stale (panel unmount). Mirrors
 * `cancelNightSkyRequest` / `cancelSeriesRequest`: a later answer is rejected
 * as `stale` rather than acting on state the caller has already left.
 */
export function cancelSunEventsRequest(): void {
  generation += 1;
  activeController?.abort();
  activeController = null;
}

/**
 * Fetch and validate the sun events for an observer at an instant.
 *
 * @param lat latitude in degrees [-90, 90]
 * @param lng longitude in degrees (finite)
 * @param atIso ISO-8601 instant with an explicit zone
 */
export async function fetchSunEvents(lat: number, lng: number, atIso: string): Promise<SunEvents> {
  if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
    throw new SunEventsError('invalid-input', 'The observer latitude must be between -90 and 90.');
  }
  if (!Number.isFinite(lng)) {
    throw new SunEventsError('invalid-input', 'The observer longitude must be a finite number.');
  }
  let atMs: number;
  try {
    atMs = parseInstant(atIso);
  } catch {
    throw new SunEventsError(
      'invalid-input',
      'The time must be ISO-8601 with an explicit zone (Z or +hh:mm).',
    );
  }

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
  const interrupted = (): SunEventsError | null => {
    if (myGeneration !== generation) {
      return new SunEventsError('stale', 'A newer sun-events request replaced this one.');
    }
    if (timedOut) {
      return new SunEventsError(
        'network',
        `The sun-events request timed out after ${REQUEST_TIMEOUT_MS / 1000} s.`,
      );
    }
    if (controller.signal.aborted) {
      return new SunEventsError('stale', 'A newer sun-events request replaced this one.');
    }
    return null;
  };

  const query = new URLSearchParams({
    latitude: String(lat),
    longitude: String(lng),
    datetime_str: new Date(atMs).toISOString(),
  });

  try {
    let response: Response;
    try {
      response = await fetch(`${apiUrl('/astrology/sun-events')}?${query.toString()}`, {
        signal: controller.signal,
      });
    } catch {
      throw interrupted() ?? new SunEventsError('network', 'Could not reach the server for sun events.');
    }
    const afterHeaders = interrupted();
    if (afterHeaders) throw afterHeaders;

    if (!response.ok) {
      const detail = await detailOf(response);
      // The error body is read after the last check above: a request superseded (or timed out) meanwhile
      // must not be reported as unavailable/http/invalid-input.
      const afterErrorBody = interrupted();
      if (afterErrorBody) throw afterErrorBody;
      if (response.status === 422) {
        throw new SunEventsError(
          'invalid-input',
          detail ?? 'The server rejected the request (422).',
          422,
        );
      }
      if (response.status === 503) {
        throw new SunEventsError('unavailable', detail ?? 'Ephemeris unavailable (503).', 503);
      }
      throw new SunEventsError(
        'http',
        detail ?? `Sun events request failed (HTTP ${response.status}).`,
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
    return validateSunEvents(body);
  } finally {
    clearTimeout(timer);
  }
}
