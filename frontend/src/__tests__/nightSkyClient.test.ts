/**
 * W3-D2a tests for frontend/src/lib/nightSkyClient.ts.
 *
 * The dome used to cast the `/night-sky` body and then throw during render when
 * `moon.phase_name` / `planets` were missing. This client validates the whole
 * shape it reads (naming the first bad path), and turns 422/503/HTTP/network
 * failures into typed errors. A newer call wins even if the older answer lands
 * last, and the newer call aborts the older one.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  NightSkyError,
  cancelNightSkyRequest,
  decodeNightSky,
  fetchNightSky,
  type NightSky,
} from '../lib/nightSkyClient';

const PLANET = {
  id: 'jupiter',
  name: 'Jupiter',
  glyph: '♃',
  altitude: 58.2,
  azimuth: 142.1,
  sign: 'Cancer',
  sign_glyph: '♋',
  visible: true,
  color: '#a855f7',
  esoteric_quality: 'Guru · Expansive Grace',
};

const STAR = {
  id: 'sirius',
  name: 'Sirius (Mrigavyadha)',
  altitude: 35.8,
  azimuth: 122.4,
  magnitude: -1.46,
  visible: true,
  color: '#a6d8ff',
  nakshatra: 'Ardra',
  quality: 'Supreme Cosmic Fire',
};

function payload(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    timestamp_utc: '2026-10-22T02:00:00Z',
    observer: {
      latitude: 37.7749,
      longitude: -122.4194,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Waning Crescent', illumination: 22.6 },
    planets: [{ ...PLANET }],
    visible_planets_count: 1,
    sacred_stars: [{ ...STAR }],
    visible_stars_count: 1,
    provenance: { observer: 'computed' },
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) } as Response;
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  cancelNightSkyRequest();
});

describe('decodeNightSky', () => {
  it('accepts the validated shape and returns only the fields the dome reads', () => {
    const sky: NightSky = decodeNightSky(payload());
    expect(sky.observer.local_sidereal_time_hms).toBe('19:52:26');
    expect(sky.moon.phase_name).toBe('Waning Crescent');
    expect(sky.planets[0].esoteric_quality).toContain('Guru');
    expect(sky.sacred_stars[0].nakshatra).toBe('Ardra');
    expect(sky.visible_planets_count).toBe(1);
  });

  it('rejects the exact body that used to crash the render ({observer} only)', () => {
    const error = (() => {
      try {
        decodeNightSky({
          observer: {
            latitude: 0,
            longitude: 0,
            local_sidereal_time_deg: 0,
            local_sidereal_time_hms: '00:00:00',
          },
        });
        return null;
      } catch (caught) {
        return caught;
      }
    })();
    expect(error).toBeInstanceOf(NightSkyError);
    expect(error).toMatchObject({ kind: 'invalid-response' });
    expect(String((error as Error).message)).toContain('timestamp_utc');
  });

  it('accepts optional J2000 sacred-star coordinates when present', () => {
    const sky = decodeNightSky(
      payload({ sacred_stars: [{ ...STAR, ra_j2000: 101.287, dec_j2000: -16.716 }] }),
    );
    expect(sky.sacred_stars[0].ra_j2000).toBe(101.287);
    expect(sky.sacred_stars[0].dec_j2000).toBe(-16.716);
  });

  it('rejects out-of-range J2000 fields, naming the path', () => {
    for (const [field, value] of [['ra_j2000', 400], ['dec_j2000', -95]] as const) {
      const body = payload({ sacred_stars: [{ ...STAR, [field]: value }] });
      expect(() => decodeNightSky(body), field).toThrow(new RegExp(`sacred_stars\\[0\\]\\.${field}`));
    }
  });

  it('names the first bad path for each field class', () => {
    const mutations: [string, (body: Record<string, unknown>) => void, RegExp][] = [
      ['timestamp without zone', (body) => (body.timestamp_utc = '2026-10-22T02:00:00'), /timestamp_utc/],
      ['observer latitude type', (body) => ((body.observer as Record<string, unknown>).latitude = 'north'), /observer\.latitude/],
      ['observer hms missing', (body) => delete (body.observer as Record<string, unknown>).local_sidereal_time_hms, /observer\.local_sidereal_time_hms/],
      ['moon phase missing', (body) => delete (body.moon as Record<string, unknown>).phase_name, /moon\.phase_name/],
      ['planets not an array', (body) => (body.planets = {}), /planets/],
      ['planet altitude missing', (body) => delete ((body.planets as Record<string, unknown>[])[0] as Record<string, unknown>).altitude, /planets\[0\]\.altitude/],
      ['planet visible not boolean', (body) => (((body.planets as Record<string, unknown>[])[0] as Record<string, unknown>).visible = 1), /planets\[0\]\.visible/],
      ['star name missing', (body) => delete ((body.sacred_stars as Record<string, unknown>[])[0] as Record<string, unknown>).name, /sacred_stars\[0\]\.name/],
      ['star magnitude not finite', (body) => (((body.sacred_stars as Record<string, unknown>[])[0] as Record<string, unknown>).magnitude = Number.NaN), /sacred_stars\[0\]\.magnitude/],
      ['count negative', (body) => (body.visible_stars_count = -1), /visible_stars_count/],
      ['provenance missing', (body) => delete body.provenance, /provenance/],
    ];
    for (const [label, mutate, path] of mutations) {
      const body = payload();
      mutate(body);
      expect(() => decodeNightSky(body), label).toThrow(path);
    }
  });
});

describe('fetchNightSky: request', () => {
  it('calls the proxy-relative route with the observer, and no time by default', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(37.7749, -122.4194);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/astrology/night-sky?');
    expect(url).toContain('latitude=37.7749');
    expect(url).toContain('longitude=-122.4194');
    expect(url).not.toContain('datetime_str');
    expect(init.signal).toBeDefined();
  });

  it('sends an explicit instant when given one', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(0, 0, '2026-10-24T11:00:00+02:00');
    const url = String((fetchMock.mock.calls[0] as [string, RequestInit])[0]);
    expect(url).toContain(encodeURIComponent('2026-10-24T09:00:00.000Z'));
  });

  it('rejects bad local input without calling the network', async () => {
    await expect(fetchNightSky(91, 0)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchNightSky(0, Number.NaN)).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchNightSky(0, 0, '2026-10-24T09:00:00')).rejects.toMatchObject({
      kind: 'invalid-input',
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('fetchNightSky: typed failures', () => {
  it('maps 422, 503, other statuses and network to typed errors', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'bad observer' }, 422));
    await expect(fetchNightSky(0, 0)).rejects.toMatchObject({ kind: 'invalid-input', status: 422 });

    fetchMock.mockResolvedValue(jsonResponse({ detail: 'ephemeris offline' }, 503));
    await expect(fetchNightSky(0, 0)).rejects.toMatchObject({ kind: 'unavailable', status: 503 });

    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await expect(fetchNightSky(0, 0)).rejects.toMatchObject({ kind: 'http', status: 500 });

    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(fetchNightSky(0, 0)).rejects.toMatchObject({ kind: 'network' });
  });

  it('rejects a malformed body as invalid-response, naming the path', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        observer: { latitude: 0, longitude: 0, local_sidereal_time_deg: 0, local_sidereal_time_hms: '00:00:00' },
      }),
    );
    const error = await fetchNightSky(0, 0).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(NightSkyError);
    expect(error).toMatchObject({ kind: 'invalid-response' });
    expect(String((error as Error).message)).toMatch(/timestamp_utc|moon/);
  });
});

describe('fetchNightSky: newest request wins', () => {
  it('aborts the older request when a newer one starts', async () => {
    const pending: ((response: Response) => void)[] = [];
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          pending.push(resolve);
        }),
    );
    const older = fetchNightSky(10, 20);
    const olderRejection = expect(older).rejects.toMatchObject({ kind: 'stale' });
    const newer = fetchNightSky(30, 40);
    const signals = fetchMock.mock.calls.map(
      (call) => (call as [string, RequestInit])[1].signal as AbortSignal,
    );
    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);

    pending[1](jsonResponse(payload()));
    await expect(newer).resolves.toMatchObject({ visible_planets_count: 1 });
    pending[0](jsonResponse(payload()));
    await olderRejection;
  });

  it('cancelNightSkyRequest aborts the in-flight call as stale', async () => {
    let pendingResolve: ((response: Response) => void) | null = null;
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          pendingResolve = resolve;
        }),
    );
    const pending = fetchNightSky(0, 0);
    const rejection = expect(pending).rejects.toMatchObject({ kind: 'stale' });
    cancelNightSkyRequest();
    const signal = (fetchMock.mock.calls[0] as [string, RequestInit])[1].signal as AbortSignal;
    expect(signal.aborted).toBe(true);
    (pendingResolve as unknown as (response: Response) => void)(jsonResponse(payload()));
    await rejection;
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

describe('fetchNightSky: a superseded request is never reported as a real error', () => {
  it('is stale when it is superseded while its 200 body is being read', async () => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, 200)),
    );
    const older = settle(fetchNightSky(0, 0));
    await nextMacrotask(); // let the older call reach `response.json()`
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await expect(fetchNightSky(0, 0)).resolves.toMatchObject({ visible_planets_count: 1 });
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it.each([422, 500, 503])('is stale when it is superseded after a %i arrived', async (status) => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, status)),
    );
    const older = settle(fetchNightSky(0, 0));
    await nextMacrotask();
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(0, 0);
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });

  it('cancelNightSkyRequest makes an in-flight call stale, also mid-body', async () => {
    fetchMock.mockImplementationOnce((_url: string, init: RequestInit) =>
      Promise.resolve(slowBodyResponse(init.signal, 200)),
    );
    const inFlight = settle(fetchNightSky(0, 0));
    await nextMacrotask();
    cancelNightSkyRequest();
    expect(await inFlight).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});

describe('fetchNightSky: timeout', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('abandons a server that never answers as a network error after 15 s', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(neverAnswers);
    const outcome = settle(fetchNightSky(0, 0));
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
    const outcome = settle(fetchNightSky(0, 0));
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
    const outcome = settle(fetchNightSky(0, 0));
    await vi.advanceTimersByTimeAsync(15_000);
    expect(await outcome).toMatchObject({ ok: false, error: { kind: 'network' } });
  });

  it('leaves no timer behind after a success, a failure or a cancel', async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(0, 0);
    expect(vi.getTimerCount()).toBe(0);

    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500));
    await settle(fetchNightSky(0, 0));
    expect(vi.getTimerCount()).toBe(0);

    fetchMock.mockImplementation(neverAnswers);
    const cancelled = settle(fetchNightSky(0, 0));
    cancelNightSkyRequest();
    await cancelled;
    expect(vi.getTimerCount()).toBe(0);
  });

  it('a request that was superseded and then timed out is still stale', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(neverAnswers);
    const older = settle(fetchNightSky(0, 0));
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(0, 0);
    await vi.advanceTimersByTimeAsync(20_000);
    expect(await older).toMatchObject({ ok: false, error: { kind: 'stale' } });
  });
});

describe('fetchNightSky: the observer is checked and the longitude wrapped before requesting', () => {
  const requested = () =>
    String((fetchMock.mock.calls[fetchMock.mock.calls.length - 1] as [string, RequestInit])[0]);

  it.each([
    [190, '-170'],
    [-190, '170'],
    [180, '-180'],
    [540, '-180'],
    [360, '0'],
    [-360, '0'],
    [725, '5'],
  ])('wraps longitude %d into [-180, 180) as %s', async (lng, wrapped) => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(10, lng);
    expect(new URL(requested(), 'http://x').searchParams.get('longitude')).toBe(wrapped);
  });

  it('keeps an in-range longitude byte for byte (no floating-point noise)', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    for (const lng of [-122.4194, 179.9999, -180, 0, 18.42]) {
      await fetchNightSky(10, lng);
      expect(requested()).toContain(`longitude=${lng}`);
    }
  });

  it('wraps an enormous finite longitude into range', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(10, 1_000_000);
    const sent = Number(new URL(requested(), 'http://x').searchParams.get('longitude'));
    expect(sent).toBeGreaterThanOrEqual(-180);
    expect(sent).toBeLessThan(180);
    expect(((1_000_000 - sent) % 360 + 360) % 360).toBeCloseTo(0, 6);
  });

  it('rejects a latitude outside [-90, 90] as invalid-input, without a request', async () => {
    for (const lat of [90.0001, -91, 95, 1000, Number.POSITIVE_INFINITY, Number.NaN]) {
      await expect(fetchNightSky(lat, 0), String(lat)).rejects.toMatchObject({ kind: 'invalid-input' });
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('accepts the latitude boundaries', async () => {
    fetchMock.mockResolvedValue(jsonResponse(payload()));
    await fetchNightSky(90, 0);
    await fetchNightSky(-90, 0);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
