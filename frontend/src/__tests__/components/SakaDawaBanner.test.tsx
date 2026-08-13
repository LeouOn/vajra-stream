/**
 * SakaDawaBanner — active month vs upcoming Duchen (Losar-anchored).
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import type { SakaDawaResult } from '../../types';

const wsState: { sakaDawa: SakaDawaResult | null } = { sakaDawa: null };

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => wsState,
}));

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: { playTelemetry: vi.fn() },
}));

describe('SakaDawaBanner', () => {
  beforeEach(() => {
    wsState.sakaDawa = null;
  });

  it('renders the upcoming Duchen when the month is not active', async () => {
    const { default: SakaDawaBanner } = await import('../../components/UI/SakaDawaBanner');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    const payload: SakaDawaResult = {
      is_saka_dawa: false,
      is_duchen: false,
      multiplier: 1,
      current_date: '2026-08-12T00:00:00',
      losar: '2026-02-18',
      saka_dawa_month_start: '2027-05-07',
      saka_dawa_month_end: '2027-06-04',
      saka_dawa_duchen: '2027-05-21',
      days_until_duchen: 282,
    };

    await act(async () => {
      root.render(<SakaDawaBanner sakaDawa={payload} />);
    });

    expect(container.querySelector('[data-testid="saka-dawa-upcoming"]')).not.toBeNull();
    expect(container.textContent).toContain('Next Saka Dawa Duchen');
    expect(container.textContent).toMatch(/282 days/);

    root.unmount();
    container.remove();
  });

  it('renders the active banner on Duchen with the 100,000× badge', async () => {
    const { default: SakaDawaBanner } = await import('../../components/UI/SakaDawaBanner');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    const payload: SakaDawaResult = {
      is_saka_dawa: true,
      is_duchen: true,
      multiplier: 100000,
      current_date: '2026-05-31T00:00:00',
      saka_dawa_month_start: '2026-05-17',
      saka_dawa_month_end: '2026-06-15',
      saka_dawa_duchen: '2026-05-31',
      practice: {
        description: 'A compassionate blessing radiating merit for the Month of Merits.',
        tradition: 'Mahayana/Vajrayana',
        blessing_prompt: 'Generate an epic three-part sutra.',
      },
    };

    await act(async () => {
      root.render(<SakaDawaBanner sakaDawa={payload} />);
    });

    expect(container.querySelector('[data-testid="saka-dawa-active"]')).not.toBeNull();
    expect(container.textContent).toContain('Saka Dawa Duchen');
    expect(container.textContent).toContain('Merit ×100,000');

    root.unmount();
    container.remove();
  });
});
