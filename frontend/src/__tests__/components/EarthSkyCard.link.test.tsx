// @vitest-environment happy-dom
/**
 * W6-A — EarthSkyCard shareable-sky surface: the "Copy link" button, its
 * clipboard fallback and the outside-window note (driven by useSkyUrlSync,
 * which is real here; the URL is placed with replaceState before render).
 *
 * The dome, the planetary-hour readout and the earth-state store are stubbed
 * exactly like EarthSkyCard.test.tsx (their slots are not under test); the
 * strip renders for real but stays idle. No WebSocket, no network.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import EarthSkyCard from '../../components/UI/EarthSkyCard';
import { useSkyStore } from '../../stores/skyStore';

vi.mock('../../components/UI/CelestialSkyDome', async () => {
  const ReactModule = await import('react');
  return { default: () => ReactModule.createElement('div', { 'data-testid': 'dome-stub' }) };
});

vi.mock('../../components/UI/PlanetaryHourReadout', async () => {
  const ReactModule = await import('react');
  return { default: () => ReactModule.createElement('div', { 'data-testid': 'readout-stub' }) };
});

vi.mock('../../stores/earthStateStore', () => ({
  useEarthState: () => ({ status: 'idle', state: null, fetchedAt: null, error: null }),
}));

let root: Root | null = null;
const spyReplaceState = () => vi.spyOn(window.history, 'replaceState');
let replaceStateSpy: ReturnType<typeof spyReplaceState>;
let container: HTMLElement;

/** happy-dom's location ignores replaceState; setURL is the supported way. */
interface HappyDomHandle {
  happyDOM?: { setURL(url: string): void };
}

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

function renderCard(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root?.render(<EarthSkyCard />);
  });
}

function unmountNow(): void {
  act(() => {
    root?.unmount();
  });
  root = null;
  document.body.removeChild(container);
}

function setClipboard(writeText: (() => Promise<void>) | undefined): void {
  Object.defineProperty(navigator, 'clipboard', {
    value: writeText === undefined ? undefined : { writeText },
    configurable: true,
  });
}

beforeEach(() => {
  replaceStateSpy = spyReplaceState();
  useSkyStore.getState().setAt(null);
  useSkyStore.getState().setObserver(37.7749, -122.4194);
  setSearch('');
});

afterEach(() => {
  if (root !== null) {
    unmountNow();
  }
  replaceStateSpy.mockRestore();
  setClipboard(undefined);
});

