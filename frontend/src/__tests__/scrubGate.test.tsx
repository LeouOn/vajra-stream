// @vitest-environment happy-dom
/**
 * W3-K — the always-loaded scrub gate.
 *
 * While the sky is live nothing of the scrub machinery is imported. The first
 * scrub dynamically loads it; until the chunk and then the series answer, the
 * slice is `loading` with a null state (never the live state). A failed chunk
 * load is `unavailable` with a readable reason and retries on the next scrub.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

vi.mock('../lib/earthSeriesClient', async () => {
  const actual = await vi.importActual<typeof import('../lib/earthSeriesClient')>('../lib/earthSeriesClient');
  return { ...actual, fetchSeries: vi.fn(), cancelSeriesRequest: vi.fn() };
});

import { fetchSeries } from '../lib/earthSeriesClient';
import { decodeSeries, type SkySeries } from '../lib/skySeries';
import {
  resetScrubGateForTest,
  useScrubGate,
  type ScrubGateSnapshot,
} from '../stores/scrubGate';
import { resetSkySeriesStore } from '../stores/skySeriesStore';
import { useEarthState, useEarthStateStore, type EarthStateSlice } from '../stores/earthStateStore';
import { useSkyStore } from '../stores/skyStore';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const NOW = '2026-10-24T09:00:00.000Z';
const SCRUB_MS = Date.parse('2026-10-24T13:00:00.000Z');
const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];

function seriesAround(shownMs: number): SkySeries {
  const body = (id: string, i: number) => ({ id, lat: 10 + i * 0.1, lon: -40 - i * 0.6 });
  const samples = [-1, 0, 1].map((i) => ({
    at: new Date(shownMs + i * 603_000).toISOString(),
    gast_deg: (30 + i * 2.5 + 360) % 360,
    sun: body('sun', i),
    moon: body('moon', i),
    planets: PLANET_IDS.map((id) => body(id, i)),
  }));
  return decodeSeries({
    ephemeris: 'swisseph',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[2].at,
    step_seconds: 603,
    count: 3,
    samples,
    provenance: {},
  });
}

const liveFetch = vi.fn();

interface ProbeRecord {
  slice: EarthStateSlice;
  gate: ScrubGateSnapshot;
}

function Probe({ log }: { log: ProbeRecord[] }): null {
  const slice = useEarthState();
  const gate = useScrubGate();
  log.push({ slice, gate });
  return null;
}

let logs: ProbeRecord[];
let container: HTMLDivElement;
let root: Root;
let seriesMock: ReturnType<typeof vi.mocked<typeof fetchSeries>>;

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function latest(): ProbeRecord {
  const last = logs[logs.length - 1];
  if (!last) throw new Error('probe never rendered');
  return last;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  logs = [];
  liveFetch.mockReset();
  liveFetch.mockResolvedValue(
    new Response(
      JSON.stringify({
        at: NOW,
        ephemeris: 'swisseph',
        gast_deg: 60,
        sun: { id: 'sun', name: 'Sun', ra_deg: 0, dec_deg: -11, lat: -11, lon: 146 },
        moon: { id: 'moon', name: 'Moon', ra_deg: 0, dec_deg: -8, lat: -8, lon: -82 },
        planets: [],
        provenance: {},
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ),
  );
  vi.stubGlobal('fetch', liveFetch);
  seriesMock = vi.mocked(fetchSeries);
  seriesMock.mockReset();
  resetSkySeriesStore();
  resetScrubGateForTest();
  useSkyStore.setState({ at: null });
  useEarthStateStore.setState({ status: 'idle', state: null, fetchedAt: null, error: null });

  act(() => {
    root.render(<Probe log={logs} />);
  });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  resetSkySeriesStore();
  resetScrubGateForTest();
  useSkyStore.setState({ at: null });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('scrubGate', () => {
  it('does not load the scrub module while the sky is live', async () => {
    await flush();
    expect(latest().gate.module).toBeNull();
    expect(latest().slice.status).toBe('ok');
    expect(latest().slice.frozen).toBeUndefined();
    expect(seriesMock).not.toHaveBeenCalled();
  });

  it('loads lazily on the first scrub; loading never exposes the live state', async () => {
    await flush();
    expect(latest().slice.state).not.toBeNull(); // live state is there

    seriesMock.mockReturnValue(new Promise<SkySeries>(() => {})); // stays pending
    act(() => {
      useSkyStore.getState().setAt(new Date(SCRUB_MS).toISOString());
    });
    // Give the dynamic import a microtask to resolve; the series stays pending.
    await flush();

    expect(latest().gate.module).not.toBeNull();
    expect(latest().slice.status).toBe('loading');
    expect(latest().slice.state).toBeNull();
    expect(latest().slice.frozen).toBe(true);
  });

  it('builds the frozen slice once the shared series answers', async () => {
    const series = seriesAround(SCRUB_MS);
    seriesMock.mockResolvedValue(series);
    act(() => {
      useSkyStore.getState().setAt(new Date(SCRUB_MS).toISOString());
    });
    await flush();

    expect(latest().slice.status).toBe('ok');
    expect(latest().slice.frozen).toBe(true);
    expect(latest().slice.fetchedAt).toBe(SCRUB_MS);
    expect(latest().slice.state?.sun.lat).toBeCloseTo(10, 6);
  });

  it('reports a failed chunk load as unavailable and retries on the next scrub', async () => {
    resetScrubGateForTest(() => Promise.reject(new Error('chunk unavailable')));
    act(() => {
      useSkyStore.getState().setAt(new Date(SCRUB_MS).toISOString());
    });
    await flush();

    expect(latest().slice.status).toBe('unavailable');
    expect(latest().slice.state).toBeNull();
    expect(latest().slice.error).toContain('could not be loaded');

    // Back to live, then a new scrub with a working loader.
    act(() => {
      useSkyStore.getState().goLive();
    });
    await flush();
    resetScrubGateForTest();
    seriesMock.mockResolvedValue(seriesAround(SCRUB_MS));
    act(() => {
      useSkyStore.getState().setAt(new Date(SCRUB_MS).toISOString());
    });
    await flush();

    expect(latest().slice.status).toBe('ok');
    expect(latest().slice.frozen).toBe(true);
  });
});
