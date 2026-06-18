/**
 * Wave 5 Task 33 — Consolidate to shared ErrorBoundary.
 *
 * Regression guard: `frontend/src/App.jsx` must NOT define its own local
 * `class ErrorBoundary`. It must import the canonical shared component
 * from `./components/UI/ErrorBoundary` so there is exactly one
 * ErrorBoundary implementation in the frontend.
 *
 * See evaluation Issue 4.4.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const APP_PATH = resolve(
  __dirname,
  '..',
  '..',
  'App.jsx',
);

const APP_SOURCE = readFileSync(APP_PATH, 'utf-8');

describe('App.jsx — no local ErrorBoundary class (remediation-33)', () => {
  it('does not declare a local `class ErrorBoundary`', () => {
    // Reject any `class ErrorBoundary extends ...` declaration.
    // Allow leading whitespace; reject trailing non-word so we don't
    // accidentally match a hypothetical `ErrorBoundaryWrapper`.
    const localClassPattern = /\bclass\s+ErrorBoundary\b\s+extends\b/;
    expect(localClassPattern.test(APP_SOURCE)).toBe(false);
  });

  it('imports ErrorBoundary from the shared UI ErrorBoundary module', () => {
    // Accept either a default import of the file ErrorBoundary.jsx
    // (with or without the .jsx extension, and with or without `type`).
    const importPattern =
      /import\s+ErrorBoundary\s+from\s+['"][./]+components\/UI\/ErrorBoundary(\.jsx)?['"]/;
    expect(importPattern.test(APP_SOURCE)).toBe(true);
  });
});
