// @vitest-environment happy-dom
/**
 * W6-A — useSkyUrlSync: restore-once, then keep the URL in step with skyStore.
 *
 * Behaviour under test (from the W6-A row):
 * - on mount, valid lat+lng (both required together) set the observer;
 *   a valid `at` inside the +-24 h window sets the scrub instant;
 * - a valid but outside-window `at` leaves the card LIVE and surfaces ONE
 *   dismissible note ("sky-link-note"); an INVALID at is dropped silently
 *   (parse problems are the parser's business);
 * - afterwards the URL follows the store: live removes `at`, scrubbed sets
 *   it, lat/lng always; debounced ~500 ms; history.replaceState (NOT push)
 *   with the router's state object preserved; never during the restore;
 * - unknown query params (the Operations page's own) are preserved.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import { useSkyUrlSync } from '../../hooks/useSkyUrlSync';
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

type SyncResult = ReturnType<typeof useSkyUrlSync>;
let root: Root | null = null;
const spyReplaceState = () => vi.spyOn(window.history, 'replaceState');
let replaceStateSpy: ReturnType<typeof spyReplaceState>;

/** A probe that exposes the hook's result and nothing else. */
function Probe({ out }: { out: { current: SyncResult | null } }) {
  out.current = useSkyUrlSync();
  return null;
}

/** happy-dom's location ignores replaceState; setURL is the supported way. */
interface HappyDomHandle {
  happyDOM?: { setURL(url: string): void };
}

/** Point the address bar somewhere, then reset the spy. */
function setSearch(search: string): void {
  const happy = (window as unknown as HappyDomHandle).happyDOM;
  const url = `http://localhost/${search === '' ? '' : `?${search}`}`;
  if (happy !== undefined) {
    happy.setURL(url);
  } else {
    window.history.replaceState(null, '', url);
  }
  replaceStateSpy.mockClear();
}

function renderProbe(out: { current: SyncResult | null }): void {
  const container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root?.render(<Probe out={out} />);
  });
}

function unmountNow(): void {
  act(() => {
    root?.unmount();
  });
  root = null;
}

beforeEach(() => {
  vi.useFakeTimers();
  replaceStateSpy = spyReplaceState();
  useSkyStore.getState().setAt(null);
  useSkyStore.getState().setObserver(DEFAULT_LAT, DEFAULT_LNG);
});

afterEach(() => {
  if (root !== null) {
    unmountNow();
  }
  replaceStateSpy.mockRestore();
  vi.useRealTimers();
  setSearch('');
});

describe('useSkyUrlSync — restore on mount', () => {
  it('restores observer and scrubbed instant from the address bar', () => {
    const at = new Date(Date.now() - 3600_000).toISOString();
    setSearch(`lat=48.85&lng=2.35&at=${at}`);
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(useSkyStore.getState().lat).toBe(48.85);
    expect(useSkyStore.getState().lng).toBe(2.35);
    expect(useSkyStore.getState().at).toBe(at);
    expect(out.current?.note).toBeNull();
    // The restore itself must not rewrite the URL (the link stays intact).
    expect(replaceStateSpy).not.toHaveBeenCalled();
  });

  it('wraps an out-of-range lng on restore', () => {
    setSearch('lat=0&lng=190');
    renderProbe({ current: null });
    expect(useSkyStore.getState().lng).toBe(-170);
  });

  it('a valid at outside the +-24 h window stays LIVE with ONE note', () => {
    setSearch(`lat=1&lng=2&at=${new Date(Date.now() - 3 * 24 * 3600_000).toISOString()}`);
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(useSkyStore.getState().at).toBeNull();
    expect(out.current?.note).toBe('That link points outside the +-24 h window: showing Live.');
    // Still restores the observer.
    expect(useSkyStore.getState().lat).toBe(1);
    expect(replaceStateSpy).not.toHaveBeenCalled();
  });

  it('the note is dismissible', () => {
    setSearch(`at=${new Date(Date.now() + 3 * 24 * 3600_000).toISOString()}`);
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(out.current?.note).not.toBeNull();
    act(() => {
      out.current?.dismissNote();
    });
    expect(out.current?.note).toBeNull();
  });

  it('an invalid at selects Live with the invalid note (observer still restored)', () => {
    setSearch('lat=48.85&lng=2.35&at=garbage');
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(useSkyStore.getState().at).toBeNull();
    expect(useSkyStore.getState().lat).toBe(48.85);
    expect(out.current?.note).toBe('That link has an invalid instant: showing Live.');
  });

  it('a lone lat moves neither lat nor lng', () => {
    setSearch('lat=48.85');
    renderProbe({ current: null });
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
    expect(useSkyStore.getState().lng).toBe(DEFAULT_LNG);
  });
});

