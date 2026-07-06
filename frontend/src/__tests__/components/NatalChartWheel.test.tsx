/**
 * Regression tests for NatalChartWheel midheaven-asymmetry fix.
 *
 * Before the fix, the wheel threw `Cannot read properties of undefined (reading
 * 'longitude')` whenever the backend returned `positions.ascendant` but
 * `positions.midheaven` was missing — the early-return at line 266 only checked
 * ascendant.longitude, so the AngleMark lines 312 and 322 crashed.
 *
 * These tests pin the contract: when midheaven is absent, the wheel still
 * renders the ASC/DSC marks and the SVG without crashing.
 *
 * Pattern follows AstrologyExtractionPanel.test.tsx: raw createRoot + act
 * with ConfigProvider wrapper, no @testing-library (not in deps).
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider, theme as antdTheme } from 'antd';

import NatalChartWheel from '../../components/UI/NatalChartWheel';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
  vi.restoreAllMocks();
});

function renderWheel(data: any) {
  let thrown: unknown = null;
  act(() => {
    try {
      root.render(
        <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
          <NatalChartWheel data={data} name="Test Chart" />
        </ConfigProvider>,
      );
    } catch (e) {
      thrown = e;
    }
  });
  return thrown;
}

describe('NatalChartWheel — midheaven-asymmetry regression', () => {
  const baseWestern = {
    dominant_element: 'Earth',
    dominant_modality: 'Cardinal',
    positions: {
      ascendant: {
        longitude: 280.0,
        sign: 'Capricorn',
        degree: 10.0,
        formatted: 'Capricorn 10.00°',
        retrograde: false,
      },
      sun: {
        longitude: 280.0,
        sign: 'Capricorn',
        degree: 10.0,
        formatted: 'Capricorn 10.00°',
        retrograde: false,
      },
    },
    houses: {},
  };

  it('renders without crashing when midheaven is missing from positions', () => {
    // The pre-fix code threw "Cannot read properties of undefined (reading 'longitude')"
    // when reading positions.midheaven.longitude at line 312. After the fix the MC
    // and IC AngleMarks are guarded by `positions.midheaven && (...)`.
    const data = { western: baseWestern };
    const thrown = renderWheel(data);
    expect(thrown).toBeNull();
  });

  it('shows the chart title even when midheaven is absent', () => {
    const data = { western: baseWestern };
    renderWheel(data);
    expect(container.textContent).toMatch(/Test Chart/);
  });

  it('still falls back to "Chart wheel unavailable" when ascendant is also missing', () => {
    const data = {
      western: {
        ...baseWestern,
        positions: { sun: baseWestern.positions.sun },
      },
    };
    renderWheel(data);
    expect(container.textContent).toMatch(/Chart wheel unavailable/);
  });

  it('renders full wheel when both ascendant and midheaven are present', () => {
    const fullWestern = {
      ...baseWestern,
      positions: {
        ...baseWestern.positions,
        midheaven: {
          longitude: 10.0,
          sign: 'Aries',
          degree: 10.0,
          formatted: 'Aries 10.00°',
          retrograde: false,
        },
      },
    };
    const data = { western: fullWestern };
    const thrown = renderWheel(data);
    expect(thrown).toBeNull();
    expect(container.textContent).toMatch(/Test Chart/);
  });

  it('handles missing positions entirely (no ascendant, no midheaven)', () => {
    const data = { western: { ...baseWestern, positions: {} } };
    const thrown = renderWheel(data);
    expect(thrown).toBeNull();
    expect(container.textContent).toMatch(/Chart wheel unavailable/);
  });
});