/**
 * WorkingInstrument — tactile folio board + kamea rate trace.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { useRateStore } from '../../stores/rateStore';
import WorkingInstrument, { rateToKameaCoords, paletteForFolio } from '../../components/CommandCenter/WorkingInstrument';

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: { playSuccess: vi.fn(), playDialAdjust: vi.fn(), playClick: vi.fn() },
}));

describe('rateToKameaCoords', () => {
  it('maps five dials onto Saturn square cells', () => {
    const coords = rateToKameaCoords([12, 44, 70, 33, 81]);
    expect(coords).toHaveLength(5);
    expect(coords.every((c) => c.x >= 0 && c.x <= 2 && c.y >= 0 && c.y <= 2)).toBe(true);
    expect(coords.map((c) => c.value)).toEqual([3, 8, 7, 6, 9]);
  });
});

describe('paletteForFolio', () => {
  it('uses transcendence on Duchen-scale merit', () => {
    expect(paletteForFolio({ saka_dawa: { multiplier: 100000 } })).toBe('transcendence');
    expect(paletteForFolio({ saka_dawa: { is_saka_dawa: true, multiplier: 10000 } })).toBe('compassion');
    expect(paletteForFolio({})).toBe('peace');
  });
});

describe('WorkingInstrument', () => {
  beforeEach(() => {
    useRateStore.setState({ loadedWorkingId: null, boardRevision: 0 });
  });

  it('renders dials and loads them onto the board', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <WorkingInstrument
          folio={{
            working_id: 'wrk_test',
            intention: 'May the waters be clean',
            rate_values: [12, 44, 70, 33, 81],
            solfeggio_names: ['UT', 'RE', 'MI', 'FA', 'SOL'],
            frequencies: [396, 417, 528, 639, 741],
            source: 'operations-composer',
            hour_stamp: { planetary_hour: 'Venus', moon_phase: 'Waxing Gibbous' },
          }}
        />,
      );
    });
    expect(container.querySelector('[data-testid="working-instrument"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="working-dials"]')).not.toBeNull();
    expect(container.textContent).toContain('Hour of Venus');
    expect(container.textContent).toContain('geometric witness');

    await act(async () => {
      container.querySelector('[data-testid="load-onto-board"]')?.dispatchEvent(
        new MouseEvent('click', { bubbles: true }),
      );
    });
    expect(useRateStore.getState().currentRate.values).toEqual([12, 44, 70, 33, 81]);
    expect(useRateStore.getState().loadedWorkingId).toBe('wrk_test');

    root.unmount();
    container.remove();
  });
});
