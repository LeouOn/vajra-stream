/**
 * S3 — VisualizerTab must render 3D sacred geometry large enough to fill
 * most of the canvas. Pre-fix the Canvas camera sat at z=20 with a flower-
 * of-life pattern of radius 6, giving the geometry only ~7-9% of canvas
 * height (mostly empty upper-center cluster + 65% dark void below).
 *
 * Fix: move camera closer (z=8-10) so the geometry is the visualizer's
 * centerpiece, not a postage stamp in the middle of a void. This test
 * pins the camera distance contract — any future regression that pushes
 * the camera further out (or shrinks the geometry) will be caught here.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import VisualizerTab from '../../routes/Practice/VisualizerTab';

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children, camera, className }: { children: React.ReactNode; camera?: { position?: [number, number, number]; fov?: number }; className?: string }) => (
    <div data-testid="r3f-canvas" data-camera={JSON.stringify(camera || {})} className={className}>
      {children}
    </div>
  ),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Stars: () => null,
  Environment: () => null,
}));

vi.mock('../../components/3D/SacredGeometry', () => ({
  default: () => null,
}));

vi.mock('../../components/3D/SacredMandala', () => ({
  default: () => null,
}));

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({ audioSpectrum: [] }),
}));

vi.mock('../../stores/audioStore', () => ({
  useAudioStore: (selector?: (s: unknown) => unknown) => selector ? selector({ isPlaying: false, frequency: 528 }) : { isPlaying: false, frequency: 528 },
}));

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
});

describe('VisualizerTab — camera distance (S3)', () => {
  it('camera position z is close enough that 3D geometry fills the canvas', async () => {
    await act(async () => {
      root.render(<VisualizerTab />);
      await new Promise((r) => setTimeout(r, 100));
    });
    const canvas = container.querySelector('[data-testid="r3f-canvas"]') as HTMLElement;
    expect(canvas, 'R3F Canvas should render after Suspense resolves').not.toBeNull();
    const cam = JSON.parse(canvas.getAttribute('data-camera') || '{}');
    expect(cam.position).toBeDefined();
    const z = cam.position[2];
    expect(z).toBeLessThanOrEqual(10);
    expect(z).toBeGreaterThanOrEqual(4);
  });

  it('canvas has full-screen layout (w-full h-full) so geometry is centered', async () => {
    await act(async () => {
      root.render(<VisualizerTab />);
    });
    const canvas = container.querySelector('[data-testid="r3f-canvas"]') as HTMLElement;
    expect(canvas?.className).toContain('w-full');
    expect(canvas?.className).toContain('h-full');
  });
});
