// @vitest-environment happy-dom
/**
 * W3-J tests for components/UI/PlanetaryHourReadout.tsx.
 *
 * The client is mocked with a deterministic fake planetary-hour grid (hours of 55 minutes from a fixed base, so the
 * test knows exactly which hour any instant is in); the real skyStore and skyClock are used. Timers are fake and
 * the system clock is pinned. What is pinned: what a person reads (ruler, day or night hour, time left), that the
 * countdown does not hit the network, that the hour boundary does, the scrub debounce, newest-wins, the honest
 * polar / unavailable / refused-estimate states, and a clean unmount.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

vi.mock('../../lib/planetaryHourClient', async () => {
  const actual = await vi.importActual<typeof import('../../lib/planetaryHourClient')>('../../lib/planetaryHourClient');
  return { ...actual, fetchPlanetaryHour: vi.fn(), cancelPlanetaryHourRequest: vi.fn() };
});

import PlanetaryHourReadout from '../../components/UI/PlanetaryHourReadout';
import {
  PlanetaryHourError,
  cancelPlanetaryHourRequest,
  fetchPlanetaryHour,
  type PlanetaryHour,
  type PlanetaryRuler,
} from '../../lib/planetaryHourClient';
import { useSkyStore } from '../../stores/skyStore';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const clientMock = vi.mocked(fetchPlanetaryHour);
const cancelMock = vi.mocked(cancelPlanetaryHourRequest);

const NOW = '2026-10-24T09:00:00.000Z';
const NOW_MS = Date.parse(NOW);
const BASE_MS = Date.parse('2026-10-24T08:00:00.000Z'); // an hour starts here
const HOUR_MS = 55 * 60_000;
const CHALDEAN: PlanetaryRuler[] = ['Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus', 'Mercury', 'Moon'];

/** The fake backend: which fake hour an instant is in. Index 1.. counts from BASE; the 13th hour onward is "night". */
function fakeHour(atMs: number, polar = false): PlanetaryHour {
  const base = {
    at: new Date(atMs).toISOString(),
    atMs,
    latitude: 0,
    longitude: 0,
    provenance: { at: 'computed', solar_day: 'computed', hour: 'computed' },
  };
  if (polar) {
    return { ...base, solarDay: null, hour: null, reason: 'No sunrise-to-sunrise day brackets this instant at this place (polar day or night), so there is no planetary hour.' };
  }
  const n = Math.floor((atMs - BASE_MS) / HOUR_MS);
  const startsAtMs = BASE_MS + n * HOUR_MS;
  const endsAtMs = startsAtMs + HOUR_MS;
  const inDay = ((n % 24) + 24) % 24;
  return {
    ...base,
    solarDay: {
      sunrise: new Date(BASE_MS).toISOString(),
      sunset: new Date(BASE_MS + 12 * HOUR_MS).toISOString(),
      nextSunrise: new Date(BASE_MS + 24 * HOUR_MS).toISOString(),
      dayRuler: 'Venus',
    },
    hour: {
      ruler: CHALDEAN[(((n % 7) + 7) % 7 + 4) % 7],
      isDaytime: inDay < 12,
      index: (inDay % 12) + 1,
      startsAt: new Date(startsAtMs).toISOString(),
      endsAt: new Date(endsAtMs).toISOString(),
      startsAtMs,
      endsAtMs,
      lengthSeconds: HOUR_MS / 1000,
      timeRemainingSeconds: (endsAtMs - atMs) / 1000,
    },
    reason: null,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

let container: HTMLDivElement;
let root: Root | null = null;

function mount(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root!.render(<PlanetaryHourReadout />);
  });
}
const flush = () =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
const advance = (ms: number) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
const scrubTo = (iso: string) =>
  act(() => {
    useSkyStore.getState().setAt(iso);
  });
