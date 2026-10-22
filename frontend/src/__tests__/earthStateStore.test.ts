// @vitest-environment happy-dom
/**
 * W1-D1 earth-state store. The sun lat/lon are copied from the oracle case
 * 2026-10-22T02:00:00Z (docs/notes/earthsky/wave1/oracle/oracle_cases.json).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useEarthStateStore } from '../stores/earthStateStore';

const SUN_LAT = -11.007839;
const SUN_LON = 146.135149;

function earthBody(id: string, lat: number, lon: number) {
  return { id, name: id, ra_deg: 0, dec_deg: lat, lat, lon };
}

function oracleState() {
  return {
    at: '2026-10-22T02:00:00Z',
    ephemeris: 'de432s',
    gast_deg: 60.525177,
    sun: earthBody('sun', SUN_LAT, SUN_LON),
    moon: earthBody('moon', -8.166428, -82.025959),
    planets: [earthBody('mercury', -20.950951, 166.816802)],
    provenance: { sun: 'computed' },
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('earthStateStore', () => {
  let hidden = false;
  const unsubscribers: Array<() => void> = [];

  beforeEach(() => {
    hidden = false;
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => hidden,
    });
    vi.useFakeTimers();
    useEarthStateStore.setState({
      status: 'idle',
      state: null,
      fetchedAt: null,
      error: null,
    });
  });

  afterEach(() => {
    unsubscribers.splice(0).forEach((unsubscribe) => unsubscribe());
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useEarthStateStore.setState({
      status: 'idle',
      state: null,
      fetchedAt: null,
      error: null,
    });
  });

  function subscribe(): () => void {
    const unsubscribe = useEarthStateStore.getState().subscribe();
    unsubscribers.push(unsubscribe);
    return unsubscribe;
  }

  it('ref-counts subscribers, polls every 60 s, and stops on the last unsubscribe', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      void url;
      return jsonResponse(200, oracleState());
    });
    vi.stubGlobal('fetch', fetchMock);

    const first = subscribe();
    const second = subscribe();
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toBe('/api/v1/astrology/earth-state');
    expect(useEarthStateStore.getState().status).toBe('ok');
    expect(useEarthStateStore.getState().state?.sun.lat).toBe(SUN_LAT);
    expect(useEarthStateStore.getState().state?.sun.lon).toBe(SUN_LON);

    await vi.advanceTimersByTimeAsync(59_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    first();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(fetchMock).toHaveBeenCalledTimes(3);

    second();
    await vi.advanceTimersByTimeAsync(120_000);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('pauses while the document is hidden and refreshes once it is visible', async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, oracleState()));
    vi.stubGlobal('fetch', fetchMock);

    subscribe();
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    hidden = true;
    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(180_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    hidden = false;
    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('does not start a request while the document is already hidden', async () => {
    hidden = true;
    const fetchMock = vi.fn(async () => jsonResponse(200, oracleState()));
    vi.stubGlobal('fetch', fetchMock);
    subscribe();
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(useEarthStateStore.getState().status).toBe('idle');
  });

  it('stores unavailable and a null state on HTTP 503', async () => {
    const fetchMock = vi.fn(async () => jsonResponse(503, { detail: 'ephemeris unavailable' }));
    vi.stubGlobal('fetch', fetchMock);
    useEarthStateStore.setState({
      status: 'ok',
      state: oracleState(),
      fetchedAt: 1,
      error: null,
    });

    await useEarthStateStore.getState().refresh();
    expect(useEarthStateStore.getState().status).toBe('unavailable');
    expect(useEarthStateStore.getState().state).toBeNull();
    expect(useEarthStateStore.getState().fetchedAt).toBeNull();
  });

  it('keeps a single in-flight request when refresh overlaps', async () => {
    let release: (response: Response) => void = () => {};
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    const fetchMock = vi.fn(() => gate);
    vi.stubGlobal('fetch', fetchMock);

    const first = useEarthStateStore.getState().refresh();
    const second = useEarthStateStore.getState().refresh();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    release(jsonResponse(200, oracleState()));
    await Promise.all([first, second]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(useEarthStateStore.getState().status).toBe('ok');
  });
});
