/**
 * W3-D2a — the dome follows the observer store and survives bad/slow answers.
 *
 * Uses the real `nightSkyClient` against a deferred `fetch`, so the ordering
 * and abort behaviour is the production one. Nothing here claims how the dome
 * looks; only which request was made and which honest state is visible.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

const PLANET = {
  id: 'jupiter',
  name: 'Jupiter',
  glyph: '♃',
  altitude: 58.2,
  azimuth: 142.1,
  sign: 'Cancer',
  sign_glyph: '♋',
  visible: true,
  color: '#a855f7',
  esoteric_quality: 'Guru · Expansive Grace',
};

const STAR = {
  id: 'sirius',
  name: 'Sirius (Mrigavyadha)',
  altitude: 35.8,
  azimuth: 122.4,
  magnitude: -1.46,
  visible: true,
  color: '#a6d8ff',
  nakshatra: 'Ardra',
  quality: 'Supreme Cosmic Fire',
};

function payload(lst = 298.11, hms = '19:52:26', lat = DEFAULT_LAT, lng = DEFAULT_LNG) {
  return {
    timestamp_utc: '2026-10-22T02:00:00Z',
    observer: {
      latitude: lat,
      longitude: lng,
      local_sidereal_time_deg: lst,
      local_sidereal_time_hms: hms,
    },
    moon: { phase_name: 'Waning Crescent', illumination: 22.6 },
    planets: [{ ...PLANET }],
    visible_planets_count: 1,
    sacred_stars: [{ ...STAR }],
    visible_stars_count: 1,
    provenance: { observer: 'computed' },
  };
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) } as Response;
}

interface PendingRequest {
  url: string;
  init: RequestInit;
  resolve: (value: Response) => void;
  reject: (reason: unknown) => void;
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
let requests: PendingRequest[];

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

async function deliver(index: number, body: unknown, status = 200): Promise<void> {
  await act(async () => {
    requests[index].resolve(response(body, status));
  });
  await flush();
}

async function fail(index: number, reason: unknown = new TypeError('Failed to fetch')): Promise<void> {
  await act(async () => {
    requests[index].reject(reason);
  });
  await flush();
}

function refreshButton(): HTMLButtonElement {
  const button = Array.from(container.querySelectorAll('button')).find((candidate) =>
    candidate.textContent?.includes('Refresh'),
  );
  if (!(button instanceof HTMLButtonElement)) throw new Error('Refresh button missing');
  return button;
}

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  const canvasProto: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvasProto, 'getContext').mockReturnValue(stubCtx());
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  vi.stubGlobal(
    'setInterval',
    vi.fn((_handler: TimerHandler, _timeout?: number) => 1),
  );
  vi.stubGlobal('clearInterval', vi.fn());

  useSkyStore.getState().setObserver(DEFAULT_LAT, DEFAULT_LNG);
  useSkyStore.getState().goLive();

  requests = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(
      (url: string, init: RequestInit) =>
        new Promise<Response>((resolve, reject) => {
          requests.push({ url: String(url), init: init ?? {}, resolve, reject });
        }),
    ),
  );
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('CelestialSkyDome observer store', () => {
  it('renders an honest unavailable state for the {observer}-only body instead of throwing', async () => {
    await mount();
    await deliver(0, {
      observer: {
        latitude: 0,
        longitude: 0,
        local_sidereal_time_deg: 0,
        local_sidereal_time_hms: '00:00:00',
      },
    });

    const unavailable = container.querySelector('[data-testid="sky-unavailable"]');
    expect(unavailable).not.toBeNull();
    expect(unavailable?.getAttribute('data-reason')).toBe('invalid-response');
    expect(container.textContent).toContain('unavailable');
    // No fake zero counts, and no LST pretending to be real.
    expect(container.textContent).not.toContain('Planets (0)');
    expect(container.textContent).not.toContain('00:00:00');
  });

  it('drops a slow older answer that arrives after the newer place', async () => {
    await mount();
    expect(requests).toHaveLength(1);

    act(() => {
      useSkyStore.getState().setObserver(10, 20, 'Newer');
    });
    expect(requests).toHaveLength(2);

    await deliver(1, payload(111.1, '11:11:11', 10, 20));
    expect(container.textContent).toContain('11:11:11');

    await deliver(0, payload(222.2, '22:22:22', DEFAULT_LAT, DEFAULT_LNG));
    expect(container.textContent).toContain('11:11:11');
    expect(container.textContent).not.toContain('22:22:22');
  });

  it('aborts the in-flight request on a place change and starts exactly one new one', async () => {
    await mount();
    expect(requests).toHaveLength(1);

    act(() => {
      useSkyStore.getState().setObserver(-33.8688, 151.2093, 'Sydney');
    });

    expect(requests).toHaveLength(2);
    expect((requests[0].init.signal as AbortSignal).aborted).toBe(true);
    expect(requests[1].url).toContain('latitude=-33.8688');
  });

  it('shows a clear first-load failure with its reason class', async () => {
    await mount();
    await fail(0);

    const unavailable = container.querySelector('[data-testid="sky-unavailable"]');
    expect(unavailable?.getAttribute('data-reason')).toBe('network');
    expect(container.textContent).toContain('unavailable');
    expect(container.querySelector('[data-testid="celestial-sky-dome-canvas"]')).toBeNull();
  });

  it('keeps the last good sky but marks planets and stars stale after a later failure', async () => {
    await mount();
    await deliver(0, payload(298.11, '19:52:26'));
    expect(container.textContent).toContain('19:52:26');
    expect(container.textContent).toContain('Jupiter');
    expect(container.textContent).toContain('Sirius');

    act(() => {
      refreshButton().click();
    });
    expect(requests).toHaveLength(2);
    await fail(1);

    const stale = container.querySelector('[data-testid="sky-stale"]');
    expect(stale).not.toBeNull();
    expect(stale?.getAttribute('data-reason')).toBe('network');
    expect(container.textContent).toContain('19:52:26');
    expect(container.textContent).toContain('Jupiter');
    expect(container.textContent).toContain('Sirius');
    expect(container.textContent).not.toContain('unavailable');

    // A later success clears the stale state and resumes the live clock.
    act(() => {
      refreshButton().click();
    });
    expect(requests).toHaveLength(3);
    await deliver(2, payload(300.5, '20:02:00'));
    expect(container.querySelector('[data-testid="sky-stale"]')).toBeNull();
    expect(container.textContent).toContain('20:02:00');
  });

  it('keeps the spinner while a newer request is in flight after a stale answer', async () => {
    await mount(); // request 0
    act(() => {
      useSkyStore.getState().setObserver(-33.8688, 151.2093, 'Sydney');
    });
    await flush();
    expect(requests).toHaveLength(2);
    const spinning = () => container.querySelector('svg.animate-spin') !== null;
    expect(spinning()).toBe(true);

    // The earlier (aborted) answer resolves stale; the newer request is still
    // in flight, so the spinner must not be cleared by the older settlement.
    await deliver(0, payload(10, '01:00:00', DEFAULT_LAT, DEFAULT_LNG));
    expect(spinning()).toBe(true);

    await deliver(1, payload(20, '02:00:00', -33.8688, 151.2093));
    expect(spinning()).toBe(false);
  });

  it('says stale data are for another place after a failed place change', async () => {
    await mount();
    await deliver(0, payload(298.11, '19:52:26'));
    act(() => {
      useSkyStore.getState().setObserver(-33.8688, 151.2093, 'Sydney');
    });
    await flush();
    expect(requests).toHaveLength(2);
    await fail(1);

    const stale = container.querySelector('[data-testid="sky-stale"]');
    expect(stale?.getAttribute('data-other-place')).toBe('true');
    expect(stale?.textContent).toContain('another place');
    // The transient "updating" note is replaced by the stale-place note.
    expect(container.querySelector('[data-testid="sky-updating-place"]')).toBeNull();
  });

  it('lets explicit props win over the store', async () => {
    useSkyStore.getState().setObserver(1, 2, 'Store place');

    await mount(<CelestialSkyDome latitude={48.8566} longitude={2.3522} />);
    expect(requests).toHaveLength(1);
    expect(requests[0].url).toContain('latitude=48.8566');
    expect(requests[0].url).toContain('longitude=2.3522');

    act(() => {
      useSkyStore.getState().setObserver(-10, -20, 'Elsewhere');
    });
    expect(requests).toHaveLength(1);
  });

  it('makes exactly one new request for a store-driven place change', async () => {
    await mount();
    expect(requests).toHaveLength(1);

    act(() => {
      useSkyStore.getState().setObserver(35.6762, 139.6503, 'Tokyo');
    });
    expect(requests).toHaveLength(2);
    expect(requests[1].url).toContain('latitude=35.6762');
  });

  it('aborts the in-flight request on unmount', async () => {
    await mount();
    expect(requests).toHaveLength(1);
    const signal = requests[0].init.signal as AbortSignal;
    expect(signal.aborted).toBe(false);

    act(() => {
      root.unmount();
    });
    expect(signal.aborted).toBe(true);
    root = createRoot(container);
  });
});
