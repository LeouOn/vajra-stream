// @vitest-environment happy-dom
/**
 * W3-L1 — MiniEarth must redraw as soon as the selected instant changes, not
 * only on its next 1 Hz tick. Replacing the slice after a stable mount (a
 * scrub) must repaint without advancing any timer.
 */
import React, { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import type { EarthState } from '../../lib/earth';
import type { EarthStateSlice } from '../../stores/earthStateStore';

const sliceBox: { current: EarthStateSlice } = {
  current: { status: 'idle', state: null, fetchedAt: null, error: null },
};
vi.mock('../../stores/earthStateStore', () => ({
  useEarthState: () => sliceBox.current,
}));

import { MiniEarth } from '../../components/2D/MiniEarth';

const noop = () => {};

function earthState(at: string, sunLon: number): EarthState {
  return {
    at,
    ephemeris: 'de432s',
    gast_deg: 60,
    sun: { id: 'sun', name: 'Sun', ra_deg: 0, dec_deg: 10, lat: 10, lon: sunLon },
    moon: { id: 'moon', name: 'Moon', ra_deg: 0, dec_deg: -5, lat: -5, lon: -20 },
    planets: [],
    provenance: {},
  };
}

let container: HTMLDivElement;
let root: Root;
let draws: number;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  draws = 0;
  const ctx = {
    clearRect: () => {
      draws += 1;
    },
    save: noop,
    restore: noop,
    beginPath: noop,
    arc: noop,
    clip: noop,
    fillRect: noop,
    fill: noop,
    stroke: noop,
    moveTo: noop,
    lineTo: noop,
    closePath: noop,
    ellipse: noop,
    setTransform: noop,
    translate: noop,
    scale: noop,
    rotate: noop,
    createImageData: (width: number, height: number) => ({
      data: new Uint8ClampedArray(width * height * 4),
      width,
      height,
    }),
    putImageData: noop,
    drawImage: noop,
    globalCompositeOperation: 'source-over',
  } as unknown as CanvasRenderingContext2D;
  const proto: { getContext(id: '2d'): CanvasRenderingContext2D | null } = HTMLCanvasElement.prototype;
  vi.spyOn(proto, 'getContext').mockReturnValue(ctx);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.restoreAllMocks();
});

describe('MiniEarth redraw', () => {
  it('repaints immediately when the selected slice changes, without advancing time', async () => {
    sliceBox.current = { status: 'ok', state: earthState('2026-10-24T09:00:00Z', 146), fetchedAt: 1, error: null };
    await act(async () => {
      root.render(<MiniEarth isActive={false} size="small" />);
      // the 110 m land chunk loads asynchronously; let that paint happen
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    const before = draws;
    expect(before).toBeGreaterThan(0);

    // A scrub replaces the slice; no timer is advanced here.
    sliceBox.current = {
      status: 'ok',
      state: earthState('2026-10-24T15:00:00Z', 160),
      fetchedAt: Date.parse('2026-10-24T15:00:00Z'),
      error: null,
      frozen: true,
    };
    await act(async () => {
      root.render(<MiniEarth isActive={false} size="small" />);
    });

    expect(draws).toBeGreaterThan(before);
  });
});
