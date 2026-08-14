/**
 * RenderMessageWidgets — run_working folio card.
 */
import React from 'react';
import { describe, it, expect } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { RenderMessageWidgets } from '../../components/CommandCenter/RenderMessageWidgets';

describe('Working folio widget', () => {
  it('renders dials and the spoken charge', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <RenderMessageWidgets
          toolCalls={[{
            status: 'success',
            tool_name: 'run_working',
            result: {
              working_id: 'wrk_test',
              intention: 'May the waters be clean',
              target: 'the watershed',
              rate_values: [12, 44, 70, 33, 81],
              spoken_charge: 'For the watershed: May the waters be clean.',
              saka_dawa: { saka_dawa_duchen: '2027-05-21', days_until_duchen: 281 },
              broadcast: { status: 'active' },
            },
          }]}
        />,
      );
    });
    expect(container.querySelector('[data-testid="working-folio"]')).not.toBeNull();
    expect(container.textContent).toContain('12 · 44 · 70 · 33 · 81');
    expect(container.textContent).toContain('May the waters be clean');
    root.unmount();
    container.remove();
  });
});
