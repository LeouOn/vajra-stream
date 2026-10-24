/**
 * W3-I: the mini globe draws a scrubbed (frozen) earth state at exactly that instant, and still advances a live
 * one with Earth's rotation. Observed through the sub-solar point handed to `nightFactorMask`; the canvas context
 * is a stub (the exact night mask is pinned in orthographic-night.test.ts).
 *
 * TEARDOWN RULE (W3-A2): the 110 m land is a dynamic import; it is held behind a gate this file never releases
 * during a test, and every root is unmounted inside act while the window is alive.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const LAND_GATE = vi.hoisted(() => new Promise<never>(() => undefined));
vi.mock('../../data/land-110m.json', async () => LAND_GATE);

vi.mock('../../lib/orthographic', async () => {
  const actual = await vi.importActual<typeof import('../../lib/orthographic')>('../../lib/orthographic');
  return { ...actual, nightFactorMask: vi.fn(() => new Float32Array(0)) };
});

const SLICE = vi.hoisted(() => ({
  current: null as null | {
    status: 'ok';
    state: unknown;
    fetchedAt: number | null;
    error: null;
    frozen?: boolean;
  },
}));
vi.mock('../../stores/earthStateStore', () => ({ useEarthState: () => SLICE.current }));

import { MiniEarth } from '../../components/2D/MiniEarth';
import { wrapLon } from '../../lib/earth';
import { nightFactorMask } from '../../lib/orthographic';

const maskMock = vi.mocked(nightFactorMask);
const SHOWN_ISO = '2026-03-20T14:56:00.000Z';
const SHOWN_MS = Date.parse(SHOWN_ISO);
const SUN = { lat: 9.1e-5, lon: -39.649388 };
const RATE = 360.9856 / 86400; // Earth's rotation, degrees per second

function earthState() {
  return {
    at: SHOWN_ISO,
    ephemeris: 'swisseph',
    gast_deg: 39.6,
    sun: { id: 'sun', name: 'Sun', ra_deg: 0, dec_deg: SUN.lat, lat: SUN.lat, lon: SUN.lon },
    moon: { id: 'moon', name: 'Moon', ra_deg: 0, dec_deg: 11, lat: 11, lon: -22 },
    planets: [],
    provenance: {},
  };
}

/** A 2d context that accepts every call and hands back blank image data. */
function stubContext(): CanvasRenderingContext2D {
  const noop = () => undefined;
  return new Proxy({} as Record<string, unknown>, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      if (prop === 'createImageData') {
        return (w: number, h: number) => ({ data: new Uint8ClampedArray(w * h * 4), width: w, height: h });
      }
      return noop;
    },
    set(target, prop: string, value) {
      target[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

function mount(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root!.render(<MiniEarth isActive={false} size="small" />);
  });
}

/** The sub-solar point of the most recent night-mask computation. */
function lastSun(): { lat: number; lon: number } {
  const call = maskMock.mock.calls[maskMock.mock.calls.length - 1] as unknown as [unknown, { lat: number; lon: number }];
  return call[1];
}

beforeEach(() => {
  vi.useFakeTimers();
  // the wall clock is 5 minutes after the shown instant
  vi.setSystemTime(new Date(SHOWN_MS + 5 * 60_000));
  maskMock.mockClear();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
    (() => stubContext()) as unknown as typeof HTMLCanvasElement.prototype.getContext,
  );
});

afterEach(() => {
  if (root !== null) act(() => root!.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
  vi.useRealTimers();
  document.body.innerHTML = '';
});

describe('MiniEarth: a frozen slice is drawn at its own instant', () => {
  it('uses the sub-solar point of the shown instant, unchanged, however long the wall clock runs', () => {
    SLICE.current = { status: 'ok', state: earthState(), fetchedAt: SHOWN_MS, error: null, frozen: true };
    mount();
    expect(maskMock).toHaveBeenCalled();
    expect(lastSun().lon).toBeCloseTo(SUN.lon, 9);
    expect(lastSun().lat).toBeCloseTo(SUN.lat, 9);
    act(() => {
      vi.advanceTimersByTime(120_000);
    });
    expect(lastSun().lon).toBeCloseTo(SUN.lon, 9);
  });

  it('still advances a LIVE state with Earth rotation (5 min after its instant, then 2 min more)', () => {
    SLICE.current = { status: 'ok', state: earthState(), fetchedAt: SHOWN_MS, error: null };
    mount();
    expect(lastSun().lon).toBeCloseTo(wrapLon(SUN.lon - RATE * 300), 6);
    act(() => {
      vi.advanceTimersByTime(120_000);
    });
    expect(lastSun().lon).toBeCloseTo(wrapLon(SUN.lon - RATE * 420), 6);
  });
});
