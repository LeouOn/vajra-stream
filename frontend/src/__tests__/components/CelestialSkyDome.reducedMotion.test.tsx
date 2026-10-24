/**
 * W2-D — the dome must respect `prefers-reduced-motion`.
 *
 * With reduced motion on: the star twinkle is a constant, the per-frame
 * requestAnimationFrame loop does not run, and a 1 Hz redraw keeps the sky
 * following the clock. Off: the existing twinkle/loop behaviour is unchanged.
 *
 * The canvas context here records the globalAlpha in force at every `fill`,
 * so the assertions are about what is *drawn*, not about a helper function.
 * The star/line catalogue loaders are parked (never resolve) so the sacred
 * stars — the only twinkling layer — are exercised without the lazy chunks.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';

vi.mock('../../lib/sky', async () => {
  const actual = await vi.importActual<typeof import('../../lib/sky')>('../../lib/sky');
  return {
    ...actual,
    loadStars: vi.fn(() => new Promise<never>(() => {})),
    loadConstellationLines: vi.fn(() => new Promise<never>(() => {})),
  };
});

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mockNightSkyResponse = {
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
  sacred_stars: [
    {
      id: 'sirius',
      name: 'Sirius (Mrigavyadha)',
      sanskrit: 'मृगव्याध',
      altitude: 35.8,
      azimuth: 122.4,
      magnitude: -1.46,
      visible: true,
      color: '#a6d8ff',
      nakshatra: 'Ardra',
      quality: 'Supreme Cosmic Fire',
      zenith_distance: 54.2,
    },
    {
      id: 'polaris',
      name: 'Polaris (Dhruva)',
      sanskrit: 'ध्रुव',
      altitude: 37.8,
      azimuth: 0.5,
      magnitude: 1.98,
      visible: true,
      color: '#f8fafc',
      nakshatra: 'Uttara Ashadha',
      quality: 'The Fixed Point',
      zenith_distance: 52.2,
    },
  ],
  visible_stars_count: 2,
  provenance: { observer: 'computed' },
};

type ChangeListener = (event: MediaQueryListEvent) => void;

interface MediaQueryStub {
  matches: boolean;
  media: string;
  onchange: null;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  addListener: ReturnType<typeof vi.fn>;
  removeListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
  listeners: Set<ChangeListener>;
  fire: (matches: boolean) => void;
}

function installMatchMedia(initial: boolean): MediaQueryStub {
  const stub: MediaQueryStub = {
    matches: initial,
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    listeners: new Set<ChangeListener>(),
    addEventListener: vi.fn((type: string, listener: ChangeListener) => {
      if (type === 'change') stub.listeners.add(listener);
    }),
    removeEventListener: vi.fn((type: string, listener: ChangeListener) => {
      if (type === 'change') stub.listeners.delete(listener);
    }),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
    fire(matches: boolean) {
      stub.matches = matches;
      for (const listener of Array.from(stub.listeners)) {
        listener({ matches } as MediaQueryListEvent);
      }
    },
  };
  const matchMedia = vi.fn(() => stub);
  Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: matchMedia });
  return stub;
}

const noop = () => {};

function recordingCtx(): { ctx: CanvasRenderingContext2D; alphas: number[] } {
  const alphas: number[] = [];
  const target = {
    globalAlpha: 1,
    clearRect: noop,
    beginPath: noop,
    arc: noop,
    fill() {
      alphas.push(target.globalAlpha);
    },
    stroke: noop,
    moveTo: noop,
    lineTo: noop,
    fillText: noop,
    setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    createRadialGradient: () =>
      ({
        addColorStop: noop,
      }) as unknown as CanvasGradient,
    save: noop,
    restore: noop,
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  };
  return { ctx: target as unknown as CanvasRenderingContext2D, alphas };
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let alphas: number[];
let rafCallbacks: FrameRequestCallback[];
let intervalCalls: { callback: TimerHandler; delay?: number }[];

function framesWithDelay(delay: number): TimerHandler[] {
  return intervalCalls.filter((call) => call.delay === delay).map((call) => call.callback);
}

async function mount(): Promise<HTMLElement> {
  await act(async () => {
    root.render(<CelestialSkyDome latitude={37.7749} longitude={-122.4194} />);
  });
  const canvas = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
  if (!(canvas instanceof HTMLElement)) throw new Error('canvas missing');
  return canvas;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  const recording = recordingCtx();
  alphas = recording.alphas;
  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(recording.ctx);

  rafCallbacks = [];
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
    rafCallbacks.push(callback);
    return rafCallbacks.length;
  });
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});

  intervalCalls = [];
  // Recorded, not scheduled: the tests call the 1 Hz tick by hand instead of
  // waiting a real second.
  vi.spyOn(window, 'setInterval').mockImplementation(((callback: TimerHandler, delay?: number) => {
    intervalCalls.push({ callback, delay });
    return intervalCalls.length;
  }) as typeof window.setInterval);
  vi.spyOn(window, 'clearInterval').mockImplementation(() => {});

  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockNightSkyResponse),
    } as Response),
  );
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
});

describe('CelestialSkyDome prefers-reduced-motion', () => {
  it('with reduce on: no per-frame loop and the drawn twinkle alpha does not vary with time', async () => {
    installMatchMedia(true);
    await mount();

    // Nothing schedules a full-rate animation frame...
    expect(rafCallbacks).toHaveLength(0);
    // ...but the sky still redraws once per second.
    expect(framesWithDelay(1000)).toHaveLength(1);

    const first = alphas.slice();
    expect(first.length).toBeGreaterThan(0);
    // The star core is the only fill drawn at full twinkle strength; with
    // reduced motion it sits at the mean of the old sine, 0.8.
    expect(first.some((alpha) => Math.abs(alpha - 0.8) < 1e-12)).toBe(true);

    alphas.length = 0;
    const tick = framesWithDelay(1000)[0];
    vi.spyOn(performance, 'now').mockReturnValue(5000);
    act(() => {
      if (typeof tick !== 'function') throw new Error('1 Hz tick is not callable');
      tick();
    });

    expect(alphas).toEqual(first);
  });

  it('with reduce off: the loop runs and the drawn twinkle alpha varies with time', async () => {
    installMatchMedia(false);
    await mount();

    expect(framesWithDelay(1000)).toHaveLength(0);
    expect(rafCallbacks.length).toBeGreaterThan(0);

    const first = alphas.slice();
    alphas.length = 0;
    const frame = rafCallbacks[rafCallbacks.length - 1];
    act(() => {
      frame(1000);
    });

    expect(alphas).not.toEqual(first);
  });

  it('removes its media-query listener on unmount', async () => {
    const media = installMatchMedia(true);
    await mount();
    expect(media.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    const added = media.addEventListener.mock.calls[0][1] as ChangeListener;

    act(() => {
      root.unmount();
    });

    expect(media.removeEventListener).toHaveBeenCalledWith('change', added);
    // Re-create a root so afterEach's unmount has something to tear down.
    root = createRoot(container);
  });

  it('flips behaviour when the media query changes, without remounting', async () => {
    const media = installMatchMedia(false);
    const canvas = await mount();
    expect(rafCallbacks.length).toBeGreaterThan(0);
    const framesBefore = rafCallbacks.length;

    await act(async () => {
      media.fire(true);
    });

    expect(container.querySelector('[data-testid="celestial-sky-dome-canvas"]')).toBe(canvas);
    expect(rafCallbacks.length).toBe(framesBefore);
    expect(framesWithDelay(1000)).toHaveLength(1);
  });
});
