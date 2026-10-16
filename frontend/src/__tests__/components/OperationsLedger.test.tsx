/**
 * OperationsLedger shows statuses and timing straight from the record:
 *   - queued   → "queued"
 *   - running  → live count from started_at (this device's clock)
 *   - finished → the measured elapsed_seconds, never finished_at - started_at
 * plus error text for error/interrupted, the summary line, and working links.
 * Active rows can be cancelled (POST /operations/{id}/cancel); 409 and 404
 * get a calm note in the row.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import OperationsLedger from '../../components/Operations/OperationsLedger';
import { useOperationsStore } from '../../stores/operationsStore';
import type { Operation, OperationsSummary } from '../../types/operations';

const NOW = Date.parse('2026-10-14T12:00:00Z');

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
    created_at: '2026-10-14T11:00:00+00:00',
    started_at: null,
    finished_at: null,
    elapsed_seconds: null,
    ...overrides,
  };
}

const OPS: Operation[] = [
  op({ id: 'q', title: 'queued render', status: 'queued', created_at: '2026-10-14T11:59:00+00:00' }),
  op({
    id: 'r',
    title: 'running render',
    status: 'running',
    created_at: '2026-10-14T11:58:00+00:00',
    started_at: new Date(NOW - 83_000).toISOString(),
  }),
  op({
    id: 's',
    kind: 'broadcast',
    title: 'finished broadcast',
    status: 'success',
    created_at: '2026-10-14T11:00:00+00:00',
    started_at: '2026-10-14T11:00:00+00:00',
    // 10 minutes of wall clock between the stamps; the ledger must show the measured 147.25s.
    finished_at: '2026-10-14T11:10:00+00:00',
    elapsed_seconds: 147.25,
    working_id: 'w-123',
  }),
  op({
    id: 'e',
    title: 'failed render',
    status: 'error',
    created_at: '2026-10-14T10:00:00+00:00',
    started_at: '2026-10-14T10:00:00+00:00',
    finished_at: '2026-10-14T10:00:09+00:00',
    elapsed_seconds: 9.4,
    error: 'ComfyUI node_errors: UNETLoader missing model',
  }),
  op({
    id: 'i',
    kind: 'working',
    title: 'interrupted working',
    status: 'interrupted',
    created_at: '2026-10-14T09:00:00+00:00',
    started_at: '2026-10-14T09:00:00+00:00',
    finished_at: '2026-10-14T09:30:00+00:00',
    error: 'server restarted while this operation was in flight',
  }),
];

const SUMMARY: OperationsSummary = {
  since: null,
  by_status: { success: 4, queued: 1, running: 1 },
  by_kind: { render: 5, broadcast: 1 },
  active: 2,
  completed: 4,
  seconds_held: 3723,
};

let fetchSpy: ReturnType<typeof vi.fn>;
let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  useOperationsStore.getState().clear();
  vi.spyOn(Date, 'now').mockReturnValue(NOW);
  fetchSpy = vi.fn((url: string) => {
    const body = url.startsWith('/api/v1/operations/summary') ? SUMMARY : { operations: OPS, count: OPS.length };
    return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response);
  });
  vi.stubGlobal('fetch', fetchSpy);
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function renderLedger(path = '/operations/ledger'): Promise<void> {
  await act(async () => {
    root.render(
      <ConfigProvider>
        <MemoryRouter initialEntries={[path]}>
          <OperationsLedger />
        </MemoryRouter>
      </ConfigProvider>,
    );
  });
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
}

function row(status: string): HTMLElement {
  const el = container.querySelector<HTMLElement>(`[data-testid="ledger-row"][data-status="${status}"]`);
  if (!el) throw new Error(`no ${status} row`);
  return el;
}

function timing(status: string): string {
  return row(status).querySelector('[data-testid="ledger-timing"]')?.textContent ?? '';
}

describe('OperationsLedger', () => {
  it('fetches the ledger and summary through apiUrl', async () => {
    await renderLedger();
    const urls = fetchSpy.mock.calls.map((c) => String(c[0]));
    expect(urls).toContain('/api/v1/operations?limit=200');
    expect(urls).toContain('/api/v1/operations/summary');
  });

  it('lists operations newest first with kind, title and status', async () => {
    await renderLedger();
    const rows = Array.from(container.querySelectorAll<HTMLElement>('[data-testid="ledger-row"]'));
    expect(rows.map((r) => r.dataset.status)).toEqual(['queued', 'running', 'success', 'error', 'interrupted']);
    expect(row('success').textContent).toContain('broadcast');
    expect(row('success').textContent).toContain('finished broadcast');
  });

  it('shows queued as queued and running as a live count from started_at', async () => {
    await renderLedger();
    expect(timing('queued')).toMatch(/^queued/);
    expect(timing('running')).toContain('1m 23s since start');
    expect(timing('running')).toContain('counted on this device');
  });

  it('shows the measured elapsed_seconds for finished operations, not the stamp difference', async () => {
    await renderLedger();
    expect(timing('success')).toContain('took 2m 27s (measured)');
    expect(timing('success')).not.toContain('10m');
    expect(timing('success')).toContain('finished');
    expect(timing('error')).toContain('took 9.4s (measured)');
  });

  it('shows the error text for error and interrupted operations', async () => {
    await renderLedger();
    expect(row('error').querySelector('[data-testid="ledger-error"]')?.textContent).toContain('UNETLoader missing model');
    expect(row('interrupted').querySelector('[data-testid="ledger-error"]')?.textContent).toContain('server restarted');
    expect(row('success').querySelector('[data-testid="ledger-error"]')).toBeNull();
  });

  it('links to the working when working_id is set', async () => {
    await renderLedger();
    const link = row('success').querySelector('a');
    expect(link?.getAttribute('href')).toBe('/workings?open=w-123');
    expect(row('queued').querySelector('a')).toBeNull();
  });

  it('renders the summary line from /operations/summary', async () => {
    await renderLedger();
    const text = container.querySelector('[data-testid="ledger-summary"]')?.textContent ?? '';
    expect(text).toContain('4 completed');
    expect(text).toContain('1h 02m 03s');
    expect(text).toContain('2 active');
  });

  it('says plainly when the ledger cannot be read', async () => {
    fetchSpy.mockImplementation(() => Promise.resolve({ ok: false, status: 503, json: async () => ({}) } as Response));
    await renderLedger();
    expect(container.textContent).toContain('Could not load the ledger');
    expect(container.textContent).toContain('Summary unavailable');
  });

  describe('cancel', () => {
    type Reply = { status: number; body: unknown };
    let cancelReply: Reply;
    let opReply: Reply;

    beforeEach(() => {
      cancelReply = { status: 200, body: { operation: { ...OPS[1], status: 'cancelled', finished_at: '2026-10-14T12:00:00+00:00', elapsed_seconds: 83 } } };
      opReply = { status: 404, body: { detail: 'not found' } };
      fetchSpy.mockImplementation((url: string, init?: RequestInit) => {
        let reply: Reply;
        if (url.endsWith('/cancel') && init?.method === 'POST') reply = cancelReply;
        else if (url.startsWith('/api/v1/operations/summary')) reply = { status: 200, body: SUMMARY };
        else if (url.startsWith('/api/v1/operations?')) reply = { status: 200, body: { operations: OPS, count: OPS.length } };
        else reply = opReply;
        return Promise.resolve({
          ok: reply.status >= 200 && reply.status < 300,
          status: reply.status,
          json: async () => reply.body,
        } as Response);
      });
    });

    async function cancel(status: string): Promise<void> {
      const button = row(status).querySelector<HTMLButtonElement>('[data-testid="ledger-cancel"]');
      if (!button) throw new Error(`no cancel on ${status} row`);
      await act(async () => {
        button.click();
      });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });
    }

    function cancelCalls(): string[] {
      return fetchSpy.mock.calls
        .filter((c) => String(c[0]).endsWith('/cancel'))
        .map((c) => `${(c[1] as RequestInit).method} ${String(c[0])}`);
    }

    it('offers Cancel only on queued and running rows', async () => {
      await renderLedger();
      expect(row('queued').querySelector('[data-testid="ledger-cancel"]')).not.toBeNull();
      expect(row('running').querySelector('[data-testid="ledger-cancel"]')).not.toBeNull();
      for (const s of ['success', 'error', 'interrupted']) {
        expect(row(s).querySelector('[data-testid="ledger-cancel"]')).toBeNull();
      }
    });

    it('200: posts to the generic route and shows the cancelled record', async () => {
      await renderLedger();
      await cancel('running');
      expect(cancelCalls()).toEqual(['POST /api/v1/operations/r/cancel']);
      expect(container.querySelector('[data-testid="ledger-row"][data-status="running"]')).toBeNull();
      const cancelled = row('cancelled');
      expect(cancelled.textContent).toContain('running render');
      expect(cancelled.querySelector('[data-testid="ledger-cancel"]')).toBeNull();
      expect(cancelled.querySelector('[data-testid="ledger-cancel-note"]')).toBeNull();
    });

    it('200 while the loop is still stopping: says the cancel was requested', async () => {
      cancelReply = { status: 200, body: { operation: OPS[1] } };
      await renderLedger();
      await cancel('running');
      expect(row('running').querySelector('[data-testid="ledger-cancel-note"]')?.textContent).toBe(
        'Cancel requested; it stops at its next step.',
      );
    });

    it('409 for a finished operation: re-reads it and says it already finished', async () => {
      cancelReply = { status: 409, body: { detail: 'operation is already success' } };
      opReply = {
        status: 200,
        body: { ...OPS[0], status: 'success', finished_at: '2026-10-14T12:00:00+00:00', elapsed_seconds: 30 },
      };
      await renderLedger();
      await cancel('queued');
      const done = row('success');
      expect(done.textContent).toContain('queued render');
      const note = done.querySelector('[data-testid="ledger-cancel-note"]');
      expect(note?.textContent).toBe('This operation already finished (success).');
      expect(note?.className).not.toContain('red');
    });

    it("409 for a kind with no cancel handler: says it can't be cancelled", async () => {
      cancelReply = { status: 409, body: { detail: 'no cancel handler for kind tts' } };
      opReply = { status: 200, body: OPS[0] };
      await renderLedger();
      await cancel('queued');
      expect(row('queued').querySelector('[data-testid="ledger-cancel-note"]')?.textContent).toBe(
        "This operation can't be cancelled.",
      );
    });

    it('404: says the operation is no longer in the ledger', async () => {
      cancelReply = { status: 404, body: { detail: 'Operation not found' } };
      await renderLedger();
      await cancel('queued');
      expect(row('queued').querySelector('[data-testid="ledger-cancel-note"]')?.textContent).toBe(
        'This operation is no longer in the ledger.',
      );
    });
  });
});

describe('OperationsLedger ?op= deep link (from the Gallery)', () => {
  it('marks the linked row', async () => {
    await renderLedger('/operations/ledger?op=e');
    expect(row('error').dataset.focused).toBe('true');
    expect(container.querySelectorAll('[data-focused]')).toHaveLength(1);
  });

  it('fetches a linked operation that is not in the listed page', async () => {
    const older = op({ id: 'old', title: 'an older render', status: 'success', created_at: '2026-09-01T00:00:00+00:00' });
    fetchSpy.mockImplementation((url: string) => {
      const body = url.startsWith('/api/v1/operations/summary')
        ? SUMMARY
        : url === '/api/v1/operations/old'
          ? older
          : { operations: OPS, count: OPS.length };
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response);
    });
    await renderLedger('/operations/ledger?op=old');
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
    expect(fetchSpy.mock.calls.map((c) => String(c[0]))).toContain('/api/v1/operations/old');
    expect(container.querySelector<HTMLElement>('[data-focused]')?.textContent).toContain('an older render');
  });

  it('says so when the linked operation is gone', async () => {
    fetchSpy.mockImplementation((url: string) => {
      if (url === '/api/v1/operations/gone') {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: async () => ({ detail: 'operation not found' }),
        } as Response);
      }
      const body = url.startsWith('/api/v1/operations/summary') ? SUMMARY : { operations: OPS, count: OPS.length };
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response);
    });
    await renderLedger('/operations/ledger?op=gone');
    expect(container.querySelector('[data-testid="ledger-focus-error"]')?.textContent).toContain('gone');
  });
});