const text = (testId: string) => container.querySelector(`[data-testid="${testId}"]`)?.textContent ?? null;
const state = () => container.querySelector('[data-testid="planetary-hour-readout"]')?.getAttribute('data-state');
const requestedInstants = () => clientMock.mock.calls.map((call) => Date.parse(call[2]));

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(NOW));
  clientMock.mockReset();
  cancelMock.mockReset();
  clientMock.mockImplementation(async (_lat, _lng, atIso) => fakeHour(Date.parse(atIso)));
  useSkyStore.setState({ lat: 37.7749, lng: -122.4194, label: undefined, at: null });
});

afterEach(() => {
  if (root !== null) act(() => root!.unmount());
  root = null;
  container?.remove();
  vi.useRealTimers();
  document.body.innerHTML = '';
});

describe('PlanetaryHourReadout: live', () => {
  it('shows loading, then the ruler, day or night hour and the time left, labelled computed', async () => {
    mount();
    expect(state()).toBe('loading');
    await flush();
    expect(state()).toBe('ready');
    // NOW is 60 min after BASE: fake hour n = 1 (the 2nd), which starts 08:55 and ends 09:50
    expect(text('planetary-hour-ruler')).toBe(fakeHour(NOW_MS).hour!.ruler);
    expect(text('planetary-hour-kind')).toMatch(/day hour 2 of 12/i);
    expect(text('planetary-hour-left')).toBe('50 min 00 s');
    expect(container.querySelector('[data-provenance="computed"]')).not.toBeNull();
    expect(text('planetary-hour-day-ruler')).toMatch(/Venus/);
    expect(clientMock).toHaveBeenCalledTimes(1);
    expect(clientMock.mock.calls[0][0]).toBe(37.7749);
    expect(clientMock.mock.calls[0][1]).toBe(-122.4194);
    expect(requestedInstants()[0]).toBe(NOW_MS);
  });

  it('counts down every second without any request', async () => {
    mount();
    await flush();
    await advance(1000);
    expect(text('planetary-hour-left')).toBe('49 min 59 s');
    await advance(59_000);
    expect(text('planetary-hour-left')).toBe('49 min 00 s');
    await advance(10 * 60_000);
    expect(text('planetary-hour-left')).toBe('39 min 00 s');
    expect(clientMock).toHaveBeenCalledTimes(1);
  });

  it('asks again exactly when the hour ends, and shows the next hour', async () => {
    mount();
    await flush();
    await advance(50 * 60_000 - 1);
    expect(clientMock).toHaveBeenCalledTimes(1);
    expect(text('planetary-hour-left')).toBe('1 s');
    await advance(1);
    await flush();
    expect(clientMock).toHaveBeenCalledTimes(2);
    expect(requestedInstants()[1]).toBeGreaterThanOrEqual(NOW_MS + 50 * 60_000);
    expect(text('planetary-hour-ruler')).toBe(fakeHour(NOW_MS + HOUR_MS).hour!.ruler); // the next fake hour
    expect(fakeHour(NOW_MS + HOUR_MS).hour!.ruler).not.toBe(fakeHour(NOW_MS).hour!.ruler);
    expect(text('planetary-hour-kind')).toMatch(/day hour 3 of 12/i);
    expect(text('planetary-hour-left')).toMatch(/^5[45] min/);
  });

  it('keeps the last good hour dimmed with an updating cue while the next hour is on its way (never a negative time left)', async () => {
    const pending = deferred<PlanetaryHour>();
    mount();
    await flush();
    const firstRuler = text('planetary-hour-ruler');
    clientMock.mockReturnValueOnce(pending.promise);
    await advance(50 * 60_000 + 5000);
    expect(state()).toBe('updating'); // not a stale "-5 s" hour, not a blank loading card
    expect(container.querySelector('[data-testid="planetary-hour-left"]')).toBeNull();
    expect(text('planetary-hour-ruler')).toBe(firstRuler); // the last good answer stays
    expect(text('planetary-hour-kind')).toMatch(/hour \d+ of 12/i);
    expect(container.querySelector('[data-testid="planetary-hour-updating"]')?.textContent).toMatch(/updating/i);
    pending.resolve(fakeHour(Date.now()));
    await flush();
    expect(state()).toBe('ready');
  });

  it('a new place asks again at once and does not keep showing the old place’s hour', async () => {
    mount();
    await flush();
    const pending = deferred<PlanetaryHour>();
    clientMock.mockReturnValueOnce(pending.promise);
    act(() => {
      useSkyStore.getState().setObserver(-33.8688, 151.2093, 'Sydney');
    });
    expect(state()).toBe('loading');
    expect(clientMock).toHaveBeenCalledTimes(2);
    expect(clientMock.mock.calls[1][0]).toBe(-33.8688);
    expect(clientMock.mock.calls[1][1]).toBe(151.2093);
    pending.resolve(fakeHour(NOW_MS));
    await flush();
    expect(state()).toBe('ready');
  });
});

