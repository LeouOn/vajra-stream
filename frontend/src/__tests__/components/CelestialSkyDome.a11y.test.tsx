// @vitest-environment happy-dom
/**
 * W6-D2 — the dome is tappable, keyboard-steppable, named and readable.
 * Covers audit findings F2 (id-based tap/keyboard selection), F3 (truthful
 * composed label), F4 (switch names + single-toggle rows + hit area) and F6
 * (footer contrast class), plus the reviewer's F1/F3/F4 follow-ups.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { decodeSeries, type SkySeries } from '../../lib/skySeries';
import { resetSkySeriesStore } from '../../stores/skySeriesStore';
import { useSkyStore } from '../../stores/skyStore';
import { skyAtInstant } from '../../lib/skyScrub';
import { moonIlluminatedFraction } from '../../lib/moonlight';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import type { LabelItem, PlacedLabel } from '../../lib/skyLabels';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  fetchSeries: vi.fn(),
  buildSkyLayer: vi.fn(),
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
  placeLabels: vi.fn(),
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
vi.mock('../../lib/skyLabels', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/skyLabels')>();
  return { ...actual, placeLabels: mocks.placeLabels };
});

import CelestialSkyDome, { formatDeg } from '../../components/UI/CelestialSkyDome';

const PLANET_IDS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
const SCRUB_MS = Date.parse('2026-10-24T13:00:00.000Z');
const SCRUB = new Date(SCRUB_MS).toISOString();

interface PlanetFixture {
  id: string;
  name: string;
  glyph?: string;
  alt: number;
  az: number;
  visible?: boolean;
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
    color: '#a855f7',
    esoteric_quality: 'quality',
    right_ascension: 0,
    declination: 0,
  };
}

function star(id: string, name: string, alt: number, az: number) {
  return {
    id,
    name,
    altitude: alt,
    azimuth: az,
    magnitude: 1,
    visible: true,
    color: '#a6d8ff',
    nakshatra: 'Ardra',
    quality: 'quality',
  };
}

function payload(
  planets: PlanetFixture[],
  options: {
    sunAlt?: number;
    moonAlt?: number;
    moonAz?: number;
    stars?: ReturnType<typeof star>[];
    observer?: { latitude: number; longitude: number };
  } = {},
) {
  const { sunAlt = -30, moonAlt = 12.44, moonAz = 180, stars = [] } = options;
  const observer = options.observer ?? { latitude: DEFAULT_LAT, longitude: DEFAULT_LNG };
  return {
    timestamp_utc: '2026-10-24T09:00:00Z',
    observer: {
      latitude: observer.latitude,
      longitude: observer.longitude,
      local_sidereal_time_deg: 298.11,
      local_sidereal_time_hms: '19:52:26',
    },
    moon: { phase_name: 'Waxing Crescent', illumination: 22.6 },
    planets: [
      planet({ id: 'sun', name: 'Sun', glyph: '☉', alt: sunAlt, az: 270 }),
      planet({ id: 'moon', name: 'Moon', glyph: '☽', alt: moonAlt, az: moonAz, visible: moonAlt > 0 }),
      ...planets.map(planet),
    ],
    visible_planets_count: planets.length + 2,
    sacred_stars: stars,
    visible_stars_count: stars.length,
    provenance: { observer: 'computed' },
    position_frame: 'topocentric',
  };
}

function seriesFixture(): SkySeries {
  const samples = [-1, 0, 1].map((i) => ({
    at: new Date(SCRUB_MS + i * 603_000).toISOString(),
    gast_deg: 0,
    sun: { id: 'sun', lat: 0, lon: 0 },
    moon: { id: 'moon', lat: 10, lon: 180 },
    planets: PLANET_IDS.map((id) => ({ id, lat: 0, lon: 0 })),
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

const noop = () => {};
function stubCtx(): CanvasRenderingContext2D {
  return {
    globalAlpha: 1,
    fillStyle: '',
    strokeStyle: '',
    font: '',
    textAlign: 'left',
    textBaseline: 'alphabetic',
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
let rafCallbacks: FrameRequestCallback[];
let current: Record<string, unknown>;
let resolvers: ((series: SkySeries) => void)[];

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function mount(): Promise<void> {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(current) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
  await flush();
}

function canvas(): HTMLCanvasElement {
  const element = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
  if (!(element instanceof HTMLCanvasElement)) throw new Error('canvas missing');
  return element;
}

interface PointerOptions {
  pointerId?: number;
  isPrimary?: boolean;
  button?: number;
  pointerType?: string;
}

function pointerAt(
  type: 'pointerdown' | 'pointermove' | 'pointerup' | 'pointercancel',
  x: number,
  y: number,
  options: PointerOptions = {},
): void {
  act(() => {
    canvas().dispatchEvent(
      new PointerEvent(type, {
        bubbles: true,
        cancelable: true,
        pointerId: options.pointerId ?? 1,
        isPrimary: options.isPrimary ?? true,
        button: options.button ?? 0,
        pointerType: options.pointerType ?? 'touch',
        clientX: x,
        clientY: y,
      }),
    );
  });
}

function tap(x: number, y: number, options: PointerOptions = {}): void {
  pointerAt('pointerdown', x, y, options);
  pointerAt('pointerup', x, y, options);
}

function tooltip(): Element | null {
  return container.querySelector('[data-testid="sky-hover-tooltip"]');
}

function liveText(): string {
  return container.querySelector('[data-testid="sky-dome-live"]')?.textContent ?? '';
}

function label(): string {
  return canvas().getAttribute('aria-label') ?? '';
}

function key(name: string): void {
  act(() => {
    canvas().dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true }));
  });
}

async function refresh(): Promise<void> {
  await act(async () => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await flush();
}

/** Project alt/az to the canvas fallback geometry used by the dome. */
function project(alt: number, az: number, size = 500): { x: number; y: number } {
  const radius = size * 0.42;
  const r = ((90 - Math.max(0, alt)) / 90) * radius;
  const rad = (az * Math.PI) / 180;
  return { x: size / 2 - r * Math.sin(rad), y: size / 2 - r * Math.cos(rad) };
}

