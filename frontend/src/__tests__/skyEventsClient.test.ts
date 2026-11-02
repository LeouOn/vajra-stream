/**
 * W7-3b tests for frontend/src/lib/skyEventsClient.ts.
 *
 * The validator accepts the real W7-2 responses exactly (extra keys ignored),
 * rejects malformed shapes, and the fetch turns 422/503/network failures into
 * typed errors while a newer call makes an older one stale. The fetch-key and
 * window-cover helpers are pure and pinned here.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  SkyEventsError,
  cancelSkyEventsRequest,
  fetchSkyEvents,
  skyEventsFetchKey,
  skyEventsWindowCovers,
  validateSkyEvents,
} from '../lib/skyEventsClient';

const SF = {
  "status": "success",
  "window": {
    "from": "2026-06-20T12:00:00Z",
    "to": "2026-06-23T12:00:00Z"
  },
  "observer": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "convention": "Rise and set: upper edge of the disc at the apparent horizon, standard refraction (34 arcmin). Twilight: centre of the Sun at -6, -12 and -18 degrees, no refraction. Transit: highest point.",
  "events": [
    {
      "body": "sun",
      "kind": "civil_dawn",
      "at": "2026-06-20T12:16:32Z"
    },
    {
      "body": "sun",
      "kind": "rise",
      "at": "2026-06-20T12:47:38Z"
    },
    {
      "body": "moon",
      "kind": "rise",
      "at": "2026-06-20T19:07:04Z"
    },
    {
      "body": "sun",
      "kind": "transit",
      "at": "2026-06-20T20:11:21Z"
    },
    {
      "body": "moon",
      "kind": "transit",
      "at": "2026-06-21T01:31:41Z"
    },
    {
      "body": "sun",
      "kind": "set",
      "at": "2026-06-21T03:35:04Z"
    },
    {
      "body": "sun",
      "kind": "civil_dusk",
      "at": "2026-06-21T04:06:11Z"
    },
    {
      "body": "sun",
      "kind": "nautical_dusk",
      "at": "2026-06-21T04:45:27Z"
    },
    {
      "body": "sun",
      "kind": "astronomical_dusk",
      "at": "2026-06-21T05:30:01Z"
    },
    {
      "body": "moon",
      "kind": "set",
      "at": "2026-06-21T07:45:48Z"
    },
    {
      "body": "sun",
      "kind": "astronomical_dawn",
      "at": "2026-06-21T10:52:55Z"
    },
    {
      "body": "sun",
      "kind": "nautical_dawn",
      "at": "2026-06-21T11:37:28Z"
    },
    {
      "body": "sun",
      "kind": "civil_dawn",
      "at": "2026-06-21T12:16:45Z"
    },
    {
      "body": "sun",
      "kind": "rise",
      "at": "2026-06-21T12:47:51Z"
    },
    {
      "body": "moon",
      "kind": "rise",
      "at": "2026-06-21T20:10:57Z"
    },
    {
      "body": "sun",
      "kind": "transit",
      "at": "2026-06-21T20:11:34Z"
    },
    {
      "body": "moon",
      "kind": "transit",
      "at": "2026-06-22T02:14:46Z"
    },
    {
      "body": "sun",
      "kind": "set",
      "at": "2026-06-22T03:35:17Z"
    },
    {
      "body": "sun",
      "kind": "civil_dusk",
      "at": "2026-06-22T04:06:23Z"
    },
    {
      "body": "sun",
      "kind": "nautical_dusk",
      "at": "2026-06-22T04:45:40Z"
    },
    {
      "body": "sun",
      "kind": "astronomical_dusk",
      "at": "2026-06-22T05:30:13Z"
    },
    {
      "body": "moon",
      "kind": "set",
      "at": "2026-06-22T08:09:04Z"
    },
    {
      "body": "sun",
      "kind": "astronomical_dawn",
      "at": "2026-06-22T10:53:09Z"
    },
    {
      "body": "sun",
      "kind": "nautical_dawn",
      "at": "2026-06-22T11:37:42Z"
    },
    {
      "body": "sun",
      "kind": "civil_dawn",
      "at": "2026-06-22T12:16:59Z"
    },
    {
      "body": "sun",
      "kind": "rise",
      "at": "2026-06-22T12:48:05Z"
    },
    {
      "body": "sun",
      "kind": "transit",
      "at": "2026-06-22T20:11:47Z"
    },
    {
      "body": "moon",
      "kind": "rise",
      "at": "2026-06-22T21:13:01Z"
    },
    {
      "body": "moon",
      "kind": "transit",
      "at": "2026-06-23T02:57:06Z"
    },
    {
      "body": "sun",
      "kind": "set",
      "at": "2026-06-23T03:35:28Z"
    },
    {
      "body": "sun",
      "kind": "civil_dusk",
      "at": "2026-06-23T04:06:34Z"
    },
    {
      "body": "sun",
      "kind": "nautical_dusk",
      "at": "2026-06-23T04:45:50Z"
    },
    {
      "body": "sun",
      "kind": "astronomical_dusk",
      "at": "2026-06-23T05:30:22Z"
    },
    {
      "body": "moon",
      "kind": "set",
      "at": "2026-06-23T08:32:35Z"
    },
    {
      "body": "sun",
      "kind": "astronomical_dawn",
      "at": "2026-06-23T10:53:27Z"
    },
    {
      "body": "sun",
      "kind": "nautical_dawn",
      "at": "2026-06-23T11:37:59Z"
    }
  ],
  "always": {
    "sun": null,
    "moon": null
  },
  "timezone": "America/Los_Angeles",
  "provenance": {
    "window": "computed",
    "convention": "computed",
    "events": "computed",
    "always": "computed",
    "timezone": "computed"
  }
};
const TROMSO = {
  "status": "success",
  "window": {
    "from": "2026-06-20T12:00:00Z",
    "to": "2026-06-23T12:00:00Z"
  },
  "observer": {
    "latitude": 69.65,
    "longitude": 18.96
  },
  "convention": "Rise and set: upper edge of the disc at the apparent horizon, standard refraction (34 arcmin). Twilight: centre of the Sun at -6, -12 and -18 degrees, no refraction. Transit: highest point.",
  "events": [
    {
      "body": "moon",
      "kind": "transit",
      "at": "2026-06-20T15:48:45Z"
    },
    {
      "body": "moon",
      "kind": "set",
      "at": "2026-06-20T22:37:42Z"
    },
    {
      "body": "moon",
      "kind": "rise",
      "at": "2026-06-21T10:17:14Z"
    },
    {
      "body": "sun",
      "kind": "transit",
      "at": "2026-06-21T10:45:58Z"
    },
    {
      "body": "moon",
      "kind": "transit",
      "at": "2026-06-21T16:32:30Z"
    },
    {
      "body": "moon",
      "kind": "set",
      "at": "2026-06-21T22:14:09Z"
    },
    {
      "body": "sun",
      "kind": "transit",
      "at": "2026-06-22T10:46:11Z"
    },
    {
      "body": "moon",
      "kind": "rise",
      "at": "2026-06-22T12:12:40Z"
    },
    {
      "body": "moon",
      "kind": "transit",
      "at": "2026-06-22T17:14:58Z"
    },
    {
      "body": "moon",
      "kind": "set",
      "at": "2026-06-22T21:49:45Z"
    },
    {
      "body": "sun",
      "kind": "transit",
      "at": "2026-06-23T10:46:24Z"
    }
  ],
  "always": {
    "sun": "up",
    "moon": null
  },
  "timezone": "Europe/Oslo",
  "provenance": {
    "window": "computed",
    "convention": "computed",
    "events": "computed",
    "always": "computed",
    "timezone": "computed"
  }
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  cancelSkyEventsRequest();
  vi.unstubAllGlobals();
});

describe('validateSkyEvents: the real responses', () => {
  it('accepts the San Francisco response exactly as W7-2 returned it', () => {
    const data = validateSkyEvents(SF);
    expect(data.status).toBe('success');
    expect(data.window.from).toBe('2026-06-20T12:00:00Z');
    expect(data.window.to).toBe('2026-06-23T12:00:00Z');
    expect(data.observer.latitude).toBeCloseTo(37.7749, 4);
    expect(data.observer.longitude).toBeCloseTo(-122.4194, 4);
    expect(data.timezone).toBe('America/Los_Angeles');
    expect(data.events).toHaveLength(SF.events.length);
    expect(data.events[0].kind).toBe('civil_dawn');
    expect(data.always).toEqual({ sun: null, moon: null });
    // ascending by instant
    expect(data.events.every((event, i) => i === 0 || event.atMs >= data.events[i - 1].atMs)).toBe(true);
  });

  it('accepts the Tromso polar-day response exactly (always.sun = "up")', () => {
    const data = validateSkyEvents(TROMSO);
    expect(data.timezone).toBe('Europe/Oslo');
    expect(data.always.sun).toBe('up');
    expect(data.always.moon).toBeNull();
    expect(data.events).toHaveLength(TROMSO.events.length);
  });

  it('ignores unknown top-level keys (status/provenance are already handled)', () => {
    const data = validateSkyEvents({ ...SF, extra: 'ignored', provenance: { events: 'computed' } });
    expect(data.events).toHaveLength(SF.events.length);
  });

  it('rejects a wrong status, a bad window, an unknown event kind and bad always', () => {
    expect(() => validateSkyEvents({ ...SF, status: 'ok' })).toThrow(SkyEventsError);
    expect(() => validateSkyEvents({ ...SF, window: { from: SF.window.to, to: SF.window.from } })).toThrow(/window\.from/);
    const badKind = { ...SF, events: [{ body: 'sun', kind: 'eclipse', at: SF.window.from }] };
    expect(() => validateSkyEvents(badKind)).toThrow(/kind/);
    const badAlways = { ...SF, always: { sun: 'above', moon: null } };
    expect(() => validateSkyEvents(badAlways)).toThrow(/always\.sun/);
  });
});

describe('fetchSkyEvents: request and errors', () => {
  it('calls the proxy-relative route with the observer and the normalised UTC instant', async () => {
    fetchMock.mockResolvedValue(jsonResponse(SF));
    const data = await fetchSkyEvents(37.7749, -122.4194, '2026-06-21T20:00:00+02:00');
    expect(data.events.length).toBe(SF.events.length);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/astrology/sky-events?');
    expect(url).toContain('latitude=37.7749');
    expect(url).toContain('longitude=-122.4194');
    expect(url).toContain(encodeURIComponent('2026-06-21T18:00:00.000Z'));
    expect(init.signal).toBeDefined();
  });

  it('maps 422, 503, HTTP and network failures to typed errors', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'bad latitude' }, 422));
    await expect(fetchSkyEvents(0, 0, '2026-06-21T18:00:00Z')).rejects.toMatchObject({ kind: 'invalid-input', status: 422 });
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ephemeris unavailable' }, 503));
    await expect(fetchSkyEvents(0, 0, '2026-06-21T18:00:00Z')).rejects.toMatchObject({ kind: 'unavailable', status: 503 });
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 500));
    await expect(fetchSkyEvents(0, 0, '2026-06-21T18:00:00Z')).rejects.toMatchObject({ kind: 'http', status: 500 });
    fetchMock.mockRejectedValueOnce(new Error('offline'));
    await expect(fetchSkyEvents(0, 0, '2026-06-21T18:00:00Z')).rejects.toMatchObject({ kind: 'network' });
  });

  it('rejects bad input without a request', async () => {
    await expect(fetchSkyEvents(91, 0, '2026-06-21T18:00:00Z')).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSkyEvents(0, 181, '2026-06-21T18:00:00Z')).rejects.toMatchObject({ kind: 'invalid-input' });
    await expect(fetchSkyEvents(0, 0, 'not-a-time')).rejects.toMatchObject({ kind: 'invalid-input' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('a newer request makes the older one stale', async () => {
    const resolvers: Array<(response: Response) => void> = [];
    fetchMock.mockImplementation(
      () => new Promise<Response>((resolve) => resolvers.push(resolve)),
    );
    const first = fetchSkyEvents(0, 0, '2026-06-21T18:00:00Z');
    const second = fetchSkyEvents(0, 1, '2026-06-21T18:00:00Z');
    resolvers[1](jsonResponse(TROMSO));
    await expect(second).resolves.toBeTruthy();
    resolvers[0](jsonResponse(SF));
    await expect(first).rejects.toMatchObject({ kind: 'stale' });
  });
});

describe('fetch key and window cover', () => {
  it('rounds the observer to 0.01 degrees and buckets the instant to 6 h', () => {
    const a = skyEventsFetchKey(37.7749, -122.4194, Date.parse('2026-06-21T18:00:00Z'));
    const b = skyEventsFetchKey(37.77491, -122.41942, Date.parse('2026-06-21T23:59:00Z'));
    expect(a).toMatch(/^37\.77,-122\.42@\d+$/);
    expect(b).toBe(a);
    const c = skyEventsFetchKey(37.7749, -122.4194, Date.parse('2026-06-22T00:00:00Z'));
    expect(c).not.toBe(a);
  });

  it('covers the window minus a 3 h margin on each side', () => {
    const from = Date.parse('2026-06-20T12:00:00Z');
    const to = Date.parse('2026-06-23T12:00:00Z');
    expect(skyEventsWindowCovers(from, to, from + 2 * 3_600_000)).toBe(false);
    expect(skyEventsWindowCovers(from, to, from + 3 * 3_600_000)).toBe(true);
    expect(skyEventsWindowCovers(from, to, to - 3 * 3_600_000)).toBe(true);
    expect(skyEventsWindowCovers(from, to, to - 2 * 3_600_000)).toBe(false);
  });
});
