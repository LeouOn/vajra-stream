/**
 * Vitest coverage for AstrologyExtractionPanel — URL prefix regression test.
 *
 * Wave 1 Task 8 (RED-GREEN-REFACTOR):
 *   The panel's on-mount effect historically called
 *   `${API_BASE}/api/v1/astrology/locations`, but API_BASE already
 *   ends in `/api/v1`, so the request resolved to the doubled path
 *   `/api/v1/api/v1/astrology/locations` → 404.
 *
 * Correct call: `${API_BASE}/astrology/locations` → `/api/v1/astrology/locations`.
 *
 * This test pins the contract by spying on `globalThis.fetch` and
 * asserting (a) the URL has a single `/api/v1` prefix and (b) the
 * doubled `api/v1/api/v1` substring never reappears.
 *
 * Pattern follows ProviderSettings.test.tsx: raw createRoot + act,
 * ConfigProvider + MemoryRouter wrapper, module-level fetch stub.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';

/* ------------------------------------------------------------------ *
 * fetch stub — defaults to an empty 200 so the on-mount effect
 * settles cleanly. Tests inspect `fetchSpy.mock.calls` to assert URL.
 * ------------------------------------------------------------------ */
const fetchSpy = vi.fn();
beforeEach(() => {
  fetchSpy.mockReset();
  fetchSpy.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
  (globalThis as any).fetch = fetchSpy;
});

import AstrologyExtractionPanel from '../../components/UI/AstrologyExtractionPanel';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
});

function renderPanel() {
  act(() => {
    root.render(
      <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
        <MemoryRouter>
          <AstrologyExtractionPanel />
        </MemoryRouter>
      </ConfigProvider>,
    );
  });
}

/* ------------------------------------------------------------------ *
 * Helper — scans all fetch calls for the astrology/locations URL.
 * (Was firstFetchUrl, but useWebSocketStable now fires a /ready check
 * before the locations fetch, so the locations call may not be calls[0].)
 * ------------------------------------------------------------------ */
function locationsFetchUrl(): string {
  const locationsCall = fetchSpy.mock.calls.find((call) => {
    const arg = call[0];
    const url = typeof arg === 'string' ? arg : String((arg as any)?.url ?? arg);
    return url.includes('astrology/locations');
  });
  if (!locationsCall) return '';
  const arg = locationsCall[0];
  return typeof arg === 'string' ? arg : String((arg as any)?.url ?? arg);
}

/* ------------------------------------------------------------------ *
 * Helpers — Replay/Results journey. AntD Tabs mount TabPanes lazily,
 * so these tests click the real tab buttons and then poll (waitForCond)
 * for the async fetch + render to settle, the raw-createRoot equivalent
 * of findBy/waitFor.
 * ------------------------------------------------------------------ */