beforeEach(async () => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  rafCallbacks = [];
  resolvers = [];
  useSkyStore.setState({ at: null });
  useSkyStore.getState().setObserver(DEFAULT_LAT, DEFAULT_LNG);
  resetSkySeriesStore();
  current = payload(
    [
      { id: 'mars', name: 'Mars', alt: 40, az: 100 },
      { id: 'jupiter', name: 'Jupiter', alt: 35, az: 200 },
    ],
    { stars: [star('sirius', 'Sirius (Mrigavyadha)', 30, 50), star('vega', 'Vega', 28, 250)] },
  );

  class FakeImageData {
    readonly data: Uint8ClampedArray;
    constructor(data: Uint8ClampedArray) {
      this.data = data;
    }
  }
  vi.stubGlobal('ImageData', FakeImageData);
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
    rafCallbacks.push(callback);
    return rafCallbacks.length;
  });
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());

  const actualLabels = await vi.importActual<typeof import('../../lib/skyLabels')>('../../lib/skyLabels');
  mocks.placeLabels.mockReset();
  mocks.placeLabels.mockImplementation(actualLabels.placeLabels);
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

describe('F2: tap and keyboard inspection', () => {
  it('a tap on a planet shows the tooltip; a drag does not', async () => {
    await mount();
    const mars = project(40, 100);

    pointerAt('pointerdown', mars.x, mars.y);
    pointerAt('pointerup', mars.x + 20, mars.y);
    expect(tooltip()).toBeNull();

    tap(mars.x, mars.y);
    expect(tooltip()).not.toBeNull();
    expect(tooltip()?.textContent).toContain('Mars');
  });

  it('invalidates a tap that leaves the slop and comes back', async () => {
    await mount();
    const mars = project(40, 100);
    pointerAt('pointerdown', mars.x, mars.y);
    pointerAt('pointermove', mars.x + 60, mars.y);
    pointerAt('pointerup', mars.x, mars.y);
    expect(tooltip()).toBeNull();
  });

  it('ignores an up from a different pointer id and a second contact', async () => {
    await mount();
    const mars = project(40, 100);
    pointerAt('pointerdown', mars.x, mars.y, { pointerId: 11 });
    pointerAt('pointerup', mars.x, mars.y, { pointerId: 12 });
    expect(tooltip()).toBeNull();

    pointerAt('pointerdown', mars.x, mars.y, { pointerId: 21 });
    pointerAt('pointerdown', mars.x, mars.y, { pointerId: 22 });
    pointerAt('pointerup', mars.x, mars.y, { pointerId: 22 });
    pointerAt('pointerup', mars.x, mars.y, { pointerId: 21 });
    expect(tooltip()).toBeNull();
  });

  it('a non-primary second finger invalidates a pending tap (primary released first)', async () => {
    await mount();
    const mars = project(40, 100);
    pointerAt('pointerdown', mars.x, mars.y, { pointerId: 11, isPrimary: true });
    // A real second finger is not primary; it must still invalidate the gesture.
    pointerAt('pointerdown', mars.x + 30, mars.y, { pointerId: 12, isPrimary: false });
    pointerAt('pointerup', mars.x, mars.y, { pointerId: 11, isPrimary: true });
    expect(tooltip()).toBeNull();
    expect(liveText()).toBe('');
    pointerAt('pointerup', mars.x + 30, mars.y, { pointerId: 12, isPrimary: false });
    expect(tooltip()).toBeNull();
  });

  it('a pen tap still opens the tooltip and announces', async () => {
    await mount();
    const mars = project(40, 100);
    tap(mars.x, mars.y, { pointerId: 7, pointerType: 'pen' });
    expect(tooltip()?.textContent).toContain('Mars');
    expect(liveText()).toContain('Mars');
  });

  it('ignores compatibility mouse events right after a touch tap', async () => {
    await mount();
    const mars = project(40, 100);
    tap(mars.x, mars.y);
    expect(tooltip()?.textContent).toContain('Mars');
    expect(liveText()).toContain('Mars');

    // Chromium may dispatch a mousemove elsewhere and a mouseleave after the
    // touch. Both are inside the guard window and must not undo the tap.
    act(() => {
      canvas().dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 5, clientY: 5 }));
    });
    act(() => {
      canvas().dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
    });
    expect(tooltip()?.textContent).toContain('Mars');
    expect(liveText()).toContain('Mars');
  });

  it('cancels a pending tap on pointercancel', async () => {
    await mount();
    const mars = project(40, 100);
    pointerAt('pointerdown', mars.x, mars.y);
    pointerAt('pointercancel', mars.x, mars.y);
    pointerAt('pointerup', mars.x, mars.y);
    expect(tooltip()).toBeNull();
  });

  it('steps by azimuth with arrows and closes on Escape', async () => {
    await mount();
    canvas().focus();
    // Sirius az 50 -> Mars 100 -> Moon 180 -> Jupiter 200 -> Vega 250 -> Sun 270.
    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Sirius');
    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Mars');
    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Moon');
    key('ArrowLeft');
    expect(tooltip()?.textContent).toContain('Mars');
    key('Escape');
    expect(tooltip()).toBeNull();
  });

  it('steps relative to the selected identity after a reorder/shrink', async () => {
    await mount();
    canvas().focus();
    key('ArrowRight');
    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Mars');

    // Drop Sirius so Mars moves from index 2 to index 0. A stale numeric index
    // (2) would now pick Jupiter; identity stepping must pick the next by az.
    current = payload([
      { id: 'mars', name: 'Mars', alt: 40, az: 100 },
      { id: 'jupiter', name: 'Jupiter', alt: 35, az: 200 },
    ]);
    await refresh();
    expect(label()).toContain('2 planets');

    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Moon');
  });

  it('updates the tooltip altitude from a new payload instead of a snapshot', async () => {
    await mount();
    canvas().focus();
    key('ArrowRight');
    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Alt: 40.00');

    current = payload(
      [
        { id: 'mars', name: 'Mars', alt: 15, az: 100 },
        { id: 'jupiter', name: 'Jupiter', alt: 35, az: 200 },
      ],
      { stars: [star('sirius', 'Sirius (Mrigavyadha)', 30, 50), star('vega', 'Vega', 28, 250)] },
    );
    await refresh();
    expect(tooltip()?.textContent).toContain('Mars');
    expect(tooltip()?.textContent).toContain('Alt: 15.00');
  });

  it('clears a selection when its object disappears from the payload', async () => {
    await mount();
    canvas().focus();
    key('ArrowRight');
    key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Mars');

    current = payload([
      { id: 'venus', name: 'Venus', alt: 30, az: 100 },
      { id: 'jupiter', name: 'Jupiter', alt: 35, az: 200 },
    ]);
    await refresh();
    expect(label()).toContain('Venus');
    expect(tooltip()).toBeNull();
    expect(liveText()).not.toContain('Mars');
  });

  it('clears a selected star when daylight hides it', async () => {
    await mount();
    canvas().focus();
    // Sirius 50, Mars 100, Moon 180, Jupiter 200, Vega 250.
    for (let step = 0; step < 5; step += 1) key('ArrowRight');
    expect(tooltip()?.textContent).toContain('Vega');

    current = payload(
      [
        { id: 'mars', name: 'Mars', alt: 40, az: 100 },
        { id: 'jupiter', name: 'Jupiter', alt: 35, az: 200 },
      ],
      { sunAlt: 40, stars: [star('sirius', 'Sirius (Mrigavyadha)', 30, 50), star('vega', 'Vega', 28, 250)] },
    );
    await refresh();
    expect(tooltip()).toBeNull();
  });

  it('follows the current displayed position after a layout change', async () => {
    await mount();
    Object.defineProperty(canvas(), 'clientWidth', { configurable: true, value: 500 });
    Object.defineProperty(canvas(), 'clientHeight', { configurable: true, value: 500 });
    canvas().focus();
    key('ArrowRight');
    key('ArrowRight');
    const beforeStyle = tooltip()?.getAttribute('style');
    expect(beforeStyle).toBeTruthy();

    current = payload(
      [
        { id: 'mars', name: 'Mars', alt: 40, az: 140 },
        { id: 'jupiter', name: 'Jupiter', alt: 35, az: 200 },
      ],
      { stars: [star('sirius', 'Sirius (Mrigavyadha)', 30, 50), star('vega', 'Vega', 28, 250)] },
    );
    await refresh();
    await act(async () => {
      rafCallbacks[rafCallbacks.length - 1](2000);
    });
    await flush();

    const after = tooltip();
    expect(after).not.toBeNull();
    expect(after?.textContent).toContain('Mars');
    expect(after?.getAttribute('style')).not.toBe(beforeStyle);
  });

  it('selects the displaced marker and names exactly that object', async () => {
    current = payload(
      [
        { id: 'saturn', name: 'Saturn', glyph: '♄', alt: 8.74, az: 265.4 },
        { id: 'neptune', name: 'Neptune', glyph: '♆', alt: 1.68, az: 268.29 },
      ],
      { moonAlt: 12.18, moonAz: 270.97 },
    );
    await mount();
    Object.defineProperty(canvas(), 'clientWidth', { configurable: true, value: 309 });
    Object.defineProperty(canvas(), 'clientHeight', { configurable: true, value: 309 });
    await act(async () => {
      rafCallbacks[rafCallbacks.length - 1](1000);
    });

    const items = mocks.placeLabels.mock.calls[mocks.placeLabels.mock.calls.length - 1][0] as LabelItem[];
    const trueSaturn = project(8.74, 265.4, 309);
    const trueNeptune = project(1.68, 268.29, 309);
    const candidates = items
      .filter((item) => item.id === 'saturn' || item.id === 'neptune' || item.id === 'moon')
      .map((item) => ({
        item,
        displaced:
          item.id === 'saturn'
            ? Math.hypot(item.x - trueSaturn.x, item.y - trueSaturn.y)
            : item.id === 'neptune'
              ? Math.hypot(item.x - trueNeptune.x, item.y - trueNeptune.y)
              : Number.NaN,
      }))
      .filter((entry) => Number.isFinite(entry.displaced))
      .sort((a, b) => b.displaced - a.displaced);
    expect(candidates.length).toBeGreaterThan(0);
    const chosen = candidates[0];
    // The chosen marker must actually have been displaced from its true spot;
    // otherwise the test would be vacuous.
    expect(chosen.displaced).toBeGreaterThan(5);

    tap(chosen.item.x, chosen.item.y);
    expect(tooltip()).not.toBeNull();
    expect(tooltip()?.textContent).toContain(chosen.item.id === 'saturn' ? 'Saturn' : 'Neptune');
  });
});

