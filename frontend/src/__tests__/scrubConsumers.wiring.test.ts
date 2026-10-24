/**
 * W3-I wiring guard (source level). `WorldEmanation` and `RadionicsGlobe` draw inside an R3F canvas that the
 * component tests replace with a stub, so their frozen behaviour cannot be observed headless. The behaviour is
 * pinned where it can be (skySeriesStore.test.ts: `shownNowMs` + `drawnBodies`; MiniEarth/WorldStrip.frozen
 * tests); this file pins the WIRING: every consumer of `useEarthState()` ages its state with `shownNowMs`, and no
 * unwired consumer can appear unnoticed (a fifth file using the hook fails here and must be read and wired).
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = path.resolve(__dirname, '..');

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return name === '__tests__' ? [] : sourceFiles(full);
    return /\.(ts|tsx)$/.test(name) ? [full] : [];
  });
}
const rel = (file: string) => path.relative(SRC, file).split(path.sep).join('/');

const WIRED = [
  'components/2D/MiniEarth.tsx',
  'components/2D/WorldStrip.tsx',
  'components/3D/WorldEmanation.tsx',
  'components/3D/RadionicsGlobe.tsx',
];

describe('useEarthState consumers age their state with shownNowMs', () => {
  it('the set of components that call useEarthState() is exactly the four wired ones', () => {
    const users = sourceFiles(SRC)
      .filter((file) => /\buseEarthState\(\)/.test(readFileSync(file, 'utf8')))
      .map(rel)
      .filter((name) => name !== 'stores/earthStateStore.ts')
      .sort();
    expect(users).toEqual([...WIRED].sort());
  });

  it.each(WIRED)('%s imports and uses shownNowMs', (name) => {
    const source = readFileSync(path.join(SRC, name), 'utf8');
    expect(source).toMatch(/import\s*\{[^}]*\bshownNowMs\b[^}]*\}\s*from\s*'..\/..\/lib\/earth'/s);
    expect(source).toMatch(/shownNowMs\(/);
  });

  it.each(['components/3D/WorldEmanation.tsx', 'components/3D/RadionicsGlobe.tsx'])(
    '%s passes the shown clock, not the wall clock, to drawnBodies',
    (name) => {
      const source = readFileSync(path.join(SRC, name), 'utf8');
      const calls = [...source.matchAll(/drawnBodies\(([^)]*)\)/g)].map((match) => match[1]);
      expect(calls.length).toBeGreaterThan(0);
      for (const args of calls) expect(args).toContain('shownNowMs(');
    },
  );

  it('MiniEarth and WorldStrip do not age a state with a bare Date.now()', () => {
    for (const name of ['components/2D/MiniEarth.tsx', 'components/2D/WorldStrip.tsx']) {
      const source = readFileSync(path.join(SRC, name), 'utf8');
      expect(source, name).not.toMatch(/\(Date\.now\(\)\s*-\s*atMs\)/);
    }
  });
});
