/**
 * The Cosmic Clock computes the live sky for the saved home location when
 * there is one, and only asks the browser for its position when there isn't.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { installFetch, apiPath, flush, type FetchCall } from './domHelpers';

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: { playClick: vi.fn(), playTabChange: vi.fn(), playSuccess: vi.fn(), playError: vi.fn() },
}));

import AstrologyPanel from '../../components/UI/AstrologyPanel';

let root: Root | null = null;
let container: HTMLDivElement | null = null;
let calls: FetchCall[] = [];
const getCurrentPosition = vi.fn();

function mountWith(location: Record<string, unknown> | null) {
  ({ calls } = installFetch((url) => {
    const p = apiPath(url);
    if (p === '/settings/location') {
      return { body: { location, default: { latitude: 37.7749, longitude: -122.4194 }, display: null } };
    }
    if (p === '/astrology/charts') return { body: [] };
    return undefined;
  }));
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root?.render(<AstrologyPanel />));
}

const currentSkyQuery = () => {
  const call = calls.find((c) => apiPath(c.url).startsWith('/astrology/current'));
  return call ? new URLSearchParams(apiPath(call.url).split('?')[1]) : null;
};

beforeEach(() => {
  getCurrentPosition.mockReset();
  Object.defineProperty(navigator, 'geolocation', { value: { getCurrentPosition }, configurable: true });
});

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

describe('Cosmic Clock location', () => {
  it('uses the saved home location and does not ask the browser', async () => {
    mountWith({ latitude: 27.7172, longitude: 85.324, label: 'Kathmandu', source: 'typed' });
    await flush(50);
    const query = currentSkyQuery();
    expect(query?.get('latitude')).toBe('27.7172');
    expect(query?.get('longitude')).toBe('85.324');
    expect(getCurrentPosition).not.toHaveBeenCalled();
  });

  it('falls back to the browser position when no home location is saved', async () => {
    getCurrentPosition.mockImplementation((ok: (p: { coords: { latitude: number; longitude: number } }) => void) =>
      ok({ coords: { latitude: 51.5, longitude: -0.1 } }),
    );
    mountWith(null);
    await flush(50);
    expect(getCurrentPosition).toHaveBeenCalledTimes(1);
    expect(currentSkyQuery()?.get('latitude')).toBe('51.5');
  });
});
