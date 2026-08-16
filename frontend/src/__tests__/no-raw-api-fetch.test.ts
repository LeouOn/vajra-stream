/**
 * Regression test (ADR 004): no raw `/api/v1` fetch calls outside `utils/api.ts`.
 *
 * Every frontend HTTP call must compose its URL through `apiUrl()` from
 * `utils/api.ts` (proxy-relative strategy). Hardcoding `fetch('/api/v1/...')`
 * bypasses the `VITE_API_BASE` build-time override and reintroduces the
 * doubled-prefix bug class (see docs/decisions/004-url-strategy.md).
 *
 * `utils/api.ts` itself is exempt — it is the one place allowed to spell out
 * the `/api/v1` prefix. Comment lines are skipped so doc mentions stay legal.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const SRC_ROOT = path.resolve(__dirname, '..');
const EXEMPT = new Set<string>([path.join('utils', 'api.ts')]);

/** Matches `fetch(` immediately followed by a quoted/backticked `/api/v1` literal. */
const RAW_FETCH_RE = /fetch\((['"`])\/api\/v1/;

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(full));
    } else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

describe('ADR 004: proxy-relative URL strategy', () => {
  it('no raw /api/v1 fetch literals outside utils/api.ts', () => {
    const offenders: string[] = [];
    for (const file of walk(SRC_ROOT)) {
      const rel = path.relative(SRC_ROOT, file);
      if (EXEMPT.has(rel)) continue;
      const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
      lines.forEach((line, i) => {
        const trimmed = line.trimStart();
        if (trimmed.startsWith('*') || trimmed.startsWith('//')) return;
        if (RAW_FETCH_RE.test(line)) {
          offenders.push(`${rel}:${i + 1}: ${trimmed.trim().slice(0, 100)}`);
        }
      });
    }
    expect(offenders, `Raw /api/v1 fetch calls found:\n${offenders.join('\n')}\nUse apiUrl('/foo') from utils/api instead.`).toEqual([]);
  });
});
