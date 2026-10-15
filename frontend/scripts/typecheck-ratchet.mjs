#!/usr/bin/env node
/**
 * TypeScript error gate.
 *
 * `vite build` does not type-check, so type errors used to ship silently
 * (e.g. an un-imported <UniverseTab> that crashed the Outlook tab at runtime).
 * The backlog was burned down to zero (2026-10-15), so `.tsc-baseline` is 0
 * and any error fails. The ratchet machinery stays for honesty: the baseline
 * can only go down, never up.
 *
 *   npm run typecheck                  # fail on any error above the baseline (0)
 *   npm run typecheck -- --update      # lower the baseline to the current count
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const baselinePath = join(root, '.tsc-baseline');
const tsc = createRequire(import.meta.url).resolve('typescript/bin/tsc');

let output = '';
try {
  output = execFileSync(process.execPath, [tsc, '--noEmit', '-p', root], { cwd: root, encoding: 'utf8' });
} catch (err) {
  // tsc exits non-zero whenever errors exist; the count is what we gate on.
  output = `${err.stdout ?? ''}${err.stderr ?? ''}`;
}

const errors = output.split(/\r?\n/).filter((line) => /error TS\d+/.test(line));
const count = errors.length;

const baseline = Number.parseInt(readFileSync(baselinePath, 'utf8').trim(), 10);
if (Number.isNaN(baseline)) {
  console.error(`Could not parse ${baselinePath}.`);
  process.exit(2);
}

if (process.argv.includes('--update')) {
  if (count > baseline) {
    // The gate only tightens: a rise is fixed in code, not by raising the baseline.
    console.error(
      `Refusing to raise the tsc baseline from ${baseline} to ${count}. Fix the new errors:\n`,
    );
    console.error(errors.join('\n'));
    process.exit(1);
  }
  writeFileSync(baselinePath, `${count}\n`);
  console.log(`tsc baseline set to ${count}.`);
  process.exit(0);
}

if (count > baseline) {
  const what = baseline === 0 ? 'TypeScript must stay error-free' : `TypeScript errors rose from ${baseline}`;
  console.error(`${what}: ${count} error(s). Fix them:\n`);
  console.error(errors.join('\n'));
  process.exit(1);
}
if (count < baseline) {
  console.error(
    `TypeScript errors fell from ${baseline} to ${count} — nice. ` +
      'Lock it in with `npm run typecheck -- --update` and commit .tsc-baseline.',
  );
  process.exit(1);
}
console.log(`TypeScript errors: ${count} (baseline ${baseline}).`);
