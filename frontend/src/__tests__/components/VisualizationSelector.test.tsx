/**
 * Tests for VisualizationSelector — the header dropdown that picks
 * the active visualization mode on the /visualizers route.
 *
 * Uses happy-dom + createRoot (same pattern as StatusIndicator.test.tsx)
 * to avoid pulling in @testing-library/react.
 *
 * Note: Antd's <Select> renders options into a portal on open, so we
 * assert on the always-visible labelRender output (the value display
 * in the collapsed Select) rather than the dropdown options list.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import VisualizationSelector from '../../components/UI/VisualizationSelector';

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

const render = (props: React.ComponentProps<typeof VisualizationSelector>) => {
  act(() => { root.render(<VisualizationSelector {...props} />); });
};

describe('<VisualizationSelector /> (happy-dom)', () => {
  it('renders Sacred Geometry by default', () => {
    render({ currentType: 'sacred-geometry', onChange: () => {} });
    expect(container.textContent).toContain('Sacred Geometry');
  });

  it('renders Astrocartography when currentType=astrocartography', () => {
    render({ currentType: 'astrocartography', onChange: () => {} });
    expect(container.textContent).toContain('Astrocartography');
  });

  it('renders Radionics when currentType=radionics', () => {
    render({ currentType: 'radionics', onChange: () => {} });
    expect(container.textContent).toContain('Radionics');
  });
});
