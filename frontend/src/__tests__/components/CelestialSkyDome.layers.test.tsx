/**
 * W2-B dome layers. The canvas context under happy-dom cannot hold pixels,
 * so these tests assert the switches, the load gate, and the existing
 * planet/star text. skyLayer is mocked; the real buffer tests live in
 * skyLayer.test.ts.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import type { ConstellationLines, Star } from '../../lib/sky';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const starsBox: { resolve: (stars: Star[]) => void } = {
  resolve: () => {
    throw new Error('stars resolver missing');
  },
};
const linesBox: { resolve: (lines: ConstellationLines) => void } = {
  resolve: () => {
    throw new Error('lines resolver missing');
  },
};

vi.mock('../../lib/sky', async () => {
  const actual = await vi.importActual<typeof import('../../lib/sky')>('../../lib/sky');
  return {
    ...actual,
    loadStars: vi.fn(
      () =>
        new Promise<Star[]>((resolve) => {
          starsBox.resolve = resolve;
        }),
    ),
    loadConstellationLines: vi.fn(
      () =>
        new Promise<ConstellationLines>((resolve) => {
          linesBox.resolve = resolve;
        }),
    ),
  };
});

vi.mock('../../lib/skyLayer', () => ({
  buildSkyLayer: vi.fn((request: { size: number }) => {
    const grid = Math.max(1, Math.round(request.size));
    return {
      stars: new Uint8ClampedArray(grid * grid * 4),
      figures: [],
      ecliptic: [],
    };
  }),
}));

import CelestialSkyDome from '../../components/UI/CelestialSkyDome';
import { buildSkyLayer } from '../../lib/skyLayer';

const mockNightSkyResponse = {
  timestamp_utc: '2026-10-22T02:00:00Z',
  observer: {
    latitude: 37.7749,
    longitude: -122.4194,
    local_sidereal_time_deg: 298.11,
    local_sidereal_time_hms: '19:52:26',
  },
  moon: {
    altitude: 10,
    azimuth: 80,
    phase_name: 'Waning Crescent',
    illumination: 22.6,
    visible: true,
    sign: 'Cancer',
  },
  planets: [
    {
      id: 'jupiter',
      name: 'Jupiter',
      glyph: '♃',
      altitude: 58.2,
      azimuth: 142.1,
      right_ascension: 92.1,
      declination: 22.4,
      longitude_ecliptic: 91.5,
      sign: 'Cancer',
      sign_glyph: '♋',
      sign_degree: 1.5,
      visible: true,
      color: '#a855f7',
      esoteric_quality: 'Guru · Expansive Grace',
    },
  ],
  visible_planets_count: 1,
  sacred_stars: [
    {
      id: 'sirius',
      name: 'Sirius (Mrigavyadha)',
      sanskrit: 'मृगव्याध',
      altitude: 35.8,
      azimuth: 122.4,
      magnitude: -1.46,
      visible: true,
      color: '#a6d8ff',
      nakshatra: 'Ardra',
      quality: 'Supreme Cosmic Fire',
      zenith_distance: 54.2,
    },
  ],
  visible_stars_count: 1,
  provenance: { observer: 'computed' },
};

const noop = () => {};
const stubCtx = () =>
  ({
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
    createRadialGradient: () =>
      ({
        addColorStop: noop,
      }) as unknown as CanvasGradient,
    save: noop,
    restore: noop,
    setTransform: noop,
    putImageData: noop,
    drawImage: noop,
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  }) as unknown as CanvasRenderingContext2D;

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  const canvas2d: { getContext(contextId: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(canvas2d, 'getContext').mockReturnValue(stubCtx());
  global.fetch = vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockNightSkyResponse),
    } as Response),
  );
  vi.mocked(buildSkyLayer).mockClear();
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.restoreAllMocks();
});

function switchButton(testId: string): HTMLButtonElement {
  const host = container.querySelector(`[data-testid="${testId}"]`);
  const button = host?.querySelector('button');
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error(`missing switch ${testId}`);
  }
  return button;
}

describe('CelestialSkyDome catalogue layers', () => {
  it('shows the three layer switches on, and they toggle', async () => {
    await act(async () => {
      root.render(<CelestialSkyDome latitude={37.7749} longitude={-122.4194} />);
    });
    expect(container.textContent).toContain('Jupiter');
    expect(container.textContent).toContain('Sirius');
    expect(container.textContent).toContain('Catalogue');
    expect(container.textContent).toContain('Figures');
    expect(container.textContent).toContain('Ecliptic');
    for (const id of ['sky-switch-catalogue', 'sky-switch-figures', 'sky-switch-ecliptic']) {
      const button = switchButton(id);
      expect(button.getAttribute('aria-checked')).toBe('true');
      await act(async () => {
        button.click();
      });
      expect(button.getAttribute('aria-checked')).toBe('false');
    }
  });

  it('draws the computed ecliptic before the catalogue arrives, then adds the catalogue layer', async () => {
    await act(async () => {
      root.render(<CelestialSkyDome latitude={37.7749} longitude={-122.4194} />);
    });
    const canvas = container.querySelector('[data-testid="celestial-sky-dome-canvas"]');
    expect(canvas?.getAttribute('data-sky-layers')).toBe('pending');

    // The ecliptic does not depend on either lazy chunk.
    expect(buildSkyLayer).toHaveBeenCalled();
    const firstRequest = vi.mocked(buildSkyLayer).mock.calls[0][0];
    expect(firstRequest.stars).toHaveLength(0);
    expect(firstRequest.showEcliptic).toBe(true);

    const stars: Star[] = [{ hr: 1, ra: 0, dec: 45, v: 4, bv: null }];
    const lines: ConstellationLines = {
      crosswalk: 'test',
      tolerance_arcsec: 180,
      constellations: {},
    };
    await act(async () => {
      starsBox.resolve(stars);
      linesBox.resolve(lines);
    });
    expect(canvas?.getAttribute('data-sky-layers')).toBe('ready');
    const lastRequest = vi.mocked(buildSkyLayer).mock.calls[vi.mocked(buildSkyLayer).mock.calls.length - 1]?.[0];
    expect(lastRequest?.stars).toHaveLength(1);
  });

  it('labels computed and decorative layers honestly in the footer', async () => {
    await act(async () => {
      root.render(<CelestialSkyDome latitude={37.7749} longitude={-122.4194} />);
    });
    const footer = container.querySelector('[data-testid="sky-layer-footer"]');
    if (!(footer instanceof HTMLElement)) throw new Error('footer missing');
    for (const label of [
      'Star and planet positions',
      'Ecliptic line',
      'Constellation figures',
      'Twinkle',
    ]) {
      expect(footer.textContent).toContain(label);
    }
    // The precession-only sentence stays scoped to the star catalogue.
    expect(footer.textContent).toContain(
      'precession only; proper motion, nutation and aberration ignored',
    );
    // W3-D2a: the live path is geocentric, so the dome says so.
    expect(footer.textContent).toContain('geocentric');
    expect(footer.querySelectorAll('[data-provenance="computed"]')).toHaveLength(2);
    expect(footer.querySelectorAll('[data-provenance="decorative"]')).toHaveLength(2);
  });
});
