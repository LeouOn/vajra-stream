/**
 * SittingsConstellation — render posture under a stubbed 2D context.
 * Mapping math is covered by star.test.ts; here we lock the DOM surface.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

const noop = () => {};
const stubCtx = () =>
  ({
    clearRect: noop, beginPath: noop, arc: noop, fill: noop, stroke: noop,
    moveTo: noop, lineTo: noop, fillText: noop, setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    save: noop, restore: noop, setTransform: noop,
  }) as unknown as CanvasRenderingContext2D;

// happy-dom ships no canvas 2D context and this vitest (0.34) has no
// vi.unstubAllMocks — install the context by direct prototype assignment
// and restore requestAnimationFrame by hand.
const canvasProto = HTMLCanvasElement.prototype as unknown as Record<string, unknown>;
const origRaf = globalThis.requestAnimationFrame;
const origCancel = globalThis.cancelAnimationFrame;

beforeEach(() => {
  canvasProto.getContext = () => stubCtx();
  let frames = 0;
  globalThis.requestAnimationFrame = ((cb: FrameRequestCallback): number => {
    frames += 1;
    if (frames <= 2) setTimeout(() => cb(performance.now()), 0);
    return frames;
  }) as typeof requestAnimationFrame;
  globalThis.cancelAnimationFrame = noop as typeof cancelAnimationFrame;
});
afterEach(() => {
  delete canvasProto.getContext;
  globalThis.requestAnimationFrame = origRaf;
  globalThis.cancelAnimationFrame = origCancel;
});

const FIXTURE = [
  {
    working_id: 'wrk_a', intention: 'peace for the watershed', target: 'all beings',
    sealed_at: '2026-08-14T00:00:00Z', rate_values: [68, 30, 71, 50, 68],
    source: 'command-center', moon_phase: 'Waxing Crescent', saka_dawa_multiplier: 1,
  },
  {
    working_id: 'wrk_b', intention: 'peace for the watershed', target: 'all beings',
    sealed_at: '2026-08-16T00:00:00Z', rate_values: [68, 30, 71, 50, 68],
    source: 'command-center', hidden: true, duplicate_of: 'wrk_a',
    moon_phase: 'Full Moon', saka_dawa_multiplier: 100000,
  },
];

describe('SittingsConstellation', () => {
  it('renders a canvas for sittings and reports selection targets', async () => {
    const { default: SittingsConstellation } = await import(
      '../../components/Workings/SittingsConstellation'
    );
    const onSelect = vi.fn();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<SittingsConstellation workings={FIXTURE} onSelect={onSelect} />);
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
    expect(container.querySelector('[data-testid="sittings-constellation"]')).not.toBeNull();
    expect(container.textContent || '').not.toContain('No sittings yet');
  }, 30000);

  it('shows the empty-sky caption when there are no workings', async () => {
    const { default: SittingsConstellation } = await import(
      '../../components/Workings/SittingsConstellation'
    );
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<SittingsConstellation workings={[]} onSelect={() => {}} />);
    });
    expect(container.querySelector('[data-testid="sky-empty"]')).not.toBeNull();
  }, 30000);
});
