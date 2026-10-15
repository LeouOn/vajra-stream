/**
 * Draws read as drawn (docs/DEVELOPMENT_ROADMAP.md, "the honest instrument").
 * RNG-derived potency and attunement values must carry a "drawn" label and
 * never render as a measured percentage.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import RitualVisualization from '../../components/UI/RitualVisualization';
import ProvenanceTag from '../../components/UI/ProvenanceTag';
import { AttunementChartTitle, ATTUNEMENT_CAPTION } from '../../components/UI/AttunementChart';
import { potencyProvenance } from '../../lib/provenance';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
});

const render = (node: React.ReactElement) => {
  act(() => { root.render(node); });
};

describe('ProvenanceTag', () => {
  it('names a draw as "drawn"', () => {
    render(<ProvenanceTag kind="draw" />);
    const tag = container.querySelector('[data-provenance="draw"]');
    expect(tag?.textContent).toBe('drawn');
  });

  it('names the other kinds plainly', () => {
    render(<><ProvenanceTag kind="computed" /><ProvenanceTag kind="record" /></>);
    expect(container.textContent).toContain('computed');
    expect(container.textContent).toContain('record');
  });
});

describe('RitualVisualization potency', () => {
  it('labels a drawn balancing potency as drawn, not as a percentage', () => {
    render(
      <RitualVisualization
        rates={{
          balancing: [
            { values: [12, 34, 56], name: 'Balance-1', potency: 0.6234, provenance: { values: 'draw', potency: 'draw' } },
          ],
        }}
      />,
    );
    const text = container.textContent ?? '';
    expect(text).toContain('Balance potency: 0.62');
    expect(container.querySelector('[data-provenance="draw"]')?.textContent).toBe('drawn');
    expect(text).not.toMatch(/Potency: \d+(\.\d+)?%/i);
  });

  it('treats a legacy potency without provenance as a draw', () => {
    render(<RitualVisualization rates={{ balancing: [{ values: [1, 2, 3], name: 'Balance-1', potency: 0.5 }] }} />);
    expect(container.querySelector('[data-provenance="draw"]')).not.toBeNull();
    expect(potencyProvenance({ potency: 0.5 })).toBe('draw');
  });

  it('shows no potency line for a computed signature with zero potency', () => {
    render(<RitualVisualization rates={{ signature: { values: [1, 2, 3], name: 'sig', potency: 0, provenance: { values: 'computed' } } }} />);
    expect(container.textContent).not.toContain('Potency');
  });
});

describe('AttunementChart header', () => {
  it('calls the e-meter values draws and makes no measurement claim', () => {
    render(<AttunementChartTitle />);
    expect(container.textContent).toContain('Attunement Draws');
    expect(container.querySelector('[data-provenance="draw"]')?.textContent).toBe('drawn');
    expect(container.textContent).not.toMatch(/metric/i);
    expect(ATTUNEMENT_CAPTION).toMatch(/not measurements/i);
  });
});
