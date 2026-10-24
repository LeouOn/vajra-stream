/**
 * Earth & Sky wave 3 — the series client (row W3-D1).
 *
 * One validated read of `GET /astrology/earth-state/series`. The response is
 * checked by `decodeSeries` (never cast); 422, 503, other HTTP failures,
 * network failures and stale answers become typed, readable
 * `EarthSeriesError`s. A newer call supersedes an older one: the older request
 * is aborted and, even if its answer still arrives, it rejects as `stale`, so a
 * slow older answer can never overwrite a newer one.
 */
import { apiUrl } from '../utils/api';
import { parseInstant } from './skyClock';
import { decodeSeries, type SkySeries } from './skySeries';

export type EarthSeriesErrorKind =
  | 'invalid-input'
  | 'invalid-response'
  | 'unavailable'
  | 'network'
  | 'http'
  | 'stale';

export class EarthSeriesError extends Error {
  readonly kind: EarthSeriesErrorKind;
  readonly status?: number;

  constructor(kind: EarthSeriesErrorKind, message: string, status?: number) {
    super(message);
    this.name = 'EarthSeriesError';
    this.kind = kind;
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

async function detailOf(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (isRecord(body) && typeof body.detail === 'string' && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    /* a non-JSON error body is fine; fall back to the status message */
  }
  return null;
}

/** Monotonic request generation: a newer call makes every older one stale. */
let generation = 0;
let activeController: AbortController | null = null;

/**
 * Abort the in-flight series request and make it stale (dome unmount / leaving
 * scrub mode). Mirrors `cancelNightSkyRequest`; a later answer is rejected as
 * `stale` rather than overwriting the caller's newer state.
 */
export function cancelSeriesRequest(): void {
  generation += 1;
  activeController?.abort();
  activeController = null;
}

function parseRequestInstant(value: string, field: 'start' | 'end'): number {
  try {
    return parseInstant(value);
  } catch {
    throw new EarthSeriesError(
      'invalid-input',
      `The series ${field} must be ISO-8601 with an explicit zone (Z or +hh:mm).`,
    );
  }
}

/**
 * Fetch and validate an apparent-GAST sub-point series.
 *
 * @param startIso ISO-8601 instant with an explicit zone
 * @param endIso ISO-8601 instant with an explicit zone, not before start
 * @param stepSeconds integer seconds, 60..3600 (the scrubber asks for 603)
 */
export async function fetchSeries(
  startIso: string,
  endIso: string,
  stepSeconds: number,
): Promise<SkySeries> {
  const startMs = parseRequestInstant(startIso, 'start');
  const endMs = parseRequestInstant(endIso, 'end');
  if (startMs > endMs) {
    throw new EarthSeriesError('invalid-input', 'The series start must not be after its end.');
  }
  if (!Number.isInteger(stepSeconds) || stepSeconds < 60 || stepSeconds > 3600) {
    throw new EarthSeriesError(
      'invalid-input',
      'The series step must be a whole number of seconds between 60 and 3600.',
    );
  }

  const myGeneration = (generation += 1);
  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;

  const query = new URLSearchParams({
    start: new Date(startMs).toISOString(),
    end: new Date(endMs).toISOString(),
    step_seconds: String(stepSeconds),
  });

  let response: Response;
  try {
    response = await fetch(`${apiUrl('/astrology/earth-state/series')}?${query.toString()}`, {
      signal: controller.signal,
    });
  } catch {
    if (myGeneration !== generation || controller.signal.aborted) {
      throw new EarthSeriesError('stale', 'A newer series request replaced this one.');
    }
    throw new EarthSeriesError('network', 'Could not reach the server for the earth-state series.');
  }
  if (myGeneration !== generation) {
    throw new EarthSeriesError('stale', 'A newer series request replaced this one.');
  }

  if (!response.ok) {
    const detail = await detailOf(response);
    if (response.status === 422) {
      throw new EarthSeriesError(
        'invalid-input',
        detail ?? 'The server rejected the series request (422).',
        422,
      );
    }
    if (response.status === 503) {
      throw new EarthSeriesError(
        'unavailable',
        detail ?? 'The earth-state series is unavailable (503).',
        503,
      );
    }
    throw new EarthSeriesError(
      'http',
      detail ?? `The series request failed (HTTP ${response.status}).`,
      response.status,
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new EarthSeriesError('invalid-response', 'The series response body was not JSON.');
  }
  if (myGeneration !== generation) {
    throw new EarthSeriesError('stale', 'A newer series request replaced this one.');
  }

  try {
    return decodeSeries(body);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new EarthSeriesError('invalid-response', `The series response was not valid: ${detail}.`);
  }
}
