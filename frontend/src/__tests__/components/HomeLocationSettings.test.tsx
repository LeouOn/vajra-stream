/**
 * HomeLocationSettings — the home location workings are sealed at.
 *
 * fetch is stubbed with a tiny in-memory /settings/location; geolocation
 * is stubbed per test. Coordinates must only ever be shown rounded.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import HomeLocationSettings from '../../components/Settings/HomeLocationSettings';
import { describeLocation, formatCoords, parseTypedCoords, roundCoord } from '../../lib/homeLocationApi';

interface Call { method: string; path: string; body: unknown }

let stored: Record<string, unknown> | null = null;
let calls: Call[] = [];
const DEFAULT = { latitude: 37.7749, longitude: -122.4194 };

function reply(status: number, body: unknown) {
  return { ok: status < 400, status, json: async () => body };
}

const fetchStub = vi.fn(async (url: string, init?: RequestInit) => {
  const method = init?.method ?? 'GET';
  const path = String(url).replace(/^.*\/api\/v1/, '');
  const body: unknown = init?.body ? JSON.parse(String(init.body)) : null;
  calls.push({ method, path, body });
  if (path !== '/settings/location') return reply(404, { detail: 'nope' });
  if (method === 'PUT') {
    const b = body as Record<string, unknown>;
    if (typeof b.place === 'string') {
      if (b.place.startsWith('Xyzzy')) return reply(400, { detail: `could not find a place called '${b.place}'` });
      stored = { latitude: 35.6762, longitude: 139.6503, label: b.place, source: 'geocoded' };
    } else {
      stored = { latitude: b.latitude, longitude: b.longitude, label: b.label ?? null, source: b.source };
    }
  }
  if (method === 'DELETE') stored = null;
  return reply(200, { location: stored, default: DEFAULT, display: null });
});

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  stored = null;
  calls = [];
  fetchStub.mockClear();
  vi.stubGlobal('fetch', fetchStub);
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
  vi.unstubAllGlobals();
});

async function flush() {
  await act(async () => {
    for (let i = 0; i < 5; i += 1) await Promise.resolve();
  });
}

async function renderPanel() {
  act(() => { root.render(<HomeLocationSettings />); });
  await flush();
}

function lastCall(): Call | undefined {
  return calls[calls.length - 1];
}

function current(): string {
  return container.querySelector('[data-testid="home-location-current"]')?.textContent ?? '';
}

function typeInto(value: string) {
  const input = container.querySelector('input[aria-label="Place name or coordinates"]') as HTMLInputElement;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

async function click(testId: string) {
  const button = container.querySelector(`[data-testid="${testId}"]`) as HTMLButtonElement;
  act(() => { button.click(); });
  await flush();
}

describe('homeLocationApi helpers', () => {
  it('rounds coordinates to one decimal for display', () => {
    expect(roundCoord(27.717245)).toBe(27.7);
    expect(formatCoords(27.717245, 85.323961)).toBe('27.7°, 85.3°');
    expect(describeLocation({ latitude: 27.717245, longitude: 85.323961, label: 'Kathmandu', source: 'browser' }))
      .toBe('Kathmandu (27.7°, 85.3°)');
    expect(describeLocation({ latitude: -33.8688, longitude: 151.2093, label: null, source: 'typed' }))
      .toBe('-33.9°, 151.2°');
  });

  it('tells typed coordinates from place names', () => {
    expect(parseTypedCoords('27.7, 85.3')).toEqual({ latitude: 27.7, longitude: 85.3 });
    expect(parseTypedCoords('-33.87 151.21')).toEqual({ latitude: -33.87, longitude: 151.21 });
    expect(parseTypedCoords('Kathmandu')).toBeNull();
    expect(parseTypedCoords('95, 10')).toBeNull();
  });
});

describe('HomeLocationSettings', () => {
  it('says the default location is used when none is set', async () => {
    await renderPanel();
    expect(calls[0]).toMatchObject({ method: 'GET', path: '/settings/location' });
    expect(current()).toContain('Not set');
    expect(current()).toContain('37.8°, -122.4°');
    const clear = container.querySelector('[data-testid="home-location-clear"]') as HTMLButtonElement;
    expect(clear.disabled).toBe(true);
  });

  it('geocodes a typed place name', async () => {
    await renderPanel();
    typeInto('Tokyo');
    await click('home-location-save');
    expect(lastCall()).toMatchObject({ method: 'PUT', body: { place: 'Tokyo' } });
    expect(current()).toContain('Tokyo (35.7°, 139.7°)');
    expect(current()).toContain('looked up');
    expect(current()).not.toContain('35.6762');
  });

  it('saves typed coordinates as typed', async () => {
    await renderPanel();
    typeInto('27.717245, 85.323961');
    await click('home-location-save');
    expect(lastCall()).toMatchObject({
      method: 'PUT',
      body: { latitude: 27.717245, longitude: 85.323961, source: 'typed' },
    });
    expect(current()).toContain('27.7°, 85.3°');
    expect(current()).not.toContain('27.717');
  });

  it('uses the browser location', async () => {
    const getCurrentPosition = vi.fn((ok: PositionCallback) => {
      ok({ coords: { latitude: 51.507351, longitude: -0.127758 } } as GeolocationPosition);
    });
    vi.stubGlobal('navigator', { ...navigator, geolocation: { getCurrentPosition } });
    await renderPanel();
    await click('home-location-browser');
    expect(getCurrentPosition).toHaveBeenCalled();
    expect(lastCall()).toMatchObject({ method: 'PUT', body: { latitude: 51.507351, source: 'browser' } });
    expect(current()).toContain('51.5°, -0.1°');
    expect(current()).toContain('from this browser');
  });

  it('shows a geocoding failure and keeps the old value', async () => {
    await renderPanel();
    typeInto('Xyzzy Nowhere');
    await click('home-location-save');
    expect(container.querySelector('[data-testid="home-location-error"]')?.textContent).toContain('could not find');
    expect(current()).toContain('Not set');
  });

  it('clears the home location', async () => {
    stored = { latitude: 48.8566, longitude: 2.3522, label: 'Paris', source: 'typed' };
    await renderPanel();
    expect(current()).toContain('Paris (48.9°, 2.4°)');
    await click('home-location-clear');
    expect(lastCall()).toMatchObject({ method: 'DELETE' });
    expect(current()).toContain('Not set');
  });
});
