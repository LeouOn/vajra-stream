// @vitest-environment happy-dom
/**
 * W7-3c — the fetch re-use rule, isolated from the rendering tests so the
 * exact request count is not perturbed by earlier components' effects.
 */
import React, { StrictMode, act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';

import type { SkyEvent, SkyEvents } from '../../lib/skyEventsClient';
import { useSkyStore } from '../../stores/skyStore';

const FETCH = vi.hoisted(() => ({ mock: vi.fn() }));
vi.mock('../../lib/skyEventsClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/skyEventsClient')>();
  return { ...actual, fetchSkyEvents: FETCH.mock, cancelSkyEventsRequest: vi.fn() };
});

import SkyEventsReadout from '../../components/UI/SkyEventsReadout';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root | null = null;

function event(body: 'sun' | 'moon', kind: SkyEvent['kind'], at: string): SkyEvent {
  return { body, kind, at, atMs: Date.parse(at) };
}

function fixtureWithWindow(fromMs: number, toMs: number, setAt = '2026-06-22T03:00:00Z'): SkyEvents {
  return {
    status: 'success',
    window: { from: new Date(fromMs).toISOString(), to: new Date(toMs).toISOString(), fromMs, toMs },
    observer: { latitude: 37.7749, longitude: -122.4194 },
    timezone: 'America/Los_Angeles',
    convention: 'convention',
    events: [
      event('sun', 'rise', '2026-06-21T12:00:00Z'),
      event('sun', 'transit', '2026-06-21T19:30:00Z'),
      event('sun', 'set', setAt),
      event('moon', 'rise', '2026-06-21T18:30:00Z'),
      event('moon', 'transit', '2026-06-22T00:00:00Z'),
      event('moon', 'set', '2026-06-22T05:00:00Z'),
    ],
    always: { sun: null, moon: null },
  };
}

