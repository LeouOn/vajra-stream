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
  fetchSpy.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ providers: [], healthy_count: 0, total_count: 0 }),
  });
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

  it('fires a fetch to an LLM endpoint on mount', () => {
    renderPage();
    expect(fetchSpy).toHaveBeenCalled();
    const urls = fetchSpy.mock.calls.map((c: unknown[]) => String(c[0]));
    const hasLlmFetch = urls.some((u: string) => u.includes('/llm/'));
    expect(hasLlmFetch, `expected at least one fetch to /llm/*, got: ${urls.join(', ')}`).toBe(true);
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

  it('renders HTTP rows before any WebSocket push arrives', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        providers: [
          {
            provider: 'http-ollama',
            healthy: true,
            latency_ms: 45,
            models_available: 3,
            error: null,
          },
        ],
        healthy_count: 1,
        total_count: 1,
      }),
    });
    renderPage();
    await act(async () => {
      await Promise.resolve();
    });
    expect(container.textContent).toContain('http-ollama');
    expect(container.textContent).toContain('1 / 1 providers healthy');
    expect(container.textContent).toContain('45ms');
    expect(container.textContent).toContain('Healthy');
  });

  it('retains newer push data when a deferred HTTP response resolves late', async () => {
    let resolveDeferredFetch!: (val: any) => void;
    const deferredPromise = new Promise((resolve) => {
      resolveDeferredFetch = resolve;
    });
    fetchSpy.mockReturnValue(deferredPromise);

    renderPage();

    // Deliver a newer push before HTTP resolves
    act(() => {
      wsState.lastProviderHealthUpdate = Date.now();
      wsState.providerHealth = [
        {
          provider: 'ws-provider-fast',
          healthy: true,
          latency_ms: 15,
          models_available: 2,
          error: null,
        },
      ];
      root.render(
        <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
          <MemoryRouter>
            <ProviderSettings />
          </MemoryRouter>
        </ConfigProvider>,
      );
    });

    expect(container.textContent).toContain('ws-provider-fast');

    // Resolve deferred HTTP response with different provider data
    await act(async () => {
      resolveDeferredFetch({
        ok: true,
        status: 200,
        json: async () => ({
          providers: [
            {
              provider: 'stale-http-provider',
              healthy: true,
              latency_ms: 999,
              models_available: 1,
              error: null,
            },
          ],
        }),
      });
      await Promise.resolve();
    });

    // Newer push data must remain, stale HTTP response must not overwrite
    expect(container.textContent).toContain('ws-provider-fast');
    expect(container.textContent).not.toContain('stale-http-provider');
  });

  it('gives precedence to a genuine empty push over initial HTTP rows', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        providers: [
          {
            provider: 'initial-http-provider',
            healthy: true,
            latency_ms: 60,
            models_available: 4,
            error: null,
          },
        ],
      }),
    });

    renderPage();
    await act(async () => {
      await Promise.resolve();
    });
    expect(container.textContent).toContain('initial-http-provider');

    // A genuine empty push lands
    act(() => {
      wsState.lastProviderHealthUpdate = Date.now();
      wsState.providerHealth = [];
      root.render(
        <ConfigProvider theme={{ algorithm: antdTheme.darkAlgorithm }}>
          <MemoryRouter>
            <ProviderSettings />
          </MemoryRouter>
        </ConfigProvider>,
      );
    });

    // Genuine empty push wins over initial HTTP rows
    expect(container.textContent).not.toContain('initial-http-provider');
    expect(container.textContent).toContain('0 / 0 providers healthy');
    expect(container.textContent).toContain('No providers registered');
  });

function getAllByText(rootEl: HTMLElement, text: string): HTMLElement[] {
  return Array.from(rootEl.querySelectorAll('*')).filter(
    (el) => el.children.length === 0 && (el.textContent || '').includes(text)
  ) as HTMLElement[];
}

  it('shows error state on non-OK response distinctly from no providers registered', async () => {
    fetchSpy.mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: async () => ({}),
    });

    renderPage();
    await act(async () => {
      await Promise.resolve();
    });

    expect(getAllByText(container, 'Failed to fetch provider health')).toHaveLength(1);
    expect(getAllByText(container, 'HTTP 503')).toHaveLength(1);
    expect(container.textContent).not.toContain('No providers registered');
  });

  it('shows error state on network failure distinctly from no providers registered', async () => {
    fetchSpy.mockRejectedValue(new Error('Network connection failed'));

    renderPage();
    await act(async () => {
      await Promise.resolve();
    });

    expect(getAllByText(container, 'Failed to fetch provider health')).toHaveLength(1);
    expect(getAllByText(container, 'Network connection failed')).toHaveLength(1);
    expect(container.textContent).not.toContain('No providers registered');
  });

  it('handles unmount before fetch resolves without throwing or warning', async () => {
    const errorSpy = vi.spyOn(console, 'error');
    const warnSpy = vi.spyOn(console, 'warn');

    const healthJsonSpy = vi.fn().mockResolvedValue({
      providers: [
        {
          provider: 'unmounted-provider',
          healthy: true,
          latency_ms: 10,
          models_available: 1,
          error: null,
          last_checked: 0,
        },
      ],
    });

    let resolveHealthPending!: (val: any) => void;
    fetchSpy.mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/llm/providers/health')) {
        return new Promise((res) => { resolveHealthPending = res; });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({}),
      });
    });

    renderPage();

    act(() => {
      root.unmount();
      root = createRoot(container);
    });

    await act(async () => {
      resolveHealthPending({
        ok: true,
        status: 200,
        json: healthJsonSpy,
      });
      await Promise.resolve();
    });

    // Deterministic proof: response was not decoded after unmount
    expect(healthJsonSpy).not.toHaveBeenCalled();

    // Assert no React unmounted component warning was logged
    const unmountedErrors = errorSpy.mock.calls.filter(([msg]) =>
      typeof msg === 'string' && msg.includes('unmounted')
    );
    expect(unmountedErrors).toHaveLength(0);

    const unmountedWarns = warnSpy.mock.calls.filter(([msg]) =>
      typeof msg === 'string' && msg.includes('unmounted')
    );
    expect(unmountedWarns).toHaveLength(0);

    errorSpy.mockRestore();
    warnSpy.mockRestore();
  });
});
