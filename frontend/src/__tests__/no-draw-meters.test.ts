/**
 * Guard: a draw is never rendered as a meter (docs/DEVELOPMENT_ROADMAP.md,
 * Phase 2, "the honest instrument").
 *
 * Bars are allowed only for records and computed values. The sanctioned bar is
 * `ReadingMeter` (components/UI/Reading.tsx), whose `provenance` prop only
 * accepts `record | computed` and which renders nothing for anything else. Any
 * other bar primitive in frontend/src (antd `<Progress>`, `<meter>`, a
 * progressbar/meter role, or a `width: \`${x}%\`` fill) must be listed below
 * with the provenance of what it shows. `MeterKind` has no `draw` member, so a
 * draw cannot be listed at all.
 *
 * Two checks are structural and need no judgement:
 *   1. every file with a raw bar is listed (and no listing is stale);
 *   2. a file that labels anything as a draw (`kind="draw"` /
 *      `provenance="draw"`) contains no raw bar.
 *
 * Twin of no-unlabeled-math-random.test.ts (which reviews where randomness
 * comes from); this one reviews how values are shown.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const SRC_DIR = path.resolve(__dirname, '..');

/** What a raw bar may show. There is deliberately no 'draw'. */
type MeterKind = 'record' | 'computed' | 'decorative' | 'primitive';

// path relative to frontend/src (posix) -> [kind, reason]
const METER_ALLOWED: Record<string, [MeterKind, string]> = {
  'components/UI/Reading.tsx': ['primitive', 'ReadingMeter: refuses anything but record/computed'],
  'components/2D/RothkoGenerator.tsx': ['decorative', 'percentage sizes of the color-field blocks; layout, not a value'],
  'components/Settings/VideoSettingsPanel.tsx': ['record', 'daily video spend against the configured cap'],
  'components/UI/AstrologyExtractionPanel.tsx': ['record', 'completed / total tuples of an extraction run'],
  'components/UI/DharaniReciter.tsx': ['record', 'recitations counted in the current mala'],
  'components/UI/PracticeDetail.tsx': ['record', 'beads counted in the current mala'],
  'routes/Buddhas/index.tsx': ['record', 'Buddha names recited out of 88'],
  'components/UI/SessionTimeline.tsx': ['record', 'session durations relative to the longest'],
  'components/UI/SynastryViewer.tsx': ['computed', 'aspect-count compatibility score and aspect mix between two charts'],
  'components/UI/TransitComparison.tsx': ['computed', 'aspect exactness (orb) between transit and natal planets'],
  'components/UI/TimeCycles.tsx': ['computed', 'progress through the requested date range'],
};

const RAW_METER_PATTERNS: Array<[string, RegExp]> = [
  ['antd <Progress>', /<Progress\b/],
  ['<meter>', /<meter\b/],
  ['progressbar/meter role', /role=["'](?:progressbar|meter)["']/],
  ['recharts <RadialBar>', /<RadialBar\b/],
  ['percentage width/height fill', /(?:width|height):\s*`\$\{[^`]*\}%`/],
  ['concatenated percentage width/height', /(?:width|height):\s*[^,}\n]*\+\s*['"]%['"]/],
];

const DRAW_LABEL = /\b(?:kind|provenance)=["']draw["']/;

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

interface SourceFile {
  rel: string;
  text: string;
}

const SOURCES: SourceFile[] = walk(SRC_DIR).map((file) => ({
  rel: path.relative(SRC_DIR, file).split(path.sep).join('/'),
  text: fs.readFileSync(file, 'utf8'),
}));

function rawMeters(text: string): string[] {
  return RAW_METER_PATTERNS.filter(([, re]) => re.test(text)).map(([name]) => name);
}

describe('no draw rendered as a meter (honest instrument)', () => {
  const withMeters = SOURCES.filter((s) => rawMeters(s.text).length > 0);

  it('every file with a raw bar is reviewed and shows a record or computed value', () => {
    const unreviewed = withMeters
      .filter((s) => !(s.rel in METER_ALLOWED))
      .map((s) => `${s.rel}: ${rawMeters(s.text).join(', ')}`);
    expect(
      unreviewed,
      'Show record/computed bars with ReadingMeter (components/UI/Reading.tsx). A draw gets a Reading ("drawn"), never a bar. ' +
        'If a raw bar is unavoidable, add the file to METER_ALLOWED with the provenance of what it shows.',
    ).toEqual([]);
  });

  it('has no stale entries', () => {
    const withMeterPaths = new Set(withMeters.map((s) => s.rel));
    const stale = Object.keys(METER_ALLOWED).filter((rel) => !withMeterPaths.has(rel));
    expect(stale).toEqual([]);
  });

  it('a file that shows a draw has no raw bar', () => {
    const offenders = withMeters
      .filter((s) => s.rel !== 'components/UI/Reading.tsx' && DRAW_LABEL.test(s.text))
      .map((s) => `${s.rel}: ${rawMeters(s.text).join(', ')}`);
    expect(offenders, 'Render the drawn value with <Reading provenance="draw"> and drop the bar.').toEqual([]);
  });

  it('every entry explains itself', () => {
    for (const [rel, [kind, reason]] of Object.entries(METER_ALLOWED)) {
      expect(['record', 'computed', 'decorative', 'primitive'], rel).toContain(kind);
      expect(reason.length, rel).toBeGreaterThan(10);
    }
  });

  it('the detector sees the bar shapes it claims to', () => {
    expect(rawMeters('<Progress percent={5} />')).toEqual(['antd <Progress>']);
    expect(rawMeters('style={{ width: `${pct}%` }}')).toEqual(['percentage width/height fill']);
    expect(rawMeters("style={{ width: pct + '%' }}")).toEqual(['concatenated percentage width/height']);
    expect(rawMeters('<div role="progressbar" />')).toEqual(['progressbar/meter role']);
    expect(rawMeters('<ReadingMeter percent={5} provenance="record" />')).toEqual([]);
    expect(DRAW_LABEL.test('<Reading value={1} provenance="draw" />')).toBe(true);
    expect(DRAW_LABEL.test('<ProvenanceTag kind="draw" />')).toBe(true);
  });
});
