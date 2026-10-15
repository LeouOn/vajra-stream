// @vitest-environment happy-dom
/**
 * `operation_update` WS messages reach the operations store.
 *
 * A fake WebSocket replaces the global before the hook module loads; the
 * test mounts one consumer (opening the singleton socket) and pushes frames
 * through its `onmessage`, exactly as the backend would.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import type { Operation } from '../../types/operations';

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

const operation: Operation = {
  id: 'op-render-1',
  kind: 'render',
  status: 'running',
  title: 'render: a quiet lake',
  working_id: null,
  params: { prompt: 'a quiet lake', seed: 7 },
  provenance: { seed: 'draw' },
  result: null,
  error: null,
  created_at: '2026-10-14T10:00:00+00:00',
  started_at: '2026-10-14T10:00:03+00:00',
  finished_at: null,
  elapsed_seconds: null,
};

let root: Root;
let container: HTMLDivElement;

beforeAll(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.spyOn(console, 'log').mockImplementation(() => undefined);
});

afterAll(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

beforeEach(async () => {
  const { useOperationsStore } = await import('../../stores/operationsStore');
  useOperationsStore.getState().clear();
});

describe("useWebSocketStable: 'operation_update'", () => {
  it('upserts the pushed operation into the operations store', async () => {
    const { useWebSocketStable } = await import('../../hooks/useWebSocketStable');
    const { useOperationsStore } = await import('../../stores/operationsStore');

    function Consumer(): null {
      useWebSocketStable();
      return null;
    }
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root.render(<Consumer />));

    const ws = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
    expect(ws).toBeDefined();

    act(() => ws?.push({ type: 'operation_update', data: operation }));
    expect(useOperationsStore.getState().byId['op-render-1']?.status).toBe('running');

    const finished: Operation = {
      ...operation,
      status: 'success',
      finished_at: '2026-10-14T10:02:30+00:00',
      elapsed_seconds: 147.4,
      result: { image_url: '/api/v1/render/jobs/op-render-1/image', width: 1024, height: 1024, seed: 7 },
    };
    act(() => ws?.push({ type: 'operation_update', data: finished }));
    const stored = useOperationsStore.getState().byId['op-render-1'];
    expect(stored?.status).toBe('success');
    expect(stored?.elapsed_seconds).toBe(147.4);
  });

  it('ignores a malformed operation_update without breaking the socket handler', async () => {
    const { useOperationsStore } = await import('../../stores/operationsStore');
    const ws = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
    act(() => ws?.push({ type: 'operation_update', data: { id: 'half' } }));
    expect(useOperationsStore.getState().byId).toEqual({});
  });
});
