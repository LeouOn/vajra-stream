#!/usr/bin/env node
/**
 * TypeScript error ratchet.
 *
 * `vite build` does not type-check, so type errors used to ship silently
 * (e.g. an un-imported <UniverseTab> that crashed the Outlook tab at runtime).
 * The codebase still carries a backlog of pre-existing errors, so this gate
 * cannot demand zero yet. Instead it fails when the count rises above the
 * committed baseline, and asks for the baseline to be lowered when it falls.
 *
 *   npm run typecheck                  # check against baseline
 *   npm run typecheck -- --update      # rewrite baseline to the current count
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

if (process.argv.includes('--update')) {
  writeFileSync(baselinePath, `${count}\n`);
  console.log(`tsc baseline set to ${count}.`);
  process.exit(0);
}

const baseline = Number.parseInt(readFileSync(baselinePath, 'utf8').trim(), 10);
if (Number.isNaN(baseline)) {
  console.error(`Could not parse ${baselinePath}.`);
  process.exit(2);
}

if (count > baseline) {
  console.error(`TypeScript errors rose from ${baseline} to ${count}. Fix the new errors:\n`);
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
