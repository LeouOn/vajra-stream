// @vitest-environment happy-dom
/**
 * W6-D2a: the globe's touch policy is EXPLICIT and PINNED (audit F5).
 *
 * three-stdlib's OrbitControls writes `touch-action: none` onto the element
 * it connects to at connect() and `auto` at dispose() — its lifecycle race
 * decided the policy before (measured `auto` in the live dev page). With drei
 * that element is R3F's wrapper <div> around the canvas, not the canvas
 * (measured in Chromium), so the pin covers the canvas AND its ancestors up
 * to the globe container. These tests pin the deliberate policy:
 *   - one finger scrolls the page: the canvas and the wrapper chain above it
 *     are `touch-action: pan-y`;
 *   - two fingers rotate/zoom: OrbitControls `touches` maps TWO to
 *     DOLLY_ROTATE and ONE to nothing (undefined hits three-stdlib's
 *     `default: STATE.NONE` branch, OrbitControls.js:743-756);
 *   - mouse behaviour is untouched (no `mouse` prop: left-drag rotate,
 *     wheel zoom stay three-stdlib defaults);
 *   - the pick's 5px/500ms discrimination is not this file's concern, but
 *     the pick test file must stay green untouched (run alongside).
 *
 * The r3f Canvas is mocked exactly as WorldEmanation.test.tsx does; the
 * mocks RECORD the props the component passes, so a refactor that drops
 * style/onCreated/touches fails here even though no WebGL runs.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import * as THREE from 'three';

const recorded = vi.hoisted(() => ({
  canvasProps: [] as Array<Record<string, unknown>>,
  orbitProps: [] as Array<Record<string, unknown>>,
  // when set, the mocked Canvas calls onCreated ONCE, in its layout effect, with this canvas (before the parent's passive
  // effects run), the way a Canvas whose root is ready on first commit would
  createCanvas: null as null | (() => HTMLCanvasElement),
}));

vi.mock('@react-three/fiber', () => ({
  // Renders the children so the OrbitControls prop capture works (the
  // scene subtree uses no r3f context hooks beyond the mocked useFrame).
  Canvas: (props: { children?: React.ReactNode } & Record<string, unknown>) => {
    recorded.canvasProps.push(props);
    const created = React.useRef(false);
    React.useLayoutEffect(() => {
      if (created.current || !recorded.createCanvas) return;
      created.current = true; // a ref survives StrictMode's simulated remount, like R3F's one-time root
      (props.onCreated as (state: { gl: { domElement: HTMLCanvasElement } }) => void)({
        gl: { domElement: recorded.createCanvas() },
      });
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    return <div data-testid="r3f-canvas">{props.children}</div>;
  },
  useFrame: () => {},
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: (props: Record<string, unknown>) => {
    recorded.orbitProps.push(props);
    return null;
  },
  Stars: () => null,
  Text: () => null,
}));

import WorldEmanation from '../../components/3D/WorldEmanation';

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  recorded.canvasProps.length = 0;
  recorded.orbitProps.length = 0;
  recorded.createCanvas = null;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  if (container.parentNode) container.parentNode.removeChild(container);
  // a pin that leaked onto the page must not colour the next test
  document.body.style.touchAction = '';
  document.documentElement.style.touchAction = '';
});

async function render(variant: 'compact' | 'full' = 'full'): Promise<void> {
  await act(async () => {
    root.render(<WorldEmanation variant={variant} />);
  });
}

describe('the globe touch policy is explicit (audit F5)', () => {
  it('declares touch-action: pan-y on the Canvas container style', async () => {
    await render();
    expect(recorded.canvasProps.length).toBeGreaterThan(0);
    const style = recorded.canvasProps[0].style as { touchAction?: string } | undefined;
    expect(style?.touchAction).toBe('pan-y');
  });

  it('pins the canvas element to pan-y via onCreated, re-asserting after the library rewrites it', async () => {
    await render();
    const onCreated = recorded.canvasProps[0].onCreated as
      | ((state: { gl: { domElement: HTMLCanvasElement } }) => void)
      | undefined;
    if (typeof onCreated !== 'function') {
      throw new Error('Canvas has no onCreated handler');
    }

    const canvas = document.createElement('canvas');
    onCreated({ gl: { domElement: canvas } });
    // The explicit write happens immediately.
    expect(canvas.style.touchAction).toBe('pan-y');

    // three-stdlib's connect()/dispose() rewrite the style after mount
    // (OrbitControls.js:300/:309); the pin must observe the mutation and
    // win. Under happy-dom a style PROPERTY write does not reach the
    // attribute (measured), so the hostile writes below go through
    // setAttribute — which real browsers' property writes are equivalent
    // to (CSSOM style writes reflect into the style attribute).
    canvas.setAttribute('style', 'touch-action: none;'); // what connect() does
    // (happy-dom may deliver the observer callback synchronously, so the
    // hostile value can be unobservable — only the pin's win is asserted.)
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    expect(canvas.style.touchAction).toBe('pan-y'); // the pin re-won

    canvas.setAttribute('style', 'touch-action: auto;'); // what dispose() does
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    expect(canvas.style.touchAction).toBe('pan-y');
  });

  it('pins every element between the canvas and the globe container, not only the canvas (real-browser finding)', async () => {
    // Measured in Chromium (W6-D2a): drei's OrbitControls connects to R3F's wrapper <div> (events.connected), not to
    // the canvas, so connect() writes `touch-action: none` onto the WRAPPER. A pan-y canvas under a `none` ancestor has
    // the effective policy `none` (touch-action intersects up the ancestor chain): one finger never scrolled the page.
    await render();
    const onCreated = recorded.canvasProps[0].onCreated as (state: { gl: { domElement: HTMLCanvasElement } }) => void;
    const globe = document.createElement('div');
    globe.setAttribute('data-testid', 'world-emanation');
    const wrapper = document.createElement('div'); // R3F's container div (events.connected)
    const inner = document.createElement('div');
    const canvas = document.createElement('canvas');
    inner.appendChild(canvas);
    wrapper.appendChild(inner);
    globe.appendChild(wrapper);
    document.body.appendChild(globe);
    try {
      onCreated({ gl: { domElement: canvas } });
      for (const el of [canvas, inner, wrapper]) expect(el.style.touchAction).toBe('pan-y');

      // what OrbitControls.connect() and dispose() do to its domElement
      wrapper.setAttribute('style', 'touch-action: none;');
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
      });
      expect(wrapper.style.touchAction).toBe('pan-y');
      wrapper.setAttribute('style', 'touch-action: auto;');
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
      });
      expect(wrapper.style.touchAction).toBe('pan-y');

      // the effective policy (the intersection of touch-action up the chain to the container) is pan-y everywhere
      const values = [canvas, inner, wrapper].map((el) => el.style.touchAction);
      expect(new Set(values)).toEqual(new Set(['pan-y']));
    } finally {
      globe.remove();
    }
  });

  // D2a-F (dev-d2's review of D2a): the pin must be removable and must never leave the globe's own container.
  type OnCreated = (state: { gl: { domElement: HTMLCanvasElement } }) => void;
  const settle = (): Promise<void> =>
    act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
  /** root[data-testid=world-emanation] > wrapper > inner > canvas, attached to the document (what R3F builds). */
  function globeChain(): { globe: HTMLElement; wrapper: HTMLElement; inner: HTMLElement; canvas: HTMLCanvasElement } {
    const globe = document.createElement('div');
    globe.setAttribute('data-testid', 'world-emanation');
    const wrapper = document.createElement('div');
    const inner = document.createElement('div');
    const canvas = document.createElement('canvas');
    inner.appendChild(canvas);
    wrapper.appendChild(inner);
    globe.appendChild(wrapper);
    document.body.appendChild(globe);
    return { globe, wrapper, inner, canvas };
  }

  it('stops re-pinning once the globe unmounts (the observer is disconnected)', async () => {
    await render();
    const onCreated = recorded.canvasProps[0].onCreated as OnCreated;
    const { globe, wrapper, canvas } = globeChain();
    try {
      onCreated({ gl: { domElement: canvas } });
      wrapper.setAttribute('style', 'touch-action: none;');
      await settle();
      expect(wrapper.style.touchAction).toBe('pan-y'); // alive: the pin wins

      await act(async () => {
        root.unmount();
      });
      wrapper.setAttribute('style', 'touch-action: none;'); // what a late dispose() of a removed globe would do
      await settle();
      expect(wrapper.style.touchAction).toBe('none'); // dead: nothing watches it any more
    } finally {
      globe.remove();
    }
  });

  it('moves the pin to the new canvas when the canvas is re-created, and releases the old one', async () => {
    await render();
    const onCreated = recorded.canvasProps[0].onCreated as OnCreated;
    const first = globeChain();
    const second = globeChain();
    try {
      onCreated({ gl: { domElement: first.canvas } });
      onCreated({ gl: { domElement: second.canvas } });
      for (const el of [second.canvas, second.inner, second.wrapper]) expect(el.style.touchAction).toBe('pan-y');

      first.wrapper.setAttribute('style', 'touch-action: none;');
      second.wrapper.setAttribute('style', 'touch-action: none;');
      await settle();
      expect(first.wrapper.style.touchAction).toBe('none'); // released
      expect(second.wrapper.style.touchAction).toBe('pan-y'); // pinned
    } finally {
      first.globe.remove();
      second.globe.remove();
    }
  });

  it('keeps the pin alive through React StrictMode\'s simulated unmount/remount of effects (dev)', async () => {
    // the canvas exists BEFORE the parent's effects run, so StrictMode's simulated cleanup releases the first pin and the
    // effect must pin the remembered canvas again
    const { globe, wrapper, canvas } = globeChain();
    recorded.createCanvas = () => canvas;
    try {
      await act(async () => {
        root.render(
          <React.StrictMode>
            <WorldEmanation variant="full" />
          </React.StrictMode>,
        );
      });
      expect(canvas.style.touchAction).toBe('pan-y');
      wrapper.setAttribute('style', 'touch-action: none;');
      await settle();
      expect(wrapper.style.touchAction).toBe('pan-y');

      await act(async () => {
        root.unmount();
      });
      wrapper.setAttribute('style', 'touch-action: none;');
      await settle();
      expect(wrapper.style.touchAction).toBe('none'); // and the real unmount still releases it
    } finally {
      globe.remove();
    }
  });

  it('never writes touch-action outside the globe container, even when the container cannot be found', async () => {
    await render();
    const onCreated = recorded.canvasProps[0].onCreated as OnCreated;
    // a canvas under body > div > div with NO [data-testid=world-emanation] (the test id renamed, or another shell)
    const outer = document.createElement('div');
    const middle = document.createElement('div');
    const canvas = document.createElement('canvas');
    middle.appendChild(canvas);
    outer.appendChild(middle);
    document.body.appendChild(outer);
    try {
      onCreated({ gl: { domElement: canvas } });
      expect(canvas.style.touchAction).toBe('pan-y');
      // body/html carry the page's own pinch-zoom and pan policy: pinning them would change the whole page
      expect(document.body.style.touchAction).toBe('');
      expect(document.documentElement.style.touchAction).toBe('');
      expect(middle.style.touchAction).toBe('');
      expect(outer.style.touchAction).toBe('');
    } finally {
      outer.remove();
    }
  });

  it('with the container found, writes only between the canvas and the container', async () => {
    await render();
    const onCreated = recorded.canvasProps[0].onCreated as OnCreated;
    const { globe, canvas } = globeChain();
    try {
      onCreated({ gl: { domElement: canvas } });
      expect(globe.style.touchAction).toBe(''); // the container itself is not written
      expect(document.body.style.touchAction).toBe('');
      expect(document.documentElement.style.touchAction).toBe('');
    } finally {
      globe.remove();
    }
  });

  it('maps two fingers to DOLLY_ROTATE and one finger to nothing', async () => {
    await render();
    expect(recorded.orbitProps.length).toBeGreaterThan(0);
    const touches = recorded.orbitProps[0].touches as
      | { ONE?: THREE.TOUCH; TWO?: THREE.TOUCH }
      | undefined;
    // ONE omitted (not null: the three-stdlib .d.ts does not allow null).
    // r3f applyProps ASSIGNS the whole object (no nested merge), so ONE is
    // undefined on the instance and the one-finger switch falls through to
    // STATE.NONE — one finger belongs to the page scroll, not the globe.
    expect(touches).toBeDefined();
    expect(touches?.ONE).toBeUndefined();
    expect(touches?.TWO).toBe(THREE.TOUCH.DOLLY_ROTATE);
  });

  it('leaves mouse behaviour at the library defaults (no mouse prop)', async () => {
    await render();
    expect(recorded.orbitProps[0].mouse).toBeUndefined();
  });

  it('applies the same policy in the compact variant', async () => {
    await render('compact');
    const style = recorded.canvasProps[0].style as { touchAction?: string } | undefined;
    expect(style?.touchAction).toBe('pan-y');
    expect((recorded.orbitProps[0].touches as { TWO?: THREE.TOUCH })?.TWO).toBe(
      THREE.TOUCH.DOLLY_ROTATE,
    );
  });
});
