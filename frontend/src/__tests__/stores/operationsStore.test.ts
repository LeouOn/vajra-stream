import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  isOperation,
  selectActive,
  selectByWorkingId,
  selectOperations,
  selectRecent,
  useOperationsStore,
} from '../../stores/operationsStore';
import type { Operation } from '../../types/operations';

function op(overrides: Partial<Operation> & Pick<Operation, 'id'>): Operation {
  return {
    kind: 'render',
    status: 'queued',
    title: overrides.id,
    working_id: null,
    params: null,
    provenance: null,
    result: null,
    error: null,
    created_at: '2026-10-14T10:00:00+00:00',
    started_at: null,
    finished_at: null,
    elapsed_seconds: null,
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

const state = () => useOperationsStore.getState();

describe('operationsStore', () => {
  beforeEach(() => {
    state().clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('upserts by id, replacing the same operation as it advances', () => {
    state().upsert(op({ id: 'a', status: 'queued' }));
    state().upsert(op({ id: 'a', status: 'running', started_at: '2026-10-14T10:00:05+00:00' }));
    expect(Object.keys(state().byId)).toEqual(['a']);
    expect(state().byId.a.status).toBe('running');
    expect(state().byId.a.started_at).toBe('2026-10-14T10:00:05+00:00');
  });

  it('ignores a stale, less-advanced copy (e.g. a REST page landing after a WS success)', () => {
    state().upsert(op({ id: 'a', status: 'success', elapsed_seconds: 55.2 }));
    state().upsertMany([op({ id: 'a', status: 'running' }), op({ id: 'b' })]);
    expect(state().byId.a.status).toBe('success');
    expect(state().byId.a.elapsed_seconds).toBe(55.2);
    expect(state().byId.b).toBeDefined();
  });

  it('keeps the same byId reference when nothing changes', () => {
    state().upsert(op({ id: 'a', status: 'success' }));
    const before = state().byId;
    state().upsertMany([op({ id: 'a', status: 'queued' })]);
    expect(state().byId).toBe(before);
  });

  it('ingest validates untrusted WS payloads', () => {
    expect(state().ingest(op({ id: 'x' }))).toBe(true);
    expect(state().ingest({ id: 'y', status: 'running' })).toBe(false);
    expect(state().ingest({ id: 'z', kind: 'render', status: 'exploded', created_at: 'now' })).toBe(false);
    expect(state().ingest(null)).toBe(false);
    expect(Object.keys(state().byId)).toEqual(['x']);
    expect(isOperation(op({ id: 'q' }))).toBe(true);
  });

  it('selectOperations is newest first by created_at', () => {
    state().upsertMany([
      op({ id: 'old', created_at: '2026-10-14T09:00:00+00:00' }),
      op({ id: 'new', created_at: '2026-10-14T11:00:00+00:00' }),
      op({ id: 'mid', created_at: '2026-10-14T10:00:00+00:00' }),
    ]);
    expect(selectOperations(state()).map((o) => o.id)).toEqual(['new', 'mid', 'old']);
  });

  it('selectActive returns queued/running oldest first (queue order), optionally by kind', () => {
    state().upsertMany([
      op({ id: 'r2', status: 'queued', created_at: '2026-10-14T10:02:00+00:00' }),
      op({ id: 'r1', status: 'running', created_at: '2026-10-14T10:01:00+00:00' }),
      op({ id: 'done', status: 'success', created_at: '2026-10-14T10:00:00+00:00' }),
      op({ id: 'b1', kind: 'broadcast', status: 'running', created_at: '2026-10-14T09:00:00+00:00' }),
    ]);
    expect(selectActive(state()).map((o) => o.id)).toEqual(['b1', 'r1', 'r2']);
    expect(selectActive(state(), 'render').map((o) => o.id)).toEqual(['r1', 'r2']);
  });

  it('selectRecent returns finished operations, most recently finished first, limited', () => {
    state().upsertMany([
      op({ id: 'a', status: 'success', finished_at: '2026-10-14T10:05:00+00:00' }),
      op({ id: 'b', status: 'error', finished_at: '2026-10-14T10:09:00+00:00' }),
      op({ id: 'c', status: 'cancelled', finished_at: '2026-10-14T10:07:00+00:00' }),
      op({ id: 'live', status: 'running' }),
    ]);
    expect(selectRecent(state()).map((o) => o.id)).toEqual(['b', 'c', 'a']);
    expect(selectRecent(state(), 2).map((o) => o.id)).toEqual(['b', 'c']);
    expect(selectRecent(state(), 10, 'broadcast')).toEqual([]);
  });

  it('selectByWorkingId filters to one working, newest first', () => {
    state().upsertMany([
      op({ id: 'w1a', working_id: 'w1', created_at: '2026-10-14T10:00:00+00:00' }),
      op({ id: 'w1b', working_id: 'w1', created_at: '2026-10-14T10:01:00+00:00' }),
      op({ id: 'w2a', working_id: 'w2' }),
      op({ id: 'none' }),
    ]);
    expect(selectByWorkingId(state(), 'w1').map((o) => o.id)).toEqual(['w1b', 'w1a']);
  });

  it('fetchOperations calls GET /api/v1/operations with filters and upserts the page', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      jsonResponse({ operations: [op({ id: 'r1', status: 'success' }), { junk: true }], count: 2 }),
    );
    vi.stubGlobal('fetch', fetchSpy);
    const ops = await state().fetchOperations({ kind: 'render', status: 'success', limit: 24 });
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/operations?kind=render&status=success&limit=24');
    expect(ops.map((o) => o.id)).toEqual(['r1']);
    expect(state().byId.r1.status).toBe('success');
  });

  it('fetchOperations rejects on HTTP errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'nope' }, 500)));
    await expect(state().fetchOperations()).rejects.toThrow(/HTTP 500/);
  });

  it('fetchSummary stores the backend summary as-is', async () => {
    const summary = { since: null, by_status: { success: 3 }, by_kind: { render: 3 }, active: 1, completed: 3, seconds_held: 441.5 };
    const fetchSpy = vi.fn().mockResolvedValue(jsonResponse(summary));
    vi.stubGlobal('fetch', fetchSpy);
    await state().fetchSummary();
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/operations/summary');
    expect(state().summary).toEqual(summary);
  });

  it('fetchOperation upserts a single operation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(op({ id: 'one', status: 'running' }))));
    const got = await state().fetchOperation('one');
    expect(got.status).toBe('running');
    expect(state().byId.one).toBeDefined();
  });
});