/** Click the AntD tab whose visible label is `name` (in `rootEl`, default the shared container). */
async function clickTab(name: string, rootEl: HTMLElement = container) {
  const tab = Array.from(rootEl.querySelectorAll('.ant-tabs-tab')).find(
    (t) => (t.textContent ?? '').trim() === name,
  );
  if (!tab) throw new Error(`tab not found: ${name}`);
  await act(async () => {
    tab.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

/** Poll `cond` inside act-flushed macrotasks until true or timeout. */
async function waitForCond(cond: () => boolean, timeoutMs = 2000): Promise<void> {
  const start = Date.now();
  while (!cond()) {
    if (Date.now() - start > timeoutMs) {
      throw new Error('waitForCond: condition not met within ' + timeoutMs + 'ms');
    }
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
}

async function flushAsync(times = 4) {
  for (let i = 0; i < times; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

const tableRows = () => container.querySelectorAll('.ant-table-row');

const cellTexts = () =>
  Array.from(container.querySelectorAll('.ant-table-row td')).map(
    (td) => (td.textContent ?? '').trim(),
  );

/** Click the first table row button whose exact label is `label`. */
async function clickRowButton(label: string) {
  const btn = Array.from(container.querySelectorAll('tbody button')).find(
    (b) => (b.textContent ?? '').trim() === label,
  );
  if (!btn) throw new Error(`row button not found: ${label}`);
  await act(async () => {
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

interface MockResponse {
  ok: boolean;
  status: number;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
}

/** Route fetch mocks by URL so mount-time calls (locations, /ready) stay 200. */
function mockFetchByUrl(handler: (url: string) => MockResponse) {
  fetchSpy.mockImplementation(async (input: unknown) => {
    const url = typeof input === 'string' ? input : String((input as { url?: string })?.url ?? input);
    return handler(url);
  });
}

const RUN_7 = {
  id: 7,
  created_at: '2026-07-05T12:00:00',
  status: 'done',
  total_tuples: 4,
  completed_tuples: 4,
};

const envelopeWith = (runs: unknown[]) => ({
  limit: 50,
  offset: 0,
  total: runs.length,
  runs,
});

const RUN_8 = {
  id: 8,
  created_at: '2026-08-08T08:00:00',
  status: 'done',
  total_tuples: 2,
  completed_tuples: 2,
};

/** Click the View button in the table row whose ID cell equals `id`. */
async function clickViewForRow(id: number | string) {
  const row = Array.from(container.querySelectorAll('.ant-table-row')).find((tr) => {
    const firstCell = tr.querySelector('td');
    return (firstCell?.textContent ?? '').trim() === String(id);
  });
  if (!row) throw new Error(`row not found for id ${id}`);
  const btn = Array.from(row.querySelectorAll('button')).find(
    (b) => (b.textContent ?? '').trim() === 'View',
  );
  if (!btn) throw new Error(`View button not found in row ${id}`);
  await act(async () => {
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

function fetchUrlOf(call: unknown[]): string {
  const arg = (call as unknown[])[0];
  return typeof arg === 'string' ? arg : String((arg as { url?: string })?.url ?? arg);
}

/** URL of the last fetch call made so far (for ordering assertions). */
function lastFetchUrl(): string {
  const calls = fetchSpy.mock.calls;
  return calls.length ? fetchUrlOf(calls[calls.length - 1]) : '';
}

type ResolveResults = (text: string) => void;

/**
 * Mock fetch so every /astrology/runs/{id}/results request returns a promise
 * the test resolves manually; the list endpoint serves both runs.
 */
function mockDeferredResults(resultsDeferred: Map<number, ResolveResults>) {
  fetchSpy.mockImplementation(async (input: unknown) => {
    const url = typeof input === 'string' ? input : String((input as { url?: string })?.url ?? input);
    const match = url.match(/\/astrology\/runs\/(\d+)\/results/);
    if (match) {
      const runId = Number(match[1]);
      return new Promise((resolve) => {
        resultsDeferred.set(runId, (text: string) =>
          resolve({ ok: true, status: 200, text: async () => text }),
        );
      });
    }
    if (url.includes('/astrology/runs')) {
      return { ok: true, status: 200, json: async () => envelopeWith([RUN_7, RUN_8]) };
    }
    return { ok: true, status: 200, json: async () => [] };
  });
}

describe('AstrologyExtractionPanel — locations endpoint URL', () => {
  it('fetches locations from a single /api/v1/astrology/locations path on mount', async () => {
    renderPanel();

    // Flush the on-mount async fetch.
    await act(async () => { await Promise.resolve(); });

    expect(fetchSpy).toHaveBeenCalled();
    const url = locationsFetchUrl();

    // Contract: exactly one `/api/v1` prefix, not two.
    expect(url).toContain('/api/v1/astrology/locations');
    expect(url).not.toContain('api/v1/api/v1');
  });
});

/* ------------------------------------------------------------------ *
 * Regression: Replay tab must accept both response shapes from
 * GET /api/v1/astrology/runs. The backend wraps the list in a
 * {limit, offset, total, runs: [...]} envelope, but the panel
 * historically did `setRuns(await r.json())` — feeding the whole
 * envelope object to antd <Table dataSource> which then crashed with
 * "runs.some is not a function" (Table's internal variable name) and
 * bubbled up to the "Cosmic Clock failed to load" ErrorBoundary.
 *
 * The fix unwraps defensively:
 *   - bare array  → use directly
 *   - {runs: [...]} envelope → take .runs
 *   - anything else → fall back to []
 *
 * These tests verify the panel MOUNTS WITHOUT CRASHING under each
 * shape. They do not click the Replay tab — that's a deeper
 * integration test. The point is: with the old code, mounting the
 * panel under the envelope shape would throw inside ReplayTab's
 * fetch callback and bubble to the ErrorBoundary.
 * ------------------------------------------------------------------ */
describe('AstrologyExtractionPanel — Replay runs envelope unwrap', () => {
  it('mounts without crashing when backend returns the {runs: [...]} envelope', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        limit: 50,
        offset: 0,
        total: 1,
        runs: [
          { id: 1, created_at: '2026-07-05T12:00:00', status: 'done', total_tuples: 4, completed_tuples: 4 },
        ],
      }),
    });

    renderPanel();
    // Flush the on-mount fetch + state update.
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await Promise.resolve(); });

    // Critical contract: no ErrorBoundary fallback text rendered. If the
    // envelope weren't unwrapped, antd Table would throw "runs.some is not a
    // function" and the parent ErrorBoundary would replace the panel with
    // "Cosmic Clock failed to load".
    expect(container.textContent).not.toMatch(/failed to load/i);
    expect(container.textContent).toMatch(/Setup|Sweep|Results|Replay/);
  });

  it('mounts without crashing when backend returns a bare array', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [
        { id: 42, created_at: '2026-07-05T12:00:00', status: 'partial', total_tuples: 4, completed_tuples: 2 },
      ],
    });

    renderPanel();
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await Promise.resolve(); });

    expect(container.textContent).not.toMatch(/failed to load/i);
  });

  it('mounts without crashing when backend returns an unexpected error envelope', async () => {
    // Simulate a validation/error payload that the frontend doesn't expect —
    // the panel must NOT crash; it should silently render with no runs.
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ detail: 'unexpected validation error' }),
    });

    renderPanel();
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await Promise.resolve(); });

    expect(container.textContent).not.toMatch(/failed to load/i);
  });
});