describe('PlanetaryHourReadout: scrubbed', () => {
  it('shows the hour of the shown instant, with the time left measured from it, and it does not tick', async () => {
    mount();
    await flush();
    await scrubTo('2026-10-24T03:30:00.000Z'); // fake hour n = -5: 03:25 .. 04:20, so 50 min left
    await advance(250);
    await flush();
    const asked = requestedInstants()[requestedInstants().length - 1];
    expect(asked).toBe(Date.parse('2026-10-24T03:30:00.000Z'));
    const expected = fakeHour(asked).hour!;
    expect(text('planetary-hour-ruler')).toBe(expected.ruler);
    expect(text('planetary-hour-left')).toBe('50 min 00 s');
    const before = text('planetary-hour-left');
    await advance(30_000);
    expect(text('planetary-hour-left')).toBe(before); // a paused instant is static
    expect(container.textContent).toMatch(/2026-10-24 03:30:00 UTC/);
  });

  it('debounces: nothing is requested until the scrub has been still for 250 ms, then only the last instant', async () => {
    mount();
    await flush();
    clientMock.mockClear();
    const instants = ['2026-10-24T01:00:00.000Z', '2026-10-24T02:10:00.000Z', '2026-10-24T03:20:00.000Z', '2026-10-24T04:30:00.000Z'];
    for (const iso of instants) {
      await scrubTo(iso);
      await advance(100); // a drag: each step well inside the debounce
    }
    expect(clientMock).not.toHaveBeenCalled();
    await advance(249 - 100 + 1 - 1); // 249 ms of stillness in total since the last step
    expect(clientMock).not.toHaveBeenCalled();
    await advance(1);
    await flush();
    expect(clientMock).toHaveBeenCalledTimes(1);
    expect(requestedInstants()).toEqual([Date.parse(instants[3])]);
  });

  it('newest wins: an older answer that arrives after a newer instant was shown is ignored', async () => {
    mount();
    await flush();
    const older = deferred<PlanetaryHour>();
    clientMock.mockReset();
    clientMock.mockReturnValueOnce(older.promise);
    await scrubTo('2026-10-24T01:00:00.000Z');
    await advance(250); // first request in flight, unanswered
    expect(clientMock).toHaveBeenCalledTimes(1);
    clientMock.mockImplementation(async (_lat, _lng, atIso) => fakeHour(Date.parse(atIso)));
    await scrubTo('2026-10-24T05:00:00.000Z');
    await advance(250);
    await flush();
    const newest = fakeHour(Date.parse('2026-10-24T05:00:00.000Z')).hour!;
    expect(text('planetary-hour-ruler')).toBe(newest.ruler);
    older.resolve(fakeHour(Date.parse('2026-10-24T01:00:00.000Z'))); // late
    await flush();
    expect(text('planetary-hour-ruler')).toBe(newest.ruler);
    expect(container.textContent).toMatch(/05:00:00 UTC/);
  });

  it('moving inside the held hour makes no request; leaving it keeps the last good hour dimmed and asks again after the debounce', async () => {
    mount();
    await flush();
    await scrubTo('2026-10-24T09:10:00.000Z');
    await advance(250);
    await flush();
    const afterFirst = clientMock.mock.calls.length;
    await scrubTo('2026-10-24T09:20:00.000Z'); // same fake hour (08:55..09:50)
    await advance(1000);
    expect(clientMock.mock.calls.length).toBe(afterFirst);
    expect(state()).toBe('ready');
    await scrubTo('2026-10-24T10:30:00.000Z'); // a later hour
    expect(state()).toBe('updating');
    expect(container.querySelector('[data-testid="planetary-hour-updating"]')).not.toBeNull();
    expect(text('planetary-hour-ruler')).toBe(fakeHour(NOW_MS + 10 * 60_000).hour!.ruler);
    await advance(250);
    await flush();
    expect(clientMock.mock.calls.length).toBe(afterFirst + 1);
    expect(state()).toBe('ready');
  });

  it('going back to live resumes the live clock and countdown', async () => {
    mount();
    await flush();
    await scrubTo('2026-10-24T04:00:00.000Z');
    await advance(250);
    await flush();
    act(() => {
      useSkyStore.getState().goLive();
    });
    await flush();
    await advance(1000);
    expect(text('planetary-hour-left')).toBe('49 min 59 s'); // 1.25 s after NOW, rounded up; the hour ends 09:50
  });
});

