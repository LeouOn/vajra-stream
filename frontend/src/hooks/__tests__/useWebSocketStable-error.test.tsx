/**
 * @vitest-environment happy-dom
 *
 * Task 10 (Wave 1) — RED→GREEN test for uppercase WS ERROR message handling.
 *
 * Backend emits BOTH lowercase `error` (connection_manager_stable_v2.py:89,93)
 * AND uppercase `ERROR` (lines 109,131) — distinct strings. The frontend
 * switch previously handled only the lowercase variant, so uppercase ERROR
 * silently fell through to the default branch (`console.log`) and hid
 * session-start / orchestrator-unavailable failures from the user.
 *
 * Evidence file: .omo/evidence/wave1-task10-error-toast.txt
 *
 * Style follows CommandCenterHooks.test.tsx: raw `createRoot` + `act` plus a
 * per-hook harness that captures the return value. WebSocket is mocked so we
 * can deliver synthetic messages directly into the hook's `onmessage` handler.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import { useWebSocketStable } from '../useWebSocketStable';

/* -------------------------------------------------------------------------- *
 * Mock WebSocket — capture the instance so tests can drive its handlers.
 * -------------------------------------------------------------------------- */

interface MockWsInstance {
  readyState: number;
  url: string;
  onopen: ((ev?: unknown) => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onerror: ((ev?: unknown) => void) | null;
  onclose: ((ev?: unknown) => void) | null;
  close: () => void;
  send: (data: string) => void;
}

let capturedWs: MockWsInstance | null = null;

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  CONNECTING = 0;
  OPEN = 1;
  CLOSING = 2;
  CLOSED = 3;

  readyState: number = MockWebSocket.OPEN;
  url: string;
  onopen: MockWsInstance['onopen'] = null;
  onmessage: MockWsInstance['onmessage'] = null;
  onerror: MockWsInstance['onerror'] = null;
  onclose: MockWsInstance['onclose'] = null;

  constructor(url: string) {
    this.url = url;
    // Capture `this` for test driving. Assign a fresh object each test via beforeEach.
    capturedWs = this as unknown as MockWsInstance;
  }
  close() { /* no-op */ }
  send(_data: string) { /* no-op */ }
}

/* -------------------------------------------------------------------------- *
 * Harness
 * -------------------------------------------------------------------------- */

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
let captured: ReturnType<typeof useWebSocketStable> | null = null;
let originalWebSocket: typeof WebSocket | undefined;

function HookHarness() {
  captured = useWebSocketStable('ws://test.local/ws');
  return null;
}

beforeEach(() => {
  captured = null;
  capturedWs = null;
  originalWebSocket = (globalThis as { WebSocket?: typeof WebSocket }).WebSocket;
  (globalThis as { WebSocket: unknown }).WebSocket = MockWebSocket as unknown;

  // The hook polls GET /ready before opening the WebSocket so it doesn't
  // race backend lifespan startup. Mock fetch to return {ready: true}
  // immediately so tests don't have to wait or hit a real backend.
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({ ready: true }),
  })));

  // Silence hook's console output during tests.
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});

  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
  if (originalWebSocket !== undefined) {
    (globalThis as { WebSocket: typeof WebSocket }).WebSocket = originalWebSocket;
  } else {
    delete (globalThis as { WebSocket?: typeof WebSocket }).WebSocket;
  }
  vi.restoreAllMocks();
});

async function mountHook() {
  await act(async () => {
    root.render(<HookHarness />);
    // Flush microtasks so the hook's async connect() (which polls /ready
    // before constructing the WebSocket) reaches `new WebSocket(url)` and
    // populates `capturedWs`.
    await Promise.resolve();
    await Promise.resolve();
  });
}

function deliverMessage(payload: unknown) {
  if (!capturedWs || !capturedWs.onmessage) {
    throw new Error('WebSocket instance / onmessage not captured before deliverMessage');
  }
  act(() => {
    capturedWs!.onmessage!({ data: JSON.stringify(payload) });
  });
}

/* -------------------------------------------------------------------------- *
 * Tests
 * -------------------------------------------------------------------------- */

describe('useWebSocketStable — ERROR message handling (Task 10)', () => {
  it('surfaces uppercase {type:"ERROR"} messages via the error state', async () => {
    await mountHook();

    // RED until `case 'ERROR':` falls through to setError(data.message).
    // Before the fix this hits the `default` branch and `error` stays null.
    deliverMessage({ type: 'ERROR', message: 'Session service not available' });
    expect(captured!.error).toBe('Session service not available');
  });

  it('regression: still surfaces lowercase {type:"error"} messages via the error state', async () => {
    await mountHook();

    deliverMessage({ type: 'error', message: 'lowercase still works' });
    expect(captured!.error).toBe('lowercase still works');
  });

  it('does not surface unknown uppercase types as errors', async () => {
    await mountHook();

    deliverMessage({ type: 'TOTALLY_UNKNOWN_TYPE', message: 'ignore me' });
    expect(captured!.error).toBeNull();
  });

  it('clearError resets the error state regardless of source case', async () => {
    await mountHook();

    deliverMessage({ type: 'ERROR', message: 'transient failure' });
    expect(captured!.error).toBe('transient failure');

    act(() => { captured!.clearError(); });
    expect(captured!.error).toBeNull();
  });
});
