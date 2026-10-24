// @vitest-environment happy-dom
/**
 * W3-M1 — the dome prints alt/az to exactly two decimals in BOTH modes
 * (drawing keeps the raw values), and the side panel carries the layout rules
 * d1's browser assertions can check (min-width:0, wrapping grid, overflow).
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { decodeSeries, type SkySeries } from '../../lib/skySeries';
import { skyAtInstant } from '../../lib/skyScrub';
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { parseInstant } from '../../lib/skyClock';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];

function seriesAround(shownMs: number): SkySeries {
  const body = (id: string, i: number) => ({ id, lat: 10.123456 + i * 0.1, lon: -40.654321 - i * 0.6 });
  const samples = [-1, 0, 1].map((i) => ({
    at: new Date(shownMs + i * 603_000).toISOString(),
    gast_deg: (30.123456 + i * 2.5 + 360) % 360,
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

const SCRUB_MS = Date.parse('2026-10-24T13:00:00.000Z');
const SCRUB = new Date(SCRUB_MS).toISOString();
const SERIES = seriesAround(SCRUB_MS);

function planet(id: string, name: string, altitude: number, azimuth: number) {
  return {
    id,
    name,
    glyph: '♃',
    altitude,
    azimuth,
    sign: 'Cancer',
    sign_glyph: '♋',
    visible: true,
    color: '#a855f7',
    esoteric_quality: 'quality',
  };
}

function star(id: string, name: string) {
  return {
    id,
    name,
    altitude: 20,
    azimuth: 90,
    magnitude: 1,
    visible: true,
    color: '#a6d8ff',
    nakshatra: 'Ardra',
    quality: 'quality',
    ra_j2000: 267,
    dec_j2000: 38,
  };
}

function payload(liveAlt = 56.06, liveAz = 117.35) {
  return {
    timestamp_utc: '2026-10-24T09:00:00Z',
    observer: {
      latitude: DEFAULT_LAT,
      longitude: DEFAULT_LNG,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Waning Crescent', illumination: 22.6 },
    planets: [planet('sun', 'Sun', liveAlt, liveAz), planet('jupiter', 'Jupiter', liveAlt + 1, liveAz + 1)],
    visible_planets_count: 2,
    sacred_stars: [star('sirius', 'Sirius'), star('vega', 'Vega')],
    visible_stars_count: 2,
    provenance: { observer: 'computed' },
  };
}

const mockSeriesView = {
  status: 'ready' as const,
  series: SERIES,
  error: null,
  errorKind: null,
  fetchedAtMs: Date.now(),
};
vi.mock('../../stores/skySeriesStore', async () => {
  const actual = await vi.importActual<typeof import('../../stores/skySeriesStore')>(
    '../../stores/skySeriesStore',
  );
  return { ...actual, useSkySeries: () => mockSeriesView };
});
vi.mock('../../lib/skyLayer', () => ({
  buildSkyLayer: (request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }),
}));

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';

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

const TWO_DP = /^-?\d+\.\d{2}$/;

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

async function mount(): Promise<void> {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload()) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
  useSkyStore.setState({ at: null });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  useSkyStore.setState({ at: null });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome number formatting', () => {
  it('prints scrub-mode alt/az and sacred badges to exactly two decimals', async () => {
    useSkyStore.setState({ at: SCRUB });
    await mount();

    const cards = Array.from(container.querySelectorAll('[data-testid="sky-planet-card"]'));
    expect(cards.length).toBeGreaterThan(0);
    for (const card of cards) {
      const alt = /Alt (-?\d+\.\d+)°/.exec(card.textContent ?? '');
      const az = /Az (-?\d+\.\d+)°/.exec(card.textContent ?? '');
      expect(alt, card.textContent ?? '').not.toBeNull();
      expect(az, card.textContent ?? '').not.toBeNull();
      expect(alt?.[1]).toMatch(TWO_DP);
      expect(az?.[1]).toMatch(TWO_DP);
    }

    const badges = Array.from(container.querySelectorAll('[data-testid="sky-sacred-badge"]'));
    expect(badges.length).toBeGreaterThan(0);
    for (const badge of badges) {
      const value = /\+(-?\d+\.\d+)°/.exec(badge.textContent ?? '');
      expect(value, badge.textContent ?? '').not.toBeNull();
      expect(value?.[1]).toMatch(TWO_DP);
    }

    // The hover tooltip uses the same two-decimal formatting.
    const expected = skyAtInstant(SERIES, SCRUB_MS, DEFAULT_LAT, DEFAULT_LNG, [
      { id: 'sirius', ra_j2000: 267, dec_j2000: 38 },
      { id: 'vega', ra_j2000: 267, dec_j2000: 38 },
    ]);
    const sun = expected.positions.sun;
    expect(sun.alt).toBeGreaterThan(0);
    const size = 500;
    const radius = size * 0.42;
    const r = ((90 - Math.max(0, sun.alt)) / 90) * radius;
    const radAz = (sun.az * Math.PI) / 180;
    const canvas = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
    if (!(canvas instanceof HTMLCanvasElement)) throw new Error('canvas missing');
    await act(async () => {
      canvas.dispatchEvent(
        new MouseEvent('mousemove', {
          bubbles: true,
          clientX: size / 2 - r * Math.sin(radAz),
          clientY: size / 2 - r * Math.cos(radAz),
        }),
      );
    });
    const sub = container.textContent ?? '';
    const hover = /Alt: (-?\d+\.\d+)° · Az: (-?\d+\.\d+)°/.exec(sub);
    expect(hover, sub).not.toBeNull();
    expect(hover?.[1]).toMatch(TWO_DP);
    expect(hover?.[2]).toMatch(TWO_DP);
  });

  it('shows live values unchanged (already two decimals)', async () => {
    await mount();
    const cards = Array.from(container.querySelectorAll('[data-testid="sky-planet-card"]'));
    expect(cards.length).toBeGreaterThan(0);
    expect(container.textContent).toContain('Alt 56.06°');
    expect(container.textContent).toContain('Az 117.35°');
  });
});

describe('CelestialSkyDome side-panel layout rules', () => {
  it('carries the shrink/wrap/overflow rules d1 asserts in the browser', async () => {
    useSkyStore.setState({ at: SCRUB });
    await mount();

    const panel = container.querySelector('[data-testid="sky-side-panel"]');
    if (!(panel instanceof HTMLElement)) throw new Error('side panel missing');
    expect(panel.className).toContain('min-w-0');
    expect(panel.className).toContain('overflow-hidden');

    const grid = container.querySelector('[data-testid="sky-planet-grid"]');
    if (!(grid instanceof HTMLElement)) throw new Error('planet grid missing');
    expect(grid.className).toMatch(/auto-fill/);
    expect(grid.className).toContain('min-w-0');

    for (const card of Array.from(container.querySelectorAll('[data-testid="sky-planet-card"]'))) {
      expect(card.className).toContain('min-w-0');
      expect(card.className).toContain('overflow-hidden');
    }
    expect(container.querySelector('[data-testid="sky-visible-header"]')).not.toBeNull();
  });
});
