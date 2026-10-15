/**
 * Today's ledger summary is read once and shared: the footer (MainLayout)
 * and the Scalar tab both use `useTodaySummary`, so mounting both makes a
 * single `GET /operations/summary?since=...` and runs a single interval.
 * Their text is unchanged from when each polled on its own.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import type { OperationsSummary } from '../../types/operations';

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({
    idleReflectionCount: 0,
    scalarStatus: null,
    crystalStatus: null,
    sessions: [],
    isConnected: false,
    lastJourneyEventAt: null,
  }),
}));

vi.mock('../../components/2D/ScalarWaveVisualizer', async () => {
  const { forwardRef } = await import('react');
  return { default: forwardRef<HTMLDivElement>((_props, ref) => <div ref={ref} data-testid="scalar-viz-mock" />) };
});

import MainLayout from '../../components/Layout/MainLayout';
import ScalarTab from '../../routes/Practice/ScalarTab';
import { SUMMARY_POLL_MS, useOperationsStore } from '../../stores/operationsStore';

const SUMMARY: OperationsSummary = {
  since: '2026-10-14T07:00:00+00:00',
  by_status: { success: 2, running: 1 },
  by_kind: { render: 2, broadcast: 1 },
  active: 1,
  completed: 2,
  seconds_held: 3 * 3600 + 12 * 60,
};

let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;

function summaryCalls(): number {
  return fetchSpy.mock.calls.filter((c) => String(c[0]).startsWith('/api/v1/operations/summary')).length;
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  vi.useFakeTimers();
  useOperationsStore.getState().clear();
  fetchSpy = vi.fn((url: string) => {
    if (url.startsWith('/api/v1/operations/summary')) {
      return Promise.resolve({ ok: true, status: 200, json: async () => SUMMARY } as Response);
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
  });
  vi.stubGlobal('fetch', fetchSpy);
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function renderBoth(): Promise<void> {
  const noop = async (): Promise<void> => undefined;
  await act(async () => {
    root.render(
      <ConfigProvider>
        <MemoryRouter initialEntries={['/practice/scalar']}>
          <MainLayout
            isConnected={false}
            isPlaying={false}
            frequency={528}
            volume={0.5}
            prayerBowlMode
            generateAudio={noop}
            playAudio={noop}
            stopAudio={() => undefined}
          >
            <ScalarTab />
          </MainLayout>
        </MemoryRouter>
      </ConfigProvider>,
    );
  });
  await advance(0);
}

describe('shared today summary (MainLayout footer + ScalarTab)', () => {
  it('reads the summary once for both and keeps their text', async () => {
    await renderBoth();
    expect(summaryCalls()).toBe(1);
    const url = String(fetchSpy.mock.calls.find((c) => String(c[0]).startsWith('/api/v1/operations/summary'))?.[0]);
    expect(url).toMatch(/^\/api\/v1\/operations\/summary\?since=/);

    const text = container.textContent ?? '';
    // Footer, desktop and compact.
    expect(text).toContain('2 operations completed today · 3h 12m held · 1 active');
    expect(text).toContain('2 done today · 1 active');
    // Scalar tab readouts (the footer has one "3h 12m"; the tab's Held row is the other).
    expect(container.querySelector('[data-testid="scalar-viz-mock"]')).not.toBeNull();
    expect(text).toContain('Completed');
    expect(text.split('3h 12m').length - 1).toBe(2);
    expect(text).toContain('Active');
    expect(text).not.toContain('Loading ledger');
  });

  it('runs one slow interval, not one per reader', async () => {
    await renderBoth();
    expect(summaryCalls()).toBe(1);
    await advance(SUMMARY_POLL_MS);
    expect(summaryCalls()).toBe(2);
    await advance(SUMMARY_POLL_MS);
    expect(summaryCalls()).toBe(3);
  });

  it('stops polling once both readers are gone', async () => {
    await renderBoth();
    act(() => root.unmount());
    root = createRoot(container);
    const before = summaryCalls();
    await advance(SUMMARY_POLL_MS * 3);
    expect(summaryCalls()).toBe(before);
  });

  it('says so when the ledger is unreachable', async () => {
    fetchSpy.mockImplementation(() => Promise.reject(new Error('offline')));
    await renderBoth();
    const text = container.textContent ?? '';
    expect(text).toContain('Ledger: unavailable');
    expect(text).toContain('Ledger unavailable');
  });
});
