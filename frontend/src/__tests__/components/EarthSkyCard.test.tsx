// @vitest-environment happy-dom
/**
 * W3-G — EarthSkyCard: the strip + dome + time controls wired through
 * skyStore, and its lazy mount inside BroadcastPanel.
 *
 * The card adds NO WebGL canvas (the Broadcast tab's globe is the existing
 * full WorldEmanation above BroadcastPanel). The dome is stubbed here so the
 * card's slot is observable: it must receive NO props, because it follows the
 * store (its own observer tests cover the request path). The strip is real:
 * a click must set the shared observer.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import EarthSkyCard from '../../components/UI/EarthSkyCard';
import BroadcastPanel from '../../components/UI/BroadcastPanel';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { useSkyStore } from '../../stores/skyStore';

const DOME = vi.hoisted(() => ({ calls: [] as Array<Record<string, unknown>> }));

vi.mock('../../components/UI/CelestialSkyDome', async () => {
  const ReactModule = await import('react');
  return {
    default: (props: Record<string, unknown>) => {
      DOME.calls.push(props);
      return ReactModule.createElement('div', { 'data-testid': 'dome-stub' });
    },
  };
});

// The planetary-hour readout would call its route; it has its own tests (PlanetaryHourReadout.test.tsx).
// Stubbed so its slot in the card is observable: it must receive NO props, because it follows the store.
const READOUT = vi.hoisted(() => ({ calls: [] as Array<Record<string, unknown>> }));

vi.mock('../../components/UI/PlanetaryHourReadout', async () => {
  const ReactModule = await import('react');
  return {
    default: (props: Record<string, unknown>) => {
      READOUT.calls.push(props);
      return ReactModule.createElement('div', { 'data-testid': 'planetary-hour-stub' });
    },
  };
});

// The strip's sun store would poll /earth-state; the strip has its own tests. The slice is controllable here so a
// test can put the strip into loading / unavailable and look at the caption next to it.
const EARTH = vi.hoisted(() => ({
  idle: { status: 'idle' as const, state: null, fetchedAt: null, error: null },
  current: null as null | Record<string, unknown>,
}));
vi.mock('../../stores/earthStateStore', () => ({
  useEarthState: () => EARTH.current ?? EARTH.idle,
}));

// BroadcastPanel's WebSocket hook would open a socket.
vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({ sessions: {} }),
}));

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const liveRoots = new Set<Root>();
let fakeTimers = true;

/** Poll until a condition holds inside act; 5 s ceiling, clear timeout error. */
async function waitForCondition(
  check: () => boolean,
  what: string,
  timeoutMs = 5000,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    let ok = false;
    try {
      ok = check();
    } catch {
      ok = false;
    }
    if (ok) return;
    if (Date.now() >= deadline) {
      throw new Error(`timed out after ${timeoutMs} ms waiting for ${what}`);
    }
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
}


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

function reset(): void {
  useSkyStore.setState({ lat: DEFAULT_LAT, lng: DEFAULT_LNG, label: undefined, at: null });
  DOME.calls.length = 0;
  READOUT.calls.length = 0;
  EARTH.current = null;
}

beforeEach(() => {
  fakeTimers = true;
  vi.useFakeTimers();
  reset();
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } })),
  );
});

afterEach(() => {
  if (fakeTimers) {
    act(() => {
      vi.runOnlyPendingTimers();
    });
  }
  for (const root of liveRoots) {
    act(() => {
      root.unmount();
    });
  }
  liveRoots.clear();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  document.body.innerHTML = '';
});

