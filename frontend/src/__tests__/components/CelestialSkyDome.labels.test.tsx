// @vitest-environment happy-dom
/**
 * W5-A — the dome draws labels at the library's placements.
 *
 * The real `placeLabels` is wrapped in a spy (so the wiring is observable);
 * the crowded payload is the real San Francisco noon case (topocentric
 * alt/az from core/celestial_sky at 2026-10-24T19:39:50Z), with the x-ray
 * toggle on so the six sacred stars are part of the crowd.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import type { PlacedLabel, LabelItem } from '../../lib/skyLabels';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  placeLabels: vi.fn(),
  buildSkyLayer: vi.fn(),
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
}));
vi.mock('../../lib/skyLabels', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/skyLabels')>();
  return { ...actual, placeLabels: mocks.placeLabels };
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

const PLANETS = [
  ['sun', 'Sun', '☉', 40.15, 175.52],
  ['mercury', 'Mercury', '☿', 27.85, 156.74],
  ['venus', 'Venus', '♀', 34.64, 179.85],
  ['mars', 'Mars', '♂', 28.01, 271.41],
  ['jupiter', 'Jupiter', '♃', 32.47, 263.02],
] as const;
const STARS = [
  ['vega', 'Vega', 33.83, 64.21, 0.03],
  ['arcturus', 'Arcturus', 69.88, 156.13, -0.05],
  ['spica', 'Spica', 40.77, 185.32, -0.23],
  ['antares', 'Antares', 14.62, 141.76, 1.83],
  ['polaris', 'Polaris', 37.19, 359.72, 0.6],
  ['regulus', 'Regulus', 36.01, 255.97, -0.11],
] as const;

function planet(id: string, name: string, glyph: string, altitude: number, azimuth: number) {
  return {
    id,
    name,
    glyph,
    altitude,
    azimuth,
    sign: 'Cancer',
    sign_glyph: '♋',
    visible: true,
    color: '#a855f7',
    esoteric_quality: 'quality',
  };
}

function sacred(id: string, name: string, altitude: number, azimuth: number, magnitude: number) {
  return {
    id,
    name,
    altitude,
    azimuth,
    magnitude,
    visible: true,
    color: '#a6d8ff',
    nakshatra: 'Ardra',
    quality: 'quality',
  };
}

function payload(crowded: boolean) {
  return {
    timestamp_utc: '2026-10-24T19:39:50Z',
    observer: {
      latitude: 37.7749,
      longitude: -122.4194,
      local_sidereal_time_deg: 205.76,
      local_sidereal_time_hms: '13:42:57',
    },
    moon: { phase_name: 'Waxing', illumination: 20 },
    planets: crowded ? PLANETS.map(([id, name, glyph, alt, az]) => planet(id, name, glyph, alt, az)) : [planet('sun', 'Sun', '☉', 40.15, 175.52)],
    visible_planets_count: crowded ? 5 : 1,
    sacred_stars: crowded ? STARS.map(([id, name, alt, az, mag]) => sacred(id, name, alt, az, mag)) : [],
    visible_stars_count: crowded ? 6 : 0,
    provenance: { observer: 'computed' },
    position_frame: 'topocentric',
  };
}

const noop = () => {};
interface TextCall {
  text: string;
  x: number;
  y: number;
  align: string;
}
let texts: TextCall[];

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
    fill: noop,
    stroke: noop,
    moveTo: noop,
    lineTo: noop,
    fillText(text: string, x: number, y: number) {
      texts.push({ text, x, y, align: target.textAlign });
    },
    setLineDash: noop,
    measureText: (text: string) => ({ width: text.length * 5 }) as TextMetrics,
    createRadialGradient: () => ({ addColorStop: noop }) as unknown as CanvasGradient,
    save: noop,
    restore: noop,
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  };
  return target as unknown as CanvasRenderingContext2D;
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let rafCallbacks: FrameRequestCallback[];
let crowded = true;

async function mount(): Promise<void> {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload(crowded)) } as Response),
  );
  await act(async () => {
    root.render(<CelestialSkyDome />);
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function projection(alt: number, az: number): { x: number; y: number } {
  const size = 500; // happy-dom has no layout, so the dome falls back to 500
  const radius = size * 0.42;
  const r = ((90 - Math.max(0, alt)) / 90) * radius;
  const rad = (az * Math.PI) / 180;
  return { x: size / 2 - r * Math.sin(rad), y: size / 2 - r * Math.cos(rad) };
}

function lastPlacement(): { items: LabelItem[]; placed: PlacedLabel[] } {
  const call = mocks.placeLabels.mock.calls[mocks.placeLabels.mock.calls.length - 1];
  const result = mocks.placeLabels.mock.results[mocks.placeLabels.mock.results.length - 1];
  if (!call) throw new Error('placeLabels was not called');
  return { items: call[0] as LabelItem[], placed: result.value as PlacedLabel[] };
}

beforeEach(async () => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  texts = [];
  crowded = true;
  rafCallbacks = [];
  try {
    window.localStorage.clear();
    window.localStorage.setItem('vajra.dome.seeThroughDaylight', '1');
  } catch {
    /* ignore */
  }
  const actualLabels = await vi.importActual<typeof import('../../lib/skyLabels')>('../../lib/skyLabels');
  mocks.placeLabels.mockReset();
  mocks.placeLabels.mockImplementation(actualLabels.placeLabels);
  mocks.buildSkyLayer.mockReset();
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));
  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));

  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
    rafCallbacks.push(callback);
    return rafCallbacks.length;
  });
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
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