describe('PlanetaryHourReadout: honest states', () => {
  it('no sunrise here (polar day or night) says so and shows no hour', async () => {
    clientMock.mockImplementation(async (_lat, _lng, atIso) => fakeHour(Date.parse(atIso), true));
    mount();
    await flush();
    expect(state()).toBe('no-sunrise');
    expect(container.textContent).toMatch(/no planetary hour/i);
    expect(container.textContent).toMatch(/polar day or night/i);
    expect(container.querySelector('[data-testid="planetary-hour-ruler"]')).toBeNull();
    expect(container.querySelector('[data-testid="planetary-hour-left"]')).toBeNull();
    expect(container.textContent).not.toMatch(/Mars|Sun hour|Saturn|Jupiter|Venus|Mercury|Moon/);
  });

  it('unavailable names the reason, retries after 10 s (not every second), and recovers', async () => {
    clientMock.mockRejectedValue(new PlanetaryHourError('unavailable', 'ephemeris unavailable', 503));
    mount();
    await flush();
    expect(state()).toBe('unavailable');
    expect(container.textContent).toMatch(/ephemeris unavailable/);
    expect(container.querySelector('[data-testid="planetary-hour-ruler"]')).toBeNull();
    await advance(9000);
    expect(clientMock).toHaveBeenCalledTimes(1);
    clientMock.mockImplementation(async (_lat, _lng, atIso) => fakeHour(Date.parse(atIso)));
    await advance(1000);
    await flush();
    expect(clientMock).toHaveBeenCalledTimes(2);
    expect(state()).toBe('ready');
  });

  it('a payload the client refused (not computed: an estimate) is unavailable, never an hour', async () => {
    clientMock.mockRejectedValue(
      new PlanetaryHourError(
        'invalid-response',
        'The planetary-hour response was not valid: provenance.hour must be "computed" (an estimate is never shown as an hour).',
      ),
    );
    mount();
    await flush();
    expect(state()).toBe('unavailable');
    expect(container.textContent).toMatch(/computed/);
    expect(container.querySelector('[data-testid="planetary-hour-ruler"]')).toBeNull();
  });

  it('a superseded (stale) answer is not an error', async () => {
    clientMock.mockRejectedValueOnce(new PlanetaryHourError('stale', 'replaced'));
    mount();
    await flush();
    expect(state()).toBe('loading');
    expect(container.textContent).not.toMatch(/unavailable/i);
  });
});

describe('PlanetaryHourReadout: unmount', () => {
  it('cancels the request in flight and leaves no timer behind', async () => {
    clientMock.mockReturnValue(deferred<PlanetaryHour>().promise);
    mount();
    expect(clientMock).toHaveBeenCalledTimes(1);
    act(() => root!.unmount());
    root = null;
    expect(cancelMock).toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('an answer that arrives after unmount changes nothing and does not throw', async () => {
    const pending = deferred<PlanetaryHour>();
    clientMock.mockReturnValue(pending.promise);
    mount();
    act(() => root!.unmount());
    root = null;
    pending.resolve(fakeHour(NOW_MS));
    await flush();
    expect(vi.getTimerCount()).toBe(0);
  });
});
