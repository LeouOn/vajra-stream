/**
 * W3-I: the flat strip draws a scrubbed (frozen) earth state at exactly that instant, and still advances a live
 * one with Earth's rotation. The draw path is observed through the arguments `drawWorldStrip` receives (the
 * canvas context is a stub; the strip's pixel physics is pinned in equirect.test.ts).
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

vi.mock('../../lib/equirect', async () => {
  const actual = await vi.importActual<typeof import('../../lib/equirect')>('../../lib/equirect');
  return { ...actual, drawWorldStrip: vi.fn() };
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

import { WorldStrip } from '../../components/2D/WorldStrip';
import { wrapLon } from '../../lib/earth';
import { drawWorldStrip } from '../../lib/equirect';

const drawMock = vi.mocked(drawWorldStrip);
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

let root: Root | null = null;
let container: HTMLDivElement | null = null;

function mount(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root!.render(<WorldStrip />);
  });
}

/** The sub-solar point of the most recent draw. */
function lastSun(): { lat: number; lon: number } {
  const call = drawMock.mock.calls[drawMock.mock.calls.length - 1];
  return (call[1] as { sun: { lat: number; lon: number } }).sun;
}

beforeEach(() => {
  vi.useFakeTimers();
  // the wall clock is 5 minutes after the shown instant
  vi.setSystemTime(new Date(SHOWN_MS + 5 * 60_000));
  drawMock.mockReset();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({} as unknown as CanvasRenderingContext2D);
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((() => 0) as unknown as typeof window.requestAnimationFrame);
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

describe('WorldStrip: a frozen slice is drawn at its own instant', () => {
  it('draws the sub-solar point of the shown instant, unchanged, however long the wall clock runs', () => {
    SLICE.current = { status: 'ok', state: earthState(), fetchedAt: SHOWN_MS, error: null, frozen: true };
    mount();
    expect(drawMock).toHaveBeenCalled();
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