describe('F1/F3: role and truthful composed label', () => {
  it('names the canvas as a custom inspector and gives keyboard instructions', async () => {
    await mount();
    expect(canvas().getAttribute('role')).toBe('application');
    expect(canvas().getAttribute('aria-roledescription')).toBe('sky dome object inspector');
    expect(container.querySelector('[data-testid="sky-dome-description"]')?.textContent).toBe(
      'Use the arrow keys to step through the planets and stars above the horizon, Escape to close.',
    );
    expect(canvas().getAttribute('aria-describedby')).toBe('sky-dome-description');
  });

  it('live night: exact composed aria-label', async () => {
    await mount();
    const expected =
      'Night-sky dome for 37.7749, -122.4194 at 2026-10-24T09:00:00Z: Sun 30.00 degrees below the horizon, Moon Waxing Crescent 23 percent lit 12.44 degrees above the horizon, 2 planets above the horizon: Mars, Jupiter.';
    expect(label()).toBe(expected);
  });

  it('live daylight with the Moon below the horizon', async () => {
    current = payload([{ id: 'venus', name: 'Venus', alt: 30, az: 100 }], {
      sunAlt: 40,
      moonAlt: -10,
    });
    await mount();
    const expected =
      'Night-sky dome for 37.7749, -122.4194 at 2026-10-24T09:00:00Z: Sun 40.00 degrees above the horizon, Moon Waxing Crescent 23 percent lit 10.00 degrees below the horizon, 1 planet above the horizon: Venus.';
    expect(label()).toBe(expected);
  });

  it('says the Sun is at the horizon when its altitude is exactly zero', async () => {
    current = payload([], { sunAlt: 0 });
    await mount();
    expect(label()).toContain('Sun at the horizon');
    expect(label()).not.toContain('Sun 0.00 degrees above');
  });

  it('scrub pending: says the instant is loading and never invents -90 / 0 planets', async () => {
    await mount();
    act(() => {
      useSkyStore.getState().setAt(SCRUB);
    });
    await flush();
    expect(label()).toBe(
      `Night-sky dome for 37.7749, -122.4194 scrubbed to ${SCRUB}: the sky for that instant is loading.`,
    );
    expect(label()).not.toContain('90.00 degrees below');
    expect(label()).not.toContain('0 planets');
    expect(label()).not.toContain('Waxing Crescent');
  });

  it('scrub unavailable: says the instant is unavailable', async () => {
    mocks.fetchSeries.mockImplementation(() => Promise.reject(new Error('offline')));
    await mount();
    act(() => {
      useSkyStore.getState().setAt(SCRUB);
    });
    await flush();
    await flush();
    expect(label()).toBe(
      `Night-sky dome for 37.7749, -122.4194 scrubbed to ${SCRUB}: the sky for that instant is unavailable.`,
    );
  });

  it('scrub ready: illumination comes from the scrub geometry, not the live phase', async () => {
    await mount();
    act(() => {
      useSkyStore.getState().setAt(SCRUB);
    });
    await flush();
    await act(async () => {
      resolvers[resolvers.length - 1](seriesFixture());
      await Promise.resolve();
    });
    await flush();
    await act(async () => {
      rafCallbacks[rafCallbacks.length - 1](1000);
    });

    const sky = skyAtInstant(seriesFixture(), SCRUB_MS, DEFAULT_LAT, DEFAULT_LNG, []);
    const sun = sky.bodies.find((body) => body.id === 'sun');
    const moon = sky.bodies.find((body) => body.id === 'moon');
    if (sun === undefined || moon === undefined) throw new Error('scrub bodies missing');
    const percent = Math.round(
      100 * moonIlluminatedFraction(sun.ra, sun.dec, moon.ra, moon.dec),
    );
    expect(percent).not.toBe(23);
    expect(label()).toContain(`Moon ${percent} percent lit`);
    expect(label()).not.toContain('Waxing Crescent');
    expect(label()).toContain(`Sun ${formatDeg(Math.abs(sky.positions.sun.alt))} degrees`);
  });

  it('previous place: qualifies the stale payload and uses its own coordinates', async () => {
    await mount();
    global.fetch = vi.fn(() => new Promise(() => {}));
    act(() => {
      useSkyStore.getState().setObserver(90, -180);
    });
    await flush();
    expect(label()).toContain('37.7749, -122.4194 (showing the previous place while the new one loads)');
    expect(label()).not.toContain('for 90.0000, -180.0000');
    expect(container.querySelector('[data-testid="sky-updating-place"]')).not.toBeNull();
    act(() => {
      useSkyStore.getState().setObserver(DEFAULT_LAT, DEFAULT_LNG);
    });
  });

  it('a payload without a Moon position still produces a finite sentence', async () => {
    current = payload([], { sunAlt: 0 });
    current.planets = (current.planets as { id: string }[]).filter((item) => item.id !== 'moon');
    await mount();
    expect(label()).toContain('Moon Waxing Crescent 23 percent lit (position unavailable)');
    expect(label()).toContain('0 planets above the horizon: none');
  });
});