async function flushMicrotasks(): Promise<void> {
  await act(async () => {
    for (let i = 0; i < 12; i += 1) await Promise.resolve();
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-06-21T18:00:00Z'));
  useSkyStore.setState({ lat: 37.7749, lng: -122.4194, at: '2026-06-21T18:00:00Z', label: undefined });
  FETCH.mock.mockReset();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  if (root !== null) {
    act(() => root!.unmount());
    root = null;
  }
  container.remove();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function deferredFixture(): { promise: Promise<SkyEvents>; resolve: (value: SkyEvents) => void } {
  let resolve!: (value: SkyEvents) => void;
  const promise = new Promise<SkyEvents>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

async function readyState(): Promise<string | null> {
  const el = container.querySelector('[data-testid="sky-events-readout"]');
  return el?.getAttribute('data-state') ?? null;
}

describe('fetch re-use', () => {
  it('a new observer while a request is in flight aborts it and fetches the new place (paused)', async () => {
    const first = deferredFixture();
    const second = fixtureWithWindow(
      Date.parse('2026-06-22T16:00:00Z'),
      Date.parse('2026-06-25T16:00:00Z'),
      '2026-06-24T03:00:00Z',
    );
    FETCH.mock.mockImplementationOnce(() => first.promise).mockImplementation(() => Promise.resolve(second));
    act(() => {
      root!.render(<SkyEventsReadout />);
    });
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(1);
    act(() => useSkyStore.getState().setObserver(40.71, -74.01));
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(2);
    expect(FETCH.mock.mock.calls[1][0]).toBe(40.71);
    expect(FETCH.mock.mock.calls[1][1]).toBe(-74.01);
    expect(await readyState()).toBe('ready');
    expect(container.querySelector('[data-testid="sky-events-sun-row"]')?.textContent).toContain('sets 20:00');
    // The first request answers late with the old place's data: it must be ignored.
    act(() => first.resolve(fixtureWithWindow(Date.parse('2026-06-20T18:00:00Z'), Date.parse('2026-06-23T18:00:00Z'), '2026-06-22T01:00:00Z')));
    await flushMicrotasks();
    expect(await readyState()).toBe('ready');
    expect(container.querySelector('[data-testid="sky-events-sun-row"]')?.textContent).toContain('sets 20:00');
    expect(container.querySelector('[data-testid="sky-events-sun-row"]')?.textContent).not.toContain('sets 18:00');
  });

  it('a new shown instant outside the window while a request is in flight refetches the new window (paused)', async () => {
    const first = deferredFixture();
    const second = fixtureWithWindow(
      Date.parse('2026-06-22T16:00:00Z'),
      Date.parse('2026-06-25T16:00:00Z'),
      '2026-06-24T03:00:00Z',
    );
    FETCH.mock.mockImplementationOnce(() => first.promise).mockImplementation(() => Promise.resolve(second));
    act(() => {
      root!.render(<SkyEventsReadout />);
    });
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(1);
    act(() => useSkyStore.getState().setAt('2026-06-23T16:00:00Z'));
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(2);
    const url = String(FETCH.mock.mock.calls[1][2]);
    expect(url).toContain('2026-06-23T16:00:00.000Z');
    expect(await readyState()).toBe('ready');
    const sun = container.querySelector('[data-testid="sky-events-sun-row"]')?.textContent ?? '';
    expect(sun).toContain('sets 20:00');
    expect(sun).not.toContain('no rise or set');
    act(() => first.resolve(fixtureWithWindow(Date.parse('2026-06-20T18:00:00Z'), Date.parse('2026-06-23T18:00:00Z'), '2026-06-22T01:00:00Z')));
    await flushMicrotasks();
    expect(container.querySelector('[data-testid="sky-events-sun-row"]')?.textContent).not.toContain('sets 18:00');
  });

  it('an identical key while the first request is still loading makes no second request', async () => {
    useSkyStore.setState({ at: null });
    vi.setSystemTime(new Date('2026-06-21T18:00:00Z'));
    const first = deferredFixture();
    FETCH.mock.mockImplementationOnce(() => first.promise).mockImplementation(() =>
      Promise.resolve(fixtureWithWindow(Date.parse('2026-06-20T18:00:00Z'), Date.parse('2026-06-23T18:00:00Z'))),
    );
    act(() => {
      root!.render(<SkyEventsReadout />);
    });
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(1);
  });


  it('a StrictMode remount while the first request is in flight still reaches ready', async () => {
    let calls = 0;
    const ms = Date.parse('2026-06-21T18:00:00Z');
    FETCH.mock.mockImplementation(() => {
      calls += 1;
      if (calls === 1) return new Promise(() => undefined);
      return Promise.resolve(fixtureWithWindow(ms - 24 * 3_600_000, ms + 48 * 3_600_000));
    });
    act(() => {
      root!.render(
        <StrictMode>
          <SkyEventsReadout />
        </StrictMode>,
      );
    });
    await flushMicrotasks();
    const readout = container.querySelector('[data-testid="sky-events-readout"]');
    expect(readout?.getAttribute('data-state')).toBe('ready');
  });

  it('ignores the fast Play ticks and asks again only when the window no longer covers', async () => {
    let activeReject: ((error: Error) => void) | null = null;
    FETCH.mock.mockImplementation(async (_lat: number, _lng: number, at: string) => {
      // Mimic the real client: a newer call aborts the older answer.
      activeReject?.(Object.assign(new Error('stale'), { kind: 'stale' }));
      const ms = Date.parse(at);
      return new Promise((resolve, reject) => {
        activeReject = reject;
        Promise.resolve().then(() => {
          if (activeReject !== reject) return;
          activeReject = null;
          resolve(fixtureWithWindow(ms - 24 * 3_600_000, ms + 48 * 3_600_000));
        });
      });
    });
    act(() => {
      root!.render(<SkyEventsReadout />);
    });
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(1);
    act(() => useSkyStore.getState().setAt('2026-06-21T20:00:00Z'));
    await flushMicrotasks();
    act(() => useSkyStore.getState().setAt('2026-06-21T23:00:00Z'));
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(1);
    act(() => useSkyStore.getState().setAt('2026-07-01T00:00:00Z'));
    await flushMicrotasks();
    expect(FETCH.mock).toHaveBeenCalledTimes(2);
  });
});
