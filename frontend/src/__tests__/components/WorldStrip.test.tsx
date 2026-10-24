/**
 * W3-E — WorldStrip component: mounting contract in a headless DOM.
 *
 * The canvas 2d context is unavailable under happy-dom, so the draw path is
 * inert here (its physics is pinned by equirect.test.ts against a stub
 * context). These tests pin: the 2:1 canvas, the fallback resolution when
 * the container cannot be measured, the unavailable label, the 1 Hz redraw
 * timer lifecycle, NO requestAnimationFrame, and click -> wrap-aware
 * lat/lng through onPick.
 */
import React from 'react';
import { describe, expect, test, vi, beforeEach, afterEach, type MockInstance } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import { WorldStrip } from '../../components/2D/WorldStrip';
import { OBSERVER_MARKER_COLOR } from '../../lib/earth';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// The component subscribes to the shared earth-state store, whose refresh()
// fires a real request and commits outside act (and, with a root left mounted
// through teardown, the same late-commit race that W3-A2 fixed in MiniEarth).
// This file tests the strip; the store has its own tests, so pin it to a ready
// slice here. The `sun` prop still overrides it where a test needs a literal.
const EARTH_SLICE = vi.hoisted(() => ({
  current: {
    status: 'ok' as const,
    state: {
      at: '2026-10-22T02:00:00Z',
      ephemeris: 'de432s',
      gast_deg: 60.525,
      sun: { id: 'sun', name: 'Sun', ra_deg: 206.66, dec_deg: -11.008, lat: -11.008, lon: 146.133 },
      moon: { id: 'moon', name: 'Moon', ra_deg: 338.5, dec_deg: -8.166, lat: -8.166, lon: -82.025 },
      planets: [],
      provenance: {},
    },
    fetchedAt: 1,
    error: null,
  },
}));

vi.mock('../../stores/earthStateStore', () => ({
  useEarthState: () => EARTH_SLICE.current,
}));

const SUN = { lat: -11.1, lon: 146.133 };

/** Every root, so afterEach can unmount it while the window still exists. */
const liveRoots = new Set<Root>();

function mount(element: React.ReactElement): { container: HTMLDivElement; root: Root } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  liveRoots.add(root);
  act(() => {
    root.render(element);
  });
  return { container, root };
}

function unmount(root: Root): void {
  if (!liveRoots.delete(root)) return;
  act(() => {
    root.unmount();
  });
}

