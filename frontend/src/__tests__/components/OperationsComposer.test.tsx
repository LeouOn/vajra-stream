/**
 * Ritual composer seals a real working folio via POST /operator/working.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';

const originalFetch = globalThis.fetch;

const sealedFolio = {
  working_id: 'wrk_composer',
  intention: 'May the waters be clean',
  target: 'all beings',
  rate_values: [12, 44, 70, 33, 81],
  spoken_charge: 'For all beings: May the waters be clean.',
  source: 'operations-composer',
  hour_stamp: { planetary_hour: 'Venus', moon_phase: 'Waxing Gibbous' },
  saka_dawa: { saka_dawa_duchen: '2027-05-21', days_until_duchen: 281 },
  broadcast: { status: 'active' },
};

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
    const url = String(input);
    let body: unknown = {};
    if (url.includes('/divination/tarot/draw')) {
      body = { cards: [{ name: 'The Star', reversed: false }], spread: [] };
    } else if (url.includes('/astrology/planetary-hours')) {
      body = { current_planetary_hour: 'Venus' };
    } else if (url.includes('/astrology/current')) {
      body = { astrology: { moon_phase: { phase_name: 'Waxing Gibbous' } } };
    } else if (url.includes('/operator/working') && !url.includes('/workings/')) {
      body = sealedFolio;
    } else if (url.includes('/speak') || url.includes('/manifest') || url.includes('/witness')) {
      body = { ...sealedFolio, spoken: { status: 'ok' }, witness: { status: 'ok' } };
    }
    return {
      ok: true,
      json: async () => body,
    } as Response;
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('Operations ritual composer', () => {
  it('seals a working from the composer intention', async () => {
    const { default: OperationsPanel } = await import('../../components/UI/OperationsPanel');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <ConfigProvider>
          <OperationsPanel />
        </ConfigProvider>,
      );
    });

    const composerTab = Array.from(container.querySelectorAll('button')).find(
      (el) => el.textContent?.includes('Ritual Composer'),
    );
    expect(composerTab).toBeTruthy();
    await act(async () => {
      composerTab?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(container.querySelector('[data-testid="seal-working"]')).not.toBeNull();
    expect(container.textContent).toContain('Oracle draw');
    expect(container.textContent).toContain('Seal the working');

    const textarea = container.querySelector('textarea');
    expect(textarea).not.toBeNull();
    await act(async () => {
      if (!textarea) return;
      const proto = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
      proto?.set?.call(textarea, 'May the waters be clean');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });

    await act(async () => {
      container.querySelector('[data-testid="seal-working"]')?.dispatchEvent(
        new MouseEvent('click', { bubbles: true }),
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 80));
    });

    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    const workingCall = calls.find(([url, init]) =>
      String(url).includes('/api/v1/operator/working') && init?.method === 'POST',
    );
    expect(workingCall).toBeTruthy();
    const payload = JSON.parse(String(workingCall?.[1]?.body || '{}')) as {
      intention: string;
      source: string;
      planetary_hour?: string;
    };
    expect(payload.intention).toBe('May the waters be clean');
    expect(payload.source).toBe('operations-composer');
    expect(payload.planetary_hour).toBe('Venus');

    root.unmount();
    container.remove();
  }, 15000);
});
