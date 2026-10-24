/**
 * W2-F cadence — the dome's redraw rate must match the spec's resource
 * budget: the decorative twinkle at most every 33 ms (~30 fps), a still sky
 * at 1 Hz, nothing while the tab is hidden, one redraw when it returns, and
 * the `/night-sky` poll paused while hidden.
 *
 * rAF is recorded rather than run, so the test drives the clock itself. The
 * 2d context counts `clearRect`, which `render` calls exactly once per draw.
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

const STAR = {
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
};

function payload(starVisible: boolean) {
  return {
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
    sacred_stars: [{ ...STAR, visible: starVisible }],
    visible_stars_count: starVisible ? 1 : 0,
    provenance: { observer: 'computed' },
  };
}

const noop = () => {};

interface Recording {
  draws: number;
  putImageData: number;
}

function recordingCtx(): { ctx: CanvasRenderingContext2D; counts: Recording } {
  const counts: Recording = { draws: 0, putImageData: 0 };
  const target = {
    globalAlpha: 1,
    clearRect() {
      counts.draws += 1;
    },
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
    putImageData() {
      counts.putImageData += 1;
    },
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  };
  return { ctx: target as unknown as CanvasRenderingContext2D, counts };
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let rafCallbacks: FrameRequestCallback[];
let cancelledFrames: number[];
let intervalCalls: { id: number; callback: TimerHandler; delay?: number }[];
let clearedIntervals: number[];
let fetchMock: ReturnType<typeof vi.fn>;
let hidden: boolean;
let clock: number;
let counts: Recording;

function installDocumentHidden(): void {
  hidden = false;
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    get: () => hidden,
  });
}

function setHidden(value: boolean): void {
  hidden = value;
  document.dispatchEvent(new Event('visibilitychange'));
}

async function mount(starVisible = true): Promise<void> {
  fetchMock = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(payload(starVisible)) } as Response),
  );
  vi.stubGlobal('fetch', fetchMock);
  await act(async () => {
    root.render(<CelestialSkyDome latitude={37.7749} longitude={-122.4194} />);
  });
}

/** Drive the recorded rAF callbacks with a 1 ms clock from 1..untilMs. */
function simulateUntil(untilMs: number): void {
  act(() => {
    for (let t = 1; t <= untilMs; t += 1) {
      clock = t;
      const callback = rafCallbacks[rafCallbacks.length - 1];
      if (!callback) throw new Error('no animation frame scheduled');
      callback(t);
    }
  });
}

function pollInterval(): { id: number; callback: TimerHandler; delay?: number } {
  const poll = intervalCalls.find((call) => call.delay === 60000);
  if (!poll) throw new Error('no 60 s poll interval');
  return poll;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  installDocumentHidden();

  const recording = recordingCtx();
  counts = recording.counts;
  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(recording.ctx);

  rafCallbacks = [];
  cancelledFrames = [];
  let rafId = 0;
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
    rafId += 1;
    rafCallbacks.push(callback);
    return rafId;
  });
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id: number) => {
    cancelledFrames.push(id);
  });

  intervalCalls = [];
  clearedIntervals = [];
  let intervalId = 0;
  vi.spyOn(window, 'setInterval').mockImplementation(((callback: TimerHandler, delay?: number) => {
    intervalId += 1;
    intervalCalls.push({ id: intervalId, callback, delay });
    return intervalId;
  }) as typeof window.setInterval);
  vi.stubGlobal(
    'clearInterval',
    vi.fn((id?: number) => {
      if (id !== undefined) clearedIntervals.push(id);
    }),
  );

  clock = 0;
  vi.spyOn(performance, 'now').mockImplementation(() => clock);

  mocks.loadStars.mockImplementation(() => new Promise<never>(() => {}));
  mocks.loadConstellationLines.mockImplementation(() => new Promise<never>(() => {}));
  mocks.buildSkyLayer.mockImplementation((request: { size: number }) => ({
    stars: new Uint8ClampedArray(Math.max(1, Math.round(request.size)) ** 2 * 4),
    figures: [],
    ecliptic: [],
  }));
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome redraw cadence', () => {
  it('caps the twinkle at ~30 fps over 3 simulated seconds', async () => {
    await mount(true); // one visible sacred star: the dome twinkles
    expect(counts.draws).toBe(1); // the initial draw

    simulateUntil(3000);

    // at t = 0, 33, 66, ... 2970
    expect(counts.draws).toBe(1 + Math.floor(3000 / 33));
  });

  it('redraws a still sky at 1 Hz over 3 simulated seconds', async () => {
    await mount(false); // nothing twinkles
    expect(counts.draws).toBe(1);

    simulateUntil(3000);

    // at t = 0, 1000, 2000, 3000
    expect(counts.draws).toBe(4);
  });

  it('draws nothing while hidden and exactly once more when the tab returns', async () => {
    await mount(true);
    expect(counts.draws).toBe(1);
    hidden = true;

    simulateUntil(3000);
    expect(counts.draws).toBe(1);

    act(() => {
      clock = 3000;
      setHidden(false);
    });
    expect(counts.draws).toBe(2);

    // and the normal cadence resumes
    simulateUntil(3033);
    expect(counts.draws).toBe(3);
  });

  it('pauses the 60 s /night-sky poll while hidden and refreshes on return', async () => {
    await mount(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const poll = pollInterval();

    hidden = true;
    upcall(poll);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    act(() => {
      clock = 5000;
      setHidden(false);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);

    act(() => {
      upcall(poll);
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('cancels the animation frame on unmount', async () => {
    await mount(true);
    act(() => {
      root.unmount();
    });
    expect(cancelledFrames.length).toBeGreaterThan(0);
    root = createRoot(container); // let afterEach unmount something
  });

  it('cancels the frame loop when reduced motion turns on, and clears its timer on unmount', async () => {
    const media = installMatchMedia(false);
    await mount(true);
    expect(rafCallbacks.length).toBeGreaterThan(0);

    cancelledFrames.length = 0;
    await act(async () => {
      media.fire(true);
    });
    expect(cancelledFrames.length).toBeGreaterThan(0);
    const still = intervalCalls.find((call) => call.delay === 1000);
    if (!still) throw new Error('1 Hz interval was not scheduled after the flip');

    act(() => {
      root.unmount();
    });
    expect(clearedIntervals).toContain(still.id);
    root = createRoot(container);
  });
});

function upcall(call: { callback: TimerHandler }): void {
  if (typeof call.callback !== 'function') throw new Error('poll interval is not callable');
  call.callback();
}

type ChangeListener = (event: MediaQueryListEvent) => void;

function installMatchMedia(initial: boolean): {
  matches: boolean;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  fire: (matches: boolean) => void;
} {
  const listeners = new Set<ChangeListener>();
  const stub = {
    matches: initial,
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    addEventListener: vi.fn((type: string, listener: ChangeListener) => {
      if (type === 'change') listeners.add(listener);
    }),
    removeEventListener: vi.fn((type: string, listener: ChangeListener) => {
      if (type === 'change') listeners.delete(listener);
    }),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
    fire(matches: boolean) {
      stub.matches = matches;
      for (const listener of Array.from(listeners)) listener({ matches } as MediaQueryListEvent);
    },
  };
  Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: () => stub });
  return stub;
}
