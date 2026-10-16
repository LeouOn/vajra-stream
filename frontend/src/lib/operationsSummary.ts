/**
 * Small, honest operations-ledger readouts (GET /api/v1/operations/summary).
 *
 * These replace the retired MOPS throughput figures (owner decision
 * 2026-10-14, docs/DEVELOPMENT_ROADMAP.md "Decisions"): instead of a
 * per-second rate, show real operations, each with a measured duration.
 * The full Ledger UI and live `operation_update` handling live elsewhere,
 * and polling is shared through `useTodaySummary` in stores/operationsStore.ts;
 * this module only fetches and formats the summary.
 */
import { apiUrl } from '../utils/api';
import type { OperationsSummary } from '../types/operations';

/**
 * Local midnight as an ISO-8601 UTC timestamp in the backend's
 * `created_at` format (`+00:00` offset), for `?since=`.
 */
export function startOfLocalDayIso(now: Date = new Date()): string {
  const midnight = new Date(now);
  midnight.setHours(0, 0, 0, 0);
  return midnight.toISOString().replace('Z', '+00:00');
}

/** Fetch the ledger summary; `null` when the backend is unreachable or errors. */
export async function fetchOperationsSummary(
  since?: string,
  init?: RequestInit,
): Promise<OperationsSummary | null> {
  const query = since ? `?since=${encodeURIComponent(since)}` : '';
  try {
    const res = await fetch(apiUrl(`/operations/summary${query}`), init);
    if (!res.ok) return null;
    return (await res.json()) as OperationsSummary;
  } catch {
    return null;
  }
}

/** Measured seconds as a short duration: `45s`, `12m`, `3h 12m`. */
export function formatHeld(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}m` : `${hours}h`;
}

/**
 * One line of ledger facts, e.g.
 * `2 operations completed today · 3h 12m held · 1 active`.
 */
export function formatOperationsSummary(summary: OperationsSummary, period = 'today'): string {
  const { completed, active, seconds_held: held } = summary;
  const parts = [
    completed === 0
      ? `No operations completed ${period}`
      : `${completed} operation${completed === 1 ? '' : 's'} completed ${period}`,
  ];
  if (completed > 0) parts.push(`${formatHeld(held)} held`);
  if (active > 0) parts.push(`${active} active`);
  return parts.join(' · ');
}