/* ------------------------------------------------------------------ *
 * Replay list + View navigation journey (feature 2).
 * Clicks the real AntD tabs, unwraps the real backend envelope shape
 * (GET /api/v1/astrology/runs → {limit, offset, total, runs}), and
 * verifies the View action selects the run and activates Results,
 * which then requests that run's markdown results.
 * ------------------------------------------------------------------ */
describe('AstrologyExtractionPanel — Replay list and View navigation', () => {
  it('lists saved runs after clicking Replay and opens Results with that run on View', async () => {
    mockFetchByUrl((url) => {
      if (url.includes('/astrology/runs/') && url.includes('/results')) {
        return { ok: true, status: 200, text: async () => '# Run 7 results markdown' };
      }
      if (url.includes('/astrology/runs')) {
        return { ok: true, status: 200, json: async () => envelopeWith([RUN_7]) };
      }
      if (url.includes('/astrology/locations')) {
        return { ok: true, status: 200, json: async () => [] };
      }
      return { ok: true, status: 200, json: async () => ({}), text: async () => '' };
    });

    renderPanel();
    await flushAsync();

    // Replay tab is lazily mounted — clicking it triggers the runs fetch.
    await clickTab('Replay');
    await waitForCond(() => tableRows().length === 1);

    // The saved run's fields are rendered as the row.
    expect(cellTexts()).toContain('7');
    expect(cellTexts()).toContain('done');

    // View: selects the run and activates the Results tab.
    await clickRowButton('View');
    await waitForCond(() => {
      const active = container.querySelector('.ant-tabs-tab-active');
      return !!active && (active.textContent ?? '').includes('Results');
    });

    // Results fetches the selected run's markdown.
    await waitForCond(() =>
      fetchSpy.mock.calls.some((call) => {
        const url = typeof call[0] === 'string' ? call[0] : String((call[0] as { url?: string })?.url ?? call[0]);
        return url.includes('/astrology/runs/7/results');
      }),
    );
    await waitForCond(() => (container.textContent ?? '').includes('Run 7 Results'));
    expect(container.textContent).toContain('# Run 7 results markdown');
  });

  it('never renders envelope metadata (limit/offset/total) as table rows', async () => {
    // A run with a legitimate completed_tuples of 0 must not be mistaken for
    // leaked envelope metadata (offset 0): discrimination comes from the row
    // count and the ID cell, not from banning the string '0'.
    const runWithZeroCompleted = { ...RUN_7, completed_tuples: 0 };
    mockFetchByUrl((url) => {
      if (url.includes('/astrology/runs')) {
        return {
          ok: true,
          status: 200,
          json: async () => envelopeWith([runWithZeroCompleted]), // limit 50, offset 0, total 1
        };
      }
      return { ok: true, status: 200, json: async () => [] };
    });

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => tableRows().length === 1);

    // Exactly the run record is a row; the envelope's metadata scalars are not
    // rendered as an extra row, and the run id leads the row.
    expect(tableRows().length).toBe(1);
    const cells = cellTexts();
    expect(cells[0]).toBe('7');
    expect(cells).toContain('0'); // legitimate completed_tuples 0
    expect(cells.some((t) => t === '50')).toBe(false); // limit must not appear
  });

  it('shows the empty state for an empty envelope', async () => {
    mockFetchByUrl((url) => {
      if (url.includes('/astrology/runs')) {
        return { ok: true, status: 200, json: async () => envelopeWith([]) };
      }
      return { ok: true, status: 200, json: async () => [] };
    });

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => (container.textContent ?? '').includes('No saved runs yet'));
    expect(tableRows().length).toBe(0);
  });

  it('tolerates a malformed envelope without crashing or inventing rows', async () => {
    mockFetchByUrl((url) => {
      if (url.includes('/astrology/runs')) {
        return { ok: true, status: 200, json: async () => ({ detail: 'unexpected validation error' }) };
      }
      return { ok: true, status: 200, json: async () => [] };
    });

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => (container.textContent ?? '').includes('No saved runs yet'));

    // Malformed (200 + wrong shape) is tolerated as empty, NOT shown as an HTTP error.
    expect(tableRows().length).toBe(0);
    expect(container.textContent).not.toMatch(/failed to load/i);
  });

  it('shows an HTTP error state when listing runs fails', async () => {
    mockFetchByUrl((url) => {
      if (url.includes('/astrology/runs')) {
        return { ok: false, status: 500 };
      }
      return { ok: true, status: 200, json: async () => [] };
    });

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => (container.textContent ?? '').includes('Failed to load runs'));
    expect(container.textContent).toContain('500');
    expect(tableRows().length).toBe(0);
  });

  it('shows an error state when the runs request rejects (network failure)', async () => {
    fetchSpy.mockImplementation(async (input: unknown) => {
      const url = typeof input === 'string' ? input : String((input as { url?: string })?.url ?? input);
      if (url.includes('/astrology/runs')) {
        throw new Error('network down');
      }
      return { ok: true, status: 200, json: async () => [] };
    });

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => (container.textContent ?? '').includes('Failed to load runs'));
    expect(container.textContent).toContain('network down');
    expect(tableRows().length).toBe(0);
  });
});

