/**
 * Workings page mounts the constellation hero and feeds it the
 * hidden-inclusive ledger (the sky always renders the full truth,
 * independent of the list's "Show hidden" toggle).
 *
 * Same environment constraints as SittingsConstellation.test.tsx:
 * happy-dom ships no canvas 2D context and vitest 0.34 lacks
 * unstubAllMocks — stub by direct prototype assignment, restore by hand.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

const noop = () => {};
const stubCtx = () =>
  ({
    clearRect: noop, beginPath: noop, arc: noop, fill: noop, stroke: noop,
    moveTo: noop, lineTo: noop, fillText: noop, setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    save: noop, restore: noop, setTransform: noop,
  }) as unknown as CanvasRenderingContext2D;

const canvasProto = HTMLCanvasElement.prototype as unknown as Record<string, unknown>;
const origRaf = globalThis.requestAnimationFrame;
const origCancel = globalThis.cancelAnimationFrame;

const SKY = {
  workings: [
    {
      working_id: 'wrk_a',
      intention: 'peace',
      target: 'all beings',
      sealed_at: '2026-08-16T00:00:00Z',
      rate_values: [1, 2, 3, 4, 5],
      source: 'command-center',
    },
  ],
};

beforeEach(() => {
  canvasProto.getContext = () => stubCtx();
  let frames = 0;
  globalThis.requestAnimationFrame = ((cb: FrameRequestCallback): number => {
    frames += 1;
    if (frames <= 2) setTimeout(() => cb(performance.now()), 0);
    return frames;
  }) as typeof requestAnimationFrame;
  globalThis.cancelAnimationFrame = noop as typeof cancelAnimationFrame;
  globalThis.fetch = vi.fn().mockImplementation(() =>
    Promise.resolve({ ok: true, status: 200, json: async () => SKY } as Response),
  );
});
afterEach(() => {
  delete canvasProto.getContext;
  globalThis.requestAnimationFrame = origRaf;
  globalThis.cancelAnimationFrame = origCancel;
  vi.restoreAllMocks();
});

describe('Workings page — sittings sky', () => {
  it('renders the constellation hero from the hidden-inclusive fetch', async () => {
    const { default: WorkingsPage } = await import('../../routes/Workings');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ConfigProvider>
          <MemoryRouter initialEntries={['/workings']}>
            <Routes>
              <Route path="/workings" element={<WorkingsPage />} />
            </Routes>
          </MemoryRouter>
        </ConfigProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(container.querySelector('[data-testid="sittings-constellation"]')).not.toBeNull();
    const fetchMock = globalThis.fetch as unknown as { mock?: { calls: unknown[][] } };
    const calls = (fetchMock.mock?.calls || []).map((c) => String(c[0]));
    expect(calls.some((url) => url.includes('include_hidden=true'))).toBe(true);
  }, 30000);
});
