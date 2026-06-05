/**
 * Proof-of-concept component tests using happy-dom + React 18 createRoot.
 *
 * Validates that the vitest/happy-dom/React pipeline works end-to-end.
 * No @testing-library/react dependency — we use createRoot directly and
 * assert on container.textContent. This keeps the dep footprint minimal.
 *
 * If component testing expands, swap to @testing-library/react.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import StatusIndicator from '../../components/UI/StatusIndicator';

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

const render = (props: React.ComponentProps<typeof StatusIndicator>) => {
  act(() => { root.render(<StatusIndicator {...props} />); });
};

describe('<StatusIndicator /> (happy-dom)', () => {
  it('renders Connected when isConnected=true', () => {
    render({ isConnected: true, isPlaying: false });
    expect(container.textContent).toContain('Connected');
    expect(container.textContent).not.toContain('Disconnected');
  });

  it('renders Disconnected when isConnected=false', () => {
    render({ isConnected: false, isPlaying: false });
    expect(container.textContent).toContain('Disconnected');
    expect(container.textContent).toContain('Offline');
  });

  it('renders Playing vs Stopped based on isPlaying', () => {
    render({ isConnected: true, isPlaying: true });
    expect(container.textContent).toContain('Playing');
    render({ isConnected: true, isPlaying: false });
    expect(container.textContent).toContain('Stopped');
  });

  it('shows Crystal Active when crystalStatus.active=true', () => {
    render({ isConnected: true, crystalStatus: { active: true, intention: 'Healing' } });
    expect(container.textContent).toContain('Crystal Active');
  });

  it('shows Crystal Idle when crystalStatus not provided', () => {
    render({ isConnected: true });
    expect(container.textContent).toContain('Crystal Idle');
  });

  it('shows Scalar Active when scalarStatus.active=true', () => {
    render({ isConnected: true, scalarStatus: { active: true, rate: 7.83 } });
    expect(container.textContent).toContain('Scalar Active');
  });

  it('formats frequency to 1 decimal with Hz', () => {
    render({ isConnected: true, frequency: 528 });
    expect(container.textContent).toContain('528.0 Hz');
  });

  it('hides frequency block when frequency is not provided', () => {
    render({ isConnected: true });
    expect(container.textContent).not.toContain('Hz');
  });

  it('hides lastUpdate block when not provided', () => {
    render({ isConnected: true });
    expect(container.textContent).not.toContain('ago');
  });

  it('formats recent lastUpdate as seconds-ago', () => {
    const tenSecondsAgo = new Date(Date.now() - 10_000);
    render({ isConnected: true, lastUpdate: tenSecondsAgo });
    expect(container.textContent).toMatch(/\d+s ago/);
  });
});
