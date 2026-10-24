// @vitest-environment happy-dom
/**
 * W6-D1a: the labelled latitude/longitude entry in the Sky time card.
 * RED first: the inputs do not exist before the change.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

import SkyTimeControls from '../../components/UI/SkyTimeControls';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { useSkyStore } from '../../stores/skyStore';

vi.mock('../../lib/sunEventsClient', () => ({
  fetchSunEvents: vi.fn(),
  cancelSunEventsRequest: vi.fn(),
}));

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;

function mount(): void {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(<SkyTimeControls />);
  });
}

function byLabel(label: string): HTMLElement {
  const el = container.querySelector<HTMLElement>(`[aria-label="${label}"]`);
  if (el === null) throw new Error(`no element with aria-label ${label}`);
  return el;
}

function setValue(el: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
  if (!setter) throw new Error('no value setter');
  setter.call(el, value);
  act(() => {
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

function click(el: Element): void {
  act(() => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-10-24T09:00:00Z'));
  useSkyStore.setState({ lat: DEFAULT_LAT, lng: DEFAULT_LNG, label: undefined, at: null });
  window.matchMedia = vi.fn(() => ({
    matches: false,
    media: '',
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('observer latitude/longitude entry', () => {
  it('shows the current observer and applies typed values with Set place', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    const lngInput = byLabel('Longitude, degrees east') as HTMLInputElement;
    expect(Number(latInput.value)).toBeCloseTo(DEFAULT_LAT, 3);
    expect(Number(lngInput.value)).toBeCloseTo(DEFAULT_LNG, 3);

    setValue(latInput, '36.1');
    setValue(lngInput, '139.4');
    click(byLabel('Set place from latitude and longitude'));
    expect(useSkyStore.getState().lat).toBeCloseTo(36.1, 4);
    expect(useSkyStore.getState().lng).toBeCloseTo(139.4, 4);
  });

  it('rejects a bad latitude with a role=alert message and leaves the store untouched', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '91');
    act(() => {
      latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    });
    const alert = container.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(alert?.textContent ?? '').toMatch(/latitude/i);
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
    expect(useSkyStore.getState().lng).toBe(DEFAULT_LNG);
  });

  it('follows a store change when not editing', () => {
    mount();
    act(() => {
      useSkyStore.getState().setObserver(10, 20);
    });
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    const lngInput = byLabel('Longitude, degrees east') as HTMLInputElement;
    expect(Number(latInput.value)).toBeCloseTo(10, 3);
    expect(Number(lngInput.value)).toBeCloseTo(20, 3);
  });

  it('does not overwrite a mid-edit field when the store changes', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '50');
    act(() => {
      useSkyStore.getState().setObserver(10, 20);
    });
    expect(Number((byLabel('Latitude, degrees north') as HTMLInputElement).value)).toBe(50);
    expect(useSkyStore.getState().lat).toBe(10);
  });

  it('rejects invalid raw text with a field-naming alert and no stale fallback', () => {
    for (const [text, pattern] of [
      ['36,1,2', /latitude must be a number like 36\.1/i],
      ['abc', /latitude must be a number like 36\.1/i],
      ['-', /latitude must be a number like 36\.1/i],
      ['', /latitude must be a number like 36\.1/i],
      ['1e2', /latitude must be a number like 36\.1/i],
    ] as const) {
      mount();
      const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
      setValue(latInput, text);
      act(() => {
        latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
      });
      expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
      expect(container.querySelector('[role="alert"]')?.textContent ?? '').toMatch(pattern);
      act(() => {
        root.unmount();
      });
      container.remove();
    }
  });

  it('wraps longitude consistently on Enter, blur and Set place, and shows the wrapped value', () => {
    for (const path of ['enter', 'blur', 'button'] as const) {
      mount();
      const lngInput = byLabel('Longitude, degrees east') as HTMLInputElement;
      setValue(lngInput, '200');
      if (path === 'enter') {
        act(() => {
          lngInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
        });
      } else if (path === 'blur') {
        act(() => {
          lngInput.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
        });
      } else {
        click(byLabel('Set place from latitude and longitude'));
      }
      expect(useSkyStore.getState().lng).toBe(-160);
      expect(Number((byLabel('Longitude, degrees east') as HTMLInputElement).value)).toBe(-160);
      act(() => {
        root.unmount();
      });
      container.remove();
    }
  });

  it('an untouched apply is a no-op and keeps the full precision', () => {
    useSkyStore.getState().setObserver(36.11111, 139.44444);
    mount();
    click(byLabel('Set place from latitude and longitude'));
    expect(useSkyStore.getState().lat).toBe(36.11111);
    expect(useSkyStore.getState().lng).toBe(139.44444);
  });

  it('shows at most 6 decimals while a no-op apply keeps the full value', () => {
    useSkyStore.getState().setObserver(36.111111111, 139.444444444);
    mount();
    const shown = (byLabel('Latitude, degrees north') as HTMLInputElement).value;
    expect(shown.length).toBeLessThanOrEqual('36.111111'.length);
    click(byLabel('Set place from latitude and longitude'));
    expect(useSkyStore.getState().lat).toBe(36.111111111);
    expect(useSkyStore.getState().lng).toBe(139.444444444);
  });

  it('keeps an incomplete draft through a pick and offers Use current place', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '-');
    act(() => {
      useSkyStore.getState().setObserver(10, 20);
    });
    expect((byLabel('Latitude, degrees north') as HTMLInputElement).value).toBe('-');
    expect(byLabel('Set place from latitude and longitude').getAttribute('data-pending')).toBe('true');
    const cancel = byLabel('Use the current place and discard the draft');
    click(cancel);
    expect(Number((byLabel('Latitude, degrees north') as HTMLInputElement).value)).toBe(10);
    expect(Number((byLabel('Longitude, degrees east') as HTMLInputElement).value)).toBe(20);
    expect(container.querySelector('[data-testid="sky-place-cancel"]')).toBeNull();
  });

  it('a valid draft follows the same path and blur commits it', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '36.5');
    act(() => {
      latInput.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
    });
    expect(useSkyStore.getState().lat).toBeCloseTo(36.5, 4);
  });

  it('accepts a comma decimal and NFKC full-width digits', () => {
    for (const [text, expected] of [['36,1', 36.1], ['３６．１', 36.1], ['+36,1', 36.1]] as const) {
      mount();
      const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
      setValue(latInput, text);
      act(() => {
        latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
      });
      expect(useSkyStore.getState().lat).toBeCloseTo(expected, 4);
      act(() => {
        root.unmount();
      });
      container.remove();
    }
  });

  it('rejects a comma and a degree sign consistently on Enter, blur and Set place', () => {
    for (const [text, which] of [['36,1,2', 'lat'], ['37.7749°', 'lng'], ['36,1,2', 'lng']] as const) {
      for (const path of ['enter', 'blur', 'button'] as const) {
        mount();
        const input = byLabel(which === 'lat' ? 'Latitude, degrees north' : 'Longitude, degrees east') as HTMLInputElement;
        const before = useSkyStore.getState();
        setValue(input, text);
        if (path === 'enter') {
          act(() => {
            input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
          });
        } else if (path === 'blur') {
          act(() => {
            input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
          });
        } else {
          click(byLabel('Set place from latitude and longitude'));
        }
        expect(useSkyStore.getState().lat).toBe(before.lat);
        expect(useSkyStore.getState().lng).toBe(before.lng);
        expect(container.querySelector('[role="alert"]')).not.toBeNull();
        act(() => {
          root.unmount();
        });
        container.remove();
      }
    }
  });

  it('an exponent-formatted store coordinate does not block a commit of the other field', () => {
    useSkyStore.getState().setObserver(1e-7, 20);
    mount();
    const lngInput = byLabel('Longitude, degrees east') as HTMLInputElement;
    setValue(lngInput, '21');
    act(() => {
      lngInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    });
    expect(useSkyStore.getState().lat).toBe(1e-7);
    expect(useSkyStore.getState().lng).toBe(21);
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it('clamps the latitude spinner at the pole instead of offering 90.1', () => {
    useSkyStore.getState().setObserver(90, 20);
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    act(() => {
      latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', keyCode: 38, bubbles: true }));
    });
    expect(Number((byLabel('Latitude, degrees north') as HTMLInputElement).value)).toBe(90);
    act(() => {
      latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    });
    expect(useSkyStore.getState().lat).toBe(90);
  });

  it('a clean field follows a pick while the other keeps its draft', () => {
    mount();
    const lngInput = byLabel('Longitude, degrees east') as HTMLInputElement;
    setValue(lngInput, '1');
    act(() => {
      useSkyStore.getState().setObserver(10, 20);
    });
    expect(Number((byLabel('Latitude, degrees north') as HTMLInputElement).value)).toBe(10);
    expect(Number((byLabel('Longitude, degrees east') as HTMLInputElement).value)).toBe(1);
    act(() => {
      lngInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    });
    expect(useSkyStore.getState().lat).toBe(10);
    expect(useSkyStore.getState().lng).toBe(1);
  });

  it('Escape cancels an unblurred draft', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '50');
    act(() => {
      latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true }));
    });
    expect(useSkyStore.getState().lat).toBe(DEFAULT_LAT);
    expect(Number((byLabel('Latitude, degrees north') as HTMLInputElement).value)).toBeCloseTo(DEFAULT_LAT, 4);
    expect(container.querySelector('[data-testid="sky-place-cancel"]')).toBeNull();
  });

  it('marks the failing field with aria-invalid and describes it from the alert', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '91');
    act(() => {
      latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    });
    expect(latInput.getAttribute('aria-invalid')).toBe('true');
    expect(latInput.getAttribute('aria-describedby')).toBe('sky-place-error-text');
    expect((byLabel('Longitude, degrees east') as HTMLInputElement).getAttribute('aria-invalid')).toBeNull();
    expect(container.querySelector('#sky-place-error-text')).not.toBeNull();
  });

  it('applies on Enter in either field', () => {
    mount();
    const latInput = byLabel('Latitude, degrees north') as HTMLInputElement;
    setValue(latInput, '12.5');
    act(() => {
      latInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
    });
    expect(useSkyStore.getState().lat).toBeCloseTo(12.5, 4);
  });
});


describe('c1 34-value x 5-path matrix regression', () => {
  const paths = ['enter', 'enterOther', 'blur', 'button', 'blurButton'] as const;
  const latValues = ['91', '-91', '36,1', '-', 'abc', '', '200', '1e2', '+36.1', '00036.1', ' 36.1 ', '36.1', '36.', '.5', '-0', '37.7749°', '３６．１', '36.1.2'];
  const lngValues = ['200', '-200', '181', '360', '540', '36,1', '-', 'abc', '', '1e2', '+139.4', '00139.4', ' 139.4 ', '139.4', '-0', '139.4°'];
  function fieldOf(which: 'lat' | 'lng'): HTMLInputElement {
    return byLabel(which === 'lat' ? 'Latitude, degrees north' : 'Longitude, degrees east') as HTMLInputElement;
  }
  function run(which: 'lat' | 'lng', value: string, path: (typeof paths)[number]) {
    mount();
    const other = which === 'lat' ? 'lng' : 'lat';
    setValue(fieldOf(which), value);
    if (path === 'enter') {
      act(() => fieldOf(which).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true })));
    } else if (path === 'enterOther') {
      act(() => fieldOf(other).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true })));
    } else if (path === 'blur') {
      act(() => fieldOf(which).dispatchEvent(new FocusEvent('focusout', { bubbles: true })));
    } else if (path === 'button') {
      click(byLabel('Set place from latitude and longitude'));
    } else {
      act(() => fieldOf(which).dispatchEvent(new FocusEvent('focusout', { bubbles: true })));
      click(byLabel('Set place from latitude and longitude'));
    }
    const state = useSkyStore.getState();
    const result = {
      store: `${state.lat},${state.lng}`,
      error: container.querySelector('[role="alert"]')?.textContent ?? null,
    };
    act(() => root.unmount());
    container.remove();
    return result;
  }
  for (const which of ['lat', 'lng'] as const) {
    for (const value of which === 'lat' ? latValues : lngValues) {
      it(`${which} ${JSON.stringify(value)} agrees on every submit path`, () => {
        const rows = paths.map((path) => run(which, value, path));
        const first = rows[0];
        const disagreements = rows.filter((row) => row.store !== first.store || (row.error === null) !== (first.error === null));
        expect(disagreements).toEqual([]);
        const moved = first.store !== `${DEFAULT_LAT},${DEFAULT_LNG}`;
        expect(moved || first.error !== null).toBe(true);
      });
    }
  }
});
