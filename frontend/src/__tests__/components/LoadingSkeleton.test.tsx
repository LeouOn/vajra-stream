/**
 * Tests for LoadingSkeleton — placeholder components for loading states.
 * Uses the same happy-dom + createRoot pattern as the other component
 * tests (StatusIndicator, VisualizationSelector, etc.).
 *
 * The component is pure render with no hooks, so tests focus on:
 *   - variant-based class selection (text, title, circle, etc.)
 *   - count-based multiplicity (renders N skeleton divs)
 *   - explicit width/height pass-through
 *   - aria-hidden for accessibility
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import {
  LoadingSkeleton,
  CardSkeleton,
  ListSkeleton,
  TableSkeleton,
  SessionSkeleton,
  DharmaTaleSkeleton,
} from '../../components/UI/LoadingSkeleton';

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

const render = (node: React.ReactElement) => {
  act(() => { root.render(node); });
};

describe('<LoadingSkeleton />', () => {
  it('renders a single skeleton div by default (count=1)', () => {
    render(<LoadingSkeleton />);
    expect(container.querySelectorAll('div')).toHaveLength(1);
  });

  it('renders N skeleton divs when count is provided', () => {
    render(<LoadingSkeleton count={5} />);
    expect(container.querySelectorAll('div')).toHaveLength(5);
  });

  it('applies animate-pulse class for the pulse animation', () => {
    render(<LoadingSkeleton />);
    expect(container.querySelector('div')?.className).toContain('animate-pulse');
  });

  it('applies circle variant class (rounded-full)', () => {
    render(<LoadingSkeleton variant="circle" />);
    expect(container.querySelector('div')?.className).toContain('rounded-full');
  });

  it('applies text variant default height of 1rem', () => {
    render(<LoadingSkeleton variant="text" />);
    const div = container.querySelector('div') as HTMLDivElement;
    expect(div.style.height).toBe('1rem');
  });

  it('applies title variant default height of 1.5rem', () => {
    render(<LoadingSkeleton variant="title" />);
    const div = container.querySelector('div') as HTMLDivElement;
    expect(div.style.height).toBe('1.5rem');
  });

  it('applies avatar variant dimensions (w-10 h-10 rounded-full)', () => {
    render(<LoadingSkeleton variant="avatar" />);
    expect(container.querySelector('div')?.className).toContain('w-10 h-10 rounded-full');
  });

  it('passes through custom width and height', () => {
    render(<LoadingSkeleton width="200px" height="50px" />);
    const div = container.querySelector('div') as HTMLDivElement;
    expect(div.style.width).toBe('200px');
    expect(div.style.height).toBe('50px');
  });

  it('applies custom className alongside base classes', () => {
    render(<LoadingSkeleton className="my-2" />);
    expect(container.querySelector('div')?.className).toContain('my-2');
  });

  it('marks skeleton as aria-hidden for screen readers', () => {
    render(<LoadingSkeleton />);
    expect(container.querySelector('div')?.getAttribute('aria-hidden')).toBe('true');
  });
});

describe('<CardSkeleton />', () => {
  it('renders a card-shaped skeleton (multiple divs)', () => {
    render(<CardSkeleton />);
    // CardSkeleton composes ~7 LoadingSkeleton divs (circle, title, text x 3, etc.)
    expect(container.querySelectorAll('div').length).toBeGreaterThan(5);
  });

  it('includes a circular avatar placeholder', () => {
    render(<CardSkeleton />);
    const avatar = container.querySelector('div.rounded-full');
    expect(avatar).not.toBeNull();
  });
});

describe('<ListSkeleton />', () => {
  it('renders 3 list items by default', () => {
    render(<ListSkeleton />);
    // 3 outer rows + each row's 3 inner skeletons = 9 + circles, etc.
    // We just check the outer-row count to keep it simple.
    const rows = container.querySelectorAll('.flex.items-center.gap-3.p-3');
    expect(rows).toHaveLength(3);
  });

  it('renders N list items when count is provided', () => {
    render(<ListSkeleton count={7} />);
    const rows = container.querySelectorAll('.flex.items-center.gap-3.p-3');
    expect(rows).toHaveLength(7);
  });
});

describe('<TableSkeleton />', () => {
  it('renders 5 rows by default', () => {
    render(<TableSkeleton />);
    const rows = container.querySelectorAll('.flex.gap-4.py-3');
    expect(rows).toHaveLength(5);
  });

  it('renders custom row and column counts', () => {
    render(<TableSkeleton rows={3} columns={2} />);
    const rows = container.querySelectorAll('.flex.gap-4.py-3');
    expect(rows).toHaveLength(3);
    // Each row should have 2 skeleton columns
    rows.forEach((row) => {
      expect(row.querySelectorAll('div')).toHaveLength(2);
    });
  });
});

describe('<SessionSkeleton />', () => {
  it('renders a session-shaped skeleton', () => {
    render(<SessionSkeleton />);
    expect(container.querySelectorAll('div').length).toBeGreaterThan(10);
  });
});

describe('<DharmaTaleSkeleton />', () => {
  it('renders 3 action button placeholders in the header', () => {
    render(<DharmaTaleSkeleton />);
    // 3 header button skeletons share w-60 h-28 (60x28)
    const headerButtons = container.querySelectorAll('.flex.gap-2 > div');
    expect(headerButtons).toHaveLength(3);
  });
});
