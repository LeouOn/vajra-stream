/**
 * Reading — one value with its provenance (docs/DEVELOPMENT_ROADMAP.md,
 * Phase 2). A draw reads as "drawn" and never becomes a meter, even when the
 * label arrives as untyped payload data.
 */
import React, { act } from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
import Reading, {
  ReadingMeter,
  isMeterProvenance,
  type MeterProvenance,
  type ReadingProps,
} from '../../components/UI/Reading';
import { fieldProvenance } from '../../lib/provenance';
import type { Provenance } from '../../types/operations';

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

const render = (node: React.ReactElement) => {
  act(() => root.render(node));
};

const meters = () => container.querySelectorAll('[role="meter"], [role="progressbar"]');

describe('Reading', () => {
  it('renders the value with its provenance tag', () => {
    render(<Reading label="Moon" value="12.5%" provenance="computed" />);
    expect(container.textContent).toBe('Moon 12.5% computed');
    expect(container.querySelector('[data-reading="computed"]')).not.toBeNull();
    expect(container.querySelector('[data-provenance="computed"]')?.textContent).toBe('computed');
  });

  it('reads a draw as "drawn"', () => {
    render(<Reading value={7} unit="/10" provenance="draw" />);
    expect(container.textContent).toBe('7/10 drawn');
    expect(container.querySelector('[data-provenance="draw"]')?.textContent).toBe('drawn');
  });

  it('draws a meter for a computed value', () => {
    render(<Reading value="40%" provenance="computed" meter={40} />);
    const bar = meters();
    expect(bar).toHaveLength(1);
    expect(bar[0].getAttribute('aria-valuenow')).toBe('40');
    expect(bar[0].getAttribute('data-meter')).toBe('computed');
  });

  it('never draws a meter for a draw, even from untyped payload data', () => {
    // A label read from JSON is only known to be a string; fieldProvenance
    // narrows it, and a draw falls through to the plain reading.
    const payload: unknown = JSON.parse('{"provenance": {"gv": "draw"}}');
    const kind: Provenance = fieldProvenance((payload as { provenance?: unknown }).provenance, 'gv', 'computed');
    expect(kind).toBe('draw');
    // The types reject `meter` with a draw; force it through as untyped data would.
    const props = { value: 812, provenance: kind, meter: 81 } as unknown as ReadingProps;
    render(<Reading {...props} />);
    expect(meters()).toHaveLength(0);
    expect(container.textContent).toBe('812 drawn');
  });

  it('ReadingMeter refuses a draw or decoration that slips past the types', () => {
    const smuggled = ['draw', 'decorative', 'measured'] as unknown as MeterProvenance[];
    render(<>{smuggled.map((p) => <ReadingMeter key={String(p)} percent={50} provenance={p} />)}</>);
    expect(meters()).toHaveLength(0);
  });

  it('clamps the meter to 0–100', () => {
    render(<ReadingMeter percent={250} provenance="record" />);
    expect(meters()[0].getAttribute('aria-valuenow')).toBe('100');
  });
});

describe('fieldProvenance', () => {
  it('prefers the payload label and falls back for legacy payloads', () => {
    expect(fieldProvenance({ moon_phase: 'decorative' }, 'moon_phase', 'computed')).toBe('decorative');
    expect(fieldProvenance(undefined, 'moon_phase', 'computed')).toBe('computed');
    expect(fieldProvenance({ moon_phase: 'measured' }, 'moon_phase', 'computed')).toBe('computed');
  });
});

describe('isMeterProvenance', () => {
  it('admits only records and computed values', () => {
    expect(isMeterProvenance('record')).toBe(true);
    expect(isMeterProvenance('computed')).toBe(true);
    expect(isMeterProvenance('draw')).toBe(false);
    expect(isMeterProvenance('decorative')).toBe(false);
  });
});
