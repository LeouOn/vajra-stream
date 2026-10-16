// @vitest-environment happy-dom
/**
 * WS frames are read in the shape the backend actually sends.
 *
 * - LLM_USAGE_UPDATE: backend/app/main.py `_broadcast_usage` nests the
 *   counters under `data`. The hook used to read them from the top level, so
 *   the live usage badge always showed 0 calls / $0.
 * - BUDDHA_RECITATION_STARTED: core/buddha_recitation_loop.py sends only
 *   `{ intention, total_buddhas }`. The hook used to store that as the whole
 *   RecitationStatus, so `running` read as undefined (stopped) until the first
 *   name was recited.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import type { UseWebSocketStableReturn } from '../../hooks/useWebSocketStable';

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readyState = FakeWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(): void {}

  close(): void {
    this.readyState = FakeWebSocket.CLOSED;
  }

  push(payload: unknown): void {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(payload) }));
  }
}

let root: Root;
let container: HTMLDivElement;
let latest: UseWebSocketStableReturn | null = null;

function socket(): FakeWebSocket {
  const ws = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
  if (!ws) throw new Error('no socket opened');
  return ws;
}

beforeAll(async () => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.spyOn(console, 'log').mockImplementation(() => undefined);

  const { useWebSocketStable } = await import('../../hooks/useWebSocketStable');
  function Consumer(): null {
    latest = useWebSocketStable();
    return null;
  }
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root.render(<Consumer />));
});

afterAll(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('useWebSocketStable payload shapes', () => {
  it('reads LLM_USAGE_UPDATE counters from data', () => {
    act(() =>
      socket().push({
        type: 'LLM_USAGE_UPDATE',
        data: {
          total_calls: 42,
          total_cost_usd: 1.25,
          calls_today: 7,
          cost_today: 0.31,
          daily_cost_usd: 0.31,
          daily_cost_cap: null,
          over_cap: false,
          remaining_balance: null,
          provider_stats: {},
        },
      }),
    );
    expect(latest?.usageUpdate).toMatchObject({
      total_calls: 42,
      total_cost_usd: 1.25,
      calls_today: 7,
      cost_today: 0.31,
    });
  });

  it('starts a fresh running status on BUDDHA_RECITATION_STARTED', () => {
    act(() =>
      socket().push({ type: 'BUDDHA_RECITATION_STARTED', data: { intention: 'May all beings be free', total_buddhas: 88 } }),
    );
    expect(latest?.buddhaStatus?.running).toBe(true);
    expect(latest?.buddhaStatus?.intention).toBe('May all beings be free');
    expect(latest?.buddhaStatus?.total_buddhas).toBe(88);
    expect(latest?.buddhaStatus?.total_recited).toBe(0);

    // A full get_status() projection still replaces the status wholesale.
    act(() =>
      socket().push({
        type: 'BUDDHA_NAME_RECITED',
        data: {
          running: true,
          intention: 'May all beings be free',
          current_index: 3,
          current_cycle: 1,
          total_recited: 3,
          mala_count: 0,
          dedications: 0,
          total_buddhas: 88,
          current_buddha: { name_chinese: '南無普光佛', category: 'past' },
          progress_pct: 3.4,
          started_at: '2026-10-15T10:00:00',
          last_recited_at: '2026-10-15T10:00:09',
        },
      }),
    );
    expect(latest?.buddhaStatus?.total_recited).toBe(3);

    // A restart is a fresh session (backend resets RecitationState), so counters zero.
    act(() =>
      socket().push({ type: 'BUDDHA_RECITATION_STARTED', data: { intention: 'Peace', total_buddhas: 88 } }),
    );
    expect(latest?.buddhaStatus?.running).toBe(true);
    expect(latest?.buddhaStatus?.intention).toBe('Peace');
    expect(latest?.buddhaStatus?.current_index).toBe(0);
    expect(latest?.buddhaStatus?.current_buddha).toEqual({});
  });

  it('forwards chat progress frames (including chat_cancelled) to the chat progress store', async () => {
    const chatProgress = await import('../../hooks/chatProgress');
    act(() => socket().push({ type: 'chat_tool_start', job_id: 'chat_abc', tool: 'get_chart', args: {} }));
    expect(chatProgress.get('chat_abc')).toMatchObject({ type: 'chat_tool_start', tool: 'get_chart' });
    act(() => socket().push({ type: 'chat_cancelled', job_id: 'chat_abc' }));
    expect(chatProgress.get('chat_abc')).toMatchObject({ type: 'chat_cancelled', tool: 'get_chart' });
  });
});
