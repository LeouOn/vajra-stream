// @vitest-environment happy-dom
/**
 * W4-D1d — the dome footer must name the frame truthfully: the live payload's
 * `position_frame` (topocentric by default since W4-T1, geocentric on the
 * no-swisseph fallback) and the scrub `moonFrame` (topocentric when the series
 * carries the Moon distance). Unknown/absent keeps the old geocentric wording.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { decodeSeries, type SkySeries } from '../../lib/skySeries';
import { resetSkySeriesStore } from '../../stores/skySeriesStore';
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  fetchSeries: vi.fn(),
  buildSkyLayer: vi.fn(),
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
}));
vi.mock('../../lib/earthSeriesClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/earthSeriesClient')>();
  return { ...actual, fetchSeries: mocks.fetchSeries, cancelSeriesRequest: vi.fn() };
});
vi.mock('../../lib/skyLayer', () => ({ buildSkyLayer: mocks.buildSkyLayer }));
vi.mock('../../lib/sky', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/sky')>();
  return {
    ...actual,
    loadStars: mocks.loadStars,
    loadConstellationLines: mocks.loadConstellationLines,
  };
});

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';

const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
const SCRUB_MS = Date.parse('2026-10-24T13:00:00.000Z');
const SCRUB = new Date(SCRUB_MS).toISOString();

function body(id: string, i: number) {
  return { id, lat: 10 + i * 0.1, lon: -40 - i * 0.6 };
}

function seriesWithMoonDistance(topocentric: boolean): SkySeries {
  const samples = [-1, 0, 1].map((i) => ({
    at: new Date(SCRUB_MS + i * 603_000).toISOString(),
    gast_deg: (30 + i * 2.5 + 360) % 360,
    sun: body('sun', i),
    moon: body('moon', i),
    planets: PLANET_IDS.map((id) => body(id, i)),
    ...(topocentric ? { moon_distance_au: 0.0025 } : {}),
  }));
  return decodeSeries({
    ephemeris: 'swisseph 2.10.03',
    sidereal_time: 'apparent',
    start: samples[0].at,
    end: samples[2].at,
    step_seconds: 603,
    count: 3,
    samples,
    provenance: {},
  });
}

function payload(positionFrame?: string) {
  return {
    timestamp_utc: '2026-10-24T09:00:00Z',
    observer: {
      latitude: DEFAULT_LAT,
      longitude: DEFAULT_LNG,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Waxing', illumination: 5 },
    planets: [],
    visible_planets_count: 0,
    sacred_stars: [],
    visible_stars_count: 0,
    provenance: { observer: 'computed' },
    ...(positionFrame === undefined ? {} : { position_frame: positionFrame }),
  };
}

const noop = () => {};
function stubCtx(): CanvasRenderingContext2D {
  return {
    globalAlpha: 1,
    clearRect: noop,
    beginPath: noop,
    arc: noop,
    fill: noop,
    stroke: noop,
    moveTo: noop,
    lineTo: noop,
    fillText: noop,
    setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    createRadialGradient: () => ({ addColorStop: noop }) as unknown as CanvasGradient,
    save: noop,
    restore: noop,
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  } as unknown as CanvasRenderingContext2D;
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let resolvers: ((series: SkySeries) => void)[];
let frame: string | undefined;

function flush(): Promise<void> {
  return act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function mountLive(): Promise<void> {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload(frame)) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
  await flush();
}

async function deliverSeries(series: SkySeries): Promise<void> {
  await act(async () => {
    resolvers[resolvers.length - 1](series);
    await Promise.resolve();
  });
  await flush();
}

function footer(): HTMLElement {
  const element = container.querySelector('[data-testid="sky-frame-footer"]');
  if (!(element instanceof HTMLElement)) throw new Error('frame footer missing');
  return element;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  frame = undefined;
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
  useSkyStore.setState({ at: null });
  resetSkySeriesStore();

  resolvers = [];
  mocks.fetchSeries.mockReset();
  mocks.fetchSeries.mockImplementation(
    () =>
      new Promise<SkySeries>((resolve) => {
        resolvers.push(resolve);
      }),
  );
  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  resetSkySeriesStore();
  useSkyStore.setState({ at: null });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('dome frame footer', () => {
  it('live topocentric payload: topocentric wording', async () => {
    frame = 'topocentric';
    await mountLive();
    expect(footer().textContent).toContain('topocentric: parallax included');
    expect(footer().textContent).toContain('without atmospheric refraction');
  });

  it('live geocentric payload: today\'s wording', async () => {
    frame = 'geocentric';
    await mountLive();
    expect(footer().textContent).toContain('geocentric (no parallax');
    expect(footer().textContent).toContain('up to about 1 degree');
  });

  it('live payload without a frame: unknown keeps today\'s wording', async () => {
    await mountLive();
    expect(footer().textContent).toContain('geocentric (no parallax');
  });

  it('scrubbed topocentric series: the Moon is topocentric, the Sun/planets geocentric', async () => {
    await mountLive();
    act(() => {
      useSkyStore.getState().setAt(SCRUB);
    });
    await flush();
    expect(mocks.fetchSeries).toHaveBeenCalled();
    await deliverSeries(seriesWithMoonDistance(true));

    expect(footer().textContent).toContain('the Moon is topocentric');
    expect(footer().textContent).toContain('the Sun and planets are geocentric');
    expect(footer().textContent).toContain('0.01 degree');
    expect(footer().textContent).toContain('without atmospheric refraction');
  });

  it('scrubbed geocentric series (no Moon distance): today\'s wording', async () => {
    await mountLive();
    act(() => {
      useSkyStore.getState().setAt(SCRUB);
    });
    await flush();
    await deliverSeries(seriesWithMoonDistance(false));

    expect(footer().textContent).toContain('geocentric (no parallax');
  });
});
