/**
 * ScalarTab shows the character journey from /operator/journey/status and
 * refetches it on every JOURNEY_* WebSocket event (lastJourneyEventAt).
 *
 * Regression: the tab read a `journeyStatus` field the hook no longer has;
 * it was always undefined, so `journey` resolved to null and the journey
 * (name, element badge) never rendered — not even the on-mount fetch.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';

const ws = { lastJourneyEventAt: null as number | null };

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({
    scalarStatus: null,
    crystalStatus: null,
    sessions: [],
    isConnected: true,
    lastJourneyEventAt: ws.lastJourneyEventAt,
  }),
}));

const moods: string[] = [];

vi.mock('../../components/2D/ScalarWaveVisualizer', async () => {
  const { forwardRef, useImperativeHandle } = await import('react');
  return {
    default: forwardRef((_props, ref) => {
      useImperativeHandle(ref, () => ({
        setElementMood: (element: string) => moods.push(element),
        setHealingMood: () => undefined,
        triggerCrystalLayer: () => undefined,
      }));
      return <div />;
    }),
  };
});

import ScalarTab from '../../routes/Practice/ScalarTab';

let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;
let journeyName = 'Tara of the Fire Lotus';

function journeyCalls(): number {
  return fetchSpy.mock.calls.filter((c) => String(c[0]).endsWith('/operator/journey/status')).length;
}

async function render(): Promise<void> {
  await act(async () => {
    root.render(
      <ConfigProvider>
        <MemoryRouter>
          <ScalarTab />
        </MemoryRouter>
      </ConfigProvider>,
    );
  });
  await act(async () => {
    await Promise.resolve();
  });
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  ws.lastJourneyEventAt = null;
  moods.length = 0;
  journeyName = 'Tara of the Fire Lotus';
  fetchSpy = vi.fn((url: string) => {
    if (String(url).endsWith('/operator/journey/status')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ active: true, current_stage: 'call', character: { name: journeyName, element: 'Fire' } }),
      } as Response);
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
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('ScalarTab journey', () => {
  it('renders the journey fetched on mount', async () => {
    await render();
    expect(journeyCalls()).toBe(1);
    expect(container.textContent).toContain('Tara of the Fire Lotus');
    // The journey's element now reaches the visualizer (this path was dead too).
    expect(moods).toContain('Fire');
  });

  it('refetches when a JOURNEY_* event arrives', async () => {
    await render();
    journeyName = 'Tara, second stage';
    ws.lastJourneyEventAt = Date.now();
    await render();
    expect(journeyCalls()).toBe(2);
    expect(container.textContent).toContain('Tara, second stage');
  });
});
