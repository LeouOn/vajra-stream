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

/** A request that has not finished (headers and body) by now is abandoned as a `network` failure. */
const REQUEST_TIMEOUT_MS = 15_000;

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
 * @param endIso ISO-8601 instant with an explicit zone, at least one step after start (two samples)
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
  // The decoder needs at least two samples; one (start == end) would come back as an invalid response.
  if (endMs - startMs < stepSeconds * 1000) {
    throw new EarthSeriesError(
      'invalid-input',
      'The series must span at least one step (two samples): end must be at least start + step.',
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
  const interrupted = (): EarthSeriesError | null => {
    if (myGeneration !== generation) {
      return new EarthSeriesError('stale', 'A newer series request replaced this one.');
    }
    if (timedOut) {
      return new EarthSeriesError(
        'network',
        `The earth-state series request timed out after ${REQUEST_TIMEOUT_MS / 1000} s.`,
      );
    }
    if (controller.signal.aborted) {
      return new EarthSeriesError('stale', 'A newer series request replaced this one.');
    }
    return null;
  };

  const query = new URLSearchParams({
    start: new Date(startMs).toISOString(),
    end: new Date(endMs).toISOString(),
    step_seconds: String(stepSeconds),
  });

  try {
    let response: Response;
    try {
      response = await fetch(`${apiUrl('/astrology/earth-state/series')}?${query.toString()}`, {
        signal: controller.signal,
      });
    } catch {
      throw (
        interrupted() ??
        new EarthSeriesError('network', 'Could not reach the server for the earth-state series.')
      );
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
      // An aborted body read rejects too: say why, instead of calling it "not JSON".
      throw interrupted() ?? new EarthSeriesError('invalid-response', 'The series response body was not JSON.');
    }
    const afterBody = interrupted();
    if (afterBody) throw afterBody;

    try {
      return decodeSeries(body);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      throw new EarthSeriesError('invalid-response', `The series response was not valid: ${detail}.`);
    }
  } finally {
    clearTimeout(timer);
  }
}
