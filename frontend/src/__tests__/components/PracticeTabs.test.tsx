/**
 * Tests for Practice tabs: MeditationTab and VisualizerTab.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter } from 'react-router-dom';
import MeditationTab from '../../routes/Practice/MeditationTab';
import VisualizerTab from '../../routes/Practice/VisualizerTab';

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({
    audioSpectrum: [0.1, 0.2, 0.3],
  }),
}));

vi.mock('../../stores/audioStore', () => ({
  useAudioStore: (selector?: (s: unknown) => unknown) =>
    selector
      ? selector({ isPlaying: false, frequency: 528.0 })
      : { isPlaying: false, frequency: 528.0 },
}));

vi.mock('../../hooks/useAmbientBowl', () => ({
  useAmbientBowl: () => ({
    start: vi.fn(),
    stop: vi.fn(),
    playing: false,
  }),
}));

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="r3f-canvas" className={className}>
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
  default: () => <div data-testid="sacred-geometry-mock" />,
}));
vi.mock('../../components/3D/SacredMandala', () => ({
  default: () => <div data-testid="sacred-mandala-mock" />,
}));
vi.mock('../../components/3D/ZhuntiMandala', () => ({
  default: () => <div data-testid="zhunti-mock" />,
}));
vi.mock('../../components/3D/TaraGreenLotus', () => ({
  default: () => <div data-testid="green-tara-mock" />,
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

describe('MeditationTab', () => {
  it('renders Rothko canvas, palette selector, and Exit Meditation button', async () => {
    await act(async () => {
      root.render(
        <MemoryRouter>
          <MeditationTab />
        </MemoryRouter>
      );
    });

    const buttons = Array.from(container.querySelectorAll('button'));
    const exitBtn = buttons.find((b) => b.textContent?.includes('Exit Meditation'));
    expect(exitBtn).toBeDefined();
    expect(exitBtn?.textContent).toContain('Exit Meditation');

    expect(container.textContent).toContain('Palette:');
    expect(container.textContent).toContain('Bowl Drone:');
    expect(container.textContent).toContain('Breath Guide');
  });
});

describe('VisualizerTab', () => {
  it('renders mode selectors and 3D canvas viewport', async () => {
    await act(async () => {
      root.render(<VisualizerTab />);
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(container.textContent).toContain('Sacred Geometry');
    expect(container.textContent).toContain('Sacred Mandala');
    expect(container.textContent).toContain('Zhunti Mother');
    expect(container.textContent).toContain('Green Tara Lotus');

    const canvas = container.querySelector('[data-testid="r3f-canvas"]');
    expect(canvas).not.toBeNull();
  });
});
