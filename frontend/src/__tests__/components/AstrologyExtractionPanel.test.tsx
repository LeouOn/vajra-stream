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
