/**
 * Cosmic Clock sky states.
 *
 * An empty ephemeris payload used to leave the page on
 * "Computing ephemeris…" forever. Illumination at or below 1% used to be
 * scaled by 100 because the UI treated the 0–100 API as a fraction.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider, theme as antdTheme } from 'antd';
import { MemoryRouter } from 'react-router-dom';

const fetchSpy = vi.fn();

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body };
}

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let geolocation: Geolocation | undefined;

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  geolocation = navigator.geolocation;
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: {
      getCurrentPosition: (_ok: PositionCallback, err?: PositionErrorCallback) => {
        err?.({ code: 1 } as GeolocationPositionError);
      },
    },
  });
  fetchSpy.mockReset();
  vi.stubGlobal('fetch', fetchSpy);
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
  vi.restoreAllMocks();
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: geolocation,
  });
  vi.unstubAllGlobals();
});

import AstrologyPanel from '../../components/UI/AstrologyPanel';

describe('AstrologyPanel sky', () => {
  it('says the ephemeris returned no chart instead of spinning forever', async () => {
    fetchSpy.mockImplementation(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes('/astrology/current')) return jsonResponse({ astrology: {} });
      if (url.includes('/astrology/charts')) return jsonResponse([]);
      return jsonResponse({});
    });
    await act(async () => {
      root.render(
        <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
          <MemoryRouter>
            <AstrologyPanel />
          </MemoryRouter>
        </ConfigProvider>,
      );
    });
    expect(container.textContent).toContain('Ephemeris returned no western chart.');
    expect(container.textContent).not.toContain('Computing ephemeris coordinates…');
  });

  it('shows a 1% moon as 1.0% and the tightest aspect in the reading', async () => {
    fetchSpy.mockImplementation(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes('/astrology/current')) {
        return jsonResponse({
          astrology: {
            datetime: '2026-10-03T12:00:00+00:00',
            location: { latitude: 37.77, longitude: -122.42 },
            moon_phase: { phase_name: 'Waxing Crescent', illumination: 1 },
            western: {
              dominant_element: 'Earth',
              dominant_modality: 'Cardinal',
              positions: {
                ascendant: { longitude: 280, sign: 'Capricorn', degree: 10, formatted: 'Capricorn 10.00°' },
                sun: { longitude: 10, sign: 'Aries', degree: 10, formatted: 'Aries 10.00°' },
              },
              elements: { Fire: 1, Earth: 4, Air: 0, Water: 0 },
              aspects: [
                { planet1: 'mars', planet2: 'saturn', aspect: 'Square', exactness: 0.2, description: 'Mars Square Saturn' },
                { planet1: 'sun', planet2: 'mercury', aspect: 'Conjunction', exactness: 0.95, description: 'Sun Conjunction Mercury' },
              ],
            },
          },
        });
      }
      if (url.includes('/astrology/charts')) return jsonResponse([]);
      return jsonResponse({});
    });
    await act(async () => {
      root.render(
        <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
          <MemoryRouter>
            <AstrologyPanel />
          </MemoryRouter>
        </ConfigProvider>,
      );
    });
    expect(container.textContent).toContain('1.0%');
    expect(container.textContent).toContain('Cardinal Earth');
    expect(container.textContent).toContain('Sun Conjunction Mercury');
    expect(container.querySelector('[data-testid="sky-reading"]')?.textContent).toContain('tightest Sun Conjunction Mercury');
    const techniques = Array.from(container.querySelectorAll('.ant-segmented-item-label')).map((el) => el.textContent);
    expect(techniques).toContain('Techniques');
  });
});
