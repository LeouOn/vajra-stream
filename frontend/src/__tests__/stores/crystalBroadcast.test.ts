/**
 * crystalStore.broadcastCrystal / cancelBroadcast — the radionics broadcast
 * runs in the background as a ledger operation (spec contract W2-3). The POST
 * returns once it has *started*; its state lives in useOperationsStore.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useCrystalStore } from '../../stores/crystalStore';
import { useOperationsStore } from '../../stores/operationsStore';
import type { Operation } from '../../types/operations';

function op(overrides: Partial<Operation> = {}): Operation {
  return {
    id: 'op-1',
    kind: 'broadcast',
    status: 'running',
    title: 'Scalar-radionics broadcast: healing',
    working_id: null,
    params: null,
    provenance: null,
    result: null,
    error: null,
    created_at: '2026-10-15T10:00:00+00:00',
    started_at: '2026-10-15T10:00:00+00:00',
    finished_at: null,
    elapsed_seconds: null,
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status < 400, status, json: async () => body } as Response;
}

describe('crystalStore background broadcast', () => {
  let originalFetch: typeof fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    useOperationsStore.getState().clear();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('treats the broadcast response as started and loads its operation', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/radionics/broadcast')) {
        return jsonResponse({
          status: 'started',
          session_id: 's-1',
          intention: 'healing',
          targets: ['all beings'],
          duration_seconds: 300,
          frequencies: null,
          solfeggio_names: null,
          crystal_output: null,
          scalar_output: null,
          operation_id: 'op-1',
        });
      }
      if (url.endsWith('/operations/op-1')) return jsonResponse(op());
      throw new Error(`unexpected fetch ${url}`);
    });
    globalThis.fetch = fetchMock as typeof fetch;

    const result = await useCrystalStore.getState().broadcastCrystal(300, 2, 'healing', ['all beings'], [42, 60]);

    expect(result?.status).toBe('started');
    expect(result?.operation_id).toBe('op-1');
    await vi.waitFor(() => expect(useOperationsStore.getState().byId['op-1']?.status).toBe('running'));
  });

  it('cancelBroadcast posts to the ledger cancel route and upserts the ended operation', async () => {
    useOperationsStore.getState().upsert(op());
    const fetchMock = vi.fn(async () =>
      jsonResponse({ operation: op({ status: 'cancelled', elapsed_seconds: 12.5, finished_at: '2026-10-15T10:00:12+00:00' }) }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    const ok = await useCrystalStore.getState().cancelBroadcast('op-1');

    expect(ok).toBe(true);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/operations\/op-1\/cancel$/);
    expect(init.method).toBe('POST');
    expect(useOperationsStore.getState().byId['op-1']?.status).toBe('cancelled');
  });

  it('cancelBroadcast reports false on 409 and refreshes the operation', async () => {
    useOperationsStore.getState().upsert(op());
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/cancel')) return jsonResponse({ detail: 'operation is already success' }, 409);
      return jsonResponse(op({ status: 'success', elapsed_seconds: 300 }));
    });
    globalThis.fetch = fetchMock as typeof fetch;

    const ok = await useCrystalStore.getState().cancelBroadcast('op-1');

    expect(ok).toBe(false);
    expect(useOperationsStore.getState().byId['op-1']?.status).toBe('success');
  });
});
