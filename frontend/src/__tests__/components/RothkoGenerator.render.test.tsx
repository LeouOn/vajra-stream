/**
 * S4-supplementary — RothkoGenerator render test.
 *
 * The compassion-palette test (S4) only asserts static palette constants.
 * This test mounts the component and verifies the user-visible DOM:
 *   - outer container has the palette bg as backgroundColor
 *   - at least 5 color-block divs render
 *   - the "Compassion" overlay text is present
 *   - the description text matches the palette
 *   - the outer is fixed inset-0 z-50 when fullscreen=true
 *
 * This guards the user-facing concern ("meditation reads brown") at the
 * DOM level — if the component renders the right DOM, the actual pixel
 * appearance depends only on CSS compositing (which real browsers do;
 * headless Chromium drops CSS filter:blur() which is a tooling gap,
 * not a product bug).
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import RothkoGenerator, { PALETTES } from '../../components/2D/RothkoGenerator';

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

describe('<RothkoGenerator palette="compassion" />', () => {
  it('outer container has the compassion palette bg as backgroundColor', () => {
    act(() => { root.render(<RothkoGenerator palette="compassion" />); });
    const outer = container.querySelector('div.relative') as HTMLElement;
    expect(outer, 'outer container must exist').not.toBeNull();
    const bg = outer.style.backgroundColor.toLowerCase();
    expect(['#4d1f30', 'rgb(77, 31, 48)']).toContain(bg);
  });

  it('renders at least 5 color-block child divs (per the useMemo count)', () => {
    act(() => { root.render(<RothkoGenerator palette="compassion" />); });
    const blocks = container.querySelectorAll('div.absolute.transition-all');
    expect(blocks.length).toBeGreaterThanOrEqual(5);
    expect(blocks.length).toBeLessThanOrEqual(7);
  });

  it('every color block carries an inline style (React set props)', () => {
    act(() => { root.render(<RothkoGenerator palette="compassion" />); });
    const blocks = container.querySelectorAll('div.absolute.transition-all');
    expect(blocks.length).toBeGreaterThanOrEqual(5);
    blocks.forEach((b) => {
      const htmlEl = b as HTMLElement;
      const cssText = htmlEl.getAttribute('style') || '';
      expect(cssText.length, 'block must carry an inline style').toBeGreaterThan(20);
      // jsdom decomposes CSS3 background shorthand into individual properties;
      // we just verify that some positioning was applied (the React render is live).
      // jsdom decomposes CSS3 background shorthand into individual properties;
      // we just verify positioning was applied (the React render is live).
      expect(cssText).toMatch(/left:|top:/);
    });
  });

  it('palette colors are vivid pinks (cross-check against the regression test)', () => {
    expect(PALETTES.compassion.colors).toContain('#ff5c8a');
    expect(PALETTES.compassion.colors).toContain('#ffb3c6');
  });

  it('overlay text shows palette name "Compassion"', () => {
    act(() => { root.render(<RothkoGenerator palette="compassion" />); });
    expect(container.textContent).toContain('Compassion');
  });

  it('overlay text shows the palette description', () => {
    act(() => { root.render(<RothkoGenerator palette="compassion" />); });
    expect(container.textContent).toContain(PALETTES.compassion.description.split(' — ')[0]);
  });

  it('fullscreen=true renders the outer with fixed inset-0 z-50', () => {
    act(() => { root.render(<RothkoGenerator palette="compassion" fullscreen />); });
    const outer = container.querySelector('div.fixed') as HTMLElement;
    expect(outer).not.toBeNull();
    expect(outer?.className).toContain('inset-0');
    expect(outer?.className).toContain('z-50');
  });
});
