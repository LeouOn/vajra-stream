/**
 * Tests for RateDial — interactive SVG radionics rate knob.
 * Uses happy-dom + createRoot + a real <svg> render so we can
 * verify the dial's aria-valuenow, role="slider", and the
 * value label below the dial.
 *
 * We focus on the keyboard interaction path (arrow keys, Home/End,
 * PageUp/PageDown) because:
 *   1. The mouse-drag path depends on getBoundingClientRect() and
 *      the real DOM geometry, which happy-dom doesn't fully model
 *      for SVG transforms.
 *   2. The audioFeedback calls are expected to be no-ops in the
 *      test environment (no AudioContext available in happy-dom),
 *      so the test only needs to verify the onChange callback
 *      was invoked with the right value.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import RateDial from '../../components/UI/RateDial';

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

const render = (props: React.ComponentProps<typeof RateDial>) => {
  act(() => { root.render(<RateDial {...props} />); });
};

const getSlider = (): HTMLElement | null =>
  container.querySelector('[role="slider"]');

describe('<RateDial />', () => {
  it('renders with role="slider" and correct aria attributes', () => {
    render({ value: 50, onChange: () => {}, min: 0, max: 100 });
    const slider = getSlider();
    expect(slider).not.toBeNull();
    expect(slider?.getAttribute('aria-valuemin')).toBe('0');
    expect(slider?.getAttribute('aria-valuemax')).toBe('100');
    expect(slider?.getAttribute('aria-valuenow')).toBe('50');
    expect(slider?.getAttribute('tabindex')).toBe('0');
  });

  it('uses the label as the aria-label when provided', () => {
    render({ value: 7, onChange: () => {}, label: 'Healing Rate' });
    expect(getSlider()?.getAttribute('aria-label')).toBe('Healing Rate');
  });

  it('falls back to a generated aria-label when no label prop is given', () => {
    render({ value: 42, onChange: () => {} });
    expect(getSlider()?.getAttribute('aria-label')).toBe('Rate dial: 42');
  });

  it('shows the numeric value below the dial when showValue=true (default)', () => {
    render({ value: 73, onChange: () => {} });
    expect(container.textContent).toContain('73');
  });

  it('hides the value label when showValue=false', () => {
    render({ value: 73, onChange: () => {}, showValue: false });
    expect(container.textContent).not.toContain('73');
  });

  it('shows the label text below the value when both are provided', () => {
    render({ value: 50, onChange: () => {}, label: 'Intensity' });
    expect(container.textContent).toContain('Intensity');
  });

  it('sets tabindex=-1 when disabled, removing from tab order', () => {
    render({ value: 50, onChange: () => {}, disabled: true });
    expect(getSlider()?.getAttribute('tabindex')).toBe('-1');
  });

  it('applies opacity-50 + cursor-not-allowed when disabled', () => {
    render({ value: 50, onChange: () => {}, disabled: true });
    const slider = getSlider();
    expect(slider?.className).toContain('opacity-50');
    expect(slider?.className).toContain('cursor-not-allowed');
  });

  it('does not call onChange when ArrowUp is pressed and disabled', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, disabled: true });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('calls onChange with value+1 on ArrowUp', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(51);
  });

  it('calls onChange with value-1 on ArrowDown', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(49);
  });

  it('clamps to max on ArrowUp at the top of the range', () => {
    const onChange = vi.fn();
    render({ value: 100, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(100);
  });

  it('clamps to min on ArrowDown at the bottom of the range', () => {
    const onChange = vi.fn();
    render({ value: 0, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('jumps by 10 on PageUp', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'PageUp', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(60);
  });

  it('jumps by -10 on PageDown', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(40);
  });

  it('clamps PageUp to max when overshoot would exceed range', () => {
    const onChange = vi.fn();
    render({ value: 95, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'PageUp', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(100);
  });

  it('clamps PageDown to min when overshoot would underflow range', () => {
    const onChange = vi.fn();
    render({ value: 5, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('Home key sets value to min', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Home', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('End key sets value to max', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'End', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(100);
  });

  it('ArrowRight behaves like ArrowUp (delta=+1)', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(51);
  });

  it('ArrowLeft behaves like ArrowDown (delta=-1)', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(49);
  });

  it('unrecognized keys do not call onChange', () => {
    const onChange = vi.fn();
    render({ value: 50, onChange, min: 0, max: 100 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })
      );
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'a', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('respects custom min/max range (0–1000)', () => {
    const onChange = vi.fn();
    render({ value: 500, onChange, min: 0, max: 1000 });
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Home', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(0);
    act(() => {
      getSlider()?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'End', bubbles: true, cancelable: true })
      );
    });
    expect(onChange).toHaveBeenCalledWith(1000);
  });
});