describe('F3/F4: switch names, single-toggle rows and hit areas', () => {
  it('names every switch and gives each a >=24px wrapper', async () => {
    await mount();
    const switches = Array.from(container.querySelectorAll('[role="switch"]'));
    expect(switches).toHaveLength(6);
    expect(switches.map((element) => element.getAttribute('aria-label'))).toEqual([
      'Planets',
      'Vedic Stars',
      'Catalogue',
      'Figures',
      'Ecliptic',
      'See through daylight',
    ]);
    const targets = Array.from(container.querySelectorAll('[data-testid^="sky-switch-target-"]'));
    expect(targets).toHaveLength(6);
    for (const target of targets) {
      expect(target.className).toContain('min-h-6');
      expect(target.className).toContain('min-w-6');
    }
  });

  it('a text click toggles exactly once and a switch click toggles exactly once', async () => {
    await mount();
    const row = container.querySelector('[data-testid="sky-switch-planets"]');
    if (!(row instanceof HTMLElement)) throw new Error('planets row missing');
    const toggle = row.querySelector('[role="switch"]');
    expect(toggle?.getAttribute('aria-checked')).toBe('true');

    await act(async () => {
      row.click();
    });
    expect(toggle?.getAttribute('aria-checked')).toBe('false');

    // A second text click is one more toggle, not a no-op.
    await act(async () => {
      row.click();
    });
    expect(toggle?.getAttribute('aria-checked')).toBe('true');

    // Clicking the switch itself is handled by onChange only: one toggle.
    if (!(toggle instanceof HTMLElement)) throw new Error('switch missing');
    await act(async () => {
      toggle.click();
    });
    expect(toggle.getAttribute('aria-checked')).toBe('false');
  });
});

describe('announcements', () => {
  it('speaks for deliberate tap/keyboard selection but not for mouse hover', async () => {
    await mount();
    const mars = project(40, 100);
    act(() => {
      canvas().dispatchEvent(
        new MouseEvent('mousemove', { bubbles: true, clientX: mars.x, clientY: mars.y }),
      );
    });
    expect(tooltip()?.textContent).toContain('Mars');
    expect(liveText()).toBe('');

    tap(mars.x, mars.y);
    expect(liveText()).toContain('Mars');

    key('Escape');
    expect(liveText()).toBe('');
    key('ArrowRight');
    expect(liveText()).toContain('Sirius');
  });
});

describe('F6: footer contrast class', () => {
  it('uses text-slate-400 on the footer', async () => {
    await mount();
    const footer = container.querySelector('[data-testid="sky-layer-footer"]');
    expect(footer?.className).toContain('text-slate-400');
    expect(footer?.className).not.toContain('text-slate-500');
  });
});

void (undefined as unknown as PlacedLabel);
