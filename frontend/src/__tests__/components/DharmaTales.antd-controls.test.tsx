/**
 * S5 — DharmaTales must use Ant Design Select, not native <select> elements.
 *
 * Pre-fix: two raw `<select>` elements rendered inside the DharmaTales
 * generation form (Theme and Tradition), bypassing the ConfigProvider theme
 * and the documented Tailwind/AntD styling split
 * (docs/frontend-styling-guide.md). This test pins that ALL form controls
 * in DharmaTales come from AntD so the dark-mode visual identity holds.
 */
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider, theme } from 'antd';

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: { playSuccess: vi.fn(), playError: vi.fn(), playClick: vi.fn() },
}));

vi.mock('../../stores/uiStore', () => ({
  useUIStore: (selector?: (s: unknown) => unknown) => selector ? selector({ addToast: vi.fn() }) : { addToast: vi.fn() },
}));

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({ info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() }),
}));

globalThis.fetch = vi.fn().mockResolvedValue({
  ok: true,
  status: 200,
  json: async () => ({}),
} as Response);

describe('DharmaTales — AntD form controls (S5)', () => {
  it('contains zero native <select> elements (must use AntD Select)', async () => {
    const { default: DharmaTales } = await import('../../components/UI/DharmaTales');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
          <DharmaTales />
        </ConfigProvider>,
      );
      await new Promise((r) => setTimeout(r, 50));
    });

    const nativeSelects = container.querySelectorAll('select');
    expect(nativeSelects.length).toBe(0);

    root.unmount();
    container.remove();
  });

  it('renders AntD .ant-select dropdowns for Theme and Tradition', async () => {
    const { default: DharmaTales } = await import('../../components/UI/DharmaTales');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
          <DharmaTales />
        </ConfigProvider>,
      );
      await new Promise((r) => setTimeout(r, 50));
    });

    const antSelects = container.querySelectorAll('.ant-select');
    expect(antSelects.length).toBeGreaterThanOrEqual(2);

    root.unmount();
    container.remove();
  });
});
