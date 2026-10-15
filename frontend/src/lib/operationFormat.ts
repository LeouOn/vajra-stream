/**
 * Honest timing / provenance text for operations (docs/DEVELOPMENT_ROADMAP.md,
 * "the honest instrument").
 *
 * - A finished operation shows the backend's measured `elapsed_seconds`.
 * - A running operation shows a live count from its recorded `started_at`,
 *   computed on this device's clock and labeled as such.
 * - Nothing here estimates progress or remaining time; the backend does not
 *   report either, so the UI does not invent them.
 */
import type { Operation, Provenance } from '../types/operations';
import { apiUrl } from '../utils/api';

/** `47.2s`, `2m 03s`, `1h 02m 13s`. Negative input (clock skew) clamps to 0. */
export function formatDuration(seconds: number): string {
  const s = Math.max(0, seconds);
  if (s < 60) return `${s < 10 ? s.toFixed(1) : Math.floor(s)}s`;
  const total = Math.floor(s);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const sec = total % 60;
  const pad = (n: number): string => String(n).padStart(2, '0');
  return h > 0 ? `${h}h ${pad(m)}m ${pad(sec)}s` : `${m}m ${pad(sec)}s`;
}

/** Local wall-clock time of an ISO timestamp, e.g. `14:02:11`. */
export function formatClock(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/** Local date + time, e.g. `Oct 14, 14:02`. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/** Seconds since `started_at` on this device's clock, or null if not started. */
export function liveElapsedSeconds(op: Pick<Operation, 'started_at'>, nowMs: number): number | null {
  if (!op.started_at) return null;
  const start = Date.parse(op.started_at);
  if (Number.isNaN(start)) return null;
  return Math.max(0, (nowMs - start) / 1000);
}

/**
 * One line describing an operation's timing from the record.
 * `nowMs` drives the live count for running operations.
 */
export function describeTiming(op: Operation, nowMs: number): string {
  switch (op.status) {
    case 'queued':
      return `queued · submitted ${formatClock(op.created_at)}`;
    case 'running': {
      const live = liveElapsedSeconds(op, nowMs);
      if (live === null) return 'running · start time not recorded';
      return `running · ${formatDuration(live)} since start at ${formatClock(op.started_at)} (counted on this device)`;
    }
    default: {
      const finished = `finished ${formatDateTime(op.finished_at)}`;
      if (op.elapsed_seconds === null || op.elapsed_seconds === undefined) {
        return op.started_at ? finished : `${finished} · never started`;
      }
      return `took ${formatDuration(op.elapsed_seconds)} (measured) · ${finished}`;
    }
  }
}

export type SeedOrigin = 'drawn' | 'chosen' | 'unrecorded';

/** Where a seed came from, per `provenance.seed`. */
export function seedOrigin(provenance: Record<string, Provenance> | null): SeedOrigin {
  const p = provenance?.seed;
  if (p === 'draw') return 'drawn';
  if (p) return 'chosen';
  return 'unrecorded';
}

/** `seed 123 (drawn)` / `seed 123 (chosen)` / `seed 123 (origin not recorded)`. */
export function seedLabel(seed: number | string, provenance: Record<string, Provenance> | null): string {
  const origin = seedOrigin(provenance);
  return `seed ${seed} (${origin === 'unrecorded' ? 'origin not recorded' : origin})`;
}

const API_PREFIX = '/api/v1';

/**
 * Resolve a backend-issued URL such as `/api/v1/render/jobs/<id>/image`
 * through `apiUrl()` so the VITE_API_BASE override applies (ADR 004).
 */
export function resolveBackendUrl(url: string): string {
  if (url.startsWith(`${API_PREFIX}/`)) return apiUrl(url.slice(API_PREFIX.length));
  return url;
}
