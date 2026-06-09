/**
 * Regression: 404 fallback Route in App.jsx.
 *
 * Catches any path that doesn't match a known route, so users see a
 * "Not Found" message instead of a blank content area. Uses the
 * Antd Result component for visual consistency with the rest of the
 * dark themed UI.
 */
import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Result, ConfigProvider, theme } from 'antd';

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

/**
 * The NotFound component mirrors the JSX rendered by the catch-all
 * Route in App.jsx. If the App.jsx implementation changes, update
 * this mirror to match (or, better, export the component from App.jsx
 * and import it here).
 */
function NotFound() {
  return (
    <div className="flex-1 flex items-center justify-center bg-gray-900">
      <Result
        status="404"
        title="404"
        subTitle="The path you requested does not match any known route."
        extra={
          <a
            href="/command-center"
            className="inline-block px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
          >
            Return to Command Center
          </a>
        }
      />
    </div>
  );
}

function renderWithRoute(initialPath: string) {
  act(() => {
    root.render(
      <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/" element={<div>Home</div>} />
            <Route path="/known" element={<div>Known</div>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </MemoryRouter>
      </ConfigProvider>
    );
  });
}

describe('404 fallback Route', () => {
  it('renders the 404 for an unknown path', () => {
    renderWithRoute('/this/does/not/exist');
    expect(container.textContent).toContain('404');
    expect(container.textContent).toContain('The path you requested does not match any known route.');
  });

  it('does NOT render the 404 for a known path', () => {
    renderWithRoute('/known');
    expect(container.textContent).toContain('Known');
    expect(container.textContent).not.toContain('404');
  });

  it('does NOT render the 404 for the root', () => {
    renderWithRoute('/');
    expect(container.textContent).toContain('Home');
    expect(container.textContent).not.toContain('404');
  });
});
