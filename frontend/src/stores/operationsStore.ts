/**
 * operationsStore.ts — client mirror of the operations ledger (core/operations.py).
 *
 * Operations are keyed by id and upserted from two sources:
 *   - REST: `GET /operations` (list) and `GET /operations/summary`.
 *   - WS:   `{ type: 'operation_update', data: Operation }` via `ingest()`,
 *           wired in hooks/useWebSocketStable.ts.
 *
 * The lifecycle only moves forward (queued → running → terminal), so an
 * upsert never lets an older, less-advanced copy overwrite a newer one —
 * e.g. a REST list fetched before a WS "success" push that lands after it.
 *
 * Derived lists are pure selector functions so components can memoize them
 * over `byId` (see `selectOperations`, `selectActive`, ...).
 */
import { create } from 'zustand';
import { apiUrl } from '../utils/api';
import {
  ACTIVE_OPERATION_STATUSES,
  type Operation,
  type OperationKind,
  type OperationStatus,
  type OperationsSummary,
} from '../types/operations';

export interface OperationsQuery {
  kind?: OperationKind;
  status?: OperationStatus;
  working_id?: string;
  limit?: number;
}

export interface OperationsState {
  byId: Record<string, Operation>;
  summary: OperationsSummary | null;
  upsert: (op: Operation) => void;
  upsertMany: (ops: Operation[]) => void;
  /** Validate an untrusted WS payload and upsert it. Returns false if it was not an Operation. */
  ingest: (payload: unknown) => boolean;
  setSummary: (summary: OperationsSummary) => void;
  /** `GET /operations` → upserts and returns the fetched page (newest first). */
  fetchOperations: (query?: OperationsQuery) => Promise<Operation[]>;
  /** `GET /operations/{id}` → upserts and returns it. */
  fetchOperation: (id: string) => Promise<Operation>;
  /** `GET /operations/summary` → stores and returns it. */
  fetchSummary: () => Promise<OperationsSummary>;
  clear: () => void;
}

const STATUSES: readonly OperationStatus[] = ['queued', 'running', 'success', 'error', 'cancelled', 'interrupted'];

/** Lifecycle stage: 0 queued, 1 running, 2 any terminal status. */
function stage(status: OperationStatus): number {
  if (status === 'queued') return 0;
  if (status === 'running') return 1;
  return 2;
}

export function isActiveStatus(status: OperationStatus): boolean {
  return ACTIVE_OPERATION_STATUSES.includes(status);
}

export function isOperation(value: unknown): value is Operation {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === 'string' &&
    typeof v.kind === 'string' &&
    typeof v.status === 'string' &&
    (STATUSES as readonly string[]).includes(v.status) &&
    typeof v.created_at === 'string'
  );
}

function merge(byId: Record<string, Operation>, ops: Operation[]): Record<string, Operation> {
  let next: Record<string, Operation> | null = null;
  for (const op of ops) {
    const existing = (next ?? byId)[op.id];
    if (existing && stage(op.status) < stage(existing.status)) continue; // stale copy
    if (!next) next = { ...byId };
    next[op.id] = op;
  }
  return next ?? byId;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) throw new Error(`GET ${path} failed (HTTP ${res.status})`);
  return (await res.json()) as T;
}

export const useOperationsStore = create<OperationsState>((set, get) => ({
  byId: {},
  summary: null,

  upsert: (op) => set((s) => ({ byId: merge(s.byId, [op]) })),

  upsertMany: (ops) => set((s) => ({ byId: merge(s.byId, ops) })),

  ingest: (payload) => {
    if (!isOperation(payload)) return false;
    get().upsert(payload);
    return true;
  },

  setSummary: (summary) => set({ summary }),

  fetchOperations: async (query = {}) => {
    const params = new URLSearchParams();
    if (query.kind) params.set('kind', query.kind);
    if (query.status) params.set('status', query.status);
    if (query.working_id) params.set('working_id', query.working_id);
    params.set('limit', String(query.limit ?? 100));
    const data = await getJson<{ operations?: unknown }>(`/operations?${params.toString()}`);
    const ops = Array.isArray(data.operations) ? data.operations.filter(isOperation) : [];
    get().upsertMany(ops);
    return ops;
  },

  fetchOperation: async (id) => {
    const data = await getJson<unknown>(`/operations/${encodeURIComponent(id)}`);
    if (!isOperation(data)) throw new Error(`operation ${id}: unexpected response`);
    get().upsert(data);
    return data;
  },

  fetchSummary: async () => {
    const summary = await getJson<OperationsSummary>('/operations/summary');
    set({ summary });
    return summary;
  },

  clear: () => set({ byId: {}, summary: null }),
}));

// ---------------------------------------------------------------------------
// Selectors (pure; pass `useOperationsStore.getState()` or `{ byId }`)
// ---------------------------------------------------------------------------

type ById = Pick<OperationsState, 'byId'>;

function ms(iso: string | null): number {
  if (!iso) return 0;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? 0 : t;
}

function newestFirst(a: Operation, b: Operation): number {
  return ms(b.created_at) - ms(a.created_at) || (a.id < b.id ? 1 : a.id > b.id ? -1 : 0);
}

/** Every known operation, newest first by `created_at`. */
export function selectOperations(state: ById): Operation[] {
  return Object.values(state.byId).sort(newestFirst);
}

/**
 * Queued and running operations, oldest first — the order the backend
 * drains them (one render at a time, by `created_at`).
 */
export function selectActive(state: ById, kind?: OperationKind): Operation[] {
  return Object.values(state.byId)
    .filter((op) => isActiveStatus(op.status) && (!kind || op.kind === kind))
    .sort((a, b) => -newestFirst(a, b));
}

/** Finished operations (any terminal status), most recently finished first. */
export function selectRecent(state: ById, limit = 20, kind?: OperationKind): Operation[] {
  const finished = (op: Operation): number => ms(op.finished_at) || ms(op.created_at);
  return Object.values(state.byId)
    .filter((op) => !isActiveStatus(op.status) && (!kind || op.kind === kind))
    .sort((a, b) => finished(b) - finished(a) || newestFirst(a, b))
    .slice(0, limit);
}

/** Operations linked to one working, newest first. */
export function selectByWorkingId(state: ById, workingId: string): Operation[] {
  return Object.values(state.byId)
    .filter((op) => op.working_id === workingId)
    .sort(newestFirst);
}
