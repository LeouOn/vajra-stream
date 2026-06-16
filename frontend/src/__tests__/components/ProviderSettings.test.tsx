/**
 * Vitest coverage for ProviderSettings (Task 3.5 of the UI/UX overhaul plan).
 *
 * The component renders a live health table fed by `useWebSocketStable`'s
 * `providerHealth` and `lastProviderHealthUpdate`, with a one-shot REST
 * fetch on mount. We mock the WS hook at the module level and stub `fetch`
 * so the table can be driven deterministically.
 *
 * Coverage:
 *   - empty state ("No providers registered") when providerHealth is []
 *   - one-shot fetch is invoked on mount
 *   - rows render with provider name + Healthy/Down Tag
 *   - "X / Y providers healthy" summary line tracks the live state
 *   - latency column renders '—' for null and '<n>ms' for numbers
 *   - last-update label reflects lastProviderHealthUpdate
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';

/* ------------------------------------------------------------------ *
 * Module-level mocks.
 * ------------------------------------------------------------------ */
const wsState = {
  providerHealth: [] as any[],
  lastProviderHealthUpdate: null as number | null,
};

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => wsState,
}));

/* fetch stub — the component does a one-shot GET /llm/providers/health. */
const fetchSpy = vi.fn();
beforeEach(() => {
  fetchSpy.mockReset();
  fetchSpy.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
  (globalThis as any).fetch = fetchSpy;
});

import ProviderSettings from '../../components/Settings/ProviderSettings';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  wsState.providerHealth = [];
  wsState.lastProviderHealthUpdate = null;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
});

function renderPage() {
  act(() => {
    root.render(
      <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
        <MemoryRouter>
          <ProviderSettings />
        </MemoryRouter>
      </ConfigProvider>,
    );
  });
}

/* ------------------------------------------------------------------ *
 * Tests
 * ------------------------------------------------------------------ */
describe('ProviderSettings', () => {
  it('renders the page header', () => {
    renderPage();
    expect(container.textContent).toContain('LLM Provider Settings');
    expect(container.textContent).toContain('Health-aware failover registry');
  });

  it('shows the empty state when providerHealth is empty', () => {
    renderPage();
    expect(container.textContent).toContain('No providers registered');
    expect(container.textContent).toContain('0 / 0 providers healthy');
  });

  it('fires the one-shot GET /llm/providers/health on mount', () => {
    renderPage();
    expect(fetchSpy).toHaveBeenCalled();
    const call = fetchSpy.mock.calls[0];
    expect(call[0]).toContain('/llm/providers/health');
  });

  it('renders Healthy / Down tags and the count summary when rows exist', () => {
    wsState.providerHealth = [
      {
        provider: 'openai',
        healthy: true,
        latency_ms: 120,
        models_available: 5,
        error: null,
      },
      {
        provider: 'anthropic',
        healthy: false,
        latency_ms: null,
        models_available: 0,
        error: 'connection refused',
      },
    ];
    renderPage();
    expect(container.textContent).toContain('openai');
    expect(container.textContent).toContain('anthropic');
    expect(container.textContent).toContain('Healthy');
    expect(container.textContent).toContain('Down');
    expect(container.textContent).toContain('1 / 2 providers healthy');
    // Latency: 120ms for openai, '—' for anthropic.
    expect(container.textContent).toContain('120ms');
    expect(container.textContent).toContain('—');
  });

  it('shows the error text for an unhealthy provider', () => {
    wsState.providerHealth = [
      {
        provider: 'mistral',
        healthy: false,
        latency_ms: 999,
        models_available: 0,
        error: 'upstream 503',
      },
    ];
    renderPage();
    expect(container.textContent).toContain('upstream 503');
  });

  it('uses "awaiting first push" before any WS push lands but after fetch', async () => {
    renderPage();
    // After mount, the one-shot fetch has completed (initialFetchAttempted=true)
    // but no WS push has arrived → "awaiting first push".
    await act(async () => { await Promise.resolve(); });
    expect(container.textContent).toContain('awaiting first push');
  });

  it('shows the formatted last-update time when lastProviderHealthUpdate is set', () => {
    const ts = new Date('2024-06-15T12:34:56Z').getTime();
    wsState.lastProviderHealthUpdate = ts;
    wsState.providerHealth = [
      { provider: 'openai', healthy: true, latency_ms: 10, models_available: 1, error: null },
    ];
    renderPage();
    // The component formats via toLocaleTimeString — just assert a non-empty
    // "Last update:" line is present and not one of the placeholder strings.
    expect(container.textContent).toContain('Last update:');
    expect(container.textContent).not.toContain('awaiting first push');
    expect(container.textContent).not.toContain('Last update: never');
  });

  it('renders the failover log placeholder', () => {
    renderPage();
    expect(container.textContent).toContain('Failover Log');
    expect(container.textContent).toContain('No failover events recorded.');
  });

  it('counts only healthy providers in the summary', () => {
    wsState.providerHealth = [
      { provider: 'a', healthy: true,  latency_ms: 1, models_available: 1, error: null },
      { provider: 'b', healthy: true,  latency_ms: 2, models_available: 1, error: null },
      { provider: 'c', healthy: false, latency_ms: 3, models_available: 0, error: 'x' },
    ];
    renderPage();
    expect(container.textContent).toContain('2 / 3 providers healthy');
  });
});
