import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { useAmbientBowl } from '../hooks/useAmbientBowl';

interface MockOscillator {
  type: string;
  frequency: { value: number };
  detune: { value: number };
  connect: ReturnType<typeof vi.fn>;
  start: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
}

interface MockGain {
  gain: { value: number };
  connect: ReturnType<typeof vi.fn>;
}

interface MockAudioContext {
  destination: object;
  createOscillator: ReturnType<typeof vi.fn>;
  createGain: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
}

function setupAudioMocks(): {
  osc: MockOscillator;
  gain: MockGain;
  ctx: MockAudioContext;
} {
  const osc: MockOscillator = {
    type: '',
    frequency: { value: 0 },
    detune: { value: 0 },
    connect: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  };
  const gain: MockGain = {
    gain: { value: 0 },
    connect: vi.fn(),
  };
  osc.connect.mockReturnValue(gain);
  gain.connect.mockReturnValue(undefined);
  const ctx: MockAudioContext = {
    destination: {},
    createOscillator: vi.fn(() => osc),
    createGain: vi.fn(() => gain),
    close: vi.fn(() => Promise.resolve()),
  };
  (globalThis as unknown as { AudioContext: typeof AudioContext }).AudioContext = vi
    .fn(() => ctx) as unknown as typeof AudioContext;
  return { osc, gain, ctx };
}

interface Harness {
  start: (freq: number) => void;
  stop: () => void;
  isPlaying: boolean;
}

interface HookHarness {
  current: Harness;
  root: Root;
  cleanup: () => void;
}

function renderHookHarness(): HookHarness {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const ref: { current: Harness | null } = { current: null };

  const Probe: React.FC = () => {
    const api = useAmbientBowl();
    ref.current = api;
    return null;
  };

  const root = createRoot(container);
  act(() => {
    root.render(React.createElement(Probe));
  });

  const harness: HookHarness = {
    get current(): Harness {
      if (!ref.current) throw new Error('Hook not mounted');
      return ref.current;
    },
    root,
    cleanup: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
  return harness;
}

describe('useAmbientBowl', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    delete (globalThis as unknown as { AudioContext?: typeof AudioContext }).AudioContext;
  });

  it('start() spins up an oscillator at the requested frequency', () => {
    const mocks = setupAudioMocks();
    const harness = renderHookHarness();
    try {
      act(() => {
        harness.current.start(261.63);
      });
      expect(mocks.ctx.createOscillator).toHaveBeenCalledOnce();
      expect(mocks.osc.frequency.value).toBe(261.63);
      expect(mocks.osc.detune.value).toBe(3);
      expect(mocks.osc.type).toBe('sine');
      expect(mocks.gain.gain.value).toBeCloseTo(0.15, 5);
      expect(mocks.osc.start).toHaveBeenCalledOnce();
      expect(harness.current.isPlaying).toBe(true);
    } finally {
      harness.cleanup();
    }
  });

  it('start() is a no-op when already running', () => {
    const mocks = setupAudioMocks();
    const harness = renderHookHarness();
    try {
      act(() => harness.current.start(261.63));
      act(() => harness.current.start(330));
      expect(mocks.ctx.createOscillator).toHaveBeenCalledOnce();
    } finally {
      harness.cleanup();
    }
  });

  it('stop() tears down osc + context', async () => {
    const mocks = setupAudioMocks();
    const harness = renderHookHarness();
    try {
      act(() => harness.current.start(220));
      act(() => harness.current.stop());
      expect(mocks.osc.stop).toHaveBeenCalledOnce();
      await Promise.resolve();
      expect(mocks.ctx.close).toHaveBeenCalledOnce();
      expect(harness.current.isPlaying).toBe(false);
    } finally {
      harness.cleanup();
    }
  });

  it('stop() is a safe no-op when nothing is playing', () => {
    setupAudioMocks();
    const harness = renderHookHarness();
    try {
      expect(() => act(() => harness.current.stop())).not.toThrow();
      expect(harness.current.isPlaying).toBe(false);
    } finally {
      harness.cleanup();
    }
  });

  it('start() survives environments without AudioContext', () => {
    delete (globalThis as unknown as { AudioContext?: typeof AudioContext }).AudioContext;
    const harness = renderHookHarness();
    try {
      expect(() => act(() => harness.current.start(220))).not.toThrow();
      expect(harness.current.isPlaying).toBe(false);
    } finally {
      harness.cleanup();
    }
  });

  it('cleanup on unmount closes the AudioContext', async () => {
    const mocks = setupAudioMocks();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    const Probe: React.FC = () => {
      const api = useAmbientBowl();
      act(() => api.start(440));
      return null;
    };
    act(() => root.render(React.createElement(Probe)));
    act(() => root.unmount());
    await Promise.resolve();
    expect(mocks.osc.stop).toHaveBeenCalledOnce();
    expect(mocks.ctx.close).toHaveBeenCalledOnce();
    container.remove();
  });
});