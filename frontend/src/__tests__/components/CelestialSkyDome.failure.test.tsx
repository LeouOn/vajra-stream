/**
 * W2-F independent layers and honest failure.
 *
 * Review finding 5: a single lazy-chunk rejection used to take the star
 * catalogue, the figures and the computed ecliptic down together, and
 * `data-sky-layers` stayed "pending" forever with no visible note. The fixes:
 *   - stars and figures load independently;
 *   - the ecliptic is built from neither (empty fallbacks), so it survives;
 *   - `data-sky-layers` names the failed layer;
 *   - the failed switch shows a small "unavailable" note.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import type { ConstellationLines, Star } from '../../lib/sky';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  loadStars: vi.fn(),
  loadConstellationLines: vi.fn(),
  buildSkyLayer: vi.fn(),
}));

vi.mock('../../lib/sky', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/sky')>();
  return {
    ...actual,
    loadStars: mocks.loadStars,
    loadConstellationLines: mocks.loadConstellationLines,
  };
});
vi.mock('../../lib/skyLayer', () => ({ buildSkyLayer: mocks.buildSkyLayer }));

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';

const STARS: Star[] = [
  { hr: 2491, ra: 101.287, dec: -16.716, v: -1.46, bv: 0.0 },
  { hr: 2326, ra: 95.988, dec: -52.696, v: -0.72, bv: 0.15 },
];
const LINES: ConstellationLines = {
  crosswalk: 'test',
  tolerance_arcsec: 180,
  constellations: { Ori: [[2491, 2326]] },
};

const payload = {
  timestamp_utc: '2026-10-22T02:00:00Z',
  observer: {
    latitude: 37.7749,
    longitude: -122.4194,
    local_sidereal_time_deg: 298.11,
    local_sidereal_time_hms: '19:52:26',
  },
  moon: {
    altitude: 10,
    azimuth: 80,
    phase_name: 'Waning Crescent',
    illumination: 22.6,
    visible: true,
    sign: 'Cancer',
  },
  planets: [],
  visible_planets_count: 0,
  sacred_stars: [],
  visible_stars_count: 0,
  provenance: { observer: 'computed' },
};

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

async function mountWith(stars: 'ok' | 'fail', figures: 'ok' | 'fail'): Promise<HTMLCanvasElement> {
  if (stars === 'ok') mocks.loadStars.mockResolvedValue(STARS);
  else mocks.loadStars.mockRejectedValue(new Error('stars chunk failed'));
  if (figures === 'ok') mocks.loadConstellationLines.mockResolvedValue(LINES);
  else mocks.loadConstellationLines.mockRejectedValue(new Error('figures chunk failed'));

  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(payload) } as Response),
  );

  await act(async () => {
    root.render(<CelestialSkyDome latitude={37.7749} longitude={-122.4194} />);
  });
  // Let both independent promise chains settle.
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });

  const canvas = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
  if (!(canvas instanceof HTMLCanvasElement)) throw new Error('canvas missing');
  return canvas;
}

function lastLayerRequest(): {
  stars: readonly Star[];
  lines: ConstellationLines;
  showEcliptic: boolean;
  showCatalogue: boolean;
  showFigures: boolean;
} {
  const call = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1];
  if (!call) throw new Error('buildSkyLayer was never called');
  return call[0] as ReturnType<typeof lastLayerRequest>;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(stubCtx());

  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [{ x1: 0, y1: 0, x2: 1, y2: 1 }],
  }));

  vi.spyOn(performance, 'now').mockReturnValue(1000);
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome independent layers', () => {
  it('keeps stars and the ecliptic when the figures chunk rejects', async () => {
    const canvas = await mountWith('ok', 'fail');

    expect(canvas.getAttribute('data-sky-layers')).toBe('figures-unavailable');
    expect(container.querySelector('[data-testid="sky-figures-unavailable"]')?.textContent).toContain(
      'unavailable',
    );
    expect(container.querySelector('[data-testid="sky-catalogue-unavailable"]')).toBeNull();

    const request = lastLayerRequest();
    expect(request.stars).toHaveLength(2);
    expect(request.lines.constellations).toEqual({});
    expect(request.showEcliptic).toBe(true);
    expect(mocks.buildSkyLayer).toHaveBeenCalled();
  });

  it('keeps the ecliptic when the stars chunk rejects', async () => {
    const canvas = await mountWith('fail', 'ok');

    expect(canvas.getAttribute('data-sky-layers')).toBe('stars-unavailable');
    expect(container.querySelector('[data-testid="sky-catalogue-unavailable"]')?.textContent).toContain(
      'unavailable',
    );
    expect(container.querySelector('[data-testid="sky-figures-unavailable"]')).toBeNull();

    const request = lastLayerRequest();
    expect(request.stars).toHaveLength(0);
    expect(request.showEcliptic).toBe(true);
  });

  it('still builds the computed ecliptic when both chunks reject', async () => {
    const canvas = await mountWith('fail', 'fail');

    expect(canvas.getAttribute('data-sky-layers')).toBe('stars+figures-unavailable');
    expect(canvas.getAttribute('data-sky-layers')).not.toBe('pending');
    const request = lastLayerRequest();
    expect(request.stars).toHaveLength(0);
    expect(request.lines.constellations).toEqual({});
    expect(request.showEcliptic).toBe(true);
  });
});
