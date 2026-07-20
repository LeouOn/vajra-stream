/**
 * S2 — OperationsPage must render without crashing on /operations/broadcast
 * with all /api/** endpoints returning {} (offline posture).
 *
 * Pre-fix: BroadcastPanel threw "Cannot access '_e' before initialization"
 * (Temporal Dead Zone) when imported alongside OperationsPanel via the
 * OperationsPage grouped-route wrapper. Lazy imports or class-field ordering
 * caused the TDZ to fire on first render.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation(() => {
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

describe('OperationsPage /broadcast — offline render (S2)', () => {
  it('does not throw when all backend endpoints return {}', async () => {
    const { default: OperationsPage } = await import(
      '../../routes/Operations'
    );

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    let threw = false;
    try {
      await act(async () => {
        root.render(
          <ConfigProvider>
            <MemoryRouter initialEntries={['/operations/broadcast']}>
              <Routes>
                <Route path="/operations/:tab" element={<OperationsPage />} />
              </Routes>
            </MemoryRouter>
          </ConfigProvider>,
        );
      });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 50));
      });
    } catch (e) {
      threw = true;
      console.error('Render threw:', e);
    }
    expect(threw).toBe(false);

    const text = container.textContent || '';
    expect(text).not.toContain('Operations failed to render');
  }, 15000);
});
