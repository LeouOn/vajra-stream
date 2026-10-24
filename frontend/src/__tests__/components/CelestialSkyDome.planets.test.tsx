// @vitest-environment happy-dom
/**
 * W5-E — naked-eye planet dimming and the twilight glow wiring.
 *
 * Typical magnitudes (no ephemeris): Neptune/Pluto never naked-eye, Uranus
 * only in a dark sky, Venus at any Sun altitude, Jupiter by day only from
 * Sun +10. A dimmed planet is not hidden: glow off, ring/glyph ~0.35, label
 * ~0.5, card + tooltip say so. See-through shows everything full strength.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  buildSkyLayer: vi.fn(),
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
}));
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

interface PlanetFixture {
  id: string;
  name: string;
  color: string;
  alt: number;
  az: number;
  ra?: number;
  dec?: number;
  visible?: boolean;
  glyph?: string;
}

function planet(fixture: PlanetFixture) {
  return {
    id: fixture.id,
    name: fixture.name,
    glyph: fixture.glyph ?? '♃',
    altitude: fixture.alt,
    azimuth: fixture.az,
    sign: 'Cancer',
    sign_glyph: '♋',
    visible: fixture.visible ?? true,
    color: fixture.color,
    esoteric_quality: 'quality',
    ...(fixture.ra === undefined ? {} : { right_ascension: fixture.ra }),
    ...(fixture.dec === undefined ? {} : { declination: fixture.dec }),
  };
}

function payload(planets: PlanetFixture[], sunAlt = -30) {
  const list = [
    planet({ id: 'sun', name: 'Sun', color: '#f59e0b', alt: sunAlt, az: 270, ra: 0, dec: 0 }),
    ...planets.map(planet),
  ];
  return {
    timestamp_utc: '2026-10-24T09:00:00Z',
    observer: {
      latitude: DEFAULT_LAT,
      longitude: DEFAULT_LNG,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Waxing', illumination: 20 },
    planets: list,
    visible_planets_count: list.length,
    sacred_stars: [],
    visible_stars_count: 0,
    provenance: { observer: 'computed' },
    position_frame: 'topocentric',
  };
}

const noop = () => {};
interface Fill {
  alpha: number;
  style: string;
}
interface Text {
  text: string;
  alpha: number;
  x: number;
  y: number;
}
let fills: Fill[];
let strokeList: Fill[];
let texts: Text[];
let gradientCalls: number;

function stubCtx(): CanvasRenderingContext2D {
  const target = {
    globalAlpha: 1,
    fillStyle: '',
    strokeStyle: '',
    font: '',
    textAlign: 'left',
    textBaseline: 'alphabetic',
    clearRect: noop,
    beginPath: noop,
    arc: noop,
    fill() {
      fills.push({ alpha: target.globalAlpha, style: String(target.fillStyle) });
    },
    stroke() {
      strokeList.push({ alpha: target.globalAlpha, style: String(target.strokeStyle) });
    },
    moveTo: noop,
    lineTo: noop,
    closePath: noop,
    clip: noop,
    fillRect: noop,
    save: noop,
    restore: noop,
    fillText(text: string, x: number, y: number) {
      texts.push({ text, alpha: target.globalAlpha, x, y });
    },
    setLineDash: noop,
    measureText: (text: string) => ({ width: text.length * 5 }) as TextMetrics,
    createRadialGradient: () => {
      gradientCalls += 1;
      return { addColorStop: noop } as unknown as CanvasGradient;
    },
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  };
  return target as unknown as CanvasRenderingContext2D;
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let current: Record<string, unknown>;

async function mount(withSeeThrough = false): Promise<void> {
  try {
    window.localStorage.clear();
    if (withSeeThrough) window.localStorage.setItem('vajra.dome.seeThroughDaylight', '1');
  } catch {
    /* ignore */
  }
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(current) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function fillsWith(style: string): Fill[] {
  return fills.filter((fill) => fill.style === style);
}

