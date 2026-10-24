// @vitest-environment happy-dom
/**
 * W3-C tests: clicking the globe sets the observer, dragging does not, and
 * the marker follows the store without re-rendering on a time scrub.
 *
 * The r3f canvas is mocked exactly as WorldEmanation.test.tsx does (happy-dom
 * has no WebGL), so a real GPU raycast is NOT exercised here. The gesture and
 * uv -> lat/lng path is driven through the same `createGlobePicker` instance
 * the mesh uses, with the real skyStore action.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import WorldEmanation, { useObserverLatLng } from '../../components/3D/WorldEmanation';
import {
  PICK_MAX_DURATION_MS,
  PICK_MAX_MOVE_PX,
  createGlobePicker,
} from '../../components/3D/worldEmanationHelpers';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { OBSERVER_MARKER_COLOR } from '../../lib/earth';
import { useSkyStore } from '../../stores/skyStore';

vi.mock('@react-three/fiber', () => ({
  Canvas: () => <div data-testid="r3f-canvas" />,
  useFrame: () => {},
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Stars: () => null,
  Text: () => null,
}));

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function pickerToStore() {
  return createGlobePicker((lat, lng) => {
    useSkyStore.getState().setObserver(lat, lng);
  });
}

function clickAt(
  picker: ReturnType<typeof createGlobePicker>,
  uv: { x: number; y: number } | null,
  from = { x: 100, y: 100, t: 0 },
  to = { x: 100, y: 100, t: 120 },
): boolean {
  picker.onPointerDown(from);
  return picker.onPointerUp({ ...to, uv });
}

beforeEach(() => {
  useSkyStore.setState({ lat: DEFAULT_LAT, lng: DEFAULT_LNG, label: undefined, at: null });
});

describe('globe click -> observer', () => {
  it('maps the intersection uv to the exact place (three known points)', () => {
    const cases: Array<[{ u: number; v: number }, { lat: number; lng: number }]> = [
      [{ u: 0.5, v: 0.5 }, { lat: 0, lng: 0 }],
      [{ u: 0.25, v: 0.75 }, { lat: 45, lng: -90 }],
      [{ u: 0.75, v: 0.25 }, { lat: -45, lng: 90 }],
    ];
    for (const [uv, expected] of cases) {
      const picker = pickerToStore();
      expect(clickAt(picker, { x: uv.u, y: uv.v })).toBe(true);
      const state = useSkyStore.getState();
      expect({ lat: state.lat, lng: state.lng }).toEqual(expected);
      // And the labels are gone: a pick is a new place, not the old name.
      expect(state.label).toBeUndefined();
    }
  });

  it('keeps poles and the antimeridian in range (uv is never out of [0,1])', () => {
    const picker = pickerToStore();
    const cases: Array<[number, number, number]> = [
      [0.3, 0, -90], // south pole -> defined lng 0
      [0.7, 1, 90], // north pole -> defined lng 0
      [0, 0.5, 0], // u=0 -> lng -180
      [1, 0.5, 0], // u=1 -> lng -180
    ];
    for (const [u, v, expectedLat] of cases) {
      clickAt(picker, { x: u, y: v });
      const { lat, lng } = useSkyStore.getState();
      expect(lat).toBe(expectedLat);
      expect(lat).toBeGreaterThanOrEqual(-90);
      expect(lat).toBeLessThanOrEqual(90);
      expect(lng).toBeGreaterThanOrEqual(-180);
      expect(lng).toBeLessThan(180);
    }
    // The four clicks above: -180 twice, plus the poles' defined 0.
    expect(clickAt(picker, { x: 0, y: 0.5 })).toBe(true);
    expect(useSkyStore.getState().lng).toBe(-180);
  });
});

describe('drag vs click', () => {
  it('does not pick when the pointer moved more than the threshold', () => {
    const picker = pickerToStore();
    const before = useSkyStore.getState();
    const picked = clickAt(
      picker,
      { x: 0.5, y: 0.5 },
      { x: 100, y: 100, t: 0 },
      { x: 100 + PICK_MAX_MOVE_PX + 1, y: 100, t: 100 },
    );
    expect(picked).toBe(false);
    expect(useSkyStore.getState()).toMatchObject({ lat: before.lat, lng: before.lng });
  });

  it('does not pick when the press lasted longer than the threshold', () => {
    const picker = pickerToStore();
    const picked = clickAt(
      picker,
      { x: 0.5, y: 0.5 },
      { x: 100, y: 100, t: 0 },
      { x: 100, y: 100, t: PICK_MAX_DURATION_MS + 1 },
    );
    expect(picked).toBe(false);
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
  });

  it('accepts the inclusive thresholds (5 px, 500 ms)', () => {
    const picker = pickerToStore();
    expect(
      clickAt(
        picker,
        { x: 0.5, y: 0.5 },
        { x: 100, y: 100, t: 0 },
        { x: 100 + PICK_MAX_MOVE_PX, y: 100, t: PICK_MAX_DURATION_MS },
      ),
    ).toBe(true);
  });

  it('does not pick without a surface uv, and a cancel clears the gesture', () => {
    const picker = pickerToStore();
    expect(clickAt(picker, null)).toBe(false);

    picker.onPointerDown({ x: 100, y: 100, t: 0 });
    picker.onPointerCancel();
    expect(picker.onPointerUp({ x: 100, y: 100, t: 100, uv: { x: 0.5, y: 0.5 } })).toBe(false);

    // An up with no preceding down is not a click either.
    expect(picker.onPointerUp({ x: 100, y: 100, t: 100, uv: { x: 0.5, y: 0.5 } })).toBe(false);
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
  });

  it('rejects a non-finite uv instead of writing NaN into the store', () => {
    const picker = pickerToStore();
    expect(clickAt(picker, { x: Number.NaN, y: 0.5 })).toBe(false);
    expect(clickAt(picker, { x: 0.5, y: Number.POSITIVE_INFINITY })).toBe(false);
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
  });
});

describe('observer marker colour', () => {
  it('uses the one marker colour from lib/earth, not a second literal', () => {
    expect(OBSERVER_MARKER_COLOR).toBe('#ffe08a');
    // happy-dom's import.meta.url is not a file: URL, so resolve from cwd
    // (vitest runs from frontend/).
    const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf8');
    const globeSource = read('src/components/3D/WorldEmanation.tsx');
    // Imported and used on the marker core; no hard-coded gold left.
    expect(globeSource).toContain('OBSERVER_MARKER_COLOR');
    expect(globeSource).toContain('color={OBSERVER_MARKER_COLOR}');
    expect(globeSource).not.toContain("'#ffe08a'");
    // The strip paints through drawWorldStrip; its own test checks the
    // rendered fill/stroke, and the shared constant must be the source.
    const stripLib = read('src/lib/equirect.ts');
    expect(stripLib).toContain('OBSERVER_MARKER_COLOR');
    expect(stripLib).not.toContain("'#7ef29a'");
  });
});

describe('marker subscription and canvas budget', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it('does not add a second canvas', async () => {
    await act(async () => {
      root.render(<WorldEmanation variant="compact" />);
    });
    expect(container.querySelectorAll('[data-testid="r3f-canvas"]')).toHaveLength(1);
  });

  it('the observer hook follows lat/lng but not a time scrub', async () => {
    let renders = 0;
    function Harness(): React.ReactElement {
      const { lat, lng } = useObserverLatLng();
      renders += 1;
      return (
        <div data-testid="observer">
          {lat},{lng}
        </div>
      );
    }
    await act(async () => {
      root.render(<Harness />);
    });
    const initialRenders = renders;
    expect(container.textContent).toBe(`${DEFAULT_LAT},${DEFAULT_LNG}`);

    act(() => {
      useSkyStore.getState().setObserver(51.4779, -0.0015, 'Greenwich');
    });
    expect(container.textContent).toBe('51.4779,-0.0015');
    expect(renders).toBeGreaterThan(initialRenders);

    const afterPlaceChange = renders;
    act(() => {
      useSkyStore.getState().setAt('2026-10-24T09:00:00Z');
    });
    expect(renders).toBe(afterPlaceChange); // a scrub must not re-render the globe
    expect(container.textContent).toBe('51.4779,-0.0015');
  });

  it('unmounting removes the handlers (no store change from later events)', async () => {
    await act(async () => {
      root.render(<WorldEmanation variant="compact" />);
    });
    act(() => {
      root.unmount();
    });
    const before = useSkyStore.getState();
    container.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    container.dispatchEvent(new Event('pointerup', { bubbles: true }));
    expect(useSkyStore.getState()).toMatchObject({ lat: before.lat, lng: before.lng });
  });
});
