/**
 * URL strategy enforcement test (Wave 4 Task 25, ADR 004).
 *
 * Pins the proxy-relative URL contract for the entire frontend source tree:
 *
 *   1. No source file under `frontend/src` may contain a hardcoded absolute
 *      backend URL of the form `http://localhost:8008/...` or
 *      `http://127.0.0.1:8008/...`. All HTTP traffic must ride the
 *      reverse-proxy-relative `/api/v1/...` form so the app works on any
 *      origin/port without per-origin CORS or hardcoded-port coupling.
 *
 *   2. No source file may reference the legacy absolute `${API_BASE}`
 *      template form (which historically resolved to the absolute
 *      `${protocol}//${hostname}:8008/api/v1`). Migrated call sites use
 *      either the `/api/v1/...` literal or the `apiUrl('/foo')` helper.
 *
 *   3. The `apiUrl(path)` helper must be exported and must produce a
 *      proxy-relative URL by default, honouring an optional
 *      `VITE_API_BASE` build-time override for non-localhost deployments.
 *
 * Background: ADR 004 (`docs/decisions/004-url-strategy.md`) records the
 * decision. Wave 1 Task 8 (commit `c8aa56e`) fixed the symptomatic
 * doubled-prefix bug in `AstrologyExtractionPanel.jsx`; this test makes
 * the entire bug class structurally impossible.
 *
 * This is a static source-tree assertion — it reads files via `node:fs`
 * and regex-matches. It runs in the default vitest `node` environment.
 */
import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { apiUrl, API_BASE } from '../api';

const SRC_ROOT = join(__dirname, '..', '..');
const SKIP_DIRS = new Set(['__tests__', 'node_modules', 'dist', '.vite']);

const SOURCE_EXTENSIONS = new Set([
  '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
]);

function walkSourceFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      walkSourceFiles(full, acc);
    } else if (SOURCE_EXTENSIONS.has(extname(full))) {
      acc.push(full);
    }
  }
  return acc;
}

function readAllSources(): Array<{ path: string; content: string }> {
  return walkSourceFiles(SRC_ROOT).map((p) => ({
    path: relative(SRC_ROOT, p).replace(/\\/g, '/'),
    content: readFileSync(p, 'utf8'),
  }));
}

describe('frontend URL strategy (ADR 004)', () => {
  it('no source file hardcodes an absolute backend URL (localhost or 127.0.0.1)', () => {
    const offenders: Array<{ path: string; line: number; text: string }> = [];
    const pattern = /http:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?\/api/i;

    for (const { path, content } of readAllSources()) {
      content.split(/\r?\n/).forEach((line, idx) => {
        if (pattern.test(line)) {
          offenders.push({ path, line: idx + 1, text: line.trim() });
        }
      });
    }

    expect(offenders).toEqual([]);
  });

  it('no source file references the legacy absolute `${API_BASE}` template form', () => {
    const offenders: Array<{ path: string; line: number; text: string }> = [];
    // Match `${API_BASE}` template substitution (escaped backtick + ${...}).
    const pattern = /\$\{API_BASE\}/;

    for (const { path, content } of readAllSources()) {
      content.split(/\r?\n/).forEach((line, idx) => {
        if (pattern.test(line)) {
          offenders.push({ path, line: idx + 1, text: line.trim() });
        }
      });
    }

    expect(offenders).toEqual([]);
  });

  it('apiUrl() helper is exported and produces a proxy-relative URL by default', () => {
    expect(typeof apiUrl).toBe('function');
    // Default: baseUrl === '' → URL is exactly `/api/v1${path}`.
    expect(apiUrl('/foo')).toBe('/api/v1/foo');
    expect(apiUrl('/healing/chakra/all')).toBe('/api/v1/healing/chakra/all');
  });

  it('API_BASE remains exported as a backward-compatible alias ending in /api/v1', () => {
    expect(typeof API_BASE).toBe('string');
    expect(API_BASE.endsWith('/api/v1')).toBe(true);
  });
});
