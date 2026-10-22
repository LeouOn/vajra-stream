import React from 'react';
import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import { MiniEarth } from '../../components/2D/MiniEarth';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/* Headless environment: the canvas 2d context is unavailable, so the draw
 * path is inert; these tests pin the mounting contract, the unavailable
 * label, the canvas size and the timer lifecycle (fake timers). */

const STATE = {
  at: '2026-10-22T02:00:00Z',
  ephemeris: 'de432s',
  gast_deg: 60.525,
  sun: { id: 'sun', name: 'Sun', ra_deg: 206.66, dec_deg: -11.008, lat: -11.008, lon: 146.133 },
  moon: { id: 'moon', name: 'Moon', ra_deg: 338.5, dec_deg: -8.166, lat: -8.166, lon: -82.025 },
  planets: [],
  provenance: {},
};

function mount(element: React.ReactElement): { container: HTMLDivElement; root: Root } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(element);
  });
  return { container, root };
}

describe('MiniEarth (headless: canvas 2d context unavailable)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  test('mounts without a 2d context and shows the unavailable label', () => {
    const { container } = mount(<MiniEarth isActive={false} size="small" />);
    const canvas = container.querySelector('canvas');
    expect(canvas).not.toBeNull();
    expect(container.textContent).toContain('ephemeris unavailable');
  });

  test('with a state it shows no unavailable label after a tick', () => {
    const { container } = mount(<MiniEarth isActive={false} size="small" state={STATE} />);
    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(container.textContent).not.toContain('unavailable');
  });

  test('stops its 1 Hz redraw timer on unmount', () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval');
    const { root } = mount(<MiniEarth isActive size="large" />);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      root.unmount();
    });
    expect(clearSpy).toHaveBeenCalled();
  });

  test('renders a canvas of the requested size', () => {
    const { container } = mount(<MiniEarth isActive size="large" />);
    const canvas = container.querySelector('canvas');
    expect(canvas?.getAttribute('width')).toBe('320');
    expect(canvas?.getAttribute('height')).toBe('320');
  });
});
