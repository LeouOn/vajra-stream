// @vitest-environment happy-dom
/**
 * W3-I tests for the scrub-aware `useEarthState()` (stores/earthStateStore.ts).
 *
 * At `skyStore.at === null` it is exactly the live poll. While scrubbed it is an EarthState-shaped slice built from
 * the shared series store, `frozen`, and the live poll is paused (resumed on goLive). The series client is mocked
 * (a synthetic window); the real skyStore, skySeriesStore and earthStateStore are used.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

vi.mock('../lib/earthSeriesClient', async () => {
  const actual = await vi.importActual<typeof import('../lib/earthSeriesClient')>('../lib/earthSeriesClient');
  return { ...actual, fetchSeries: vi.fn(), cancelSeriesRequest: vi.fn() };
});

import { shownNowMs } from '../lib/earth';
import { EarthSeriesError, cancelSeriesRequest, fetchSeries } from '../lib/earthSeriesClient';
import { decodeSeries, type SkySeries } from '../lib/skySeries';
import { useEarthState, useEarthStateStore, type EarthStateSlice } from '../stores/earthStateStore';
import { resetSkySeriesStore, scrubbedEarthState } from '../stores/skySeriesStore';
import { useSkyStore } from '../stores/skyStore';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const seriesMock = vi.mocked(fetchSeries);
const cancelMock = vi.mocked(cancelSeriesRequest);
const liveFetch = vi.fn();

const NOW = '2026-10-24T09:00:00.000Z';
const SCRUB = '2026-10-24T13:00:00.000Z';
const SCRUB_MS = Date.parse(SCRUB);
const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
const wrap180 = (value: number) => ((((value + 180) % 360) + 360) % 360) - 180;

function syntheticSeries(startIso: string, endIso: string, stepSeconds: number): SkySeries {
  const start = Date.parse(startIso);
  const count = Math.round((Date.parse(endIso) - start) / (stepSeconds * 1000)) + 1;
  const body = (id: string, i: number) => ({ id, lat: 10 + (i % 5) * 0.1, lon: wrap180(-40 - i * 0.6) });
  const samples = Array.from({ length: count }, (_, i) => ({
    at: new Date(start + i * stepSeconds * 1000).toISOString(),
    gast_deg: (30 + i * 2.5) % 360,
    sun: body('sun', i),
    moon: body('moon', i),
    planets: PLANET_IDS.map((id) => body(id, i)),
  }));
  return decodeSeries({
    ephemeris: 'swisseph',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[count - 1].at,
    step_seconds: stepSeconds,
    count,
    samples,
    provenance: {},
  });
}

function liveBody(id: string, lat: number, lon: number) {
  return { id, name: id, ra_deg: 0, dec_deg: lat, lat, lon };
}
function liveState() {
  return {
    at: NOW,
    ephemeris: 'swisseph',
    gast_deg: 60,
    sun: liveBody('sun', -11, 146),
    moon: liveBody('moon', -8, -82),
    planets: [liveBody('mercury', -20, 166)],
    provenance: { sun: 'computed' },
  };
}
const liveResponse = () =>
  new Response(JSON.stringify(liveState()), { status: 200, headers: { 'Content-Type': 'application/json' } });

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
let root: Root;
const latest: Array<EarthStateSlice | null> = [];

function Probe({ index }: { index: number }): null {
  latest[index] = useEarthState();
  return null;
}

function mount(count = 1): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(
      <>
        {Array.from({ length: count }, (_, index) => (
          <Probe key={index} index={index} />
        ))}
      </>,
    );
  });
}
const slice = (index = 0): EarthStateSlice => latest[index] as EarthStateSlice;
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
const goLive = () =>
  act(() => {
    useSkyStore.getState().goLive();
  });
const liveCalls = () =>
  liveFetch.mock.calls.filter((call) => String(call[0]).includes('/astrology/earth-state')).length;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(NOW));
  latest.length = 0;
  liveFetch.mockReset();
  liveFetch.mockImplementation(() => Promise.resolve(liveResponse()));
  vi.stubGlobal('fetch', liveFetch);
  seriesMock.mockReset();
  cancelMock.mockReset();
  seriesMock.mockImplementation((start, end, step) => Promise.resolve(syntheticSeries(start, end, step)));
  resetSkySeriesStore();
  useSkyStore.setState({ at: null });
  useEarthStateStore.setState({ status: 'idle', state: null, fetchedAt: null, error: null });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  resetSkySeriesStore();
  useSkyStore.setState({ at: null });
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useEarthState: live (unchanged)', () => {
  it('polls the live earth state and is not frozen; no series is requested', async () => {
    mount();
    await flush();
    expect(liveCalls()).toBe(1);
    expect(seriesMock).not.toHaveBeenCalled();
    expect(slice().status).toBe('ok');
    expect(slice().frozen ?? false).toBe(false);
    expect(slice().state?.sun.lat).toBe(-11);
    expect(slice().fetchedAt).toBe(Date.parse(NOW));
    expect(shownNowMs(slice(), Date.parse(NOW) + 60_000)).toBe(Date.parse(NOW) + 60_000); // live: wall clock
  });

  it('keeps polling every 60 s', async () => {
    mount();
    await flush();
    await advance(60_000);
    expect(liveCalls()).toBe(2);
  });
});

describe('useEarthState: scrubbed', () => {
  it('pauses the live poll, requests ONE series, and returns a frozen slice for that instant', async () => {
    mount();
    await flush();
    expect(liveCalls()).toBe(1);

    await scrubTo(SCRUB);
    await flush();
    await advance(180_000);
    expect(liveCalls()).toBe(1); // no pointless live requests while scrubbed
    expect(seriesMock).toHaveBeenCalledTimes(1);

    const s = slice();
    expect(s.status).toBe('ok');
    expect(s.frozen).toBe(true);
    expect(s.fetchedAt).toBe(SCRUB_MS);
    expect(s.state?.at).toBe(SCRUB);
    expect(s.state?.planets).toHaveLength(8);
    const expected = scrubbedEarthState(await seriesMock.mock.results[0].value, SCRUB_MS);
    expect(s.state?.sun.lat).toBe(expected?.sun.lat);
    expect(s.state?.moon.lon).toBe(expected?.moon.lon);
    expect(s.state?.gast_deg).toBe(expected?.gast_deg);
  });

  it('does not drift: the clock of a frozen slice stands still while the wall clock runs', async () => {
    mount();
    await scrubTo(SCRUB);
    await flush();
    const first = slice();
    await advance(60_000);
    const second = slice();
    expect(second.fetchedAt).toBe(first.fetchedAt);
    expect(second.state).toBe(first.state);
    expect(shownNowMs(second, Date.now())).toBe(SCRUB_MS);
    expect(shownNowMs(second, Date.now() + 60_000)).toBe(SCRUB_MS);
  });

  it('is loading, not the live state, while the series is on its way', async () => {
    const pending = deferred<SkySeries>();
    seriesMock.mockReturnValue(pending.promise);
    mount();
    await flush(); // the live state is ok now
    expect(slice().status).toBe('ok');
    await scrubTo(SCRUB);
    expect(slice().status).toBe('loading');
    expect(slice().state).toBeNull();
    expect(slice().frozen).toBe(true);
    pending.resolve(syntheticSeries('2026-10-23T09:00:00.000Z', '2026-10-25T09:04:21.000Z', 603));
    await flush();
    expect(slice().status).toBe('ok');
  });

  it('a failed series is unavailable with the reason, never the stale live state', async () => {
    seriesMock.mockRejectedValue(new EarthSeriesError('unavailable', 'ephemeris unavailable', 503));
    mount();
    await flush();
    expect(slice().state?.sun.lat).toBe(-11); // a perfectly good live state is in the store
    await scrubTo(SCRUB);
    await flush();
    const s = slice();
    expect(s.status).toBe('unavailable');
    expect(s.state).toBeNull();
    expect(s.fetchedAt).toBeNull();
    expect(s.error).toBe('ephemeris unavailable');
    expect(s.frozen).toBe(true);
  });

  it('an instant outside 1800-2200 is unavailable without any request', async () => {
    mount();
    await scrubTo('1799-12-31T23:59:59Z');
    await flush();
    expect(seriesMock).not.toHaveBeenCalled();
    expect(slice().status).toBe('unavailable');
    expect(slice().state).toBeNull();
    expect(slice().error).toMatch(/1800/);
  });

  it('three consumers share ONE request and the same slice', async () => {
    mount(3);
    await flush();
    await scrubTo(SCRUB);
    await flush();
    expect(seriesMock).toHaveBeenCalledTimes(1);
    expect(slice(0).state).toBe(slice(1).state);
    expect(slice(1).state).toBe(slice(2).state);
    expect(slice(2).status).toBe('ok');
  });

  it('unmounting the last consumer aborts the in-flight series', async () => {
    seriesMock.mockReturnValue(deferred<SkySeries>().promise);
    mount();
    await scrubTo(SCRUB);
    expect(cancelMock).not.toHaveBeenCalled();
    act(() => root.unmount());
    expect(cancelMock).toHaveBeenCalledTimes(1);
    root = createRoot(container); // so afterEach can unmount
  });
});

describe('useEarthState: back to live', () => {
  it('resumes the live poll at once on goLive, and polls again after 60 s', async () => {
    mount();
    await flush();
    await scrubTo(SCRUB);
    await flush();
    expect(liveCalls()).toBe(1);

    await goLive();
    await flush();
    expect(liveCalls()).toBe(2);
    expect(slice().frozen ?? false).toBe(false);
    expect(slice().status).toBe('ok');
    expect(slice().state?.sun.lat).toBe(-11);

    await advance(60_000);
    expect(liveCalls()).toBe(3);
  });

  it('recovers from an unavailable series by going live', async () => {
    seriesMock.mockRejectedValue(new EarthSeriesError('network', 'down'));
    mount();
    await scrubTo(SCRUB);
    await flush();
    expect(slice().status).toBe('unavailable');
    await goLive();
    await flush();
    expect(slice().status).toBe('ok');
    expect(slice().error).toBeNull();
  });
});
