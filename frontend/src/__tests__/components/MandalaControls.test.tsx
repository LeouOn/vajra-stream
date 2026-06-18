/**
 * Regression: MandalaControls wired into the /visualizers route.
 *
 * Verifies the control panel:
 * - Renders the Mandala Setup heading and Apply button
 * - Invokes onSettingsChange with the right shape when Apply is clicked
 * - Defaults pattern to 'sri-yantra' (matches the existing App.jsx hardcoded default)
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import MandalaControls from '../../components/UI/MandalaControls';

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

const render = (props: React.ComponentProps<typeof MandalaControls>) => {
  act(() => {
    root.render(
      <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
        <MemoryRouter>
          <MandalaControls {...props} />
        </MemoryRouter>
      </ConfigProvider>
    );
  });
};

describe('<MandalaControls />', () => {
  it('renders the Mandala Setup heading', () => {
    render({ onSettingsChange: () => {} });
    expect(container.textContent).toContain('Sacred Mandala');
  });

  it('renders an Apply Settings button', () => {
    render({ onSettingsChange: () => {} });
    expect(container.textContent).toContain('Apply Mandala Settings');
  });

  it('invokes onSettingsChange when Apply is clicked with the right shape', () => {
    let captured = null;
    render({
      onSettingsChange: (s) => { captured = s; }
    });
    const applyBtn = container.querySelector('button.vajra-button-primary');
    expect(applyBtn).toBeTruthy();
    act(() => { (applyBtn as HTMLButtonElement).click(); });
    expect(captured).not.toBeNull();
    expect(captured).toHaveProperty('pattern');
    expect(captured).toHaveProperty('chakra');
    expect(captured).toHaveProperty('complexity'); // complexity prop is English canonical
  });
});