describe('EarthSkyCard', () => {
  it('renders the strip, the dome and the controls exactly once and adds no WebGL canvas', () => {
    const { container } = mount(<EarthSkyCard />);
    expect(container.querySelectorAll('[data-testid="earth-sky-card"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-testid="world-strip"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-testid="dome-stub"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-testid="sky-time-controls"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-testid="r3f-canvas"]')).toHaveLength(0);
    expect(container.querySelectorAll('canvas')).toHaveLength(1); // the strip only
  });

  it('a strip pick sets the shared observer', () => {
    const { container } = mount(<EarthSkyCard />);
    const strip = container.querySelector('[data-testid="world-strip"]');
    expect(strip).not.toBeNull();
    act(() => {
      strip!.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: 540, clientY: 90 }));
    });
    // Buffer 720x360, unmeasured in happy-dom: x=540 -> lng 90; y=90 -> lat 45.
    expect(useSkyStore.getState().lat).toBe(45);
    expect(useSkyStore.getState().lng).toBe(90);
  });

  it('gives the dome no props, so it follows the store across a place change', () => {
    mount(<EarthSkyCard />);
    expect(DOME.calls).toHaveLength(1);
    expect(Object.keys(DOME.calls[0])).toEqual([]);

    act(() => {
      useSkyStore.getState().setObserver(51.4779, -0.0015, 'Greenwich');
    });
    const last = DOME.calls[DOME.calls.length - 1];
    expect(DOME.calls.length).toBeGreaterThan(1);
    expect(Object.keys(last)).toEqual([]); // still no explicit observer; the store is the source
  });

  it('mounts the planetary-hour readout once, directly under the dome and beside (not inside) it, with no props', () => {
    const { container } = mount(<EarthSkyCard />);
    const readout = container.querySelector('[data-testid="planetary-hour-stub"]');
    const dome = container.querySelector('[data-testid="dome-stub"]');
    expect(container.querySelectorAll('[data-testid="planetary-hour-stub"]')).toHaveLength(1);
    expect(readout).not.toBeNull();
    expect(dome).not.toBeNull();
    expect(dome!.contains(readout)).toBe(false); // not inside the dome
    expect(readout!.parentElement).toBe(dome!.parentElement); // same column
    expect(dome!.nextElementSibling).toBe(readout); // directly under it
    expect(READOUT.calls.length).toBeGreaterThan(0);
    expect(Object.keys(READOUT.calls[0])).toEqual([]);
    // the card still adds no canvas of its own: the strip only
    expect(container.querySelectorAll('canvas')).toHaveLength(1);
  });

  describe('the caption states the selected MODE and makes no claim about the data', () => {
    const caption = (container: HTMLElement) =>
      container.querySelector('[data-testid="earth-sky-caption"]') as HTMLElement;

    it('live: says it follows the current instant', () => {
      const { container } = mount(<EarthSkyCard />);
      expect(caption(container).textContent).toBe('Live: following the current instant.');
    });

    it('scrubbed: names the instant in UTC', () => {
      const { container } = mount(<EarthSkyCard />);
      act(() => {
        useSkyStore.getState().setAt('2026-10-24T09:00:00Z');
      });
      expect(caption(container).textContent).toBe('Scrubbed to 2026-10-24 09:00:00 UTC.');
      act(() => {
        useSkyStore.getState().setAt('2026-10-24T09:05:30.250Z');
      });
      expect(caption(container).textContent).toBe('Scrubbed to 2026-10-24 09:05:30 UTC.');
      act(() => {
        useSkyStore.getState().goLive();
      });
      expect(caption(container).textContent).toBe('Live: following the current instant.');
    });

    it('never says "computed" and carries no provenance tag, live or scrubbed: each child carries its own', () => {
      const { container } = mount(<EarthSkyCard />);
      expect(caption(container).textContent).not.toMatch(/computed/i);
      expect(caption(container).querySelector('[data-provenance]')).toBeNull();
      act(() => {
        useSkyStore.getState().setAt('2026-10-24T09:00:00Z');
      });
      expect(caption(container).textContent).not.toMatch(/computed/i);
      expect(caption(container).querySelector('[data-provenance]')).toBeNull();
    });

    it('live while the first live fetch failed: the strip says unavailable and the caption claims nothing', () => {
      EARTH.current = { status: 'unavailable', state: null, fetchedAt: null, error: 'HTTP 503' };
      const { container } = mount(<EarthSkyCard />);
      expect(container.querySelector('[data-testid="world-strip-unavailable"]')).not.toBeNull();
      expect(caption(container).textContent).toBe('Live: following the current instant.');
      expect(caption(container).textContent).not.toMatch(/computed/i);
      expect(caption(container).querySelector('[data-provenance]')).toBeNull();
    });

    it('scrubbed while the series is loading: the strip has no sun yet and the caption claims nothing', () => {
      EARTH.current = { status: 'loading', state: null, fetchedAt: null, error: null, frozen: true };
      const { container } = mount(<EarthSkyCard />);
      act(() => {
        useSkyStore.getState().setAt('2026-10-24T09:00:00Z');
      });
      expect(container.querySelector('[data-testid="world-strip-unavailable"]')).not.toBeNull();
      expect(caption(container).textContent).toBe('Scrubbed to 2026-10-24 09:00:00 UTC.');
      expect(caption(container).textContent).not.toMatch(/computed/i);
      expect(caption(container).querySelector('[data-provenance]')).toBeNull();
    });

    it('scrubbed while the series came back unavailable: the strip says so and the caption claims nothing', () => {
      EARTH.current = {
        status: 'unavailable',
        state: null,
        fetchedAt: null,
        error: 'ephemeris unavailable',
        frozen: true,
      };
      const { container } = mount(<EarthSkyCard />);
      act(() => {
        useSkyStore.getState().setAt('2026-10-24T09:00:00Z');
      });
      expect(container.querySelector('[data-testid="world-strip-unavailable"]')).not.toBeNull();
      expect(caption(container).textContent).not.toMatch(/computed/i);
      expect(caption(container).querySelector('[data-provenance]')).toBeNull();
    });
  });
});

describe('BroadcastPanel mount', () => {
  it('mounts the card lazily behind a Suspense fallback', async () => {
    fakeTimers = false;
    vi.useRealTimers();
    const { container } = mount(<BroadcastPanel />);
    // First commit: the lazy chunk is not here yet.
    expect(container.querySelector('[data-testid="earth-sky-card-fallback"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="earth-sky-card"]')).toBeNull();

    // Poll for the dynamic import instead of assuming a fixed delay (a 25 ms
    // sleep failed on a loaded machine / cold transform; CI is both).
    await waitForCondition(
      () =>
        container.querySelector('[data-testid="earth-sky-card"]') !== null &&
        container.querySelector('[data-testid="earth-sky-card-fallback"]') === null,
      'the lazy Earth & Sky card to mount (fallback gone)',
    );
    expect(container.querySelector('[data-testid="earth-sky-card-fallback"]')).toBeNull();
    expect(container.querySelector('[data-testid="earth-sky-card"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="r3f-canvas"]')).toBeNull();
  });
});