function isClose(value: number, expected: number): boolean {
  return Math.abs(value - expected) < 1e-6;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  fills = [];
  strokeList = [];
  texts = [];
  gradientCalls = 0;
  current = payload([
    { id: 'venus', name: 'Venus', color: '#f472b6', alt: 30, az: 100, glyph: '♀' },
    { id: 'neptune', name: 'Neptune', color: '#38bdf8', alt: 25, az: 200, glyph: '♆' },
  ]);
  class FakeImageData {
    readonly data: Uint8ClampedArray;
    constructor(data: Uint8ClampedArray) {
      this.data = data;
    }
  }
  vi.stubGlobal('ImageData', FakeImageData);
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
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
  try {
    window.localStorage.clear();
  } catch {
    /* ignore */
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('planet naked-eye dimming', () => {
  it('dims Neptune but keeps it drawn, labelled and explained; Venus is unchanged', async () => {
    await mount();
    // Glow: Venus has the full 0.2 aura, Neptune has no glow.
    expect(fillsWith('#f472b6').some((fill) => isClose(fill.alpha, 0.2))).toBe(true);
    expect(fillsWith('#38bdf8').some((fill) => isClose(fill.alpha, 0.2))).toBe(false);
    // Ring fill (dark) and glyph at 0.35 for Neptune.
    expect(
      strokeList.some((stroke) => stroke.style === '#38bdf8' && isClose(stroke.alpha, 0.35)),
    ).toBe(true);
    expect(fills.some((fill) => fill.style === '#0f172a' && isClose(fill.alpha, 0.35))).toBe(true);
    expect(texts.some((text) => text.text === '♆' && isClose(text.alpha, 0.35))).toBe(true);
    expect(texts.some((text) => text.text === '♀' && isClose(text.alpha, 1))).toBe(true);
    // Labels keep both planets, with the dimmed alpha.
    expect(texts.some((text) => text.text === 'Neptune ♋' && isClose(text.alpha, 0.5))).toBe(true);
    expect(texts.some((text) => text.text === 'Venus ♋' && isClose(text.alpha, 1))).toBe(true);
    // Card honesty note for Neptune only.
    expect(container.textContent).toContain('Not visible to the naked eye now (magnitude +7.8)');
    const noteCount = () =>
      ((container.textContent ?? '').match(/Not visible to the naked eye now/g) ?? []).length;
    expect(noteCount()).toBe(1); // the card

    const canvas = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
    if (!(canvas instanceof HTMLCanvasElement)) throw new Error('canvas missing');
    // Neptune is at (25, 200): project it with the 500 px fallback.
    const radius = 500 * 0.42;
    const r = ((90 - 25) / 90) * radius;
    const az = (200 * Math.PI) / 180;
    await act(async () => {
      canvas.dispatchEvent(
        new MouseEvent('mousemove', {
          bubbles: true,
          clientX: 250 - r * Math.sin(az),
          clientY: 250 - r * Math.cos(az),
        }),
      );
    });
    // Card + hover tooltip carry the note. W6-D2: mouse hover is deliberately
    // NOT announced in the polite live region (only tap/keyboard selection is).
    expect(noteCount()).toBeGreaterThanOrEqual(2);
    expect(container.querySelector('[data-testid="sky-dome-live"]')?.textContent).toBe('');
  });

  it('see-through daylight restores every planet to full strength', async () => {
    await mount(true);
    expect(fillsWith('#38bdf8').some((fill) => isClose(fill.alpha, 0.2))).toBe(true);
    expect(texts.some((text) => text.text === '♆' && isClose(text.alpha, 1))).toBe(true);
    expect(texts.some((text) => text.text === 'Neptune ♋' && isClose(text.alpha, 1))).toBe(true);
  });

  it('a high full Moon dims Uranus but not Saturn', async () => {
    current = payload(
      [
        { id: 'saturn', name: 'Saturn', color: '#eab308', alt: 35, az: 100 },
        { id: 'uranus', name: 'Uranus', color: '#22d3ee', alt: 40, az: 200 },
        { id: 'moon', name: 'Moon', color: '#e2e8f0', alt: 80, az: 180, ra: 180, dec: 0 },
      ],
      -40,
    );
    // The Sun's RA/Dec are 0/0 in the helper; the Moon at 180/0 is full.
    await mount();
    expect(fillsWith('#22d3ee').some((fill) => isClose(fill.alpha, 0.2))).toBe(false);
    expect(
      strokeList.some((stroke) => stroke.style === '#22d3ee' && isClose(stroke.alpha, 0.35)),
    ).toBe(true);
    expect(fillsWith('#eab308').some((fill) => isClose(fill.alpha, 0.2))).toBe(true);
  });

  it('Venus stays naked-eye by day; Jupiter only from Sun +10', async () => {
    current = payload([{ id: 'venus', name: 'Venus', color: '#f472b6', alt: 30, az: 100 }], 5);
    await mount();
    expect(fillsWith('#f472b6').some((fill) => isClose(fill.alpha, 0.2))).toBe(true);

    act(() => root.unmount());
    root = createRoot(container);
    current = payload([{ id: 'jupiter', name: 'Jupiter', color: '#a855f7', alt: 30, az: 100 }], 5);
    await mount();
    expect(fillsWith('#a855f7').some((fill) => isClose(fill.alpha, 0.2))).toBe(false);

    act(() => root.unmount());
    root = createRoot(container);
    current = payload([{ id: 'jupiter', name: 'Jupiter', color: '#a855f7', alt: 30, az: 100 }], 12);
    await mount();
    expect(fillsWith('#a855f7').some((fill) => isClose(fill.alpha, 0.2))).toBe(true);
  });
});

describe('twilight glow wiring', () => {
  it('draws one extra radial gradient during twilight and none at night', async () => {
    current = payload([], -5);
    await mount();
    expect(gradientCalls).toBe(2); // background + horizon glow
    // The glow is feathered with 20 gradient sub-wedges (plus the background).
    expect(fills.filter((fill) => fill.style === '[object Object]').length).toBeGreaterThanOrEqual(21);

    act(() => root.unmount());
    root = createRoot(container);
    gradientCalls = 0;
    fills = [];
    texts = [];
    current = payload([], -40);
    await mount();
    expect(gradientCalls).toBe(1); // background only: night is unchanged
    expect(fills.filter((fill) => fill.style === '[object Object]').length).toBe(1);

    act(() => root.unmount());
    root = createRoot(container);
    gradientCalls = 0;
    fills = [];
    texts = [];
    current = payload([], 40);
    await mount();
    expect(gradientCalls).toBe(2); // background + the faint midday halo
  });
});