describe('useSkyUrlSync — explicit Live selection from a PRE-PAUSED store (W6-A2 F1)', () => {
  // The store starts PAUSED one hour ago in every test here: the bug was that
  // a rejected or live link silently kept the previous pause.
  const pausedAt = () => new Date(Date.now() - 3600_000).toISOString();

  beforeEach(() => {
    useSkyStore.getState().setAt(pausedAt());
  });

  it('an out-of-window at explicitly selects Live (the old pause is gone)', () => {
    setSearch(`lat=1&lng=2&at=${new Date(Date.now() - 3 * 24 * 3600_000).toISOString()}`);
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(useSkyStore.getState().at).toBeNull();
    expect(out.current?.note).toBe('That link points outside the +-24 h window: showing Live.');
  });

  it('an invalid at explicitly selects Live with the invalid note', () => {
    setSearch('lat=1&lng=2&at=garbage');
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(useSkyStore.getState().at).toBeNull();
    expect(out.current?.note).toBe('That link has an invalid instant: showing Live.');
  });

  it('a live link (lat/lng, no at) explicitly selects Live', () => {
    setSearch('lat=9&lng=9');
    renderProbe({ current: null });
    expect(useSkyStore.getState().at).toBeNull();
    expect(useSkyStore.getState().lat).toBe(9);
  });

  it('a visit with NO sky keys leaves a paused store alone', () => {
    setSearch('op=42');
    renderProbe({ current: null });
    expect(useSkyStore.getState().at).toBe(pausedAt());
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
  });

  it('a valid in-window at replaces the old pause', () => {
    const at = new Date(Date.now() - 1800_000).toISOString();
    setSearch(`lat=1&lng=2&at=${at}`);
    renderProbe({ current: null });
    expect(useSkyStore.getState().at).toBe(at);
  });

  it('the note clears when the user picks a time again', () => {
    setSearch(`at=${new Date(Date.now() + 3 * 24 * 3600_000).toISOString()}`);
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    expect(out.current?.note).not.toBeNull();
    act(() => {
      useSkyStore.getState().setAt(new Date(Date.now() - 600_000).toISOString());
    });
    expect(out.current?.note).toBeNull();
  });
});

describe('useSkyUrlSync — URL follows the store', () => {
  it('writes observer moves after the 500 ms debounce (and not before)', () => {
    renderProbe({ current: null });
    act(() => {
      useSkyStore.getState().setObserver(48.85, 2.35);
    });
    expect(replaceStateSpy).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
    const query = new URLSearchParams(String(replaceStateSpy.mock.calls[0][2]).split('?')[1] ?? '');
    expect(query.get('lat')).toBe('48.8500');
    expect(query.get('lng')).toBe('2.3500');
    expect(query.get('at')).toBeNull();
  });

  it('preserves unknown query params and the router state object', () => {
    setSearch('op=42&tab=broadcast');
    renderProbe({ current: null });
    const routerState = window.history.state;
    act(() => {
      useSkyStore.getState().setObserver(10, 20);
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
    expect(replaceStateSpy.mock.calls[0][0]).toBe(routerState);
    const url = String(replaceStateSpy.mock.calls[0][2]);
    expect(url).toContain('op=42');
    expect(url).toContain('tab=broadcast');
    expect(url).toContain('lat=10.0000');
    expect(url).toContain('lng=20.0000');
  });

  it('keeps the URL fragment through a sync (W6-A2 F2)', () => {
    setSearch('op=42#anchor');
    renderProbe({ current: null });
    act(() => {
      useSkyStore.getState().setObserver(12, 34);
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
    const url = String(replaceStateSpy.mock.calls[0][2]);
    expect(url.endsWith('#anchor')).toBe(true);
    expect(url).toContain('op=42');
    expect(url).toContain('lat=12.0000');
    expect(url).toContain('lng=34.0000');
  });

  it('scrubbed sets at=; going live removes it', () => {
    renderProbe({ current: null });
    const at = new Date(Date.now() - 1200_000).toISOString();
    act(() => {
      useSkyStore.getState().setAt(at);
      vi.advanceTimersByTime(500);
    });
    let url = String(replaceStateSpy.mock.calls[0][2]);
    expect(new URLSearchParams(url.split('?')[1] ?? '').get('at')).toBe(at);
    act(() => {
      useSkyStore.getState().goLive();
      vi.advanceTimersByTime(500);
    });
    url = String(replaceStateSpy.mock.calls[1][2]);
    expect(new URLSearchParams(url.split('?')[1] ?? '').get('at')).toBeNull();
    expect(url).toContain('lat=');
  });

  it('debounces: rapid changes write once, latest wins', () => {
    renderProbe({ current: null });
    act(() => {
      useSkyStore.getState().setObserver(1, 1);
      vi.advanceTimersByTime(300);
      useSkyStore.getState().setObserver(2, 2);
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
    expect(String(replaceStateSpy.mock.calls[0][2])).toContain('lat=2.0000');
  });

  it('does not write when the URL already matches', () => {
    setSearch('lat=1.0000&lng=2.0000');
    renderProbe({ current: null });
    act(() => {
      useSkyStore.getState().setObserver(1, 2);
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).not.toHaveBeenCalled();
  });

  it('unmount cancels the pending write', () => {
    renderProbe({ current: null });
    act(() => {
      useSkyStore.getState().setObserver(3, 4);
    });
    unmountNow();
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).not.toHaveBeenCalled();
  });

  it('syncNow writes immediately and cancels the pending debounce', () => {
    const out: { current: SyncResult | null } = { current: null };
    renderProbe(out);
    act(() => {
      useSkyStore.getState().setObserver(5, 6);
      out.current?.syncNow();
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
    expect(String(replaceStateSpy.mock.calls[0][2])).toContain('lat=5.0000');
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
  });
});

describe('useSkyUrlSync — real BrowserRouter (router survival)', () => {
  it('uses replaceState with the router state preserved under a real BrowserRouter', async () => {
    const { BrowserRouter } = await import('react-router-dom');
    setSearch('lat=7&lng=8');
    const container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root?.render(
        <BrowserRouter>
          <Probe out={{ current: null }} />
        </BrowserRouter>,
      );
    });
    const routerState = window.history.state;
    replaceStateSpy.mockClear();
    act(() => {
      useSkyStore.getState().setObserver(9, 9);
      vi.advanceTimersByTime(500);
    });
    expect(replaceStateSpy).toHaveBeenCalledTimes(1);
    expect(replaceStateSpy.mock.calls[0][0]).toBe(routerState);
    expect(String(replaceStateSpy.mock.calls[0][2])).toContain('lat=9.0000');
  });
});
