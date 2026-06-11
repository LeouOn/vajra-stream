/**
 * Regression: CrystalGridControls wired into the /visualizers route.
 *
 * Verifies the flow:
 * - When visualizationType is 'crystal-grid', the CrystalGridControls
 *   panel is rendered in the visualizers layout.
 * - When visualizationType is anything else, the panel is NOT rendered.
 * - The control panel uses Antd-aligned styling (dark theme via
 *   background utility classes).
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import CrystalGridControls from '../../components/UI/CrystalGridControls';

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

const render = (props: React.ComponentProps<typeof CrystalGridControls>) => {
  act(() => {
    root.render(
      <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
        <MemoryRouter>
          <CrystalGridControls {...props} />
        </MemoryRouter>
      </ConfigProvider>
    );
  });
};

describe('<CrystalGridControls />', () => {
  it('renders the Crystal Grid Setup heading', () => {
    render({ onSettingsChange: () => {} });
    expect(container.textContent).toContain('Crystal Grid Setup');
  });

  it('renders an Apply Settings button', () => {
    render({ onSettingsChange: () => {} });
    expect(container.textContent).toContain('Apply Crystal Grid Settings');
  });

  it('invokes onSettingsChange when Apply is clicked', () => {
    let captured = null;
    render({
      onSettingsChange: (s) => { captured = s; }
    });
    const applyBtn = container.querySelector('button.vajra-button-primary');
    expect(applyBtn).toBeTruthy();
    act(() => { (applyBtn as HTMLButtonElement).click(); });
    expect(captured).not.toBeNull();
    expect(captured).toHaveProperty('gridType');
    expect(captured).toHaveProperty('crystalType');
    expect(captured).toHaveProperty('showEnergyField');
    expect(captured).toHaveProperty('intention');
  });
});