describe('EarthSkyCard — Copy link', () => {
  // happy-dom's location does not follow replaceState, so the URL a real
  // browser would hand the clipboard is staged here with setURL (the sync
  // itself is covered by the useSkyUrlSync tests, including syncNow).
  it('copies the current URL via the clipboard and announces it for 2 s', async () => {
    vi.useFakeTimers();
    setSearch('lat=37.7749&lng=-122.4194');
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    renderCard();
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    expect(writeText).toHaveBeenCalledTimes(1);
    const url = String(writeText.mock.calls[0][0]);
    expect(url).toContain('lat=37.7749');
    expect(url).toContain('lng=-122.4194');
    expect(new URLSearchParams(url.split('?')[1] ?? '').get('at')).toBeNull();
    expect(container.querySelector('[data-testid="sky-copy-status"]')?.textContent).toContain('Link copied');
    act(() => {
      vi.advanceTimersByTime(2100);
    });
    expect(container.querySelector('[data-testid="sky-copy-status"]')?.textContent).not.toContain('Link copied');
    vi.useRealTimers();
  });

  it('includes the scrubbed instant in a copied link', () => {
    const at = new Date(Date.now() - 900_000).toISOString();
    act(() => {
      useSkyStore.getState().setAt(at);
    });
    setSearch(`lat=37.7749&lng=-122.4194&at=${at}`);
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    renderCard();
    act(() => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    const url = String(writeText.mock.calls[0][0]);
    expect(url).toContain(`at=${at}`);
  });

  it('flushes the pending debounce BEFORE reading location.href (order + content)', async () => {
    // Emulate the browser: replaceState moves the address bar (happy-dom's
    // history does not), so the recorded order and the copied text prove the
    // flush happens before the read.
    const happy = (window as unknown as HappyDomHandle).happyDOM;
    const order: string[] = [];
    replaceStateSpy.mockImplementation((data: unknown, _unused: string, url?: string | URL | null) => {
      order.push('sync');
      if (happy !== undefined && typeof url === 'string') {
        happy.setURL(url.startsWith('http') ? url : `http://localhost${url}`);
      }
    });
    const writeText = vi.fn().mockImplementation((text: string): Promise<void> => {
      order.push('copy');
      expect(text).toContain('lat=37.7749');
      return Promise.resolve();
    });
    setClipboard(writeText);
    setSearch('lat=1&lng=1'); // stale: an OLD place in the bar
    renderCard();
    act(() => {
      useSkyStore.getState().setObserver(37.7749, -122.4194); // pending debounce
    });
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    expect(order).toEqual(['sync', 'copy']);
    expect(String(writeText.mock.calls[0][0])).toContain('lat=37.7749');
  });

  it('keeps the fragment in a copied link (W6-A2 F2)', async () => {
    setSearch('lat=37.7749&lng=-122.4194#anchor');
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    renderCard();
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    expect(String(writeText.mock.calls[0][0])).toContain('#anchor');
  });

  it('falls back to a selected readonly input when the clipboard is absent', () => {
    const selectSpy = vi.spyOn(HTMLInputElement.prototype, 'select');
    setSearch('lat=37.7749&lng=-122.4194');
    setClipboard(undefined);
    renderCard();
    expect(container.querySelector('[data-testid="sky-fallback-url"]')).toBeNull();
    act(() => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    const input = container.querySelector<HTMLInputElement>('[data-testid="sky-fallback-url"]');
    expect(input).not.toBeNull();
    expect(input?.readOnly).toBe(true);
    expect(input?.value).toContain('lat=37.7749');
    expect(selectSpy).toHaveBeenCalled();
    selectSpy.mockRestore();
  });

  it('announces with aria-live (the existing live-region style)', () => {
    setSearch('lat=37.7749&lng=-122.4194');
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    renderCard();
    act(() => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    const status = container.querySelector('[data-testid="sky-copy-status"]');
    expect(status?.getAttribute('aria-live')).toBe('polite');
  });
});

describe('EarthSkyCard — Copy link async lifecycle (W6-A2 F3)', () => {
  it('a late resolve after unmount changes nothing (no error, no timer)', async () => {
    vi.useFakeTimers();
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    let resolveCopy: (() => void) | undefined;
    const writeText = vi.fn().mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveCopy = resolve;
        }),
    );
    setClipboard(writeText);
    setSearch('lat=1.0000&lng=2.0000');
    renderCard();
    act(() => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    unmountNow();
    await act(async () => {
      resolveCopy?.();
    });
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    // React's act-configuration noise is filtered: what must NOT appear is an
    // update-to-an-unmounted-component error from the late resolve.
    const relevant = errSpy.mock.calls.filter(
      (call) =>
        String(call[0]).includes('unmount') ||
        String(call[0]).includes('EarthSkyCard') ||
        String(call[0]).includes('Can\'t perform a React state update'),
    );
    expect(relevant).toEqual([]);
    errSpy.mockRestore();
    vi.useRealTimers();
  });

  it('feedback matches the NEWEST attempt when an older rejection lands last', async () => {
    let rejectOld: ((reason?: unknown) => void) | undefined;
    const oldAttempt = new Promise<void>((_resolve, reject) => {
      rejectOld = reject;
    });
    const writeText = vi
      .fn()
      .mockImplementationOnce(() => oldAttempt)
      .mockImplementationOnce(() => Promise.resolve());
    setClipboard(writeText);
    setSearch('lat=1.0000&lng=2.0000');
    renderCard();
    act(() => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    expect(container.querySelector('[data-testid="sky-copy-status"]')?.textContent).toContain('Link copied');
    expect(container.querySelector('[data-testid="sky-fallback-url"]')).toBeNull();
    await act(async () => {
      rejectOld?.(new Error('older attempt fails'));
    });
    // The stale rejection is ignored: the newest attempt's success stands.
    expect(container.querySelector('[data-testid="sky-copy-status"]')?.textContent).toContain('Link copied');
    expect(container.querySelector('[data-testid="sky-fallback-url"]')).toBeNull();
  });

  it('a rejection right after an earlier success clears the success and shows the fallback', async () => {
    const writeText = vi
      .fn()
      .mockImplementationOnce(() => Promise.resolve())
      .mockImplementationOnce(() => Promise.reject(new Error('denied')));
    setClipboard(writeText);
    setSearch('lat=1.0000&lng=2.0000');
    renderCard();
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    expect(container.querySelector('[data-testid="sky-copy-status"]')?.textContent).toContain('Link copied');
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]')?.click();
    });
    expect(container.querySelector('[data-testid="sky-copy-status"]')?.textContent).not.toContain('Link copied');
    expect(container.querySelector('[data-testid="sky-fallback-url"]')).not.toBeNull();
  });
});

describe('EarthSkyCard — outside-window note', () => {
  it('shows one dismissible plain line when the link at is outside +-24 h', () => {
    setSearch(`lat=1&lng=2&at=${new Date(Date.now() + 3 * 24 * 3600_000).toISOString()}`);
    renderCard();
    const note = container.querySelector('[data-testid="sky-link-note"]');
    expect(note?.textContent).toContain('That link points outside the +-24 h window: showing Live.');
    act(() => {
      note?.querySelector<HTMLButtonElement>('button')?.click();
    });
    expect(container.querySelector('[data-testid="sky-link-note"]')).toBeNull();
  });

  it('shows no note for a clean mount', () => {
    renderCard();
    expect(container.querySelector('[data-testid="sky-link-note"]')).toBeNull();
  });
});

