// @vitest-environment happy-dom
/**
 * W3-G route-level canvas budget: /operations/broadcast must end up with
 * EXACTLY ONE WebGL canvas once the lazy Earth & Sky card has loaded.
 *
 * The tab's globe is the existing full `WorldEmanation` above
 * `BroadcastPanel`; the card adds the 2D strip, the 2D dome and the controls,
 * never a second r3f Canvas. The Canvas is mocked (no WebGL in happy-dom);
 * the globe and the card are the real components.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('@react-three/fiber', () => ({
  Canvas: () => <div data-testid="r3f-canvas" />,
  useFrame: () => {},
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Stars: () => null,
  Text: () => null,
}));

vi.mock('../../components/3D/RadionicsGlobe', () => ({
  MiniGlobe: () => <div data-testid="mini-globe-stub" />,
}));

vi.mock('../../hooks/useWebSocketStable', () => ({
  useWebSocketStable: () => ({ sessions: {} }),
}));

vi.mock('../../stores/earthStateStore', () => ({
  useEarthState: () => ({ status: 'idle', state: null, fetchedAt: null, error: null }),
}));

// The dome's own observer/request tests cover it; here only the canvas budget
// and the card's presence matter.
vi.mock('../../components/UI/CelestialSkyDome', async () => {
  const ReactModule = await import('react');
  return { default: () => ReactModule.createElement('div', { 'data-testid': 'dome-stub' }) };
});

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;

/** Poll until a condition holds inside act; 5 s ceiling, clear timeout error. */
async function waitForCondition(
  check: () => boolean,
  what: string,
  timeoutMs = 5000,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    let ok = false;
    try {
      ok = check();
    } catch {
      ok = false;
    }
    if (ok) return;
    if (Date.now() >= deadline) {
      throw new Error(`timed out after ${timeoutMs} ms waiting for ${what}`);
    }
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
  }
}


beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } })),
  );
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

describe('/operations/broadcast canvas budget', () => {
  it('has exactly one WebGL canvas once the lazy Earth & Sky card has loaded', async () => {
    const { default: OperationsPage } = await import('../../routes/Operations');

    await act(async () => {
      root.render(
        <ConfigProvider>
          <MemoryRouter initialEntries={['/operations/broadcast']}>
            <Routes>
              <Route path="/operations/:tab" element={<OperationsPage />} />
            </Routes>
          </MemoryRouter>
        </ConfigProvider>,
      );
    });
    // Poll for the lazy Earth & Sky chunk instead of assuming 50 ms (that
    // failed once under load; CI is slower than this machine).
    await waitForCondition(
      () =>
        document.querySelector('[data-testid="earth-sky-card"]') !== null &&
        document.querySelector('[data-testid="earth-sky-card-fallback"]') === null,
      'the lazy Earth & Sky card to mount (fallback gone)',
    );

    const canvases = document.querySelectorAll('[data-testid="r3f-canvas"]');
    expect(canvases).toHaveLength(1);
    // The card loaded (this is not just the globe with a pending import) and
    // contributed no canvas of its own.
    expect(document.querySelectorAll('[data-testid="earth-sky-card"]')).toHaveLength(1);
    expect(document.querySelectorAll('[data-testid="earth-sky-card-fallback"]')).toHaveLength(0);
    expect(document.querySelectorAll('[data-testid="world-strip"]')).toHaveLength(1);
  });
});
