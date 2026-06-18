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
 * Helper — pulls the first URL the component requested, regardless
 * of Request/URL object vs. raw string. Returns '' if no call yet.
 * ------------------------------------------------------------------ */
function firstFetchUrl(): string {
  const firstCall = fetchSpy.mock.calls[0];
  if (!firstCall) return '';
  const arg = firstCall[0];
  return typeof arg === 'string' ? arg : String((arg as any)?.url ?? arg);
}

describe('AstrologyExtractionPanel — locations endpoint URL', () => {
  it('fetches locations from a single /api/v1/astrology/locations path on mount', async () => {
    renderPanel();

    // Flush the on-mount async fetch.
    await act(async () => { await Promise.resolve(); });

    expect(fetchSpy).toHaveBeenCalled();
    const url = firstFetchUrl();

    // Contract: exactly one `/api/v1` prefix, not two.
    expect(url).toContain('/api/v1/astrology/locations');
    expect(url).not.toContain('api/v1/api/v1');
  });
});
