/**
 * W6-D1a: the strip canvas is focusable and moves the observer with the arrows.
 * The strip's pixel physics stays in WorldStrip.frozen.test.tsx (untouched).
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

const EARTH_SLICE = vi.hoisted(() => ({
  current: {
    status: 'ok' as const,
    state: {
      at: '2026-10-22T02:00:00Z',
      ephemeris: 'de432s',
      gast_deg: 60.525,
      sun: { id: 'sun', name: 'Sun', ra_deg: 206.66, dec_deg: -11.008, lat: -11.008, lon: 146.133 },
      moon: { id: 'moon', name: 'Moon', ra_deg: 338.5, dec_deg: -8.166, lat: -8.166, lon: -82.025 },
      planets: [],
      provenance: {},
    },
    fetchedAt: 1,
    error: null,
  },
}));
vi.mock('../../stores/earthStateStore', () => ({ useEarthState: () => EARTH_SLICE.current }));

import { WorldStrip } from '../../components/2D/WorldStrip';
import { useSkyStore } from '../../stores/skyStore';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const roots = new Set<Root>();
function mount(element: React.ReactElement): HTMLDivElement {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  roots.add(root);
  act(() => {
    root.render(element);
  });
  return container;
}
function canvas(container: HTMLElement): HTMLCanvasElement {
  const el = container.querySelector<HTMLCanvasElement>('[data-testid="world-strip"]');
  if (el === null) throw new Error('no strip canvas');
  return el;
}
function key(el: Element, name: string, shiftKey = false): KeyboardEvent {
  const event = new KeyboardEvent('keydown', { key: name, shiftKey, bubbles: true, cancelable: true });
  act(() => {
    el.dispatchEvent(event);
  });
  return event;
}

beforeEach(() => {
  useSkyStore.setState({ lat: DEFAULT_LAT, lng: DEFAULT_LNG, label: undefined, at: null });
});
afterEach(() => {
  act(() => {
    for (const root of roots) root.unmount();
  });
  roots.clear();
  document.body.innerHTML = '';
});

describe('keyboard observer', () => {
  test('the canvas is a labelled application and focusable', () => {
    const container = mount(<WorldStrip observer={{ lat: 36.1, lng: 139.4 }} onPick={() => undefined} />);
    const c = canvas(container);
    expect(c.getAttribute('tabindex')).toBe('0');
    expect(c.getAttribute('role')).toBe('application');
    expect(c.getAttribute('aria-label')).toContain('Arrow keys move the observer: 1 degree, Shift for 0.1 degree');
    expect(c.getAttribute('aria-label')).toContain('observer 36.1 N, 139.4 E');
  });

  test('arrows move 1 degree and preventDefault; Shift moves 0.1', () => {
    const picked: Array<[number, number]> = [];
    const container = mount(<WorldStrip observer={{ lat: 10, lng: 20 }} onPick={(lat, lng) => picked.push([lat, lng])} />);
    const c = canvas(container);
    const right = key(c, 'ArrowRight');
    expect(right.defaultPrevented).toBe(true);
    const up = key(c, 'ArrowUp');
    expect(up.defaultPrevented).toBe(true);
    key(c, 'ArrowLeft');
    key(c, 'ArrowDown');
    key(c, 'ArrowRight', true);
    expect(picked).toEqual([
      [10, 21],
      [11, 20],
      [10, 19],
      [9, 20],
      [10, 20.1],
    ]);
  });

  test('Alt/Ctrl/Meta arrows are left to the browser and move nothing', () => {
    const picked: Array<[number, number]> = [];
    const container = mount(<WorldStrip observer={{ lat: 10, lng: 20 }} onPick={(lat, lng) => picked.push([lat, lng])} />);
    const c = canvas(container);
    for (const modifier of ['altKey', 'ctrlKey', 'metaKey'] as const) {
      const event = new KeyboardEvent('keydown', { key: 'ArrowLeft', [modifier]: true, bubbles: true, cancelable: true });
      act(() => {
        c.dispatchEvent(event);
      });
      expect(event.defaultPrevented).toBe(false);
    }
    expect(picked).toEqual([]);
  });

  test('fine and coarse steps from a picked coordinate move only the commanded axis', () => {
    const picked: Array<[number, number]> = [];
    const observer = { lat: 36.11111, lng: 139.44444 };
    const container = mount(<WorldStrip observer={observer} onPick={(lat, lng) => picked.push([lat, lng])} />);
    const c = canvas(container);
    key(c, 'ArrowRight', true);
    key(c, 'ArrowUp', true);
    key(c, 'ArrowRight');
    key(c, 'ArrowUp');
    expect(picked[0][0]).toBe(observer.lat);
    expect(picked[0][1]).toBeCloseTo(139.54444, 9);
    expect(picked[1][0]).toBeCloseTo(36.21111, 9);
    expect(picked[1][1]).toBe(observer.lng);
    expect(picked[2][0]).toBe(observer.lat);
    expect(picked[2][1]).toBeCloseTo(140.44444, 9);
    expect(picked[3][0]).toBeCloseTo(37.11111, 9);
    expect(picked[3][1]).toBe(observer.lng);
  });

  test('latitude clamps at +-90 and other keys are ignored', () => {
    const picked: Array<[number, number]> = [];
    const north = mount(<WorldStrip observer={{ lat: 90, lng: 0 }} onPick={(lat, lng) => picked.push([lat, lng])} />);
    key(canvas(north), 'ArrowUp');
    expect(picked).toEqual([[90, 0]]);
    const south = mount(<WorldStrip observer={{ lat: -90, lng: 0 }} onPick={(lat, lng) => picked.push([lat, lng])} />);
    key(canvas(south), 'ArrowDown');
    expect(picked).toEqual([[90, 0], [-90, 0]]);
    const other = key(canvas(north), 'a');
    expect(other.defaultPrevented).toBe(false);
    expect(picked).toHaveLength(2);
  });

  test('longitude wraps through the store', () => {
    function Harness(): React.ReactElement {
      const lat = useSkyStore((s) => s.lat);
      const lng = useSkyStore((s) => s.lng);
      return (
        <WorldStrip
          observer={{ lat, lng }}
          onPick={(nextLat, nextLng) => useSkyStore.getState().setObserver(nextLat, nextLng)}
        />
      );
    }
    const container = mount(<Harness />);
    act(() => {
      useSkyStore.setState({ lat: 0, lng: 179, label: undefined, at: null });
    });
    key(canvas(container), 'ArrowRight');
    expect(useSkyStore.getState().lng).toBe(-180);
  });

  test('the label says day or night at the observer from the strip night factor', () => {
    const day = mount(<WorldStrip observer={{ lat: 0, lng: 0 }} sun={{ lat: 0, lon: 0 }} onPick={() => undefined} />);
    expect(canvas(day).getAttribute('aria-label')).toContain('it is day there');
    const night = mount(<WorldStrip observer={{ lat: 0, lng: 0 }} sun={{ lat: 0, lon: 180 }} onPick={() => undefined} />);
    expect(canvas(night).getAttribute('aria-label')).toContain('it is night there');
  });

  test('the unavailable overlay uses 11px and the canvas carries a focus-visible outline', () => {
    const container = mount(<WorldStrip observer={{ lat: 0, lng: 0 }} sun={null} onPick={() => undefined} />);
    const overlay = container.querySelector('[data-testid="world-strip-unavailable"]');
    expect(overlay?.className).toContain('text-[11px]');
    expect(canvas(container).className).toContain('focus-visible:outline');
  });
});