describe('WorldStrip (headless: canvas 2d context unavailable)', () => {
  let rafSpy: MockInstance<[FrameRequestCallback], number>;

  beforeEach(() => {
    vi.useFakeTimers();
    rafSpy = vi
      .spyOn(window, 'requestAnimationFrame')
      .mockImplementation((() => 0) as unknown as typeof window.requestAnimationFrame);
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    // Unmount while the window still exists: no React work may commit after
    // the environment teardown (the W3-A2 MiniEarth lesson).
    for (const root of liveRoots) {
      act(() => {
        root.unmount();
      });
    }
    liveRoots.clear();
    rafSpy.mockRestore();
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  test('mounts one canvas with a 2:1 buffer and an accessible label', () => {
    const { container } = mount(<WorldStrip />);
    const canvases = container.querySelectorAll('canvas');
    expect(canvases.length).toBe(1);
    const canvas = canvases[0];
    const w = Number(canvas.getAttribute('width'));
    const h = Number(canvas.getAttribute('height'));
    expect(w).toBeGreaterThan(0);
    expect(h * 2).toBe(w);
    expect(canvas.getAttribute('role')).toBe('img');
    expect(canvas.getAttribute('aria-label')).toBe(
      'Equirectangular world strip: land, the day-night boundary and the sub-solar point',
    );
  });

  test('falls back to the default resolution when the container is unmeasured', () => {
    const { container } = mount(<WorldStrip />);
    const canvas = container.querySelector('canvas');
    // happy-dom reports clientWidth 0: the component must still pick a
    // deterministic buffer (the default strip), not a zero-size canvas.
    expect(canvas?.getAttribute('width')).toBe('720');
    expect(canvas?.getAttribute('height')).toBe('360');
  });

  test('shows the unavailable label when the sun is null', () => {
    const { container } = mount(<WorldStrip sun={null} />);
    expect(container.textContent).toContain('ephemeris unavailable');
  });

  test('no unavailable label when a sun is given', () => {
    const { container } = mount(<WorldStrip sun={SUN} />);
    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(container.textContent).not.toContain('unavailable');
  });

  test('redraws on a 1 Hz interval and never via requestAnimationFrame', () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval');
    mount(<WorldStrip sun={SUN} />);
    expect(setIntervalSpy).toHaveBeenCalled();
    const call = setIntervalSpy.mock.calls.find((c) => c[1] === 1000);
    expect(call).toBeDefined();
    act(() => {
      vi.advanceTimersByTime(3500);
    });
    expect(rafSpy).not.toHaveBeenCalled();
  });

  test('stops the redraw timer on unmount', () => {
    const clearSpy = vi.spyOn(window, 'clearInterval');
    const { root } = mount(<WorldStrip sun={SUN} />);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    unmount(root);
    expect(clearSpy).toHaveBeenCalled();
  });

  test('click maps to wrap-aware lat/lng through onPick', () => {
    const onPick = vi.fn();
    const { container } = mount(<WorldStrip sun={SUN} onPick={onPick} />);
    const canvas = container.querySelector('canvas');
    expect(canvas).not.toBeNull();
    // Buffer 720x360; getBoundingClientRect is all zeros under happy-dom,
    // so clientX/clientY map directly to buffer coordinates.
    act(() => {
      canvas?.dispatchEvent(
        new MouseEvent('click', { bubbles: true, clientX: 540, clientY: 90 }),
      );
    });
    // x=540 -> lng 90; y=90 -> lat 45.
    expect(onPick).toHaveBeenCalledWith(45, 90);
    onPick.mockClear();
    act(() => {
      canvas?.dispatchEvent(
        new MouseEvent('click', { bubbles: true, clientX: 3, clientY: 2 }),
      );
    });
    // Near the left/top edge: lng ~ -178.5, lat ~ 89.
    const second = onPick.mock.calls[onPick.mock.calls.length - 1];
    expect(second[0]).toBeCloseTo(89, 0);
    expect(second[1]).toBeCloseTo(-178.5, 0);
  });

  test('draws the observer marker in the one shared colour', () => {
    const fills = new Set<string>();
    const strokes = new Set<string>();
    const surface: Record<string, unknown> = {
      fillStyle: '',
      strokeStyle: '',
      lineWidth: 1,
      globalCompositeOperation: 'source-over',
      fillRect: () => undefined,
      beginPath: () => undefined,
      moveTo: () => undefined,
      lineTo: () => undefined,
      closePath: () => undefined,
      arc: () => undefined,
      stroke: () => undefined,
      fill: () => undefined,
      strokeRect: () => undefined,
      save: () => undefined,
      restore: () => undefined,
      createImageData: (w: number, h: number) => ({
        width: w,
        height: h,
        data: new Uint8ClampedArray(w * h * 4),
      }),
      putImageData: () => undefined,
      drawImage: () => undefined,
    };
    const ctx = new Proxy(surface, {
      set(target, prop, value) {
        if (prop === 'fillStyle') fills.add(String(value));
        if (prop === 'strokeStyle') strokes.add(String(value));
        target[prop as string] = value;
        return true;
      },
    });
    const descriptor = Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype, 'getContext');
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: () => ctx as unknown as CanvasRenderingContext2D,
    });
    try {
      mount(<WorldStrip sun={null} observer={{ lat: 10, lng: 20 }} />);
      expect(OBSERVER_MARKER_COLOR).toBe('#ffe08a');
      // Ring stroke + centre dot fill, both from the shared constant.
      expect(strokes.has(OBSERVER_MARKER_COLOR)).toBe(true);
      expect(fills.has(OBSERVER_MARKER_COLOR)).toBe(true);
    } finally {
      if (descriptor) Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', descriptor);
      else Reflect.deleteProperty(HTMLCanvasElement.prototype, 'getContext');
    }
  });

  test('applies the className to the wrapper', () => {
    const { container } = mount(<WorldStrip sun={SUN} className="strip-holder" />);
    expect(container.querySelector('.strip-holder')).not.toBeNull();
  });
});