describe('dome label wiring', () => {
  it('draws every visible planet label at the library placement in a crowded sky', async () => {
    await mount();
    expect(mocks.placeLabels).toHaveBeenCalled();
    const { items, placed } = lastPlacement();
    expect(items.length).toBeGreaterThanOrEqual(11);

    // Every planet keeps a label (never hidden).
    for (const [id, name] of PLANETS) {
      const label = placed.find((entry) => entry.id === id);
      expect(label?.hidden, id).toBe(false);
      const call = texts.find(
        (entry) =>
          entry.text === `${name} ♋` &&
          entry.align === label?.anchor &&
          entry.x === label?.x &&
          entry.y === label?.y,
      );
      expect(call, `${id} at (${label?.x},${label?.y})`).toBeDefined();
    }

    // The placement is not the old fixed offset: at least one label sits away
    // from marker+10/marker-4 (crowding moved it).
    const sunLabel = placed.find((entry) => entry.id === 'sun');
    const sunMarker = projection(40.15, 175.52);
    expect(sunLabel).toBeDefined();
    expect(sunLabel?.hidden).toBe(false);
    expect([sunMarker.x + 10, sunMarker.y - 4]).not.toEqual([sunLabel?.x, sunLabel?.y]);
  });

  it('keeps the placement stable across frames when nothing moved', async () => {
    await mount();
    const calls = mocks.placeLabels.mock.calls.length;
    expect(calls).toBeGreaterThan(0);
    const callback = rafCallbacks[rafCallbacks.length - 1];
    act(() => {
      callback(1000);
    });
    expect(mocks.placeLabels.mock.calls.length).toBe(calls);
  });

  it('an uncrowded sky keeps the first (right-up) candidate', async () => {
    crowded = false;
    await mount();
    const { placed } = lastPlacement();
    const sun = placed.find((entry) => entry.id === 'sun');
    const marker = projection(40.15, 175.52);
    expect(sun?.hidden).toBe(false);
    expect(sun?.anchor).toBe('left');
    // First candidate: markerRadius (8 for a planet core) + gap 3, baseline 3 above.
    expect(sun?.x).toBeCloseTo(marker.x + 8 + 3, 6);
    expect(sun?.y).toBeCloseTo(marker.y - 3, 6);
    expect(sun?.leader).toBeNull();
    expect(texts.some((entry) => entry.text === 'Sun ♋' && entry.x === sun?.x && entry.y === sun?.y)).toBe(true);
  });
});
