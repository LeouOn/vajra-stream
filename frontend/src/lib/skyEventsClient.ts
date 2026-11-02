/**
 * W7-3b — the sky-events client.
 *
 * One validated read of `GET /astrology/sky-events` (contract:
 * docs/notes/earthsky/wave7/plan.md). The response is validated before it is
 * returned — a missing or ill-typed field is an error here, not a cast. 422,
 * 503, other HTTP failures and network failures become typed errors. A newer
 * call supersedes an older one: the older request is aborted and, even if its
 * answer still arrives, it rejects as `stale` instead of being returned.
 *
 * Two pure helpers let the readout decide when to ask again without asking on
 * every Play tick: `skyEventsFetchKey` (observer rounded to 0.01 degrees and a
 * six-hour bucket of the shown instant) and `skyEventsWindowCovers` (the shown
 * instant must stay inside the fetched window minus a three-hour margin).
 */
import { apiUrl } from '../utils/api';
import { parseInstant } from './skyClock';

export type SkyEventsErrorKind =
  | 'invalid-input'
  | 'invalid-response'
  | 'unavailable'
  | 'network'
  | 'http'
  | 'stale';

export class SkyEventsError extends Error {
  readonly kind: SkyEventsErrorKind;
  readonly status?: number;

  constructor(kind: SkyEventsErrorKind, message: string, status?: number) {
    super(message);
    this.name = 'SkyEventsError';
    this.kind = kind;
    this.status = status;
  }
}

export type SkyEventBody = 'sun' | 'moon';

export type SkyEventKind =
  | 'rise'
  | 'set'
  | 'transit'
  | 'civil_dawn'
  | 'civil_dusk'
  | 'nautical_dawn'
  | 'nautical_dusk'
  | 'astronomical_dawn'
  | 'astronomical_dusk';

export interface SkyEvent {
  body: SkyEventBody;
  kind: SkyEventKind;
  /** The instant exactly as the backend sent it (UTC, whole seconds). */
  at: string;
  /** The same instant in epoch milliseconds. */
  atMs: number;
}

export interface SkyEvents {
  status: 'success';
  window: { from: string; to: string; fromMs: number; toMs: number };
  observer: { latitude: number; longitude: number };
  /** The IANA zone of the observer, or null when the backend could not name one. */
  timezone: string | null;
  /** The convention the times follow; the UI shows it verbatim. */
  convention: string;
  /** Every event in the window, ascending by instant. */
  events: SkyEvent[];
  /** "up"/"down" when a body has neither rise nor set in the window, else null. */
  always: { sun: 'up' | 'down' | null; moon: 'up' | 'down' | null };
}

const BODIES: SkyEventBody[] = ['sun', 'moon'];
const KINDS: SkyEventKind[] = [
  'rise',
  'set',
  'transit',
  'civil_dawn',
  'civil_dusk',
  'nautical_dawn',
  'nautical_dusk',
  'astronomical_dawn',
  'astronomical_dusk',
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function invalidResponse(detail: string): SkyEventsError {
  return new SkyEventsError('invalid-response', `The sky-events response was not valid: ${detail}.`);
}

function requireInstant(value: unknown, field: string): string {
  if (typeof value !== 'string') throw invalidResponse(`${field} must be a string`);
  try {
    parseInstant(value);
  } catch {
    throw invalidResponse(`${field} is not an ISO-8601 instant with a zone`);
  }
  return value;
}

function requireNumber(value: unknown, field: string, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw invalidResponse(`${field} must be a finite number in [${min}, ${max}]`);
  }
  return value;
}

/** Validate an unknown payload; throws SkyEventsError rather than casting. */
export function validateSkyEvents(raw: unknown): SkyEvents {
  if (!isRecord(raw)) throw invalidResponse('expected an object');
  if (raw.status !== 'success') throw invalidResponse('status must be "success"');
  if (!isRecord(raw.window)) throw invalidResponse('missing window');
  const from = requireInstant(raw.window.from, 'window.from');
  const to = requireInstant(raw.window.to, 'window.to');
  const fromMs = parseInstant(from);
  const toMs = parseInstant(to);
  if (!(fromMs < toMs)) throw invalidResponse('window.from must be before window.to');
  if (!isRecord(raw.observer)) throw invalidResponse('missing observer');
  const latitude = requireNumber(raw.observer.latitude, 'observer.latitude', -90, 90);
  const longitude = requireNumber(raw.observer.longitude, 'observer.longitude', -180, 180);
  const timezone =
    raw.timezone === null
      ? null
      : typeof raw.timezone === 'string' && raw.timezone.length > 0
        ? raw.timezone
        : (() => {
            throw invalidResponse('timezone must be a string or null');
          })();
  if (typeof raw.convention !== 'string' || raw.convention.length === 0) {
    throw invalidResponse('convention must be a non-empty string');
  }
  if (!Array.isArray(raw.events)) throw invalidResponse('events must be an array');
  const events: SkyEvent[] = raw.events.map((value, index) => {
    if (!isRecord(value)) throw invalidResponse(`events[${index}] must be an object`);
    if (!BODIES.includes(value.body as SkyEventBody)) {
      throw invalidResponse(`events[${index}].body must be sun or moon`);
    }
    if (!KINDS.includes(value.kind as SkyEventKind)) {
      throw invalidResponse(`events[${index}].kind is not a known event kind`);
    }
    const at = requireInstant(value.at, `events[${index}].at`);
    return { body: value.body as SkyEventBody, kind: value.kind as SkyEventKind, at, atMs: parseInstant(at) };
  });
  events.sort((a, b) => a.atMs - b.atMs);
  const alwaysRaw = raw.always;
  if (!isRecord(alwaysRaw)) throw invalidResponse('missing always');
  const alwaysValue = (field: 'sun' | 'moon'): 'up' | 'down' | null => {
    const value = alwaysRaw[field];
    if (value === null || value === 'up' || value === 'down') return value;
    throw invalidResponse(`always.${field} must be "up", "down" or null`);
  };
  return {
    status: 'success',
    window: { from, to, fromMs, toMs },
    observer: { latitude, longitude },
    timezone,
    convention: raw.convention,
    events,
    always: { sun: alwaysValue('sun'), moon: alwaysValue('moon') },
  };
}

