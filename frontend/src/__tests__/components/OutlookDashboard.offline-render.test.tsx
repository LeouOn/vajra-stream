/**
 * S1 — Outlook must render without crashing when the backend returns
 * empty objects for /api/v1/outlook/* endpoints (offline posture).
 *
 * Pre-fix: `OutlookDashboard.tsx` crashed with "I.map is not a function"
 * inside a useMemo factory when fetch returned `{}`. Several downstream
 * child components received undefined or non-array props and called .map()
 * on them.
 *
 * The defensive `unwrap<T>` helper at L416 of OutlookDashboard.tsx accepts
 * either bare arrays, {items: []} envelopes, or {data: []} envelopes —
 * but other useMemo factories in the same file (and in child components)
 * also need to be defensive. This test pins the offline-renders-clean
 * contract end-to-end.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';

beforeEach(() => {
  // Stub ALL /api/** requests to return {} so the SPA renders offline.
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({}),
    } as Response);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('OutlookDashboard — offline render (S1)', () => {
  it('does not throw when all backend endpoints return {}', async () => {
    // Lazy import so module-level fetches in setup don't fire during the test
    const { default: OutlookDashboard } = await import(
      '../../components/UI/OutlookDashboard'
    );

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    let threw = false;
    try {
      await act(async () => {
        root.render(
          <ConfigProvider>
            <OutlookDashboard />
          </ConfigProvider>,
        );
      });
      // Let any deferred fetches fire
      await act(async () => {
        await new Promise((r) => setTimeout(r, 50));
      });
    } catch (e) {
      threw = true;
      console.error('Render threw:', e);
    }
    expect(threw).toBe(false);

    // The DOM should contain the page heading, not the ErrorBoundary fallback
    const text = container.textContent || '';
    // ErrorBoundary fallback title for /outlook is "Outlook failed to render"
    expect(text).not.toContain('Outlook failed to render');
    // The Segmented toggle "Guided Flow" / "Quick Generate" should be present
    expect(text).toMatch(/Guided Flow|Quick Generate|Generator|Universe|History/);
  }, 15000);
});
