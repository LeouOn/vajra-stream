/**
 * W3-F tests for frontend/src/lib/sunEventsClient.ts.
 *
 * The client validates the backend shape before returning it (no casts), turns
 * 422/503/network failures into typed errors, and ignores a stale response
 * when a newer request has started.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SunEventsError, fetchSunEvents, type SunEvents } from '../lib/sunEventsClient';

const AT = '2026-10-24T09:00:00Z';

function payload(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    at: '2026-10-24T09:00:00Z',
    latitude: 37.7749,
    longitude: -122.4194,
    previous_sunrise: '2026-10-24T14:32:00.000Z',
    sunset: '2026-10-25T01:12:00.000Z',
    next_sunrise: '2026-10-25T14:33:00.000Z',
    previous_sunset: '2026-10-24T01:11:00.000Z',
    next_sunset: '2026-10-25T01:12:00.000Z',
    provenance: { next_sunrise: 'computed' },
    ...overrides,
  };
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

describe('fetchSunEvents: request', () => {
  it('calls the proxy-relative route with the observer and a UTC instant', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchSunEvents(37.7749, -122.4194, AT);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/astrology/sun-events?');
    expect(url).toContain('latitude=37.7749');
    expect(url).toContain('longitude=-122.4194');
    // The client sends the normalised UTC instant (milliseconds, Z).
    expect(url).toContain(
      `datetime_str=${encodeURIComponent('2026-10-24T09:00:00.000Z')}`,
    );
    expect(init.signal).toBeDefined();
  });

  it('normalises an offset-bearing instant to ...Z', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchSunEvents(10, 20, '2026-10-24T11:00:00+02:00');
    const url = String((fetchMock.mock.calls[0] as [string, RequestInit])[0]);
    expect(url).toContain(encodeURIComponent('2026-10-24T09:00:00.000Z'));
  });

  it('rejects bad local input without calling the network', async () => {
    await expect(fetchSunEvents(91, 0, AT)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSunEvents(0, Number.NaN, AT)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSunEvents(0, 0, '2026-10-24T09:00:00')).rejects.toMatchObject({
      kind: 'invalid-input',
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('fetchSunEvents: response validation', () => {
  it('returns the validated payload, including null events', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(payload({ next_sunrise: null, sunset: null })),
    );
    const events: SunEvents = await fetchSunEvents(37.7749, -122.4194, AT);
    expect(events.next_sunrise).toBeNull();
    expect(events.sunset).toBeNull();
    expect(events.previous_sunrise).toBe('2026-10-24T14:32:00.000Z');
    expect(events.provenance).toEqual({ next_sunrise: 'computed' });
  });

  it('rejects a missing field', async () => {
    const body = payload();
    delete body.next_sunrise;
    fetchMock.mockResolvedValue(jsonResponse(body));
    const error = await fetchSunEvents(0, 0, AT).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(SunEventsError);
    expect(error).toMatchObject({ kind: 'invalid-response' });
  });

  it('rejects a wrong type instead of casting it', async () => {
    for (const bad of [42, true, {}, ['x']]) {
      fetchMock.mockResolvedValue(jsonResponse(payload({ next_sunrise: bad })));
      await expect(fetchSunEvents(0, 0, AT), String(bad)).rejects.toMatchObject({
        kind: 'invalid-response',
      });
    }
    fetchMock.mockResolvedValue(jsonResponse(payload({ latitude: 'north' })));
    await expect(fetchSunEvents(0, 0, AT)).rejects.toMatchObject({ kind: 'invalid-response' });
  });

  it('rejects an unparsable instant', async () => {
    for (const bad of ['not-a-date', '2026-10-24T09:00:00', '2026-02-30T00:00:00Z']) {
      fetchMock.mockResolvedValue(jsonResponse(payload({ next_sunrise: bad })));
      await expect(fetchSunEvents(0, 0, AT), bad).rejects.toMatchObject({
        kind: 'invalid-response',
      });
    }
  });

  it('rejects a non-object body', async () => {
    fetchMock.mockResolvedValue(jsonResponse([1, 2, 3]));
    await expect(fetchSunEvents(0, 0, AT)).rejects.toMatchObject({ kind: 'invalid-response' });
  });
});

describe('fetchSunEvents: typed failures', () => {
  it('maps 422 to invalid-input with the server detail', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: 'malformed datetime_str; expected ISO-8601' }, 422),
    );
    const error = await fetchSunEvents(0, 0, AT).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(SunEventsError);
    expect(error).toMatchObject({
      kind: 'invalid-input',
      status: 422,
      message: 'malformed datetime_str; expected ISO-8601',
    });
  });

  it('maps 503 to unavailable', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'ephemeris unavailable' }, 503));
    await expect(fetchSunEvents(0, 0, AT)).rejects.toMatchObject({
      kind: 'unavailable',
      status: 503,
    });
  });

  it('maps other HTTP failures to a readable http error', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await expect(fetchSunEvents(0, 0, AT)).rejects.toMatchObject({ kind: 'http', status: 500 });
  });

  it('maps a network failure to a readable network error', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const error = await fetchSunEvents(0, 0, AT).catch((e: unknown) => e);
    expect(error).toMatchObject({ kind: 'network' });
    expect((error as Error).message).toMatch(/could not reach/i);
  });

  it('maps an aborted request to stale', async () => {
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => {
            reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
          });
        }),
    );
    const first = fetchSunEvents(0, 0, AT);
    const firstOutcome = first.then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ ok: false as const, error }),
    );
    // Only the superseded (first) request gets the abort-aware mock; the
    // second call must get a normal answer.
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    const second = fetchSunEvents(0, 0, AT);
    await expect(second).resolves.toMatchObject({ at: '2026-10-24T09:00:00Z' });
    expect(await firstOutcome).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});

describe('fetchSunEvents: stale generation guard', () => {
  it('the newer request wins when the older resolves last', async () => {
    const pending: Array<{ resolve: (r: Response) => void }> = [];
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          pending.push({ resolve });
        }),
    );

    const older = fetchSunEvents(0, 0, AT);
    const olderOutcome = older.then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ ok: false as const, error }),
    );
    const newer = fetchSunEvents(0, 0, AT).then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ ok: false as const, error }),
    );

    // Newer arrives first, then the older answer (ignoring its abort).
    pending[1].resolve(jsonResponse(payload({ next_sunrise: '2026-10-25T16:00:00.000Z' })));
    const newerResult = await newer;
    expect(newerResult.ok).toBe(true);
    pending[0].resolve(jsonResponse(payload({ next_sunrise: '2026-10-25T10:00:00.000Z' })));
    const olderResult = await olderOutcome;

    expect(newerResult.ok && newerResult.value.next_sunrise).toBe('2026-10-25T16:00:00.000Z');
    expect(olderResult).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});
