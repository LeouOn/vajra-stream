/**
 * Unit tests for ScalarWaveVisualizer — Living Mandala and 2D wave fields.
 */
import React, { createRef } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import ScalarWaveVisualizer, {
  type ScalarVizAPI,
  MODES,
  ELEMENT_HUES,
} from '../../components/2D/ScalarWaveVisualizer';

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({
    scalarStatus: { rate: 528.0, coherence: 0.92 },
  }),
}));

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
});

describe('ScalarWaveVisualizer', () => {
  it('exports canonical modes and element hues', () => {
    expect(MODES).toContain('living');
    expect(MODES).toContain('interference');
    expect(MODES).toContain('spiral');
    expect(MODES).toContain('standing');
    expect(MODES).toContain('particle-storm');

    expect(ELEMENT_HUES.Fire).toBe(25);
    expect(ELEMENT_HUES.Water).toBe(200);
    expect(ELEMENT_HUES.Earth).toBe(60);
    expect(ELEMENT_HUES.Air).toBe(270);
    expect(ELEMENT_HUES.Wood).toBe(130);
    expect(ELEMENT_HUES.Metal).toBe(220);
    expect(ELEMENT_HUES.Cosmic).toBe(280);
  });

  it('renders a canvas element and mounts cleanly', async () => {
    await act(async () => {
      root.render(<ScalarWaveVisualizer initialMode="living" />);
    });
    const canvas = container.querySelector('canvas');
    expect(canvas).not.toBeNull();
  });

  it('exposes imperative ScalarVizAPI methods through forwardRef', async () => {
    const ref = createRef<ScalarVizAPI>();
    await act(async () => {
      root.render(<ScalarWaveVisualizer ref={ref} initialMode="living" />);
    });

    expect(ref.current).not.toBeNull();
    expect(typeof ref.current?.setElementMood).toBe('function');
    expect(typeof ref.current?.setHealingMood).toBe('function');
    expect(typeof ref.current?.triggerCrystalLayer).toBe('function');
    expect(typeof ref.current?.triggerBlessingRipple).toBe('function');
    expect(typeof ref.current?.triggerMeritParticle).toBe('function');

    // Test calling methods without error
    act(() => {
      ref.current?.setElementMood('Fire');
      ref.current?.setHealingMood(true);
      ref.current?.triggerCrystalLayer(25);
      ref.current?.triggerBlessingRipple(280, { x: 100, y: 100 });
      ref.current?.triggerMeritParticle(60, 5);
      ref.current?.setHealingMood(false);
    });
  });
});
