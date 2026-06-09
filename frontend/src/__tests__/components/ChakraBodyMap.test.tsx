/**
 * Tests for ChakraBodyMap — interactive SVG body with 7 chakra
 * energy centers. Uses happy-dom + createRoot.
 *
 * The exported CHAKRA_POINTS array is the most directly testable
 * surface: 7 chakras with id, name, cy (SVG y %), color, glow,
 * frequency (Hz), and size.
 *
 * We also test the click-to-select behavior because the selection
 * state is observable in the rendered DOM (a detail card appears
 * with the chakra's name and frequency).
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import ChakraBodyMap, { CHAKRA_POINTS } from '../../components/2D/ChakraBodyMap';

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

const render = (props?: React.ComponentProps<typeof ChakraBodyMap>) => {
  act(() => { root.render(<ChakraBodyMap {...props} />); });
};

describe('CHAKRA_POINTS constant', () => {
  it('exports exactly 7 chakras (crown through root)', () => {
    expect(CHAKRA_POINTS).toHaveLength(7);
  });

  it('every chakra has the expected shape', () => {
    CHAKRA_POINTS.forEach((c) => {
      expect(typeof c.id).toBe('string');
      expect(typeof c.name).toBe('string');
      expect(typeof c.cy).toBe('number');
      expect(typeof c.frequency).toBe('number');
      expect(typeof c.size).toBe('number');
      expect(c.color).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(c.glow).toMatch(/^#[0-9a-fA-F]{6}$/);
    });
  });

  it('includes all 7 canonical chakra ids in order from crown to root', () => {
    const ids = CHAKRA_POINTS.map((c) => c.id);
    expect(ids).toEqual([
      'crown', 'third_eye', 'throat', 'heart',
      'solar_plexus', 'sacral', 'root',
    ]);
  });

  it('frequencies descend from crown (highest Hz) to root (lowest Hz)', () => {
    const freqs = CHAKRA_POINTS.map((c) => c.frequency);
    for (let i = 1; i < freqs.length; i++) {
      expect(freqs[i]).toBeLessThan(freqs[i - 1]);
    }
  });
});

describe('<ChakraBodyMap />', () => {
  it('renders the "Energy Body" title', () => {
    render();
    expect(container.textContent).toContain('Energy Body');
  });

  it('renders the SVG container', () => {
    render();
    expect(container.querySelector('svg')).not.toBeNull();
  });

  it('renders all 7 chakra frequency labels by default', () => {
    render();
    CHAKRA_POINTS.forEach((c) => {
      expect(container.textContent).toContain(`${c.frequency} Hz`);
    });
  });

  it('does not show the detail card before any chakra is selected', () => {
    render();
    expect(container.querySelector('.animate-pulse-glow')).toBeNull();
  });

  it('clicking a chakra reveals its detail card with name + frequency', () => {
    render();
    const svgCircles = container.querySelectorAll('svg circle');
    // Find a click-target circle (cursor-pointer class)
    const clickTarget = Array.from(svgCircles).find(
      (c) => c.getAttribute('class')?.includes('cursor-pointer')
    );
    expect(clickTarget).toBeDefined();

    act(() => {
      clickTarget?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const detailCard = container.querySelector('.animate-pulse-glow');
    expect(detailCard).not.toBeNull();
    expect(container.textContent).toContain('Crown');
    expect(container.textContent).toContain('963 Hz');
  });

  it('clicking the same chakra again deselects it (detail card removed)', () => {
    render();
    const clickTarget = Array.from(container.querySelectorAll('svg circle')).find(
      (c) => c.getAttribute('class')?.includes('cursor-pointer')
    );
    expect(clickTarget).toBeDefined();

    act(() => { clickTarget?.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
    expect(container.querySelector('.animate-pulse-glow')).not.toBeNull();

    act(() => { clickTarget?.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
    expect(container.querySelector('.animate-pulse-glow')).toBeNull();
  });

  it('calls onSelectChakra with the full chakra object on selection', () => {
    const onSelectChakra = vi.fn();
    render({ onSelectChakra });
    // Click the heart chakra (4th in the list, index 3)
    const clickTargets = container.querySelectorAll('svg circle.cursor-pointer');
    expect(clickTargets.length).toBe(7);
    act(() => { clickTargets[3]?.dispatchEvent(new MouseEvent('click', { bubbles: true })); });

    expect(onSelectChakra).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'heart', name: 'Heart', frequency: 639 })
    );
  });

  it('does not call onSelectChakra on deselection click', () => {
    const onSelectChakra = vi.fn();
    render({ onSelectChakra });
    const clickTargets = container.querySelectorAll('svg circle.cursor-pointer');
    act(() => { clickTargets[0]?.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
    act(() => { clickTargets[0]?.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
    expect(onSelectChakra).toHaveBeenCalledTimes(1);
  });

  it('height prop controls the SVG height (and width = height*0.5)', () => {
    render({ height: 200 });
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('height')).toBe('200');
    expect(svg?.getAttribute('width')).toBe('100');
  });
});
