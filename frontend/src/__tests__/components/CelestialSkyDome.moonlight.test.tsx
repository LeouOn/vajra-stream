// @vitest-environment happy-dom
/**
 * W5-D — moonlight washes out the faint stars, live and scrub alike.
 *
 * The payload carries RA/Dec for the Sun and Moon; the same
 * `moonIlluminatedFraction` feed is used in both modes. With no Moon (or the
 * Moon down) the layer request is exactly the Moon-free one (no per-star
 * override). The layer cache key quantises the effective penalty to 0.05 mag.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { decodeSeries, type SkySeries } from '../../lib/skySeries';
import { skyAtInstant } from '../../lib/skyScrub';
import { resetSkySeriesStore } from '../../stores/skySeriesStore';
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import type { Star } from '../../lib/sky';

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

function planet(
  id: string,
  altitude: number,
  ra: number,
  dec: number,
  visible = true,
): Record<string, unknown> {
  return {
    id,
    name: id[0].toUpperCase() + id.slice(1),
    glyph: '☉',
    altitude,
    azimuth: 120,
    sign: 'Cancer',
    sign_glyph: '♋',
    visible,
    color: '#f59e0b',
    esoteric_quality: 'quality',
    right_ascension: ra,
    declination: dec,
  };
}

interface PayloadOptions {
  moonAlt: number;
  includeMoon?: boolean;
  sunAlt?: number;
  sunRa?: number;
  sunDec?: number;
  moonRa?: number;
  moonDec?: number;
}

function payload(options: PayloadOptions): Record<string, unknown> {
  const {
    moonAlt,
    includeMoon = true,
    sunAlt = -30,
    sunRa = 0,
    sunDec = 0,
    moonRa = 180,
    moonDec = 0,
  } = options;
  const planets = [planet('sun', sunAlt, sunRa, sunDec)];
  if (includeMoon) planets.push(planet('moon', moonAlt, moonRa, moonDec, moonAlt > 0));
  return {
    timestamp_utc: '2026-10-24T09:00:00Z',
    observer: {
      latitude: DEFAULT_LAT,
      longitude: DEFAULT_LNG,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Full', illumination: 100 },
    planets,
    visible_planets_count: planets.filter((p) => p.visible).length,
    sacred_stars: [],
    visible_stars_count: 0,
    provenance: { observer: 'computed' },
    position_frame: 'topocentric',
  };
}

function seriesFixture(): SkySeries {
  const midday = SCRUB_MS;
  const sample = (i: number) => ({
    at: new Date(midday + i * 603_000).toISOString(),
    gast_deg: 0,
    sun: { id: 'sun', lat: 0, lon: 0 },
    moon: { id: 'moon', lat: 0, lon: 180 },
    planets: PLANET_IDS.map((id) => ({ id, lat: 0, lon: 0 })),
  });
  const samples = [-1, 0, 1].map(sample);
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
    measureText: (text: string) => ({ width: text.length * 5 }) as TextMetrics,
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
let current: PayloadOptions;
let resolvers: ((series: SkySeries) => void)[];

function flush(): Promise<void> {
  return act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function mount(): Promise<void> {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload(current)) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
  await flush();
}

function refreshButton(): HTMLButtonElement {
  const button = Array.from(container.querySelectorAll('button')).find((candidate) =>
    candidate.textContent?.includes('Refresh'),
  );
  if (!(button instanceof HTMLButtonElement)) throw new Error('Refresh missing');
  return button;
}

async function refresh(next: PayloadOptions): Promise<void> {
  current = next;
  await act(async () => {
    refreshButton().click();
  });
  await flush();
}

function lastRequest(): Record<string, unknown> {
  const call = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1];
  if (!call) throw new Error('buildSkyLayer not called');
  return call[0] as Record<string, unknown>;
}

function alphaFor(request: Record<string, unknown>, v: number): number {
  const hook = request.starAlphaFor as ((star: Star) => number) | undefined;
  if (!hook) throw new Error('no starAlphaFor in the request');
  return hook({ hr: 1, ra: 0, dec: 45, v, bv: null });
}

function alphaScale(v: number): number {
  return (6.5 - v) / 0.5;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  current = { moonAlt: 80 };
  resolvers = [];
  useSkyStore.setState({ at: null });
  resetSkySeriesStore();
  mocks.fetchSeries.mockReset();
  mocks.fetchSeries.mockImplementation(
    () =>
      new Promise<SkySeries>((resolve) => {
        resolvers.push(resolve);
      }),
  );
  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));
  mocks.buildSkyLayer.mockReset();
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));
  class FakeImageData {
    readonly data: Uint8ClampedArray;
    constructor(data: Uint8ClampedArray) {
      this.data = data;
    }
  }
  vi.stubGlobal('ImageData', FakeImageData);
  vi.spyOn(performance, 'now').mockReturnValue(1000);
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  resetSkySeriesStore();
  useSkyStore.setState({ at: null });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('moonlight', () => {
  it('a high full Moon dims faint stars (mag 6 gone, mag 3 kept) and shows the caption', async () => {
    current = { moonAlt: 80 };
    await mount();
    const request = lastRequest();
    expect(request.starAlphaFor).toBeDefined();
    expect(alphaFor(request, 6)).toBe(0);
    expect(alphaFor(request, 3)).toBeGreaterThan(0);

    const caption = container.querySelector('[data-testid="sky-moonlight-caption"]');
    expect(caption?.textContent).toContain('Moonlight: faint stars dimmed');
    expect(caption?.textContent).toContain('80.0° up');
    expect(caption?.textContent).toContain('100 % lit');
  });

  it('a Moon below the horizon is exactly the Moon-free picture (no override, no caption)', async () => {
    current = { moonAlt: -10 };
    await mount();
    const moonDown = lastRequest();
    expect(moonDown.starAlphaFor).toBeUndefined();
    expect(container.querySelector('[data-testid="sky-moonlight-caption"]')).toBeNull();

    act(() => root.unmount());
    root = createRoot(container);
    current = { moonAlt: 0, includeMoon: false };
    await mount();
    const moonFree = lastRequest();
    expect(moonFree.starAlphaFor).toBeUndefined();
    // Everything the layer is built from is identical.
    expect(moonFree).toEqual(moonDown);
  });

  it('rebuilds the layer when the quantised penalty changes, not for a 0.01 mag change', async () => {
    current = { moonAlt: 30 };
    await mount();
    const builds = mocks.buildSkyLayer.mock.calls.length;

    await refresh({ moonAlt: 30.5 }); // < 0.05 mag difference -> same bucket
    expect(mocks.buildSkyLayer.mock.calls.length).toBe(builds);

    await refresh({ moonAlt: 35 }); // > 0.05 mag difference -> rebuild
    expect(mocks.buildSkyLayer.mock.calls.length).toBeGreaterThan(builds);
  });

  it('live and scrub feeds give the same fraction, caption and alphas for the same instant', async () => {
    const series = seriesFixture();
    const mid = new Date(SCRUB_MS).toISOString();
    const expected = skyAtInstant(series, SCRUB_MS, DEFAULT_LAT, DEFAULT_LNG, []);
    const sun = expected.bodies.find((body) => body.id === 'sun');
    const moon = expected.bodies.find((body) => body.id === 'moon');
    if (!sun || !moon) throw new Error('fixture bodies missing');

    // Live payload with exactly the scrub-derived RA/Dec and Moon altitude.
    current = {
      moonAlt: expected.positions.moon.alt,
      sunAlt: expected.positions.sun.alt,
      sunRa: sun.ra,
      sunDec: sun.dec,
      moonRa: moon.ra,
      moonDec: moon.dec,
    };
    await mount();
    const liveCaption = container.querySelector('[data-testid="sky-moonlight-caption"]')?.textContent;
    const liveAlpha3 = alphaFor(lastRequest(), 3);
    const liveAlpha6 = alphaFor(lastRequest(), 6);

    act(() => root.unmount());
    root = createRoot(container);
    resetSkySeriesStore();
    useSkyStore.setState({ at: mid });
    await mount();
    act(() => {
      useSkyStore.getState().setAt(mid);
    });
    await flush();
    expect(mocks.fetchSeries).toHaveBeenCalled();
    await act(async () => {
      resolvers[resolvers.length - 1](series);
      await Promise.resolve();
    });
    await flush();

    expect(container.querySelector('[data-testid="sky-moonlight-caption"]')?.textContent).toBe(
      liveCaption,
    );
    expect(alphaFor(lastRequest(), 3)).toBeCloseTo(liveAlpha3, 12);
    expect(alphaFor(lastRequest(), 6)).toBeCloseTo(liveAlpha6, 12);
  });
});

void alphaScale;