/* ------------------------------------------------------------------ *
 * Results race + unmount invalidation (F2-FIX).
 * View run 7 then run 8; the deferred /results promises resolve in both
 * orders. The card title AND body must always agree with the currently
 * selected run (8): a late run-7 response may never overwrite it.
 * ------------------------------------------------------------------ */
describe('AstrologyExtractionPanel — results fetch race and unmount', () => {
  it('late run-7 results cannot overwrite run 8 (resolve 8 first, then 7)', async () => {
    const resultsDeferred = new Map<number, ResolveResults>();
    mockDeferredResults(resultsDeferred);

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => tableRows().length === 2);

    // View run 7, then switch back and View run 8.
    await clickViewForRow(7);
    await waitForCond(() => resultsDeferred.has(7));
    await clickTab('Replay');
    await clickViewForRow(8);
    await waitForCond(() => resultsDeferred.has(8));

    // Resolve the CURRENT selection's results first.
    const resolve8 = resultsDeferred.get(8);
    if (!resolve8) throw new Error('run 8 results request not started');
    resolve8('# Run 8 MD');
    await waitForCond(() => (container.textContent ?? '').includes('Run 8 Results'));
    await waitForCond(() => (container.textContent ?? '').includes('# Run 8 MD'));

    // Then the stale run-7 response lands late.
    const resolve7 = resultsDeferred.get(7);
    if (!resolve7) throw new Error('run 7 results request not started');
    resolve7('# Run 7 MD');
    await flushAsync();

    // Title AND body still belong to run 8; run 7's body never appears.
    expect(container.textContent).toContain('Run 8 Results');
    expect(container.textContent).toContain('# Run 8 MD');
    expect(container.textContent).not.toContain('# Run 7 MD');
  });

  it('late run-7 results cannot overwrite run 8 (resolve 7 first, then 8)', async () => {
    const resultsDeferred = new Map<number, ResolveResults>();
    mockDeferredResults(resultsDeferred);

    renderPanel();
    await flushAsync();
    await clickTab('Replay');
    await waitForCond(() => tableRows().length === 2);

    await clickViewForRow(7);
    await waitForCond(() => resultsDeferred.has(7));
    await clickTab('Replay');
    await clickViewForRow(8);
    await waitForCond(() => resultsDeferred.has(8));

    // The STALE run-7 response resolves first, while run 8 is selected and
    // its own request is still pending (card hidden behind the spinner).
    const resolve7 = resultsDeferred.get(7);
    if (!resolve7) throw new Error('run 7 results request not started');
    resolve7('# Run 7 MD');
    await flushAsync();
    expect(container.textContent).not.toContain('# Run 7 MD');

    // Then the current selection's results land.
    const resolve8 = resultsDeferred.get(8);
    if (!resolve8) throw new Error('run 8 results request not started');
    resolve8('# Run 8 MD');
    await waitForCond(() => (container.textContent ?? '').includes('# Run 8 MD'));
    expect(container.textContent).toContain('Run 8 Results');
    expect(container.textContent).not.toContain('# Run 7 MD');
  });

  it('unmounting while the runs list fetch is pending applies no state afterwards', async () => {
    // Deterministic probe: replace the store toast so any post-unmount catch
    // path (setError + addToast) is observable without relying on React
    // warnings (React 18 no longer emits them for late setState).
    const { useUIStore } = await import('../../stores/uiStore');
    const addToastSpy = vi.fn();
    useUIStore.setState({ addToast: addToastSpy });

    let rejectList: ((err: Error) => void) | null = null;
    fetchSpy.mockImplementation(async (input: unknown) => {
      const url = typeof input === 'string' ? input : String((input as { url?: string })?.url ?? input);
      if (url.includes('/astrology/runs') && !url.includes('/results')) {
        return new Promise((_resolve, reject) => {
          rejectList = reject;
        });
      }
      return { ok: true, status: 200, json: async () => [] };
    });

    // Isolated root so unmounting here does not fight the shared harness.
    const localContainer = document.createElement('div');
    document.body.appendChild(localContainer);
    const localRoot = createRoot(localContainer);
    act(() => {
      localRoot.render(
        <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
          <MemoryRouter>
            <AstrologyExtractionPanel />
          </MemoryRouter>
        </ConfigProvider>,
      );
    });
    await flushAsync();
    await clickTab('Replay', localContainer);
    await waitForCond(() => rejectList !== null);

    // Unmount, THEN let the pending list request fail late.
    act(() => {
      localRoot.unmount();
    });
    localContainer.remove();
    await act(async () => {
      rejectList?.(new Error('late network failure'));
      await Promise.resolve();
    });
    await flushAsync();

    expect(addToastSpy).not.toHaveBeenCalled();
  });
});
