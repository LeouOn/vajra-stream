// @vitest-environment happy-dom
/**
 * LazySacredMandala always hands SacredMandala an `audioSpectrum` array.
 *
 * It used to omit the (required) prop; SacredMandala's frame loop evaluates
 * `isPlaying && audioSpectrum.length > 0`, so once audio started playing on
 * the Astrology wheel tab every frame threw "Cannot read properties of
 * undefined (reading 'length')".
 */
import React, { act } from 'react';
import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';

const received: Array<Record<string, unknown>> = [];

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => <div data-testid="r3f-canvas">{children}</div>,
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Stars: () => null,
  Environment: () => null,
}));

vi.mock('../../components/3D/SacredMandala', () => ({
  default: (props: Record<string, unknown>) => {
    received.push(props);
    return null;
  },
}));

let root: Root;
let container: HTMLDivElement;

beforeAll(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  // ambientLight / pointLight are R3F intrinsics; react-dom warns about them.
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterAll(() => {
  act(() => root.unmount());
  container.remove();
  vi.restoreAllMocks();
});

describe('LazySacredMandala', () => {
  it('passes an empty spectrum when the caller has none', async () => {
    const { default: LazySacredMandala } = await import('../../components/UI/LazySacredMandala');
    act(() => root.render(<LazySacredMandala isPlaying frequency={528} />));
    const props = received[received.length - 1];
    expect(Array.isArray(props?.audioSpectrum)).toBe(true);
    expect(props?.audioSpectrum).toEqual([]);
    expect(props?.isPlaying).toBe(true);
    expect(props?.frequency).toBe(528);
  });

  it('forwards a live spectrum when given one', async () => {
    const { default: LazySacredMandala } = await import('../../components/UI/LazySacredMandala');
    act(() => root.render(<LazySacredMandala isPlaying frequency={432} audioSpectrum={[0.2, 0.4]} />));
    expect(received[received.length - 1]?.audioSpectrum).toEqual([0.2, 0.4]);
  });
});
