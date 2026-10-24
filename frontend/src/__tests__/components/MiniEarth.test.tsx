import React from 'react';
import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import { MiniEarth } from '../../components/2D/MiniEarth';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/* Headless environment: the canvas 2d context is unavailable, so the draw
 * path is inert; these tests pin the mounting contract, the unavailable
 * label, the canvas size and the timer lifecycle (fake timers).
 *
 * TEARDOWN RULE (W3-A2): the 110 m land loads through a dynamic import. A
 * test that ends while a root is still mounted and the import is still in
 * flight lets the import resolve after happy-dom teardown, so React commits
 * on a dead window ("window.clearInterval is not a function" in the cleanup,
 * then "Should not already be working"). Every root is therefore unmounted
 * inside act while the window is alive (afterEach, and the helper), and the
 * loader is a deferred promise this file controls: it is only released by the
 * last test, after that root is unmounted, proving the late load is ignored.
 */

const LAND_GATE = vi.hoisted(() => {
  let release!: () => void;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { promise, release };
});

vi.mock('../../data/land-110m.json', async () => {
  await LAND_GATE.promise;
  // One ring, in the file's thousandths-of-a-degree encoding.
  return { default: { polys: [{ o: [0, 0, 90_000, 0, 0, 90_000], h: [] }] } };
});

// The component subscribes to the shared earth-state store, whose refresh()
// would fire a real request and commit outside act in this headless file.
// This file tests mounting and the timer lifecycle; the store has its own
// tests (earthStateStore.test.ts), so pin it to the idle slice here.
vi.mock('../../stores/earthStateStore', () => ({
  useEarthState: () => ({ status: 'idle', state: null, fetchedAt: null, error: null }),
}));

const STATE = {
  at: '2026-10-22T02:00:00Z',
  ephemeris: 'de432s',
  gast_deg: 60.525,
  sun: { id: 'sun', name: 'Sun', ra_deg: 206.66, dec_deg: -11.008, lat: -11.008, lon: 146.133 },
  moon: { id: 'moon', name: 'Moon', ra_deg: 338.5, dec_deg: -8.166, lat: -8.166, lon: -82.025 },
  planets: [],
  provenance: {},
};

/** Every root created here, so afterEach can unmount all of them. */
const liveRoots = new Set<Root>();

function mount(element: React.ReactElement): {
  container: HTMLDivElement;
  root: Root;
  unmount: () => void;
} {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  liveRoots.add(root);
  act(() => {
    root.render(element);
  });
  const unmount = () => {
    if (!liveRoots.delete(root)) return;
    act(() => {
      root.unmount();
    });
  };
  return { container, root, unmount };
}

describe('MiniEarth (headless: canvas 2d context unavailable)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    // Unmount while the window still exists: do not rely on the environment
    // teardown to stop React work.
    for (const root of liveRoots) {
      act(() => {
        root.unmount();
      });
    }
    liveRoots.clear();
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  test('mounts without a 2d context and shows the unavailable label', () => {
    const { container } = mount(<MiniEarth isActive={false} size="small" />);
    const canvas = container.querySelector('canvas');
    expect(canvas).not.toBeNull();
    expect(container.textContent).toContain('ephemeris unavailable');
  });

  test('with a state it shows no unavailable label after a tick', () => {
    const { container } = mount(<MiniEarth isActive={false} size="small" state={STATE} />);
    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(container.textContent).not.toContain('unavailable');
  });

  test('stops its 1 Hz redraw timer on unmount', () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = mount(<MiniEarth isActive size="large" />);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    unmount();
    expect(clearSpy).toHaveBeenCalled();
    clearSpy.mockRestore();
  });

  test('renders a canvas of the requested size', () => {
    const { container } = mount(<MiniEarth isActive size="large" />);
    const canvas = container.querySelector('canvas');
    expect(canvas?.getAttribute('width')).toBe('320');
    expect(canvas?.getAttribute('height')).toBe('320');
  });

  test('a land load that lands after unmount never touches window or restarts the timer', async () => {
    const setSpy = vi.spyOn(globalThis, 'setInterval');
    const { unmount } = mount(<MiniEarth isActive size="large" />);
    unmount();
    const setCallsAfterUnmount = setSpy.mock.calls.length;

    // Simulate the real failure: the import resolves after happy-dom has torn
    // down the window, so the timer APIs are gone when React would commit.
    const win = window as unknown as { clearInterval?: unknown; setInterval?: unknown };
    const savedClear = win.clearInterval;
    const savedSet = win.setInterval;
    win.clearInterval = undefined;
    win.setInterval = undefined;
    let setCallsAfterLateLoad = -1;
    try {
      await act(async () => {
        LAND_GATE.release();
        await Promise.resolve();
        await Promise.resolve();
      });
      // Read before mockRestore(), which clears the spy's call log.
      setCallsAfterLateLoad = setSpy.mock.calls.length;
    } finally {
      win.clearInterval = savedClear;
      win.setInterval = savedSet;
      setSpy.mockRestore();
    }

    // The component's cancelled flag drops the late load: no setState, no
    // effect re-run, no interval, no window access.
    expect(setCallsAfterUnmount).toBeGreaterThan(0);
    expect(setCallsAfterLateLoad).toBe(setCallsAfterUnmount);
  });
});
