/**
 * W2-F cache correctness and DPR backing store.
 *
 * 1. The offscreen star/figure/ecliptic layer must rebuild when the observer
 *    latitude or the epoch changes, even if the sidereal time has not moved;
 *    and it must not rebuild for a sub-0.02° sidereal step (spec contract).
 *    The failure this pins: lat +45 then -45 at identical LST reused the old
 *    layer until ~4.8 s had passed (review finding 1).
 * 2. Fractional DPR: backing size is compared as a rounded integer, so a
 *    401 CSS-px canvas at DPR 1.5 is not reallocated on every frame
 *    (review finding 6).
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';

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

interface Night {
  latitude: number;
  longitude: number;
  lst: number;
  timestamp: string;
}

function response(night: Night): Response {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        timestamp_utc: night.timestamp,
        observer: {
          latitude: night.latitude,
          longitude: night.longitude,
          local_sidereal_time_deg: night.lst,
          local_sidereal_time_hms: '00:00:00',
        },
        moon: {
          altitude: 10,
          azimuth: 80,
          phase_name: 'Waxing',
          illumination: 50,
          visible: true,
          sign: 'Cancer',
        },
        planets: [],
        visible_planets_count: 0,
        sacred_stars: [],
        visible_stars_count: 0,
        provenance: { observer: 'computed' },
      }),
  } as Response;
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
let current: Night;
let fetchMock: ReturnType<typeof vi.fn>;
let clock: number;
let rafCallbacks: FrameRequestCallback[];

async function mount(latitude: number, longitude: number): Promise<void> {
  await act(async () => {
    root.render(<CelestialSkyDome latitude={latitude} longitude={longitude} />);
  });
}

async function rerender(latitude: number, longitude: number): Promise<void> {
  await act(async () => {
    root.render(<CelestialSkyDome latitude={latitude} longitude={longitude} />);
  });
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  // happy-dom has no ImageData; the dome only commits the layer cache after a
  // successful `new ImageData(...)` and `putImageData`, so provide the former.
  class FakeImageData {
    readonly data: Uint8ClampedArray;
    readonly width: number;
    readonly height: number;
    constructor(data: Uint8ClampedArray, width: number, height: number) {
      this.data = data;
      this.width = width;
      this.height = height;
    }
  }
  vi.stubGlobal('ImageData', FakeImageData);

  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(stubCtx());

  current = { latitude: 45, longitude: 0, lst: 100, timestamp: '2026-10-22T02:00:00Z' };
  fetchMock = vi.fn(() => Promise.resolve(response(current)));
  vi.stubGlobal('fetch', fetchMock);

  // Never resolve the lazy chunks: this test is about the layer cache key.
  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));

  clock = 1000;
  vi.spyOn(performance, 'now').mockImplementation(() => clock);
  rafCallbacks = [];
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
    rafCallbacks.push(callback);
    return rafCallbacks.length;
  });
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome layer cache key', () => {
  it('rebuilds on latitude and epoch change, not on a sub-0.02 deg sidereal step', async () => {
    await mount(45, 0);
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(1);

    // Same LST and epoch, opposite latitude: must rebuild at once.
    current = { latitude: -45, longitude: 0, lst: 100, timestamp: '2026-10-22T02:00:00Z' };
    await rerender(-45, 0);
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(2);

    // Same latitude and epoch, LST moved by 0.01 deg (< 0.02): reuse.
    current = { latitude: -45, longitude: -100, lst: 100.01, timestamp: '2026-10-22T02:00:00Z' };
    await rerender(-45, -100);
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(2);

    // Same latitude and LST, next day: precession epoch changed, rebuild.
    current = { latitude: -45, longitude: -100, lst: 100.01, timestamp: '2026-10-24T02:00:00Z' };
    await rerender(-45, -101);
    expect(mocks.buildSkyLayer).toHaveBeenCalledTimes(3);

    // And the builder really saw the current observer each time.
    const lastRequest = mocks.buildSkyLayer.mock.calls[mocks.buildSkyLayer.mock.calls.length - 1]?.[0] as { latDeg: number };
    expect(lastRequest.latDeg).toBe(-45);
  });
});

describe('CelestialSkyDome fractional DPR', () => {
  it('allocates the rounded backing store once for size 401 at DPR 1.5', async () => {
    Object.defineProperty(window, 'devicePixelRatio', { configurable: true, value: 1.5 });

    let fetchResolve: ((value: Response) => void) | null = null;
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            fetchResolve = resolve;
          }),
      ),
    );

    await mount(45, 0);
    // The canvas only exists once there is a validated sky (W3-D2a).
    if (!fetchResolve) throw new Error('fetch was not started');
    await act(async () => {
      (fetchResolve as (value: Response) => void)(response(current));
    });

    const canvas = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
    if (!(canvas instanceof HTMLCanvasElement)) throw new Error('canvas missing');
    Object.defineProperty(canvas, 'clientWidth', { configurable: true, value: 401 });
    Object.defineProperty(canvas, 'clientHeight', { configurable: true, value: 401 });

    let backingWidth = 0;
    let backingHeight = 0;
    let widthWrites = 0;
    let heightWrites = 0;
    Object.defineProperty(canvas, 'width', {
      configurable: true,
      get: () => backingWidth,
      set: (value: number) => {
        widthWrites += 1;
        backingWidth = value;
      },
    });
    Object.defineProperty(canvas, 'height', {
      configurable: true,
      get: () => backingHeight,
      set: (value: number) => {
        heightWrites += 1;
        backingHeight = value;
      },
    });

    // First draw at the new CSS size allocates 602 x 602 once...
    const firstFrame = rafCallbacks[rafCallbacks.length - 1];
    act(() => {
      clock = 2000;
      firstFrame(2000);
    });
    expect(widthWrites).toBe(1);
    expect(heightWrites).toBe(1);
    expect(backingWidth).toBe(Math.round(401 * 1.5));

    // ...and a second draw one second later must not reassign the backing store.
    const secondFrame = rafCallbacks[rafCallbacks.length - 1];
    act(() => {
      clock = 4000;
      secondFrame(4000);
    });
    expect(widthWrites).toBe(1);
    expect(heightWrites).toBe(1);
  });
});