describe('EarthSkyCard — Copy link visible confirmation (W6-A3)', () => {
  const button = (): HTMLButtonElement =>
    container.querySelector<HTMLButtonElement>('[data-testid="sky-copy-link"]') as HTMLButtonElement;
  const status = (): string => container.querySelector('[data-testid="sky-copy-status"]')?.textContent ?? '';
  const press = async (): Promise<void> => {
    await act(async () => {
      button().click();
    });
  };

  it('the button label turns to "Copied" for 2 s and then back', async () => {
    vi.useFakeTimers();
    setClipboard(vi.fn().mockResolvedValue(undefined));
    renderCard();
    expect(button().textContent).toBe('Copy link');
    await press();
    expect(button().textContent).toBe('Copied');
    act(() => {
      vi.advanceTimersByTime(1900);
    });
    expect(button().textContent).toBe('Copied');
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(button().textContent).toBe('Copy link');
    vi.useRealTimers();
  });

  it('a second click restarts the 2 s', async () => {
    vi.useFakeTimers();
    setClipboard(vi.fn().mockResolvedValue(undefined));
    renderCard();
    await press();
    act(() => {
      vi.advanceTimersByTime(1500);
    });
    expect(button().textContent).toBe('Copied');
    await press(); // 1.5 s into the first window
    act(() => {
      vi.advanceTimersByTime(1500); // 3.0 s after the first click: the first window would be over
    });
    expect(button().textContent).toBe('Copied');
    act(() => {
      vi.advanceTimersByTime(600); // 2.1 s after the second click
    });
    expect(button().textContent).toBe('Copy link');
    vi.useRealTimers();
  });

  it('nothing changes after unmount and the 2 s timer is cleared (same leftovers as a click whose copy failed)', async () => {
    // A click leaves one timer of its own behind after unmount (the URL-sync debounce, outside this card's copy code);
    // the 2 s "Copied" timer must not add to it. A rejected copy never starts that timer: the control.
    vi.useFakeTimers();
    setClipboard(vi.fn().mockRejectedValue(new Error('denied')));
    renderCard();
    await press();
    unmountNow();
    const withoutCopiedTimer = vi.getTimerCount();
    vi.clearAllTimers(); // the control's leftovers must not count against the real run below

    setClipboard(vi.fn().mockResolvedValue(undefined));
    renderCard();
    await press();
    expect(button().textContent).toBe('Copied');
    unmountNow();
    expect(vi.getTimerCount()).toBe(withoutCopiedTimer);
    act(() => {
      vi.advanceTimersByTime(3000); // would throw/warn if a live timer touched the unmounted card
    });
    vi.useRealTimers();
  });

  it('keeps its accessible name, is not itself a live region, and the polite status announces once', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    renderCard();
    await press();
    expect(button().getAttribute('aria-label')).toBe('Copy link to this sky');
    expect(button().closest('[aria-live], [role="status"], [role="alert"]')).toBeNull();
    expect(button().hasAttribute('aria-live')).toBe(false);
    expect(status()).toBe('Link copied'); // the sr-only status, unchanged (the visible "Copied" is not announced)
    // exactly one live region says anything about copying: the sr-only status
    const copyRegions = Array.from(container.querySelectorAll('[aria-live]')).filter((el) => /cop/i.test(el.textContent ?? ''));
    expect(copyRegions.map((el) => el.getAttribute('data-testid'))).toEqual(['sky-copy-status']);
  });

  it('reserves the width of the longer label and is at least 24 px tall by padding', () => {
    renderCard();
    const classes = button().className;
    expect(classes).toMatch(/\bmin-w-\[\d+(\.\d+)?rem\]/);
    expect(classes).toMatch(/\btext-center\b/);
    expect(classes).toMatch(/\bpy-1\b/); // 11 px * 1.375 line + 2 * 4 px + 2 px border = 25.1 px
    expect(classes).not.toMatch(/\bpy-0\.5\b/);
    expect(classes).toMatch(/\btext-\[11px\]/); // the font did not change
  });

  it('has a success colour only while it says Copied', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    renderCard();
    expect(button().className).not.toMatch(/emerald/);
    await press();
    expect(button().className).toMatch(/text-emerald-300/);
  });

  it('stays "Copy link" and shows the fallback input when the clipboard rejects', async () => {
    setClipboard(vi.fn().mockRejectedValue(new Error('denied')));
    renderCard();
    await press();
    expect(button().textContent).toBe('Copy link');
    expect(status()).toBe('');
    expect(container.querySelector('input[readonly]')).not.toBeNull();
  });
});