async function detailOf(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (isRecord(body) && typeof body.detail === 'string' && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    /* non-JSON error body: use the status text */
  }
  return null;
}

const REQUEST_TIMEOUT_MS = 15_000;
let generation = 0;
let activeController: AbortController | null = null;

/** Abort the in-flight request and make every older answer stale (panel unmount). */
export function cancelSkyEventsRequest(): void {
  generation += 1;
  activeController?.abort();
  activeController = null;
}

/**
 * Fetch and validate the sky events for an observer at an instant.
 *
 * @param lat latitude in degrees [-90, 90]
 * @param lng longitude in degrees [-180, 180]
 * @param atIso ISO-8601 instant with an explicit zone
 */
export async function fetchSkyEvents(lat: number, lng: number, atIso: string): Promise<SkyEvents> {
  if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
    throw new SkyEventsError('invalid-input', 'The observer latitude must be between -90 and 90.');
  }
  if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
    throw new SkyEventsError('invalid-input', 'The observer longitude must be between -180 and 180.');
  }
  let atMs: number;
  try {
    atMs = parseInstant(atIso);
  } catch {
    throw new SkyEventsError('invalid-input', 'The time must be ISO-8601 with an explicit zone (Z or +hh:mm).');
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
  const interrupted = (): SkyEventsError | null => {
    if (myGeneration !== generation) return new SkyEventsError('stale', 'A newer sky-events request replaced this one.');
    if (timedOut) return new SkyEventsError('network', `The sky-events request timed out after ${REQUEST_TIMEOUT_MS / 1000} s.`);
    if (controller.signal.aborted) return new SkyEventsError('stale', 'A newer sky-events request replaced this one.');
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
      response = await fetch(`${apiUrl('/astrology/sky-events')}?${query.toString()}`, {
        signal: controller.signal,
      });
    } catch (caught) {
      const stale = interrupted();
      if (stale !== null) throw stale;
      throw new SkyEventsError(
        'network',
        caught instanceof Error && caught.message.length > 0
          ? caught.message
          : 'The sky-events request could not be made.',
      );
    }
    const staleAfterHeaders = interrupted();
    if (staleAfterHeaders !== null) throw staleAfterHeaders;
    if (response.status === 422) {
      const detail = await detailOf(response);
      throw new SkyEventsError('invalid-input', detail ?? 'The observer or instant was rejected.', 422);
    }
    if (response.status === 503) {
      const detail = await detailOf(response);
      throw new SkyEventsError('unavailable', detail ?? 'The ephemeris is unavailable.', 503);
    }
    if (!response.ok) {
      throw new SkyEventsError('http', `The sky-events request failed with HTTP ${response.status}.`, response.status);
    }
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw invalidResponse('the body is not JSON');
    }
    const staleAfterBody = interrupted();
    if (staleAfterBody !== null) throw staleAfterBody;
    return validateSkyEvents(body);
  } finally {
    clearTimeout(timer);
    if (activeController === controller) activeController = null;
  }
}

/** 0.01-degree place precision and a six-hour bucket: the readout's fetch key. */
const PLACE_PRECISION = 0.01;
const BUCKET_MS = 6 * 3600_000;
/** The fetched answer is reused while the shown instant is inside its window minus this margin. */
const WINDOW_MARGIN_MS = 3 * 3600_000;

function round2(value: number): number {
  return Math.round(value / PLACE_PRECISION) * PLACE_PRECISION;
}

/** The observer (0.01°) and the six-hour bucket of the shown instant. */
export function skyEventsFetchKey(lat: number, lng: number, atMs: number): string {
  return `${round2(lat)},${round2(lng)}@${Math.floor(atMs / BUCKET_MS)}`;
}

/**
 * Is the shown instant still inside the fetched window with a three-hour
 * margin on each side? If not, the answer may no longer cover it.
 */
export function skyEventsWindowCovers(fromMs: number, toMs: number, shownMs: number): boolean {
  return shownMs >= fromMs + WINDOW_MARGIN_MS && shownMs <= toMs - WINDOW_MARGIN_MS;
}
