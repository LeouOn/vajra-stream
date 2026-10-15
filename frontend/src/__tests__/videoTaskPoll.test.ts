// @vitest-environment happy-dom
/**
 * pollVideoTask stops itself on a terminal status.
 *
 * OutlookDashboard's inline poller read `.current` off a useState value, so
 * the clear threw (swallowed by its own catch): the interval was never
 * cleared and the finished/failed toast never fired.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { pollVideoTask, isVideoTaskTerminal } from '../lib/videoTaskPoll';

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
}

describe('pollVideoTask', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('polls until done, then stops and reports once', async () => {
    const statuses = ['queued', 'running', 'done'];
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({ task_id: 't1', status: statuses.shift() ?? 'done' }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const onStatus = vi.fn();
    const onFinish = vi.fn();

    pollVideoTask({ taskId: 't1', model: 'MiniMax-H3', intervalMs: 1000, onStatus, onFinish });

    await vi.advanceTimersByTimeAsync(3000);
    expect(onStatus).toHaveBeenCalledTimes(3);
    expect(onFinish).toHaveBeenCalledTimes(1);
    expect(onFinish).toHaveBeenCalledWith({ task_id: 't1', status: 'done' });

    // No further polling after the terminal status.
    await vi.advanceTimersByTimeAsync(10_000);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/videos/status');
  });

  it('stop() halts polling before a terminal status', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ status: 'running' }));
    vi.stubGlobal('fetch', fetchMock);
    const stop = pollVideoTask({ taskId: 't2', model: 'm', intervalMs: 1000, onStatus: vi.fn(), onFinish: vi.fn() });

    await vi.advanceTimersByTimeAsync(2000);
    stop();
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('treats succeeded/done/failed as terminal', () => {
    expect(isVideoTaskTerminal('succeeded')).toBe(true);
    expect(isVideoTaskTerminal('done')).toBe(true);
    expect(isVideoTaskTerminal('failed')).toBe(true);
    expect(isVideoTaskTerminal('running')).toBe(false);
    expect(isVideoTaskTerminal(undefined)).toBe(false);
  });
});
