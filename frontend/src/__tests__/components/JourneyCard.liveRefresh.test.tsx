// @vitest-environment happy-dom
/**
 * JourneyCard refetches the journey status when the backend reports journey
 * progress over WS.
 *
 * The card used to read `journeyStatus` from useWebSocketStable — a field the
 * hook stopped providing when the JOURNEY_STATUS broadcast went away — so it
 * only refreshed on mount and on reconnect, and stayed stale while stages
 * advanced.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
// Imported statically: the hook only touches the WebSocket global when the
// card mounts, after beforeAll has stubbed it (and a dynamic import of the
// antd-heavy card can exceed the test timeout under a parallel run).
import JourneyCard from '../../components/UI/JourneyCard';

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

const fetchMock = vi.fn(async () => new Response(JSON.stringify({ active: false }), { status: 200 }));

function statusFetches(): number {
  return fetchMock.mock.calls.filter((call: unknown[]) => String(call[0]).endsWith('/operator/journey/status')).length;
}

let root: Root;
let container: HTMLDivElement;

beforeAll(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.stubGlobal('fetch', fetchMock);
  vi.spyOn(console, 'log').mockImplementation(() => undefined);
});

afterAll(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('JourneyCard live refresh', () => {
  it('refetches /operator/journey/status on JOURNEY_* events', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => root.render(<JourneyCard />));

    const ws = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
    expect(ws).toBeDefined();
    const afterMount = statusFetches();
    expect(afterMount).toBeGreaterThanOrEqual(1);

    await act(async () =>
      ws?.push({ type: 'JOURNEY_STAGE_COMPLETED', data: { stage: 'training', name: 'Training', blessings_count: 3, next_stage: 'The Working' } }),
    );
    expect(statusFetches()).toBe(afterMount + 1);

    await act(async () => ws?.push({ type: 'JOURNEY_COMPLETED', data: { total_stages: 6, total_blessings: 18, character: {} } }));
    expect(statusFetches()).toBe(afterMount + 2);
  }, 15_000);
});
