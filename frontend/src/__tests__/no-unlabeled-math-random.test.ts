/**
 * Guard: Math.random in frontend/src needs a reviewed allow-list entry.
 *
 * The honest-instrument rule (docs/DEVELOPMENT_ROADMAP.md, Phase 2): a random
 * value must never pose as a measurement. Draws are legitimate (the stick-pad
 * analog) when labeled "drawn"; decoration, ids and retry jitter are fine.
 * Each use must still be a conscious decision, so every file that calls
 * Math.random must be listed here with its kind and a one-line reason.
 *
 * Python twin: tests/unit/test_no_unlabeled_randomness.py.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const SRC_DIR = path.resolve(__dirname, '..');

type Kind = 'draw' | 'decorative' | 'content' | 'id' | 'timing';

// path relative to frontend/src (posix) -> [kind, reason]
const ALLOWED: Record<string, [Kind, string]> = {
  'components/UI/BroadcastPanel.tsx': [
    'draw',
    'stick-plate node position is a draw, labeled "drawn" in the plate UI; plus a decorative rub-sound throttle',
  ],
  'routes/Buddhas/DedicationText.tsx': ['content', 'picks which dedication verse to show'],
  'components/2D/RothkoGenerator.tsx': ['decorative', 'band layout and blur variation'],
  'components/2D/ScalarWaveVisualizer.tsx': ['decorative', 'particle burst positions and colors'],
  'components/3D/Astrocartography.tsx': ['decorative', 'ambient particle positions'],
  'components/3D/MedicineBuddhaHealing.tsx': ['decorative', 'floating particle positions and phases'],
  'components/3D/RadionicsGlobe.tsx': ['decorative', 'globe ray heights and speeds'],
  'components/3D/SacredGeometry.tsx': ['decorative', 'particle colors, sizes and spin rates'],
  'components/3D/TaraGreenLotus.tsx': ['decorative', 'floating particle positions and phases'],
  'utils/audioFeedback.ts': ['decorative', 'pitch variation of the UI tick sound'],
  'hooks/useWebSocketStable.ts': ['timing', 'reconnect backoff jitter; never displayed'],
  'components/UI/OutlookDashboard.tsx': ['id', 'local ritual id suffix'],
  'components/UI/outlook/HistoryTab.tsx': ['id', 'local ritual id suffix'],
  'routes/Buddhas/SessionHistory.tsx': ['id', 'local session id suffix'],
  'stores/broadcastStore.ts': ['id', 'fallback broadcast event id suffix'],
  'stores/uiStore.ts': ['id', 'toast id'],
};

const SOURCE_EXT = /\.(ts|tsx|js|jsx)$/;

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '__tests__' || entry.name === 'node_modules') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (SOURCE_EXT.test(entry.name) && !/\.(test|spec)\.[jt]sx?$/.test(entry.name)) out.push(full);
  }
  return out;
}

function filesUsingMathRandom(): string[] {
  return walk(SRC_DIR)
    .filter((file) => fs.readFileSync(file, 'utf8').includes('Math.random'))
    .map((file) => path.relative(SRC_DIR, file).split(path.sep).join('/'))
    .sort();
}

describe('Math.random allow-list (honest instrument)', () => {
  const found = filesUsingMathRandom();

  it('every file using Math.random has a reviewed allow-list entry', () => {
    const unreviewed = found.filter((rel) => !(rel in ALLOWED));
    expect(
      unreviewed,
      'If the random value is displayed, label it "drawn" (ProvenanceTag); then add the file to ALLOWED with its kind and reason.',
    ).toEqual([]);
  });

  it('has no stale entries', () => {
    const stale = Object.keys(ALLOWED).filter((rel) => !found.includes(rel));
    expect(stale).toEqual([]);
  });

  it('every entry explains itself', () => {
    for (const [rel, [kind, reason]] of Object.entries(ALLOWED)) {
      expect(['draw', 'decorative', 'content', 'id', 'timing'], rel).toContain(kind);
      expect(reason.length, rel).toBeGreaterThan(5);
    }
  });
});
