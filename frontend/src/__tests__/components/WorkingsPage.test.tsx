/**
 * Workings ledger — hide/show rates and hide a sitting.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';

const originalFetch = globalThis.fetch;

const summary = {
  working_id: 'wrk_hide',
  intention: 'May the waters be clean',
  rate_values: [12, 44, 70, 33, 81],
  source: 'operations-composer',
  hidden: false,
};

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method || 'GET';
    let body: unknown = { workings: [summary] };
    if (url.includes('/operator/workings/wrk_hide') && method === 'PATCH') {
      body = { ...summary, hidden: true };
    } else if (url.includes('/operator/workings/wrk_hide') && method === 'GET') {
      body = summary;
    }
    return { ok: true, json: async () => body } as Response;
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('Workings page', () => {
  it('lists a working and can hide it', async () => {
    const { default: WorkingsPage } = await import('../../routes/Workings');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ConfigProvider>
          <WorkingsPage />
        </ConfigProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 30));
    });
    expect(container.textContent).toContain('May the waters be clean');
    expect(container.textContent).toContain('12 · 44 · 70 · 33 · 81');
    const hide = container.querySelector('[data-testid="hide-working"]');
    expect(hide).not.toBeNull();
    await act(async () => {
      hide?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    const patch = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.find(
      ([url, init]) => String(url).includes('/operator/workings/wrk_hide') && init?.method === 'PATCH',
    );
    expect(patch).toBeTruthy();
    root.unmount();
    container.remove();
  });
});
