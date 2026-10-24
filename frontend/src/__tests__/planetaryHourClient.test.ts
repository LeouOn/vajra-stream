/**
 * W3-J tests for frontend/src/lib/planetaryHourClient.ts.
 *
 * The client validates the backend shape before returning it (no casts), turns 422/503/network failures into typed
 * errors, never lets a superseded request be reported as a real error, gives up after 15 s, and refuses a payload
 * that is not labelled `computed` (an estimate must never be shown as an hour).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  PlanetaryHourError,
  cancelPlanetaryHourRequest,
  fetchPlanetaryHour,
  validatePlanetaryHour,
  type PlanetaryHour,
} from '../lib/planetaryHourClient';

const AT = '2026-10-24T09:00:00Z';

function payload(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    at: '2026-10-24T09:00:00.000Z',
    latitude: 37.7749,
    longitude: -122.4194,
    solar_day: {
      sunrise: '2026-10-23T14:25:49.941Z',
      sunset: '2026-10-24T01:09:23.130Z',
      next_sunrise: '2026-10-24T14:26:49.816Z',
      day_ruler: 'Friday-ish',
    },
    hour: {
      ruler: 'Mars',
      is_daytime: false,
      index: 8,
      starts_at: '2026-10-24T08:30:00.000Z',
      ends_at: '2026-10-24T09:25:00.000Z',
      length_seconds: 3300,
      time_remaining_seconds: 1500,
    },
    reason: null,
    provenance: { at: 'computed', solar_day: 'computed', hour: 'computed' },
    ...overrides,
  };
}

/** A payload whose solar_day uses a real ruler name (the helper above is for readability of the overrides). */
function good(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  const base = payload(overrides);
  if (!('solar_day' in overrides)) {
    base.solar_day = { ...(base.solar_day as Record<string, unknown>), day_ruler: 'Venus' };
  }
  return base;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

describe('fetchPlanetaryHour: request', () => {
  it('calls the proxy-relative route with the observer and a UTC instant', async () => {
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await fetchPlanetaryHour(37.7749, -122.4194, AT);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/astrology/planetary-hour?');
    const params = new URL(url, 'http://x').searchParams;
    expect(params.get('latitude')).toBe('37.7749');
    expect(params.get('longitude')).toBe('-122.4194');
    expect(params.get('datetime_str')).toBe('2026-10-24T09:00:00.000Z');
    expect(init.signal).toBeDefined();
  });

  it('normalises an offset-bearing instant to ...Z', async () => {
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await fetchPlanetaryHour(10, 20, '2026-10-24T11:00:00+02:00');
    const url = String((fetchMock.mock.calls[0] as [string, RequestInit])[0]);
    expect(new URL(url, 'http://x').searchParams.get('datetime_str')).toBe('2026-10-24T09:00:00.000Z');
  });

  it.each([
    [190, '-170'],
    [-190, '170'],
    [180, '-180'],
    [540, '-180'],
  ])('wraps longitude %d into [-180, 180) as %s, and leaves an in-range value alone', async (lng, wrapped) => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse(good()))); // a fresh body per call
    await fetchPlanetaryHour(10, lng, AT);
    await fetchPlanetaryHour(10, -122.4194, AT);
    const sent = (index: number) =>
      new URL(String((fetchMock.mock.calls[index] as [string, RequestInit])[0]), 'http://x').searchParams.get('longitude');
    expect(sent(0)).toBe(wrapped);
    expect(sent(1)).toBe('-122.4194');
  });

  it('rejects bad local input without calling the network', async () => {
    for (const lat of [90.0001, -91, 95, Number.NaN, Number.POSITIVE_INFINITY]) {
      await expect(fetchPlanetaryHour(lat, 0, AT), String(lat)).rejects.toMatchObject({ kind: 'invalid-input' });
    }
    await expect(fetchPlanetaryHour(0, Number.NaN, AT)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchPlanetaryHour(0, 0, '2026-10-24T09:00:00')).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('validatePlanetaryHour', () => {
  it('returns the validated payload with parsed instants', () => {
    const hour: PlanetaryHour = validatePlanetaryHour(good());
    expect(hour.hour?.ruler).toBe('Mars');
    expect(hour.hour?.isDaytime).toBe(false);
    expect(hour.hour?.index).toBe(8);
    expect(hour.hour?.timeRemainingSeconds).toBe(1500);
    expect(hour.hour?.endsAtMs).toBe(Date.parse('2026-10-24T09:25:00.000Z'));
    expect(hour.hour?.startsAtMs).toBe(Date.parse('2026-10-24T08:30:00.000Z'));
    expect(hour.solarDay?.dayRuler).toBe('Venus');
    expect(hour.atMs).toBe(Date.parse('2026-10-24T09:00:00.000Z'));
    expect(hour.reason).toBeNull();
  });

  it('accepts a polar answer: both null, with a reason, never an hour', () => {
    const polar = validatePlanetaryHour(
      good({ solar_day: null, hour: null, reason: 'No sunrise-to-sunrise day brackets this instant here.' }),
    );
    expect(polar.hour).toBeNull();
    expect(polar.solarDay).toBeNull();
    expect(polar.reason).toMatch(/sunrise/);
  });

  it('ignores extra keys', () => {
    expect(() => validatePlanetaryHour({ ...good(), extra: 1 })).not.toThrow();
  });

  it.each(['at', 'latitude', 'longitude', 'solar_day', 'hour', 'reason', 'provenance'])('rejects a missing "%s"', (key) => {
    const body = good();
    delete body[key];
    expect(() => validatePlanetaryHour(body)).toThrowError(PlanetaryHourError);
  });

  it.each(['ruler', 'is_daytime', 'index', 'starts_at', 'ends_at', 'length_seconds', 'time_remaining_seconds'])(
    'rejects an hour without "%s"',
    (key) => {
      const body = good();
      delete (body.hour as Record<string, unknown>)[key];
      expect(() => validatePlanetaryHour(body)).toThrowError(PlanetaryHourError);
    },
  );

  const hourWith = (patch: Record<string, unknown>) =>
    good({ hour: { ...(payload().hour as Record<string, unknown>), ...patch } });

  it('rejects an unknown ruler, a bad index, a non-boolean day flag', () => {
    for (const patch of [
      { ruler: 'Pluto' },
      { ruler: 'mars' },
      { ruler: 7 },
      { index: 0 },
      { index: 13 },
      { index: 2.5 },
      { is_daytime: 'yes' },
    ]) {
      expect(() => validatePlanetaryHour(hourWith(patch)), JSON.stringify(patch)).toThrowError(PlanetaryHourError);
    }
  });

  it('rejects an hour that is impossible: time left negative or longer than the hour, end not after start', () => {
    for (const patch of [
      { time_remaining_seconds: -1 },
      { time_remaining_seconds: 3301 },
      { time_remaining_seconds: Number.NaN },
      { length_seconds: 0 },
      { ends_at: '2026-10-24T08:30:00.000Z' },
      { ends_at: '2026-10-24T08:00:00.000Z' },
      { starts_at: '2026-10-24T08:30:00' },
    ]) {
      expect(() => validatePlanetaryHour(hourWith(patch)), JSON.stringify(patch)).toThrowError(PlanetaryHourError);
    }
  });

  it('rejects an hour that does not contain the instant it was asked for', () => {
    expect(() => validatePlanetaryHour(hourWith({ starts_at: '2026-10-24T09:10:00.000Z', ends_at: '2026-10-24T10:00:00.000Z' }))).toThrowError(
      PlanetaryHourError,
    );
  });

  it('rejects hour and solar_day that disagree, and a missing reason when there is no hour', () => {
    expect(() => validatePlanetaryHour(good({ hour: null, reason: 'x' }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(good({ solar_day: null }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(good({ solar_day: null, hour: null, reason: null }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(good({ solar_day: null, hour: null, reason: '' }))).toThrowError(PlanetaryHourError);
  });

  it('rejects a solar day that is out of order or has an unknown day ruler', () => {
    const day = (patch: Record<string, unknown>) =>
      good({ solar_day: { ...(good().solar_day as Record<string, unknown>), ...patch } });
    expect(() => validatePlanetaryHour(day({ sunset: '2026-10-23T10:00:00.000Z' }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(day({ day_ruler: 'Rahu' }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(day({ sunrise: 'soon' }))).toThrowError(PlanetaryHourError);
  });

  it('refuses anything not labelled computed: an estimate is never shown as an hour', () => {
    for (const provenance of [
      { at: 'computed', solar_day: 'computed', hour: 'decorative' },
      { at: 'computed', solar_day: 'decorative', hour: 'computed' },
      { at: 'computed', solar_day: 'computed' },
      {},
    ]) {
      expect(() => validatePlanetaryHour(good({ provenance })), JSON.stringify(provenance)).toThrowError(
        /computed/,
      );
    }
    expect(() => validatePlanetaryHour(good({ provenance: null }))).toThrowError(PlanetaryHourError);
  });

  it('rejects non-objects and wrong types for the place', () => {
    for (const bad of [null, 5, 'x', [1, 2]]) {
      expect(() => validatePlanetaryHour(bad)).toThrowError(PlanetaryHourError);
    }
    expect(() => validatePlanetaryHour(good({ latitude: 91 }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(good({ longitude: 'west' }))).toThrowError(PlanetaryHourError);
    expect(() => validatePlanetaryHour(good({ at: '2026-10-24T09:00:00' }))).toThrowError(PlanetaryHourError);
  });

  it('every thrown error is a typed invalid-response', () => {
    try {
      validatePlanetaryHour(good({ hour: 5 }));
      throw new Error('should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(PlanetaryHourError);
      expect(error).toMatchObject({ kind: 'invalid-response' });
    }
  });
});

describe('fetchPlanetaryHour: typed failures', () => {
  it('returns the validated payload', async () => {
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await expect(fetchPlanetaryHour(37.7749, -122.4194, AT)).resolves.toMatchObject({ hour: { ruler: 'Mars' } });
  });

  it('maps 422 to invalid-input with the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'longitude must be a number between -180 and 180' }, 422));
    await expect(fetchPlanetaryHour(0, 0, AT)).rejects.toMatchObject({
      kind: 'invalid-input',
      status: 422,
      message: 'longitude must be a number between -180 and 180',
    });
  });

  it('maps 503 to unavailable, other statuses to http, and a network failure to a readable network error', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'ephemeris unavailable' }, 503));
    await expect(fetchPlanetaryHour(0, 0, AT)).rejects.toMatchObject({ kind: 'unavailable', status: 503 });
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await expect(fetchPlanetaryHour(0, 0, AT)).rejects.toMatchObject({ kind: 'http', status: 500 });
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const error = await fetchPlanetaryHour(0, 0, AT).catch((e: unknown) => e);
    expect(error).toMatchObject({ kind: 'network' });
    expect((error as Error).message).toMatch(/could not reach/i);
  });

  it('a body that is not JSON, or not a valid payload, is invalid-response', async () => {
    fetchMock.mockResolvedValue(new Response('<html>nope</html>', { status: 200 }));
    await expect(fetchPlanetaryHour(0, 0, AT)).rejects.toMatchObject({ kind: 'invalid-response' });
    fetchMock.mockResolvedValue(jsonResponse([1, 2, 3]));
    await expect(fetchPlanetaryHour(0, 0, AT)).rejects.toMatchObject({ kind: 'invalid-response' });
  });
});

/**
 * Headers arrive at once; the body then stays open and errors when the request is aborted, as a real fetch body
 * does. (Superseding or timing out a request after its headers arrived is exactly this case.)
 */
function slowBodyResponse(signal: AbortSignal | null | undefined, status: number): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      signal?.addEventListener('abort', () => {
        controller.error(new DOMException('The operation was aborted.', 'AbortError'));
      });
    },
  });
  return new Response(stream, { status, headers: { 'Content-Type': 'application/json' } });
}

/** A fetch that never answers and rejects when aborted. */
function neverAnswers(_url: string, init: RequestInit): Promise<Response> {
  return new Promise((_resolve, reject) => {
    init.signal?.addEventListener('abort', () => {
      reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
    });
  });
}

const settle = (promise: Promise<unknown>) =>
  promise.then(
    (value) => ({ ok: true as const, value }),
    (error: unknown) => ({ ok: false as const, error }),
  );
const nextMacrotask = () => new Promise<void>((resolve) => setTimeout(resolve, 0));
const call = () => fetchPlanetaryHour(37.7749, -122.4194, AT);

describe('fetchPlanetaryHour: a superseded request is never reported as a real error', () => {
  it('is stale when superseded while its 200 body is being read', async () => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) => Promise.resolve(slowBodyResponse(init.signal, 200)));
    const older = settle(call());
    await nextMacrotask();
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await expect(call()).resolves.toMatchObject({ hour: { ruler: 'Mars' } });
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it.each([422, 500, 503])('is stale when superseded after a %i arrived', async (status) => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) => Promise.resolve(slowBodyResponse(init.signal, status)));
    const older = settle(call());
    await nextMacrotask();
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await call();
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it('the newer request wins when the older resolves last', async () => {
    const pending: Array<(r: Response) => void> = [];
    fetchMock.mockImplementation(() => new Promise<Response>((resolve) => pending.push(resolve)));
    const older = settle(call());
    const newer = settle(call());
    pending[1](jsonResponse(good({ hour: { ...(payload().hour as Record<string, unknown>), ruler: 'Venus' } })));
    const newerResult = await newer;
    expect(newerResult).toMatchObject({ ok: true, value: { hour: { ruler: 'Venus' } } });
    pending[0](jsonResponse(good()));
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it('cancelPlanetaryHourRequest makes an in-flight call stale, also mid-body, and aborts the signal', async () => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) => Promise.resolve(slowBodyResponse(init.signal, 200)));
    const inFlight = settle(call());
    await nextMacrotask();
    cancelPlanetaryHourRequest();
    expect(await inFlight).toMatchObject({ ok: false, error: { kind: 'stale' } });

    fetchMock.mockImplementation(neverAnswers);
    const waiting = settle(call());
    const signal = (fetchMock.mock.calls[fetchMock.mock.calls.length - 1] as [string, RequestInit])[1].signal as AbortSignal;
    cancelPlanetaryHourRequest();
    expect(signal.aborted).toBe(true);
    expect(await waiting).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it('cancel with nothing in flight is harmless', async () => {
    cancelPlanetaryHourRequest();
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await expect(call()).resolves.toMatchObject({ hour: { ruler: 'Mars' } });
  });
});

describe('fetchPlanetaryHour: timeout', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('abandons a server that never answers as a network error after 15 s', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(neverAnswers);
    const outcome = settle(call());
    await vi.advanceTimersByTimeAsync(14_999);
    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(1);
    const result = await outcome;
    expect(result).toMatchObject({ ok: false, error: { kind: 'network' } });
    expect(String((result as { error: Error }).error.message)).toMatch(/timed out after 15 s/i);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('also covers a body that never finishes, and an error body that never finishes', async () => {
    vi.useFakeTimers();
    for (const status of [200, 503]) {
      fetchMock.mockImplementation((_url: string, init: RequestInit) => Promise.resolve(slowBodyResponse(init.signal, status)));
      const outcome = settle(call());
      await vi.advanceTimersByTimeAsync(15_000);
      expect(await outcome).toMatchObject({ ok: false, error: { kind: 'network' } });
    }
  });

  it('leaves no timer behind after a success, a failure or a cancel', async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await call();
    expect(vi.getTimerCount()).toBe(0);
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await settle(call());
    expect(vi.getTimerCount()).toBe(0);
    fetchMock.mockImplementation(neverAnswers);
    const cancelled = settle(call());
    cancelPlanetaryHourRequest();
    await cancelled;
    expect(vi.getTimerCount()).toBe(0);
  });

  it('a request that was superseded and then timed out is still stale', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(neverAnswers);
    const older = settle(call());
    fetchMock.mockResolvedValue(jsonResponse(good()));
    await call();
    await vi.advanceTimersByTimeAsync(20_000);
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});
