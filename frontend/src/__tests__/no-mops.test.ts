/**
 * Regression test: MOPS stays retired (owner decision 2026-10-14,
 * docs/DEVELOPMENT_ROADMAP.md "Decisions").
 *
 * The backend no longer serves /api/v1/mops/* and no response carries a
 * MOPS figure. Displays use operations-ledger facts instead
 * (lib/operationsSummary.ts). Comment lines are skipped so history can be
 * described in prose.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const SRC_ROOT = path.resolve(__dirname, '..');
const SELF = path.join('__tests__', 'no-mops.test.ts');

/** A fetch of the retired routes, or code that reads/declares MOPS data. */
const MOPS_CODE_RE = /\/mops\/|scalar_mops|mopsData|mopsAverages|MopsAverages|MopsWindow|MOPS_AVERAGES/;

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) out.push(full);
  }
  return out;
}

describe('MOPS is retired', () => {
  it('no source file fetches /mops or handles MOPS payloads', () => {
    const offenders: string[] = [];
    for (const file of walk(SRC_ROOT)) {
      const rel = path.relative(SRC_ROOT, file);
      if (rel === SELF) continue;
      fs.readFileSync(file, 'utf8')
        .split(/\r?\n/)
        .forEach((line, i) => {
          const trimmed = line.trimStart();
          if (trimmed.startsWith('*') || trimmed.startsWith('//') || trimmed.startsWith('/*')) return;
          if (MOPS_CODE_RE.test(line)) offenders.push(`${rel}:${i + 1}: ${trimmed.slice(0, 100)}`);
        });
    }
    expect(offenders, `MOPS references found:\n${offenders.join('\n')}`).toEqual([]);
  });
});
