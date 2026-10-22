/**
 * W1-D1 globe chrome. The canvas is mocked, so this checks the label the
 * parent draws when earth-state is missing or present. Scene children are
 * covered by the helper tests.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import WorldEmanation from '../../components/3D/WorldEmanation';
import { useEarthStateStore } from '../../stores/earthStateStore';

vi.mock('@react-three/fiber', () => ({
  Canvas: () => <div data-testid="r3f-canvas" />,
  useFrame: () => {},
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Stars: () => null,
  Text: () => null,
}));

function earthBody(id: string, lat: number, lon: number) {
  return { id, name: id, ra_deg: 0, dec_deg: lat, lat, lon };
}

const ORACLE = {
  at: '2026-10-22T02:00:00Z',
  ephemeris: 'de432s',
  gast_deg: 60.525177,
  sun: earthBody('sun', -11.007839, 146.135149),
  moon: earthBody('moon', -8.166428, -82.025959),
  planets: [earthBody('mercury', -20.950951, 166.816802)],
  provenance: { sun: 'computed' },
};

describe('WorldEmanation earth chrome', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    useEarthStateStore.setState({ status: 'idle', state: null, fetchedAt: null, error: null });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
    useEarthStateStore.setState({ status: 'idle', state: null, fetchedAt: null, error: null });
    vi.unstubAllGlobals();
  });

  it('names an unavailable ephemeris without dropping Field Receptive', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({}),
      }),
    );
    await act(async () => {
      root.render(<WorldEmanation variant="compact" />);
    });
    await vi.waitFor(() => {
      expect(container.textContent || '').toContain('ephemeris unavailable');
    });
    expect(container.textContent || '').toContain('Field Receptive');
    expect(container.querySelector('[data-provenance="computed"]')).not.toBeNull();
  });

  it('drops the unavailable label once earth-state is ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes('/astrology/earth-state')) {
          return Promise.resolve({ ok: true, json: async () => ORACLE });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      }),
    );
    await act(async () => {
      root.render(<WorldEmanation variant="compact" />);
    });
    await vi.waitFor(() => {
      expect(container.querySelector('[data-provenance="computed"]')).not.toBeNull();
      expect(container.textContent || '').not.toContain('ephemeris unavailable');
    });
    expect(container.textContent || '').toContain('Field Receptive');
  });
});
