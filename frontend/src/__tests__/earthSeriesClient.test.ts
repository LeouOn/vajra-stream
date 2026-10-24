/**
 * W3-D1 tests for frontend/src/lib/earthSeriesClient.ts.
 *
 * The client validates the series payload with `decodeSeries` (no casts),
 * turns 422/503/network failures into typed readable errors, and lets a newer
 * call win: an older answer that arrives last is rejected as `stale`.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
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
