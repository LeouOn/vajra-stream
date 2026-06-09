/**
 * Tests for ErrorBoundary — catches render errors in children and
 * shows a compact retry panel.
 *
 * Uses happy-dom + createRoot. We trigger an error by rendering a
 * child that throws during render, then verify the fallback UI
 * appears, and that clicking Retry resets the boundary.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import ErrorBoundary from '../../components/UI/ErrorBoundary';

let container: HTMLDivElement;
let root: ReturnType<typeof createRoot>;

// Suppress React's expected error logging for thrown render errors
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => { root.unmount(); });
  container.remove();
  console.error = originalError;
});

/** A child that throws on render. The throw is wrapped in a flag
 *  so we can flip it on/off from the test to verify retry works. */
let shouldThrow = false;
function Boom(): React.ReactElement {
  if (shouldThrow) throw new Error('kaboom');
  return <span>child content</span>;
}

const renderBoundary = (children: React.ReactNode) => {
  act(() => {
    root.render(<ErrorBoundary>{children}</ErrorBoundary>);
  });
};

describe('<ErrorBoundary />', () => {
  it('renders children when no error is thrown', () => {
    shouldThrow = false;
    renderBoundary(<Boom />);
    expect(container.textContent).toContain('child content');
    expect(container.textContent).not.toContain('Component failed to load');
  });

  it('renders fallback UI when a child throws', () => {
    shouldThrow = true;
    renderBoundary(<Boom />);
    expect(container.textContent).toContain('Component failed to load');
    expect(container.textContent).toContain('kaboom');
  });

  it('uses fallbackTitle prop when provided', () => {
    shouldThrow = true;
    renderBoundary(<Boom />);
    // The renderBoundary above used the default; re-render with a custom title
    act(() => {
      root.render(
        <ErrorBoundary fallbackTitle="Visualization crashed">
          <Boom />
        </ErrorBoundary>
      );
    });
    expect(container.textContent).toContain('Visualization crashed');
  });

  it('shows a generic message when error has no message', () => {
    shouldThrow = true;
    // Throw an error without a message via a fresh component
    function SilentBoom(): React.ReactElement {
      throw new Error();
    }
    act(() => {
      root.render(
        <ErrorBoundary>
          <SilentBoom />
        </ErrorBoundary>
      );
    });
    expect(container.textContent).toContain('An unexpected error occurred');
  });

  it('resets back to children when Retry is clicked', () => {
    shouldThrow = true;
    renderBoundary(<Boom />);
    expect(container.textContent).toContain('Component failed to load');

    // Click retry — this should flip the boundary state back to hasError=false
    // and re-render children. The child Boom still throws, so we expect
    // the fallback again. But the act() of clicking must not throw.
    const retryButton = container.querySelector('button');
    expect(retryButton).not.toBeNull();
    expect(retryButton?.textContent).toContain('Retry');

    // Flip the flag so re-render succeeds — verifies the boundary actually reset
    shouldThrow = false;
    act(() => { retryButton?.click(); });
    expect(container.textContent).toContain('child content');
  });
});
