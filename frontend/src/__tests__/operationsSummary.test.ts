import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  fetchOperationsSummary,
  formatHeld,
  formatOperationsSummary,
  startOfLocalDayIso,
} from '../lib/operationsSummary';
import type { OperationsSummary } from '../types/operations';

const summary = (over: Partial<OperationsSummary> = {}): OperationsSummary => ({
  since: null,
  by_status: {},
  by_kind: {},
  active: 0,
  completed: 0,
  seconds_held: 0,
  ...over,
});

describe('operationsSummary (ledger facts that replace MOPS)', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('formats measured durations', () => {
    expect(formatHeld(0)).toBe('0s');
    expect(formatHeld(45.4)).toBe('45s');
    expect(formatHeld(12 * 60 + 5)).toBe('12m');
    expect(formatHeld(3 * 3600)).toBe('3h');
    expect(formatHeld(3 * 3600 + 12 * 60)).toBe('3h 12m');
    expect(formatHeld(-5)).toBe('0s');
  });

  it('formats a summary line with counts, held time and active ops', () => {
    expect(formatOperationsSummary(summary())).toBe('No operations completed today');
    expect(formatOperationsSummary(summary({ active: 1 }))).toBe('No operations completed today · 1 active');
    expect(formatOperationsSummary(summary({ completed: 1, seconds_held: 90 }))).toBe(
      '1 operation completed today · 1m held',
    );
    expect(
      formatOperationsSummary(summary({ completed: 4, seconds_held: 3 * 3600 + 12 * 60, active: 2 })),
    ).toBe('4 operations completed today · 3h 12m held · 2 active');
  });

  it('never mentions a rate', () => {
    const line = formatOperationsSummary(summary({ completed: 3, seconds_held: 600, active: 1 }));
    expect(line).not.toMatch(/MOPS|\/s\b|per second/i);
  });

  it('computes local midnight in the backend timestamp format', () => {
    const iso = startOfLocalDayIso(new Date(2026, 9, 14, 15, 30));
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000\+00:00$/);
    expect(new Date(iso).getTime()).toBe(new Date(2026, 9, 14, 0, 0, 0, 0).getTime());
  });

  it('fetches /operations/summary through apiUrl with an encoded since', async () => {
    const body = summary({ completed: 2 });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => body });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchOperationsSummary('2026-10-14T07:00:00.000+00:00')).resolves.toEqual(body);
    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/operations/summary?since=2026-10-14T07%3A00%3A00.000%2B00%3A00',
    );
  });

  it('returns null when the backend is down or errors', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false }) as unknown as typeof fetch;
    await expect(fetchOperationsSummary()).resolves.toBeNull();
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('offline')) as unknown as typeof fetch;
    await expect(fetchOperationsSummary()).resolves.toBeNull();
  });
});
