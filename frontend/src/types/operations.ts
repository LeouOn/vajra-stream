/**
 * Operations ledger — mirrors core/operations.py.
 *
 * REST: GET /api/v1/operations, /operations/summary, /operations/{id}
 * WS:   { type: 'operation_update', data: Operation } on every state change.
 */

export type OperationKind = 'render' | 'broadcast' | 'working' | 'audio' | 'tts' | 'video' | 'other';

export type OperationStatus = 'queued' | 'running' | 'success' | 'error' | 'cancelled' | 'interrupted';

/** Where a value came from — see docs/DEVELOPMENT_ROADMAP.md, "the honest instrument". */
export type Provenance = 'record' | 'computed' | 'draw' | 'decorative';

export interface Operation {
  id: string;
  kind: OperationKind;
  status: OperationStatus;
  title: string;
  working_id: string | null;
  params: Record<string, unknown> | null;
  /** Field name -> provenance, e.g. { seed: 'draw' }. */
  provenance: Record<string, Provenance> | null;
  result: Record<string, unknown> | null;
  error: string | null;
  /** ISO-8601 UTC. */
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  /** Measured wall-clock seconds from start to finish; null until finished. */
  elapsed_seconds: number | null;
}

export interface OperationsSummary {
  since: string | null;
  by_status: Partial<Record<OperationStatus, number>>;
  by_kind: Partial<Record<OperationKind, number>>;
  active: number;
  completed: number;
  /** Total measured seconds of successfully completed operations. */
  seconds_held: number;
}

export const ACTIVE_OPERATION_STATUSES: readonly OperationStatus[] = ['queued', 'running'];
