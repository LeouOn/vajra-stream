// @vitest-environment happy-dom
/**
 * W3-F tests for components/UI/SkyTimeControls.tsx.
 *
 * The client is mocked (a mocked backend); the real skyStore and the real
 * skyClock are used. Timers are fake and the system clock is pinned, so the
 * readout, the +-24 h clamp and the 1 Hz tick are deterministic.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import SkyTimeControls from '../../components/UI/SkyTimeControls';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { useSkyStore } from '../../stores/skyStore';

vi.mock('../../lib/sunEventsClient', () => ({
  fetchSunEvents: vi.fn(),
}));

import { fetchSunEvents } from '../../lib/sunEventsClient';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const clientMock = vi.mocked(fetchSunEvents);
const NOW = new Date('2026-10-24T09:00:00Z');

const EVENTS = {
  at: '2026-10-24T09:00:00.000Z',
  latitude: DEFAULT_LAT,
  longitude: DEFAULT_LNG,
  previous_sunrise: '2026-10-23T14:32:00.000Z',
  sunset: '2026-10-25T01:12:00.000Z',
  next_sunrise: '2026-10-24T14:32:00.000Z',
  previous_sunset: '2026-10-24T01:11:00.000Z',
  next_sunset: '2026-10-25T01:12:00.000Z',
  provenance: { next_sunrise: 'computed' },
};

let container: HTMLDivElement;
let root: Root;
let hidden = false;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function mount(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(<SkyTimeControls />);
  });
}

function byLabel(label: string): HTMLElement {
  const el = container.querySelector<HTMLElement>(`[aria-label="${label}"]`);
  if (el === null) throw new Error(`no element with aria-label ${label}`);
  return el;
}

function text(): string {
  return container.textContent ?? '';
}

function click(el: Element): void {
  act(() => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

async function clickAsync(el: Element): Promise<void> {
  await act(async () => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await Promise.resolve();
  });
}

function pressKey(el: Element, key: string, which: number): void {
  const event = new KeyboardEvent('keydown', { key, bubbles: true });
  // rc-slider reads e.which || e.keyCode.
  Object.defineProperty(event, 'which', { value: which });
  Object.defineProperty(event, 'keyCode', { value: which });
  act(() => {
    el.dispatchEvent(event);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
  hidden = false;
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
  useSkyStore.setState({ lat: DEFAULT_LAT, lng: DEFAULT_LNG, label: undefined, at: null });
  clientMock.mockReset();
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('readout and Live/Pause', () => {
  it('starts live and shows the UTC instant as computed', () => {
    mount();
    expect(text()).toContain('Live');
    expect(text()).toContain('2026-10-24 09:00:00 UTC');
    expect(text()).toContain('computed');
    expect(byLabel('Live sky time').getAttribute('aria-pressed')).toBe('true');
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('Pause freezes the store at now; Live returns to live', () => {
    mount();
    click(byLabel('Pause sky time at the current instant'));
    expect(useSkyStore.getState().at).toBe('2026-10-24T09:00:00.000Z');
    expect(text()).toContain('Paused');
    expect(byLabel('Pause sky time at the current instant').getAttribute('aria-pressed')).toBe(
      'true',
    );

    click(byLabel('Live sky time'));
    expect(useSkyStore.getState().at).toBeNull();
    expect(text()).toContain('Live');
  });

  it('ticks the readout once a second while visible and freezes it while hidden', () => {
    mount();
    expect(text()).toContain('2026-10-24 09:00:00 UTC');
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(text()).toContain('2026-10-24 09:00:03 UTC');

    hidden = true;
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(text()).toContain('2026-10-24 09:00:03 UTC');

    hidden = false;
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(text()).toContain('2026-10-24 09:00:08 UTC');
  });

  it('clears the 1 Hz interval on unmount', () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval');
    mount();
    act(() => {
      root.unmount();
    });
    expect(clearSpy).toHaveBeenCalled();
    // Guard against a double unmount in afterEach.
    mount();
  });
});

describe('scrub slider', () => {
  it('a keyboard step becomes a 1-minute scrub and pauses the sky', () => {
    mount();
    pressKey(byLabel('Time offset from now in minutes'), 'ArrowRight', 39);
    expect(useSkyStore.getState().at).toBe('2026-10-24T09:01:00.000Z');
    expect(text()).toContain('Paused');
    expect(text()).toContain('+1 min from now');
  });

  it('clamps at +24 h and -24 h instead of leaving the window', () => {
    mount();
    const handle = byLabel('Time offset from now in minutes');
    pressKey(handle, 'End', 35);
    expect(useSkyStore.getState().at).toBe('2026-10-25T09:00:00.000Z');
    expect(text()).toContain('+24 h from now');

    pressKey(handle, 'Home', 36);
    expect(useSkyStore.getState().at).toBe('2026-10-23T09:00:00.000Z');
    expect(text()).toContain('-24 h from now');
  });
});

describe('Next sunrise here', () => {
  it('sets the store to the returned sunrise and labels it computed', async () => {
    clientMock.mockResolvedValue({ ...EVENTS });
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));

    expect(clientMock).toHaveBeenCalledTimes(1);
    expect(clientMock.mock.calls[0][0]).toBe(DEFAULT_LAT);
    expect(clientMock.mock.calls[0][1]).toBe(DEFAULT_LNG);
    // The query is the shown instant + 1 s: the engine floors to the second,
    // and asking from the event itself would return the same event forever.
    expect(clientMock.mock.calls[0][2]).toBe('2026-10-24T09:00:01.000Z');
    expect(useSkyStore.getState().at).toBe('2026-10-24T14:32:00.000Z');
    expect(text()).toContain('Sunrise set: 2026-10-24 14:32:00 UTC');
    expect(text()).toContain('computed');
  });

  it('a second press returns a later sunrise (engine-like stub floors to the second)', async () => {
    // True sunrise instants (ms precision). The engine floors the *query* to
    // the second, and the route prints the event itself; asking from the
    // event (2026-10-24T14:26:49.815Z) floors to :49 and returns the SAME
    // sunrise forever. Asking from shown + 1 s crosses the boundary.
    const TRUE_SUNRISES = [
      Date.parse('2026-10-24T14:26:49.815Z'),
      Date.parse('2026-10-25T14:27:35.204Z'),
    ];
    clientMock.mockImplementation(async (_lat, _lng, atIso) => {
      const flooredToSecond = Math.floor(Date.parse(atIso) / 1000) * 1000;
      const next = TRUE_SUNRISES.find((t) => t > flooredToSecond);
      return {
        ...EVENTS,
        next_sunrise: next === undefined ? null : new Date(next).toISOString(),
      };
    });
    mount();
    const button = byLabel('Next sunrise at this location');

    await clickAsync(button);
    expect(useSkyStore.getState().at).toBe('2026-10-24T14:26:49.815Z');
    expect(clientMock.mock.calls[0][2]).toBe('2026-10-24T09:00:01.000Z');

    // Real time moves past the first sunrise, so the next one is inside the
    // component's +24 h refusal window (which is relative to the real now).
    act(() => {
      vi.setSystemTime(new Date('2026-10-24T15:00:00Z'));
    });

    await clickAsync(button);
    expect(clientMock.mock.calls[1][2]).toBe('2026-10-24T14:26:50.815Z');
    expect(useSkyStore.getState().at).toBe('2026-10-25T14:27:35.204Z');
    expect(Date.parse(useSkyStore.getState().at!)).toBeGreaterThan(
      Date.parse('2026-10-24T14:26:49.815Z'),
    );
  });

  it('says there is no sunrise at polar night and changes nothing', async () => {
    clientMock.mockResolvedValue({ ...EVENTS, next_sunrise: null });
    mount();
    click(byLabel('Pause sky time at the current instant'));
    const pausedAt = useSkyStore.getState().at;

    await clickAsync(byLabel('Next sunrise at this location'));
    expect(text()).toContain('No sunrise here within the next day (polar night or midnight sun)');
    expect(useSkyStore.getState().at).toBe(pausedAt);
  });

  it('refuses a sunrise beyond now + 24 h rather than clamping it', async () => {
    clientMock.mockResolvedValue({ ...EVENTS, next_sunrise: '2026-10-25T10:00:00.000Z' });
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));
    expect(text()).toContain('The next sunrise is more than 24 h away (outside the scrub range)');
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('shows a readable 422 message and leaves the state unchanged', async () => {
    clientMock.mockRejectedValue(
      Object.assign(new Error('malformed datetime_str; expected ISO-8601'), { kind: 'invalid-input' }),
    );
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));
    expect(text()).toContain('malformed datetime_str; expected ISO-8601');
    expect(useSkyStore.getState().at).toBeNull();
    expect(byLabel('Next sunrise at this location').hasAttribute('disabled')).toBe(false);
  });

  it('shows a readable 503 message', async () => {
    clientMock.mockRejectedValue(
      Object.assign(new Error('Ephemeris unavailable (503).'), { kind: 'unavailable' }),
    );
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));
    expect(text()).toContain('Ephemeris unavailable');
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('shows a readable network message', async () => {
    clientMock.mockRejectedValue(
      Object.assign(new Error('Could not reach the server for sun events.'), { kind: 'network' }),
    );
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));
    expect(text()).toContain('Could not reach the server for sun events.');
    expect(useSkyStore.getState().at).toBeNull();
  });

  it('the newer request wins when the older resolves last', async () => {
    const first = deferred<typeof EVENTS>();
    const second = deferred<typeof EVENTS>();
    clientMock.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    mount();
    const button = byLabel('Next sunrise at this location');

    // Two clicks in one batch (the same window a fast double-click creates).
    act(() => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(clientMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      second.resolve({ ...EVENTS, next_sunrise: '2026-10-24T16:00:00.000Z' });
      await Promise.resolve();
    });
    expect(useSkyStore.getState().at).toBe('2026-10-24T16:00:00.000Z');

    await act(async () => {
      first.resolve({ ...EVENTS, next_sunrise: '2026-10-24T10:00:00.000Z' });
      await Promise.resolve();
    });
    expect(useSkyStore.getState().at).toBe('2026-10-24T16:00:00.000Z');
    expect(text()).not.toContain('10:00:00 UTC');
  });

  it('drops an in-flight sunrise when the observer moves', async () => {
    const pending = deferred<typeof EVENTS>();
    clientMock.mockReturnValueOnce(pending.promise);
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));

    act(() => {
      useSkyStore.getState().setObserver(51.4779, -0.0015, 'Greenwich');
    });
    await act(async () => {
      pending.resolve({ ...EVENTS, next_sunrise: '2026-10-24T14:32:00.000Z' });
      await Promise.resolve();
    });

    expect(useSkyStore.getState().at).toBeNull();
    expect(text()).not.toContain('Sunrise set');
  });

  it('disables the button and shows a busy state while loading', async () => {
    const pending = deferred<typeof EVENTS>();
    clientMock.mockReturnValueOnce(pending.promise);
    mount();
    await clickAsync(byLabel('Next sunrise at this location'));
    const button = byLabel('Next sunrise at this location');
    expect(button.hasAttribute('disabled')).toBe(true);
    expect(button.textContent).toContain('Finding sunrise…');

    await act(async () => {
      pending.resolve({ ...EVENTS });
      await Promise.resolve();
    });
    expect(byLabel('Next sunrise at this location').hasAttribute('disabled')).toBe(false);
  });
});
