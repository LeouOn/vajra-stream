/**
 * Tests for RothkoGenerator — CSS color-field meditation visuals.
 * Uses happy-dom + createRoot. No Three.js / WebGL — pure CSS + SVG.
 *
 * The exported PALETTES constant is the most directly testable
 * surface: 8 named palettes with colors/bg/description. We assert
 * the data shape, then assert the rendered output reflects the
 * current palette (name and description in the overlay text,
 * background color set from palette.bg).
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
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

const render = (props?: React.ComponentProps<typeof RothkoGenerator>) => {
  act(() => { root.render(<RothkoGenerator {...props} />); });
};

describe('PALETTES constant', () => {
  it('exports exactly 8 named palettes', () => {
    expect(Object.keys(PALETTES)).toHaveLength(8);
  });

  it('every palette has a name, colors array, bg, and description', () => {
    Object.values(PALETTES).forEach((palette) => {
      expect(typeof palette.name).toBe('string');
      expect(palette.name.length).toBeGreaterThan(0);
      expect(Array.isArray(palette.colors)).toBe(true);
      expect(palette.colors.length).toBeGreaterThan(0);
      palette.colors.forEach((c) => {
        expect(c).toMatch(/^#[0-9a-fA-F]{6}$/);
      });
      expect(palette.bg).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(typeof palette.description).toBe('string');
      expect(palette.description.length).toBeGreaterThan(0);
    });
  });

  it('includes the canonical palette names', () => {
    const expected = [
      'compassion', 'wisdom', 'peace', 'awakening',
      'emptiness', 'earth', 'transcendence', 'rainbow-body',
    ];
    expected.forEach((name) => {
      expect(PALETTES).toHaveProperty(name);
    });
  });
});

describe('<RothkoGenerator />', () => {
  it('renders the default palette name in the overlay text', () => {
    render();
    expect(container.textContent).toContain('Compassion');
  });

  it('renders the description of the active palette', () => {
    render();
    expect(container.textContent).toContain('loving-kindness');
  });

  it('renders the requested palette name when palette prop is set', () => {
    render({ palette: 'wisdom' });
    expect(container.textContent).toContain('Wisdom');
    expect(container.textContent).toContain('depths of insight');
  });

  it('applies palette.bg as background color of the outer container', () => {
    render({ palette: 'wisdom' });
    const outer = container.querySelector('div.relative') as HTMLElement;
    expect(outer).not.toBeNull();
    expect(outer?.style.backgroundColor).toBe('#080818');
  });

  it('renders 5-7 color block divs (5 + floor(random*3))', () => {
    render();
    const blocks = container.querySelectorAll('div.absolute.transition-all');
    expect(blocks.length).toBeGreaterThanOrEqual(5);
    expect(blocks.length).toBeLessThanOrEqual(7);
  });

  it('applies fullscreen layout class when fullscreen=true', () => {
    render({ fullscreen: true });
    const outer = container.querySelector('div.fixed') as HTMLElement;
    expect(outer).not.toBeNull();
    expect(outer?.className).toContain('inset-0');
  });

  it('uses non-fullscreen layout class by default (w-full h-full)', () => {
    render();
    const outer = container.querySelector('div.w-full.h-full') as HTMLElement;
    expect(outer).not.toBeNull();
  });

  it('includes the rothko-blur and rothko-glow SVG filter defs', () => {
    render();
    expect(container.querySelector('filter#rothko-blur')).not.toBeNull();
    expect(container.querySelector('filter#rothko-glow')).not.toBeNull();
  });

  it('includes the rothkoFloat keyframe animation rule', () => {
    render();
    const style = container.querySelector('style');
    expect(style?.textContent).toContain('@keyframes rothkoFloat');
  });

  it('switches palette when palette prop changes (effect-driven)', () => {
    const { rerender } = { rerender: null as any };
    // Render with compassion, then re-render with wisdom
    act(() => { root.render(<RothkoGenerator palette="compassion" />); });
    expect(container.textContent).toContain('Compassion');
    act(() => { root.render(<RothkoGenerator palette="emptiness" />); });
    expect(container.textContent).toContain('Emptiness');
  });
});
