/**
 * W3-D1 tests for frontend/src/lib/earthSeriesClient.ts.
 *
 * The client validates the series payload with `decodeSeries` (no casts),
 * turns 422/503/network failures into typed readable errors, and lets a newer
 * call win: an older answer that arrives last is rejected as `stale`.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EarthSeriesError, cancelSeriesRequest, fetchSeries } from '../lib/earthSeriesClient';

const START = '2026-03-20T14:46:00Z';
const END = '2026-03-20T15:06:00Z';

const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];

function body(id: string): { id: string; lat: number; lon: number } {
  return { id, lat: 1.5, lon: -20.25 };
}

function payload(
  stepSeconds = 600,
  overrides: Partial<Record<string, unknown>> = {},
): Record<string, unknown> {
  const samples = [0, 1, 2].map((index) => ({
    at: new Date(Date.parse(START) + index * stepSeconds * 1000).toISOString(),
    gast_deg: 39.64937 + index * 2.5,
    sun: body('sun'),
    moon: body('moon'),
    planets: PLANET_IDS.map((id) => body(id)),
  }));
  return {
    ephemeris: 'swisseph 2.10.03',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[2].at,
    step_seconds: stepSeconds,
    count: 3,
    samples,
    provenance: { computed: 'computed' },
    ...overrides,
  };
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

describe('fetchSeries: request', () => {
  it('calls the proxy-relative route with normalised UTC instants and step', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    const series = await fetchSeries(START, END, 600);
    expect(series.count).toBe(3);
    expect(series.siderealTime).toBe('apparent');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/astrology/earth-state/series?');
    expect(url).toContain(`start=${encodeURIComponent('2026-03-20T14:46:00.000Z')}`);
    expect(url).toContain(`end=${encodeURIComponent('2026-03-20T15:06:00.000Z')}`);
    expect(url).toContain('step_seconds=600');
    expect(init.signal).toBeDefined();
  });

  it('accepts the scrubber fencepost step of 603 s', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload(603)));
    const end = new Date(Date.parse(START) + 2 * 603_000).toISOString();
    const series = await fetchSeries(START, end, 603);
    expect(series.stepSeconds).toBe(603);
    const url = String((fetchMock.mock.calls[0] as [string, RequestInit])[0]);
    expect(url).toContain('step_seconds=603');
  });

  it('normalises offset-bearing instants to ...Z', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchSeries('2026-03-20T15:46:00+01:00', '2026-03-20T16:06:00+01:00', 600);
    const url = String((fetchMock.mock.calls[0] as [string, RequestInit])[0]);
    expect(url).toContain(encodeURIComponent('2026-03-20T14:46:00.000Z'));
  });

  it('rejects bad local input without calling the network', async () => {
    await expect(fetchSeries('2026-03-20', END, 600)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSeries(END, START, 600)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSeries(START, END, 59)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSeries(START, END, 3601)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSeries(START, END, 600.5)).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('fetchSeries: response validation', () => {
  it('rejects a response that fails decodeSeries, naming the path', async () => {
    const bad = payload();
    const samples = bad.samples as Record<string, unknown>[];
    samples[0].planets = (samples[0].planets as unknown[]).slice(0, 7);
    fetchMock.mockResolvedValue(jsonResponse(bad));

    const error = await fetchSeries(START, END, 600).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(EarthSeriesError);
    expect(error).toMatchObject({ kind: 'invalid-response' });
    expect(String((error as Error).message)).toContain('samples[0].planets');
  });

  it('rejects a non-JSON body', async () => {
    fetchMock.mockResolvedValue(new Response('not json', { status: 200 }));
    await expect(fetchSeries(START, END, 600)).rejects.toMatchObject({ kind: 'invalid-response' });
  });
});

describe('fetchSeries: the Moon distance (W4-T2)', () => {
  function withDistances(values: (number | undefined)[]): Record<string, unknown> {
    const body = payload();
    const samples = body.samples as Record<string, unknown>[];
    values.forEach((value, index) => {
      if (value !== undefined) samples[index].moon_distance_au = value;
    });
    return body;
  }

  it('hands a series that carries it back as topocentric', async () => {
    fetchMock.mockResolvedValue(jsonResponse(withDistances([0.00246, 0.002461, 0.002462])));
    const series = await fetchSeries(START, END, 600);
    expect(series.moonFrame).toBe('topocentric');
    expect(series.samples.map((s) => s.moonDistanceAu)).toEqual([0.00246, 0.002461, 0.002462]);
  });

  it('hands a series without it back as geocentric, as before', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    expect((await fetchSeries(START, END, 600)).moonFrame).toBe('geocentric');
  });

  it('rejects a mixed series as an invalid response, naming the sample', async () => {
    fetchMock.mockResolvedValue(jsonResponse(withDistances([0.00246, undefined, 0.002462])));
    const error = await fetchSeries(START, END, 600).catch((e: unknown) => e);
    expect(error).toMatchObject({ kind: 'invalid-response' });
    expect(String((error as Error).message)).toContain('samples[1].moon_distance_au');
  });

  it('rejects a distance that is not a Moon distance in AU', async () => {
    fetchMock.mockResolvedValue(jsonResponse(withDistances([384400, 384400, 384400])));
    const error = await fetchSeries(START, END, 600).catch((e: unknown) => e);
    expect(error).toMatchObject({ kind: 'invalid-response' });
    expect(String((error as Error).message)).toContain('samples[0].moon_distance_au');
  });
});

describe('fetchSeries: typed failures', () => {
  it('maps 422 to invalid-input and keeps the server detail', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'step_seconds must be 60..3600' }, 422));
    const error = await fetchSeries(START, END, 600).catch((e: unknown) => e);
    expect(error).toMatchObject({ kind: 'invalid-input', status: 422 });
    expect(String((error as Error).message)).toContain('step_seconds must be 60..3600');
  });

  it('maps 503 to unavailable and other statuses to http', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'ephemeris offline' }, 503));
    await expect(fetchSeries(START, END, 600)).rejects.toMatchObject({
      kind: 'unavailable',
      status: 503,
    });

    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await expect(fetchSeries(START, END, 600)).rejects.toMatchObject({ kind: 'http', status: 500 });
  });

  it('maps a network rejection to network', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(fetchSeries(START, END, 600)).rejects.toMatchObject({ kind: 'network' });
  });
});

describe('fetchSeries: stale-request guard', () => {
  it('cancelSeriesRequest aborts the in-flight call as stale', async () => {
    let pendingResolve: ((response: Response) => void) | null = null;
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          pendingResolve = resolve;
        }),
    );
    const pending = fetchSeries(START, END, 600);
    const rejection = expect(pending).rejects.toMatchObject({ kind: 'stale' });
    cancelSeriesRequest();
    const signal = (fetchMock.mock.calls[0] as [string, RequestInit])[1].signal as AbortSignal;
    expect(signal.aborted).toBe(true);
    (pendingResolve as unknown as (response: Response) => void)(jsonResponse(payload()));
    await rejection;
  });

  it('lets a newer call win even when the older answer arrives last', async () => {
    const pending: ((response: Response) => void)[] = [];
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          pending.push(resolve);
        }),
    );

    const older = fetchSeries(START, END, 600);
    const olderRejection = expect(older).rejects.toMatchObject({ kind: 'stale' });
    const newer = fetchSeries(START, END, 600);

    expect(pending).toHaveLength(2);
    pending[1](jsonResponse(payload()));
    const winner = await newer;
    expect(winner.count).toBe(3);

    // The older request still answers; it must not override the newer result.
    pending[0](jsonResponse(payload()));
    await olderRejection;
  });
});

/**
 * Headers arrive at once; the body then stays open and errors when the request is aborted, as a real fetch
 * body does. (Superseding or timing out a request after its headers arrived is exactly this case.)
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

describe('fetchSeries: a superseded request is never reported as a real error', () => {
  it('is stale when it is superseded while its 200 body is being read', async () => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, 200)),
    );
    const older = settle(fetchSeries(START, END, 600));
    await nextMacrotask(); // let the older call reach `response.json()`
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await expect(fetchSeries(START, END, 600)).resolves.toMatchObject({ count: 3 });
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it.each([422, 500, 503])('is stale when it is superseded after a %i arrived', async (status) => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, status)),
    );
    const older = settle(fetchSeries(START, END, 600));
    await nextMacrotask();
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchSeries(START, END, 600);
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it('cancelSeriesRequest makes an in-flight call stale, also mid-body', async () => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, 200)),
    );
    const inFlight = settle(fetchSeries(START, END, 600));
    await nextMacrotask();
    cancelSeriesRequest();
    expect(await inFlight).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});

describe('fetchSeries: timeout', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('abandons a server that never answers as a network error after 15 s', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(neverAnswers);
    const outcome = settle(fetchSeries(START, END, 600));
    await vi.advanceTimersByTimeAsync(14_999);
    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(1);
    const result = await outcome;
    expect(result).toMatchObject({ ok: false, error: { kind: 'network' } });
    expect(String((result as { error: Error }).error.message)).toMatch(/timed out after 15 s/i);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('also covers a body that never finishes (headers arrived, nothing else)', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, 200)),
    );
    const outcome = settle(fetchSeries(START, END, 600));
    await vi.advanceTimersByTimeAsync(15_000);
    const result = await outcome;
    expect(result).toMatchObject({ ok: false, error: { kind: 'network' } });
    expect(String((result as { error: Error }).error.message)).toMatch(/timed out/i);
  });

  it('a timeout on an error body is the timeout, not the status', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, 503)),
    );
    const outcome = settle(fetchSeries(START, END, 600));
    await vi.advanceTimersByTimeAsync(15_000);
    expect(await outcome).toMatchObject({ ok: false, error: { kind: 'network' } });
  });

  it('leaves no timer behind after a success, a failure or a cancel', async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchSeries(START, END, 600);
    expect(vi.getTimerCount()).toBe(0);

    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await settle(fetchSeries(START, END, 600));
    expect(vi.getTimerCount()).toBe(0);

    fetchMock.mockImplementation(neverAnswers);
    const cancelled = settle(fetchSeries(START, END, 600));
    cancelSeriesRequest();
    await cancelled;
    expect(vi.getTimerCount()).toBe(0);
  });

  it('a request that was superseded and then timed out is still stale', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(neverAnswers);
    const older = settle(fetchSeries(START, END, 600));
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchSeries(START, END, 600);
    await vi.advanceTimersByTimeAsync(20_000);
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});

describe('fetchSeries: a window of fewer than two samples is refused up front', () => {
  it('rejects start == end without calling the network (the decoder needs at least two samples)', async () => {
    await expect(fetchSeries(START, START, 600)).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an end that is less than one step after the start', async () => {
    const shortEnd = new Date(Date.parse(START) + 599_000).toISOString();
    const error = await fetchSeries(START, shortEnd, 600).catch((e: unknown) => e);
    expect(error).toMatchObject({ kind: 'invalid-input' });
    expect(String((error as Error).message)).toMatch(/two samples|at least one step/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('accepts an end exactly one step after the start (two samples)', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    const oneStep = new Date(Date.parse(START) + 600_000).toISOString();
    await expect(fetchSeries(START, oneStep, 600)).resolves.toMatchObject({ count: 3 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
