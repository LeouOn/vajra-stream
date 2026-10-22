// @vitest-environment happy-dom
/**
 * W1-D1 shared Earth texture: one canvas, ref-counted, disposed at zero.
 */
import React, { StrictMode, act } from 'react';
import { createRoot, type Root } from 'react-dom/client';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LandData } from '../lib/earth';

const loadLand = vi.hoisted(() => vi.fn());

vi.mock('../lib/earth', async () => {
  const actual = await vi.importActual<typeof import('../lib/earth')>('../lib/earth');
  return { ...actual, loadLand };
});

import {
  EARTH_LAND,
  EARTH_OCEAN,
  createEarthSurfaceMaterial,
  createEarthTexture,
  earthSurfaceProps,
  releaseEarthTexture,
  retainEarthTexture,
  useSharedEarthTexture,
} from '../components/3D/worldEmanationHelpers';

const TINY_LAND: LandData = {
  v: 1,
  kind: 'land',
  decimals: 0,
  polys: [{ o: [0, 0, 10, 0, 10, 10, 0, 10], h: [] }],
};

function stubContext(): { styles: string[]; ctx: CanvasRenderingContext2D } {
  const styles: string[] = [];
  const gradient = { addColorStop: () => undefined };
  const ctx = {
    fillStyle: '',
    beginPath: () => undefined,
    ellipse: () => undefined,
    fill: () => undefined,
    fillRect: () => undefined,
    moveTo: () => undefined,
    lineTo: () => undefined,
    closePath: () => undefined,
    createLinearGradient: () => gradient,
  };
  Object.defineProperty(ctx, 'fillStyle', {
    configurable: true,
    get: () => '',
    set: (value: string) => {
      styles.push(value);
    },
  });
  return { styles, ctx: ctx as unknown as CanvasRenderingContext2D };
}

describe('earth texture cache', () => {
  let styles: string[] = [];

  beforeEach(() => {
    const stub = stubContext();
    styles = stub.styles;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => stub.ctx);
    loadLand.mockReset();
    loadLand.mockResolvedValue(TINY_LAND);
  });

  afterEach(() => {
    releaseEarthTexture();
    releaseEarthTexture();
    releaseEarthTexture();
    vi.restoreAllMocks();
  });

  it('returns one 2048×1024 texture from createEarthTexture and retainEarthTexture', async () => {
    const created = createEarthTexture();
    const retained = retainEarthTexture();
    expect(retained).toBe(created);
    const canvas = created.image as HTMLCanvasElement;
    expect(canvas.width).toBe(2048);
    expect(canvas.height).toBe(1024);
    const versionAfterBlob = created.version;

    await vi.waitFor(() => {
      expect(styles).toContain(EARTH_OCEAN);
      expect(styles).toContain(EARTH_LAND);
    });
    // three r157 Texture.needsUpdate is a setter: assigning true bumps version.
    expect(created.version).toBeGreaterThan(versionAfterBlob);

    const dispose = vi.spyOn(created, 'dispose');
    releaseEarthTexture();
    expect(dispose).not.toHaveBeenCalled();
    releaseEarthTexture();
    expect(dispose).toHaveBeenCalledTimes(1);
    expect(canvas.width).toBe(0);
    expect(canvas.height).toBe(0);
  });

  it('keeps the blob map when loadLand rejects', async () => {
    loadLand.mockRejectedValue(new Error('chunk missing'));
    const tex = retainEarthTexture();
    await vi.waitFor(() => {
      expect(loadLand).toHaveBeenCalled();
    });
    await Promise.resolve();
    expect(styles).not.toContain(EARTH_OCEAN);
    expect(tex.image).toBeInstanceOf(HTMLCanvasElement);
    const dispose = vi.spyOn(tex, 'dispose');
    releaseEarthTexture();
    expect(dispose).toHaveBeenCalledTimes(1);
  });

  it('attaches the shared map on the first render and disposes it after StrictMode unmount', async () => {
    const seen: Array<ReturnType<typeof useSharedEarthTexture>> = [];
    function Probe() {
      const tex = useSharedEarthTexture();
      seen.push(tex);
      return null;
    }
    const container = document.createElement('div');
    document.body.appendChild(container);
    const roots: { current: Root | null } = { current: null };
    await act(async () => {
      roots.current = createRoot(container);
      roots.current.render(React.createElement(StrictMode, null, React.createElement(Probe)));
    });
    const first = seen[0];
    if (!first) throw new Error('first render had no texture');
    expect(first.isCanvasTexture).toBe(true);
    expect(seen.every((tex) => tex === first)).toBe(true);
    const props = earthSurfaceProps(first);
    expect(props.map).toBe(first);
    expect(props.color).toBe('#ffffff');
    const material = createEarthSurfaceMaterial(first);
    expect(material.map).toBe(first);
    expect(material.color.getHexString()).toBe('ffffff');
    const dispose = vi.spyOn(first, 'dispose');
    expect(dispose).not.toHaveBeenCalled();
    await act(async () => {
      roots.current?.unmount();
    });
    await new Promise<void>((resolve) => {
      queueMicrotask(resolve);
    });
    expect(dispose).toHaveBeenCalledTimes(1);
    material.dispose();
    container.remove();
  });

  it('keeps the mounted texture when a new holder replaces the previous one in the same turn', async () => {
    const mounted: { tex: ReturnType<typeof useSharedEarthTexture> | null } = { tex: null };
    function Probe() {
      mounted.tex = useSharedEarthTexture();
      return null;
    }
    const container = document.createElement('div');
    document.body.appendChild(container);
    const firstRoot = createRoot(container);
    await act(async () => {
      firstRoot.render(React.createElement(StrictMode, null, React.createElement(Probe)));
    });
    const previous = mounted.tex;
    if (!previous) throw new Error('first mount had no texture');
    expect(previous.isCanvasTexture).toBe(true);
    const disposePrevious = vi.spyOn(previous, 'dispose');
    const roots: { next: Root | null } = { next: null };
    await act(async () => {
      firstRoot.unmount();
      roots.next = createRoot(container);
      roots.next.render(React.createElement(StrictMode, null, React.createElement(Probe)));
    });
    const current = mounted.tex;
    if (!current) throw new Error('remount had no texture');
    expect(current.isCanvasTexture).toBe(true);
    if (current === previous) {
      expect(disposePrevious).not.toHaveBeenCalled();
    } else {
      expect(disposePrevious).toHaveBeenCalledTimes(1);
    }
    const remounted = roots.next;
    if (!remounted) throw new Error('remount did not create a root');
    const disposeCurrent = current === previous ? disposePrevious : vi.spyOn(current, 'dispose');
    await act(async () => {
      remounted.unmount();
    });
    await new Promise<void>((resolve) => {
      queueMicrotask(resolve);
    });
    expect(disposeCurrent).toHaveBeenCalledTimes(1);
    container.remove();
  });
});
