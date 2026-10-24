// @vitest-environment happy-dom
/**
 * W4-D1 — the dome tells the truth about the daytime sky.
 *
 * Night rendering is unchanged (night palette byte-for-byte, the star layer
 * still draws the catalogue). In daylight the catalogue layer's stars are
 * disabled and stars are drawn per-star with the daylight alpha; with the
 * "See through daylight" toggle they are faintly visible and the figures/
 * ecliptic fade with a ~2nd-magnitude star.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import type { Star } from '../../lib/sky';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const layerMocks = vi.hoisted(() => ({ buildSkyLayer: vi.fn() }));
const starMocks = vi.hoisted(() => ({
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
  precessJ2000: vi.fn(),
}));

vi.mock('../../lib/skyLayer', () => ({ buildSkyLayer: layerMocks.buildSkyLayer }));
vi.mock('../../lib/sky', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/sky')>();
  starMocks.precessJ2000.mockImplementation(actual.precessJ2000);
  return {
    ...actual,
    loadStars: starMocks.loadStars,
    loadConstellationLines: starMocks.loadConstellationLines,
    precessJ2000: starMocks.precessJ2000,
  };
});

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';

const CATALOGUE: Star[] = [
  { hr: 1, ra: 298, dec: 38, v: -1.46, bv: 0 }, // Sirius-class, near the zenith here
  { hr: 2, ra: 298, dec: 38, v: 0.03, bv: 0.6 },
  { hr: 3, ra: 298, dec: 38, v: 6.4, bv: 1.5 },
];

function payload(sunAlt: number) {
  const planet = (id: string, altitude: number, visible: boolean) => ({
    id,
    name: id === 'sun' ? 'Sun' : 'Jupiter',
    glyph: id === 'sun' ? '☉' : '♃',
    altitude,
    azimuth: 120,
    sign: 'Cancer',
    sign_glyph: '♋',
    visible,
    color: id === 'sun' ? '#f59e0b' : '#a855f7',
    esoteric_quality: 'quality',
  });
  return {
    timestamp_utc: '2026-10-24T09:00:00Z',
    observer: {
      latitude: 37.7749,
      longitude: -122.4194,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Waxing', illumination: 5 },
    planets: [planet('sun', sunAlt, sunAlt > 0), planet('jupiter', 40, true)],
    visible_planets_count: sunAlt > 0 ? 2 : 1,
    sacred_stars: [
      {
        id: 'sirius',
        name: 'Sirius (test)',
        altitude: 30,
        azimuth: 100,
        magnitude: -1.46,
        visible: true,
        color: '#a6d8ff',
        nakshatra: 'Ardra',
        quality: 'quality',
        ra_j2000: 101.287,
        dec_j2000: -16.716,
      },
    ],
    visible_stars_count: 1,
    provenance: { observer: 'computed' },
  };
}

const noop = () => {};
interface FillEvent {
  alpha: number;
  style: string;
}
interface StrokeEvent {
  alpha: number;
  style: string;
}
let fills: FillEvent[];
let strokes: StrokeEvent[];
let gradientStops: string[];
let currentStyle = '';

function stubCtx(): CanvasRenderingContext2D {
  const target = {
    globalAlpha: 1,
    fillStyle: '',
    strokeStyle: '',
    clearRect: noop,
    beginPath: noop,
    arc: noop,
    fill() {
      fills.push({ alpha: target.globalAlpha, style: String(target.fillStyle) });
    },
    stroke() {
      strokes.push({ alpha: target.globalAlpha, style: String(target.strokeStyle) });
    },
    moveTo: noop,
    lineTo: noop,
    fillText: noop,
    setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    createRadialGradient: () => {
      gradientStops = [];
      return {
        addColorStop: (offset: number, color: string) => {
          gradientStops.push(`${offset}:${color}`);
        },
      } as unknown as CanvasGradient;
    },
    save: noop,
    restore: noop,
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  };
  currentStyle = String(target.fillStyle);
  return target as unknown as CanvasRenderingContext2D;
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let sunAlt = 40;
let rafCallbacks: FrameRequestCallback[];

function stepFrame(deltaMs: number): void {
  const callback = rafCallbacks[rafCallbacks.length - 1];
  if (!callback) throw new Error('no animation frame scheduled');
  act(() => {
    callback(deltaMs);
  });
}

async function mount(): Promise<void> {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload(sunAlt)) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
  // Let the catalogue promise chain settle and redraw.
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function canvas(): HTMLCanvasElement {
  const element = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
  if (!(element instanceof HTMLCanvasElement)) throw new Error('canvas missing');
  return element;
}

function lastRequest(): { showCatalogue: boolean; showFigures: boolean; showEcliptic: boolean } {
  const call = layerMocks.buildSkyLayer.mock.calls[layerMocks.buildSkyLayer.mock.calls.length - 1];
  if (!call) throw new Error('buildSkyLayer not called');
  return call[0] as { showCatalogue: boolean; showFigures: boolean; showEcliptic: boolean };
}

function vedicHeading(): string {
  const heading = container.querySelector('[data-testid="sky-vedic-heading"]');
  return heading?.textContent?.trim() ?? '';
}

function toggleButton(): HTMLButtonElement {
  const host = container.querySelector('[data-testid="sky-see-through"]');
  const button = host?.querySelector('button');
  if (!(button instanceof HTMLButtonElement)) throw new Error('see-through toggle missing');
  return button;
}

beforeEach(async () => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  fills = [];
  strokes = [];
  gradientStops = [];
  sunAlt = 40;
  try {
    window.localStorage.clear();
  } catch {
    /* ignore */
  }

  class FakeImageData {
    readonly data: Uint8ClampedArray;
    constructor(data: Uint8ClampedArray) {
      this.data = data;
    }
  }
  vi.stubGlobal('ImageData', FakeImageData);
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  rafCallbacks = [];
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
    rafCallbacks.push(callback);
    return rafCallbacks.length;
  });
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());

  starMocks.loadStars.mockResolvedValue(CATALOGUE);
  starMocks.loadConstellationLines.mockResolvedValue({
    crosswalk: 'test',
    tolerance_arcsec: 180,
    constellations: {},
  });
  layerMocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [{ x1: 0, y1: 0, x2: 1, y2: 1 }],
  }));
  layerMocks.buildSkyLayer.mockClear();
  starMocks.precessJ2000.mockClear();
  // `vi.restoreAllMocks()` in afterEach resets a bare vi.fn's implementation;
  // re-wire the real precession before each test.
  const actualSky = await vi.importActual<typeof import('../../lib/sky')>('../../lib/sky');
  starMocks.precessJ2000.mockImplementation(actualSky.precessJ2000);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  try {
    window.localStorage.clear();
  } catch {
    /* ignore */
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('daytime stars', () => {
  it('at noon with the toggle off: no stars/figures drawn, night layer stays off, caption shown', async () => {
    await mount();

    expect(lastRequest().showCatalogue).toBe(false);
    expect(canvas().dataset.daylight).toBe('hidden');
    expect(canvas().dataset.starMode).toBe('separate');
    expect(canvas().dataset.starsDrawn).toBe('0');
    expect(canvas().dataset.figureAlpha).toBe('0.00');
    // no per-star fill and no figure/ecliptic stroke
    expect(fills.some((event) => event.style.startsWith('rgb('))).toBe(false);
    // The altitude rings are the same accent colour but alpha 1; figures are
    // stroked at figureAlpha (0 at noon with the toggle off).
    expect(
      strokes.some((event) => event.style.includes('148, 163, 184') && event.alpha < 0.99),
    ).toBe(false);
    expect(
      strokes.some((event) => event.style.includes('251, 191, 36') && event.alpha < 0.99),
    ).toBe(false);

    const caption = container.querySelector('[data-testid="sky-daylight-caption"]');
    expect(caption?.textContent).toContain('Stars hidden');
    expect(caption?.textContent).toContain('40.00°');
  });

  it('with the toggle on: stars are drawn faintly and figures fade in', async () => {
    await mount();
    await act(async () => {
      toggleButton().click();
    });

    expect(toggleButton().getAttribute('aria-pressed')).toBe('true');
    expect(canvas().dataset.daylight).toBe('xray');
    expect(Number(canvas().dataset.starsDrawn)).toBeGreaterThan(0);
    expect(canvas().dataset.figureAlpha).not.toBe('0.00');

    const starFills = fills.filter((event) => event.style.startsWith('rgb('));
    expect(starFills.length).toBeGreaterThan(0);
    for (const event of starFills) {
      expect(event.alpha).toBeGreaterThanOrEqual(0.12 - 1e-9);
      expect(event.alpha).toBeLessThanOrEqual(0.35 + 1e-9);
    }
    // the brightest star gets the highest floor
    expect(Math.max(...starFills.map((event) => event.alpha))).toBeGreaterThan(0.3);
    expect(
      strokes.some(
        (event) => event.style.includes('148, 163, 184') && event.alpha > 0 && event.alpha < 1,
      ),
    ).toBe(true);
    expect(container.querySelector('[data-testid="sky-daylight-caption"]')?.textContent).toContain(
      'Daylight x-ray',
    );
  });

  it('in twilight: the caption says fainter stars are hidden, and bright ones are drawn', async () => {
    sunAlt = -10;
    await mount();

    const caption = container.querySelector('[data-testid="sky-daylight-caption"]');
    expect(caption?.textContent).toContain('Twilight: fainter stars are hidden');
    expect(caption?.textContent).toContain('10.00°');
    expect(canvas().dataset.daylight).toBe('hidden');
    expect(canvas().dataset.starMode).toBe('separate');
    // Sirius-class and Vega-class stars are above the horizon; the V6.4 star is not.
    expect(Number(canvas().dataset.starsDrawn)).toBe(2);
    const starFills = fills.filter((event) => event.style.startsWith('rgb('));
    expect(starFills.length).toBe(2);
    expect(starFills.every((event) => event.alpha > 0)).toBe(true);
  });

  it('draws daylight stars only when the cached layer rebuilds (one drawImage per frame)', async () => {
    await mount();
    await act(async () => {
      toggleButton().click();
    });
    expect(Number(canvas().dataset.starsDrawn)).toBeGreaterThan(0);

    const builds = layerMocks.buildSkyLayer.mock.calls.length;
    const projections = starMocks.precessJ2000.mock.calls.length;
    const starFills = fills.filter((event) => event.style.startsWith('rgb(')).length;
    const starsDrawn = canvas().dataset.starsDrawn;
    expect(projections).toBeGreaterThan(0);

    // Two one-second frames: the LST moves < 0.02 deg, so the cache is reused.
    stepFrame(1000);
    stepFrame(2000);

    expect(layerMocks.buildSkyLayer.mock.calls.length).toBe(builds);
    expect(starMocks.precessJ2000.mock.calls.length).toBe(projections);
    expect(fills.filter((event) => event.style.startsWith('rgb(')).length).toBe(starFills);
    expect(canvas().dataset.starsDrawn).toBe(starsDrawn);
  });

  it('rebuilds the cached layer when see-through changes', async () => {
    await mount();
    const before = layerMocks.buildSkyLayer.mock.calls.length;
    await act(async () => {
      toggleButton().click();
    });
    expect(layerMocks.buildSkyLayer.mock.calls.length).toBe(before + 1);
    expect(Number(canvas().dataset.starsDrawn)).toBeGreaterThan(0);
  });

  it('the Vedic heading says stars are hidden by daylight when the Sun is up', async () => {
    await mount();
    expect(vedicHeading()).toBe('Vedic stars above the horizon (hidden by daylight):');
  });

  it('the Vedic heading says fainter ones are hidden by the twilight sky', async () => {
    sunAlt = -10;
    await mount();
    expect(vedicHeading()).toBe(
      'Vedic stars above the horizon (fainter ones hidden by the twilight sky):',
    );
  });

  it('the Vedic heading says drawn faintly in x-ray mode', async () => {
    await mount();
    await act(async () => {
      toggleButton().click();
    });
    expect(vedicHeading()).toBe('Vedic stars above the horizon (drawn faintly):');
  });

  it('at night: today\'s palette and the catalogue layer, no caption, no separate stars', async () => {
    sunAlt = -40;
    await mount();

    expect(lastRequest().showCatalogue).toBe(true);
    expect(canvas().dataset.daylight).toBe('night');
    expect(canvas().dataset.starMode).toBe('layer');
    expect(canvas().dataset.figureAlpha).toBe('1.00');
    // eslint-disable-next-line no-console
    console.log('DBG fills', fills.filter((event) => event.style.startsWith('rgb(')).slice(0, 5), 'all', fills.length);
    expect(fills.some((event) => event.style.startsWith('rgb('))).toBe(false);
    expect(gradientStops).toEqual(['0:#0f172a', '0.7:#090d16', '1:#020617']);
    expect(container.querySelector('[data-testid="sky-daylight-caption"]')).toBeNull();
    expect(vedicHeading()).toBe('Visible Vedic Nakshatras Overhead:');
  });

  it('remembers the toggle, and survives localStorage throwing', async () => {
    await mount();
    await act(async () => {
      toggleButton().click();
    });
    const stored = window.localStorage.getItem('vajra.dome.seeThroughDaylight');
    expect(stored).toBe('1');

    act(() => root.unmount());
    root = createRoot(container);
    await mount();
    expect(toggleButton().getAttribute('aria-pressed')).toBe('true');

    act(() => root.unmount());
    try {
      window.localStorage.clear();
    } catch {
      /* ignore */
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage disabled');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage disabled');
    });
    root = createRoot(container);
    await mount();
    expect(toggleButton().getAttribute('aria-pressed')).toBe('false');
    await act(async () => {
      toggleButton().click();
    });
    expect(toggleButton().getAttribute('aria-pressed')).toBe('true');
  });
});
