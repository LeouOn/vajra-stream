/**
 * W3-D2c — the live path must draw the payload's own place, not the requested
 * one. The pixel harness caught Sydney failing because the star layer used the
 * new observer latitude with the previous payload's sidereal time and planets
 * while a place change was in flight.
 *
 * These tests put a payload for place A under an observer for place B, which is
 * exactly the mismatched window: every payload-derived layer must use the
 * payload's latitude/LST, the cache key must follow the payload's place, and
 * the old sky stays consistent (with an "updating place" note) until the new
 * payload arrives. Scrub mode has no payload and keeps the store/props place.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';

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
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

const SF = { lat: DEFAULT_LAT, lng: DEFAULT_LNG };
const SYDNEY = { lat: -33.8688, lng: 151.2093 };

function payload(place: { lat: number; lng: number }, lst: number, hms: string, timestamp = '2026-10-22T02:00:00Z') {
  return {
    timestamp_utc: timestamp,
    observer: {
      latitude: place.lat,
      longitude: place.lng,
      local_sidereal_time_deg: lst,
      local_sidereal_time_hms: hms,
    },
    moon: { phase_name: 'Waning Crescent', illumination: 22.6 },
    planets: [],
    visible_planets_count: 0,
    sacred_stars: [],
    visible_stars_count: 0,
    provenance: { observer: 'computed' },
  };
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) } as Response;
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

interface Pending {
  init: RequestInit;
  resolve: (value: Response) => void;
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let requests: Pending[];

function flush(): Promise<void> {
  return act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function mount(element: React.ReactElement = <CelestialSkyDome />): Promise<void> {
  await act(async () => {
    root.render(element);
  });
}

async function deliver(index: number, body: unknown): Promise<void> {
  await act(async () => {
    requests[index].resolve(response(body));
  });
  await flush();
}

function lastLayerRequest(): { latDeg: number; lstDeg: number; jd: number } {
  const call = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1];
  if (!call) throw new Error('buildSkyLayer was not called');
  return call[0] as { latDeg: number; lstDeg: number; jd: number };
}

function refresh(): void {
  const button = Array.from(container.querySelectorAll('button')).find((candidate) =>
    candidate.textContent?.includes('Refresh'),
  );
  if (!(button instanceof HTMLButtonElement)) throw new Error('Refresh missing');
  button.click();
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal('setInterval', vi.fn(() => 1));
  vi.stubGlobal('clearInterval', vi.fn());
  vi.spyOn(performance, 'now').mockReturnValue(1000);

  useSkyStore.getState().setObserver(SF.lat, SF.lng);
  useSkyStore.getState().goLive();

  requests = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((resolve) => {
          requests.push({ init: init ?? {}, resolve });
        }),
    ),
  );

  // The layer cache only commits after a successful `new ImageData(...)`.
  class FakeImageData {
    readonly data: Uint8ClampedArray;
    constructor(data: Uint8ClampedArray) {
      this.data = data;
    }
  }
  vi.stubGlobal('ImageData', FakeImageData);

  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));
  mocks.buildSkyLayer.mockClear();
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome live place consistency', () => {
  it('builds the star layer with the payload latitude and LST, not the requested place', async () => {
    await mount(); // requested: San Francisco
    await deliver(0, payload(SYDNEY, 111.1, '07:24:24'));

    const request = lastLayerRequest();
    expect(request.latDeg).toBe(SYDNEY.lat);
    // performance.now is frozen at the fetch time, so no sidereal extrapolation.
    expect(request.lstDeg).toBeCloseTo(111.1, 9);
    expect(container.querySelector('[data-testid="sky-updating-place"]')).not.toBeNull();
  });

  it('rebuilds when the payload place changes, but not for a sub-0.02 deg LST step', async () => {
    await mount();
    await deliver(0, payload(SF, 100, '06:40:00'));
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(1);
    expect(lastLayerRequest().latDeg).toBe(SF.lat);

    act(() => {
      refresh();
    });
    await deliver(1, payload(SYDNEY, 100, '06:40:00'));
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(2);
    expect(lastLayerRequest().latDeg).toBe(SYDNEY.lat);

    act(() => {
      refresh();
    });
    await deliver(2, payload(SYDNEY, 100.01, '06:40:02'));
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(2);
  });

  it('keeps the old payload sky consistent until the new place answer arrives', async () => {
    await mount();
    await deliver(0, payload(SF, 33.3, '02:13:12'));
    expect(lastLayerRequest().latDeg).toBe(SF.lat);
    expect(lastLayerRequest().lstDeg).toBeCloseTo(33.3, 9);

    act(() => {
      useSkyStore.getState().setObserver(SYDNEY.lat, SYDNEY.lng, 'Sydney');
    });
    await flush();
    expect(requests).toHaveLength(2);

    // The pending request must not repaint a half-updated sky.
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(1);
    expect(lastLayerRequest().latDeg).toBe(SF.lat);
    expect(lastLayerRequest().lstDeg).toBeCloseTo(33.3, 9);
    expect(container.querySelector('[data-testid="sky-updating-place"]')).not.toBeNull();

    await deliver(1, payload(SYDNEY, 111.1, '07:24:24'));
    expect(lastLayerRequest().latDeg).toBe(SYDNEY.lat);
    expect(lastLayerRequest().lstDeg).toBeCloseTo(111.1, 9);
    expect(container.querySelector('[data-testid="sky-updating-place"]')).toBeNull();
  });
});
