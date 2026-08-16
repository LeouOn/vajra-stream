# Sittings Constellation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the Workings ledger as a night sky — each sealed sitting a star placed by seal time and its own moon-phase stamp, sibling retries linked as constellations, collapsed duplicates as ghost stars tethered to their keeper.

**Architecture:** One additive backend change (`list_workings` summary fields) → pure mapping helpers (`star.ts`) → a 2D-canvas hero component mounted on the Workings route in the same task (keeps `no-orphan-components` green). Spec: `docs/superpowers/specs/2026-08-16-sittings-constellation-and-world-emanation-design.md` (Feature A).

**Tech Stack:** FastAPI/Python (backend summary), React 18 + TypeScript + plain Canvas 2D (no new deps), Vitest + happy-dom, pytest.

## Global Constraints

- Backend change is **additive-only** to the `list_workings()` summary dict — no schema, endpoint, or router changes.
- Frontend URLs via `apiUrl()` from `utils/api.ts` only (ADR 004); no new `API_BASE`.
- No `as any` / `@ts-ignore` / `@ts-expect-error`; widen types instead. (Test doubles may use the double-assertion `as unknown as X` pattern.)
- No `test_*.py` at `tests/` root; vitest tests live under `src/__tests__/` (component tests under `src/__tests__/components/` for the happy-dom glob).
- No new ruff suppressions; `pyproject.toml` per-file-ignores stays empty.
- New source files stay under 250 LOC.
- Windows PowerShell 5.1: no `&&`; chain with `cmd1; if ($?) { cmd2 }`.
- Stay on `origin/main`; commit per task with the repo's attribution trailers.
- Honesty rule: the sky renders folio records only — no invented astronomy, no counters/scores.

---

### Task 1: Backend — constellation fields on the workings summary

**Files:**
- Modify: `core/working.py` (`list_workings` summary dict, ~lines 81-96)
- Test: `tests/core/test_working.py`

**Interfaces:**
- Produces (JSON summary keys, consumed by Task 3's `StarSummaryInput`): `planetary_hour: string | null`, `moon_phase: string | null`, `saka_dawa_multiplier: number` (default 1), `duplicate_of: string | null`.

- [ ] **Step 1: Write the failing test**

Append to `tests/core/test_working.py`:

```python
@pytest.mark.unit
def test_list_workings_summary_carries_constellation_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    working._persist(
        {
            "working_id": "wrk_sky00000001",
            "sealed_at": "2026-08-16T00:00:00+00:00",
            "intention": "peace for the watershed",
            "target": "all beings",
            "rate_values": [68, 30, 71, 50, 68],
            "hour_stamp": {"planetary_hour": "Venus", "moon_phase": "Full Moon"},
            "saka_dawa": {"multiplier": 100000},
            "hidden": True,
            "duplicate_of": "wrk_keep000001",
        },
        index=False,
    )

    listed = working.list_workings(include_hidden=True)
    row = next(w for w in listed if w["working_id"] == "wrk_sky00000001")
    assert row["planetary_hour"] == "Venus"
    assert row["moon_phase"] == "Full Moon"
    assert row["saka_dawa_multiplier"] == 100000
    assert row["duplicate_of"] == "wrk_keep000001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_working.py::test_list_workings_summary_carries_constellation_fields -q --no-header`
Expected: FAIL — `KeyError: 'planetary_hour'` (or `None != 'Venus'`).

- [ ] **Step 3: Implement — extend the summary dict**

In `core/working.py:list_workings`, extend the dict literal in `out.append({...})` right after the `"saka_dawa_duchen"` entry:

```python
                "saka_dawa_duchen": saka.get("saka_dawa_duchen"),
                "planetary_hour": (data.get("hour_stamp") or {}).get("planetary_hour"),
                "moon_phase": (data.get("hour_stamp") or {}).get("moon_phase"),
                "saka_dawa_multiplier": saka.get("multiplier", 1),
                "duplicate_of": data.get("duplicate_of"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_working.py -q --no-header`
Expected: all PASS (13 tests).

- [ ] **Step 5: Lint + commit**

```powershell
python -m ruff check core/working.py; if ($?) { python -m ruff format --check core/working.py }
$env:GIT_MASTER='1'; git add core/working.py tests/core/test_working.py; if ($?) { git commit -m "feat(workings): summary carries constellation fields (hour, moon, merit, duplicate_of)" -m "Ultraworked with [Sisyphus](https://github.com/code-yeongyu/oh-my-openagent)" -m "Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>" }
```

---

### Task 2: Pure mapping helpers — `star.ts`

**Files:**
- Create: `frontend/src/components/Workings/star.ts`
- Test: `frontend/src/__tests__/components/star.test.ts`

**Interfaces:**
- Consumes: Task 1's JSON summary keys (mirrored by `StarSummaryInput`).
- Produces (consumed by Task 3):

```ts
export interface StarSummaryInput {
  working_id: string;
  intention?: string;
  target?: string;
  sealed_at?: string;
  rate_values?: number[];
  source?: string;
  hidden?: boolean;
  planetary_hour?: string | null;
  moon_phase?: string | null;
  saka_dawa_multiplier?: number | null;
  duplicate_of?: string | null;
}
export interface Star {
  working_id: string; intention: string; dials: string; sealedAt: string;
  multiplier: number; t: number; band: number; size: number; hue: string;
  alpha: number; ghost: boolean; groupKey: string; duplicateOf: string | null;
}
export const MOON_PHASES: readonly string[]
export const UNKNOWN_MOON_BAND: 3
export function moonPhaseToBand(phase?: string | null): number
export function sourceHue(source?: string | null): string
export function starSize(multiplier?: number | null): number
export function relativeSealTime(iso?: string): string
export function summaryToStar(summary: StarSummaryInput, index: number, all: StarSummaryInput[]): Star
export function constellationGroups(stars: Star[]): Star[][]
```

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/components/star.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import {
  constellationGroups,
  moonPhaseToBand,
  relativeSealTime,
  sourceHue,
  starSize,
  summaryToStar,
} from '../../components/Workings/star';

describe('moonPhaseToBand', () => {
  it('maps canonical phases case-insensitively', () => {
    expect(moonPhaseToBand('Full Moon')).toBe(4);
    expect(moonPhaseToBand('waning crescent')).toBe(7);
    expect(moonPhaseToBand('New')).toBe(0);
    expect(moonPhaseToBand('Last Quarter Moon')).toBe(6);
  });
  it('falls back to the neutral mid band', () => {
    expect(moonPhaseToBand(undefined)).toBe(3);
    expect(moonPhaseToBand('')).toBe(3);
    expect(moonPhaseToBand('banana')).toBe(3);
  });
});

describe('sourceHue', () => {
  it('assigns the fixed palette', () => {
    expect(sourceHue('command-center')).toBe('#22d3ee');
    expect(sourceHue('Ritual-Composer')).toBe('#f472b6');
  });
  it('falls back to starlight white', () => {
    expect(sourceHue(undefined)).toBe('#e2e8f0');
  });
});

describe('starSize', () => {
  it('keeps ordinary nights small and Duchen nights brightest', () => {
    expect(starSize(1)).toBeLessThanOrEqual(2.2);
    expect(starSize(100000)).toBeGreaterThanOrEqual(7.8);
    expect(starSize(1000000)).toBeLessThanOrEqual(8); // capped
  });
});

describe('relativeSealTime', () => {
  it('describes recent seals and rejects garbage', () => {
    expect(relativeSealTime(new Date().toISOString())).toBe('just now');
    expect(relativeSealTime('nope')).toBe('—');
    expect(relativeSealTime('')).toBe('—');
  });
});

describe('summaryToStar', () => {
  const all = [
    { working_id: 'a', intention: 'Peace', target: 'All beings', sealed_at: '2026-08-14T00:00:00Z', rate_values: [1, 2, 3, 4, 5], source: 'command-center' },
    { working_id: 'b', intention: 'peace', target: 'all beings', sealed_at: '2026-08-16T00:00:00Z', rate_values: [1, 2, 3, 4, 5], source: 'command-center', hidden: true, duplicate_of: 'a', moon_phase: 'Full Moon', saka_dawa_multiplier: 100000 },
  ];
  it('normalizes time across the set', () => {
    const stars = all.map((s, i) => summaryToStar(s, i, all));
    expect(stars[0].t).toBe(0);
    expect(stars[1].t).toBe(1);
  });
  it('ghosts hidden duplicates and shares the sibling group key', () => {
    const stars = all.map((s, i) => summaryToStar(s, i, all));
    expect(stars[1].ghost).toBe(true);
    expect(stars[1].alpha).toBe(0.25);
    expect(stars[1].duplicateOf).toBe('a');
    expect(stars[1].groupKey).toBe(stars[0].groupKey);
  });
  it('centers a lone sitting', () => {
    const star = summaryToStar(all[0], 0, [all[0]]);
    expect(star.t).toBe(0.5);
  });
});

describe('constellationGroups', () => {
  it('groups siblings and orders them chronologically', () => {
    const base = { intention: 'peace', target: 'all beings', rate_values: [1, 2, 3, 4, 5] };
    const stars = [
      { working_id: 'late', ...base, t: 0.9 },
      { working_id: 'early', ...base, t: 0.1 },
      { working_id: 'other', intention: 'healing', target: 'all beings', rate_values: [9, 9, 9, 9, 9], t: 0.5 },
    ] as const;
    // summaryToStar builds groupKey; here feed Stars directly via cast-free minimal shape:
    const built = [
      { working_id: 'late', intention: 'peace', dials: '', sealedAt: '', multiplier: 1, t: 0.9, band: 3, size: 2, hue: '#fff', alpha: 1, ghost: false, groupKey: 'peace|all beings|1,2,3,4,5', duplicateOf: null },
      { working_id: 'early', intention: 'peace', dials: '', sealedAt: '', multiplier: 1, t: 0.1, band: 3, size: 2, hue: '#fff', alpha: 1, ghost: false, groupKey: 'peace|all beings|1,2,3,4,5', duplicateOf: null },
      { working_id: 'other', intention: 'healing', dials: '', sealedAt: '', multiplier: 1, t: 0.5, band: 3, size: 2, hue: '#fff', alpha: 1, ghost: false, groupKey: 'healing|all beings|9,9,9,9,9', duplicateOf: null },
    ];
    const groups = constellationGroups(built);
    expect(groups).toHaveLength(2);
    expect(groups[0].map((s) => s.working_id)).toEqual(['early', 'late']);
    void stars;
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run (in `frontend/`): `npx vitest run src/__tests__/components/star.test.ts`
Expected: FAIL — cannot resolve `../../../components/Workings/star`.

- [ ] **Step 3: Implement `star.ts`**

Create `frontend/src/components/Workings/star.ts`:

```ts
/**
 * star.ts — pure mapping from workings summaries to night-sky stars.
 *
 * Every value is derived from the folio's own stamps (sealed_at, hour_stamp,
 * saka_dawa, duplicate_of). No invented astronomy: the moon band is the
 * folio's categorical stamp, not a computed ephemeris.
 */

export interface StarSummaryInput {
  working_id: string;
  intention?: string;
  target?: string;
  sealed_at?: string;
  rate_values?: number[];
  source?: string;
  hidden?: boolean;
  planetary_hour?: string | null;
  moon_phase?: string | null;
  saka_dawa_multiplier?: number | null;
  duplicate_of?: string | null;
}

export interface Star {
  working_id: string;
  intention: string;
  dials: string;
  sealedAt: string;
  multiplier: number;
  t: number;
  band: number;
  size: number;
  hue: string;
  alpha: number;
  ghost: boolean;
  groupKey: string;
  duplicateOf: string | null;
}

export const MOON_PHASES = [
  'new',
  'waxing crescent',
  'first quarter',
  'waxing gibbous',
  'full',
  'waning gibbous',
  'last quarter',
  'waning crescent',
] as const;

export const UNKNOWN_MOON_BAND = 3;

export function moonPhaseToBand(phase?: string | null): number {
  if (!phase) return UNKNOWN_MOON_BAND;
  const low = phase.toLowerCase();
  const idx = MOON_PHASES.findIndex((p) => low.includes(p));
  return idx >= 0 ? idx : UNKNOWN_MOON_BAND;
}

const SOURCE_HUES: Record<string, string> = {
  'command-center': '#22d3ee',
  'ritual-composer': '#f472b6',
  operator: '#a78bfa',
  composer: '#f59e0b',
};

export function sourceHue(source?: string | null): string {
  return SOURCE_HUES[(source || '').toLowerCase()] || '#e2e8f0';
}

export function starSize(multiplier?: number | null): number {
  const m = Math.max(1, Number(multiplier) || 1);
  return 2 + Math.min(6, Math.log10(m) * 1.2);
}

export function relativeSealTime(iso?: string): string {
  if (!iso) return '—';
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return '—';
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export function summaryToStar(summary: StarSummaryInput, _index: number, all: StarSummaryInput[]): Star {
  const times = all.map((s) => Date.parse(s.sealed_at || '')).filter((n) => !Number.isNaN(n));
  const own = Date.parse(summary.sealed_at || '');
  const min = times.length ? Math.min(...times) : 0;
  const max = times.length ? Math.max(...times) : 1;
  const span = Math.max(1, max - min);
  const t = times.length <= 1 || Number.isNaN(own) ? 0.5 : Math.min(1, Math.max(0, (own - min) / span));

  const multiplier = Math.max(1, Number(summary.saka_dawa_multiplier) || 1);
  const values = (summary.rate_values || []).slice(0, 5);
  const intention = (summary.intention || '').trim().toLowerCase();
  const target = (summary.target || 'all beings').trim().toLowerCase();

  return {
    working_id: summary.working_id,
    intention: summary.intention || '—',
    dials: values.length ? values.join(' · ') : '—',
    sealedAt: summary.sealed_at || '',
    multiplier,
    t,
    band: moonPhaseToBand(summary.moon_phase),
    size: starSize(multiplier),
    hue: sourceHue(summary.source),
    alpha: summary.hidden ? 0.25 : 1,
    ghost: summary.hidden === true,
    groupKey: `${intention}|${target}|${values.join(',')}`,
    duplicateOf: summary.duplicate_of || null,
  };
}

export function constellationGroups(stars: Star[]): Star[][] {
  const groups = new Map<string, Star[]>();
  for (const star of stars) {
    const arr = groups.get(star.groupKey);
    if (arr) arr.push(star);
    else groups.set(star.groupKey, [star]);
  }
  return [...groups.values()].map((members) => [...members].sort((a, b) => a.t - b.t));
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run (in `frontend/`): `npx vitest run src/__tests__/components/star.test.ts`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```powershell
$env:GIT_MASTER='1'; git add frontend/src/components/Workings/star.ts frontend/src/__tests__/components/star.test.ts; if ($?) { git commit -m "feat(workings): pure star mapping helpers for the sittings sky" -m "Ultraworked with [Sisyphus](https://github.com/code-yeongyu/oh-my-openagent)" -m "Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>" }
```

---

### Task 3: Component + Workings mount (same task — keeps `no-orphan-components` green)

**Files:**
- Create: `frontend/src/components/Workings/SittingsConstellation.tsx`
- Modify: `frontend/src/routes/Workings/index.tsx`
- Test: `frontend/src/__tests__/components/SittingsConstellation.test.tsx`, `frontend/src/__tests__/components/Workings.sky.test.tsx`

**Interfaces:**
- Consumes: `star.ts` (Task 2) and Task 1's summary keys via `StarSummaryInput`.
- Produces: `export default function SittingsConstellation({ workings, onSelect }: { workings: StarSummaryInput[]; onSelect: (workingId: string) => void })`.

- [ ] **Step 1: Write the failing component test**

Create `frontend/src/__tests__/components/SittingsConstellation.test.tsx`:

```tsx
/**
 * SittingsConstellation — render posture under a stubbed 2D context.
 * Mapping math is covered by star.test.ts; here we lock the DOM surface.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

const noop = () => {};
const stubCtx = () =>
  ({
    clearRect: noop, beginPath: noop, arc: noop, fill: noop, stroke: noop,
    moveTo: noop, lineTo: noop, fillText: noop, setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    save: noop, restore: noop, setTransform: noop,
  }) as unknown as CanvasRenderingContext2D;

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(stubCtx());
  let frames = 0;
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    frames += 1;
    if (frames <= 2) setTimeout(() => cb(performance.now()), 0);
    return frames;
  });
  vi.stubGlobal('cancelAnimationFrame', noop);
});
afterEach(() => {
  vi.unstubAllMocks();
  vi.restoreAllMocks();
});

const FIXTURE = [
  {
    working_id: 'wrk_a', intention: 'peace for the watershed', target: 'all beings',
    sealed_at: '2026-08-14T00:00:00Z', rate_values: [68, 30, 71, 50, 68],
    source: 'command-center', moon_phase: 'Waxing Crescent', saka_dawa_multiplier: 1,
  },
  {
    working_id: 'wrk_b', intention: 'peace for the watershed', target: 'all beings',
    sealed_at: '2026-08-16T00:00:00Z', rate_values: [68, 30, 71, 50, 68],
    source: 'command-center', hidden: true, duplicate_of: 'wrk_a',
    moon_phase: 'Full Moon', saka_dawa_multiplier: 100000,
  },
];

describe('SittingsConstellation', () => {
  it('renders a canvas for sittings and reports selection targets', async () => {
    const { default: SittingsConstellation } = await import(
      '../../components/Workings/SittingsConstellation'
    );
    const onSelect = vi.fn();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<SittingsConstellation workings={FIXTURE} onSelect={onSelect} />);
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
    expect(container.querySelector('[data-testid="sittings-constellation"]')).not.toBeNull();
    expect(container.textContent || '').not.toContain('No sittings yet');
  }, 30000);

  it('shows the empty-sky caption when there are no workings', async () => {
    const { default: SittingsConstellation } = await import(
      '../../components/Workings/SittingsConstellation'
    );
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(<SittingsConstellation workings={[]} onSelect={() => {}} />);
    });
    expect(container.querySelector('[data-testid="sky-empty"]')).not.toBeNull();
  }, 30000);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (in `frontend/`): `npx vitest run src/__tests__/components/SittingsConstellation.test.tsx`
Expected: FAIL — cannot resolve the component module.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/Workings/SittingsConstellation.tsx`:

```tsx
/**
 * SittingsConstellation — the Workings ledger as a night sky.
 *
 * Each sealed sitting is a star placed by seal time (x) and the folio's
 * own moon-phase stamp (band). Siblings of one sitting share a
 * constellation line; collapsed duplicates stay visible as faint ghost
 * stars tethered to their keeper. A representation of the folio
 * records — not a second oracle.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  constellationGroups,
  relativeSealTime,
  summaryToStar,
  type Star,
  type StarSummaryInput,
} from './star';

const MOON_GLYPHS = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'] as const;
const RIBBON_W = 26;
const PAD = 34;

interface Props {
  workings: StarSummaryInput[];
  onSelect: (workingId: string) => void;
}

export default function SittingsConstellation({ workings, onSelect }: Props): React.ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const positionsRef = useRef<Map<string, { x: number; y: number; r: number }>>(new Map());
  const [hover, setHover] = useState<{ star: Star; x: number; y: number } | null>(null);

  const stars = useMemo(
    () => workings.map((s, i) => summaryToStar(s, i, workings)),
    [workings],
  );
  const groups = useMemo(() => constellationGroups(stars), [stars]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let raf = 0;

    const draw = (now: number) => {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth || 600;
      const h = canvas.clientHeight || 280;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const innerLeft = RIBBON_W + 12;
      const xOf = (t: number) => innerLeft + t * Math.max(0, w - innerLeft - PAD);
      const yOf = (band: number) => PAD + (band / 7) * (h - 2 * PAD);

      // Moon ribbon — the y-axis legend, from the folio's categorical stamps.
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(245, 230, 200, 0.45)';
      MOON_GLYPHS.forEach((glyph, b) => ctx.fillText(glyph, 6, yOf(b)));

      const pos = new Map<string, { x: number; y: number; r: number }>();
      stars.forEach((s) => pos.set(s.working_id, { x: xOf(s.t), y: yOf(s.band), r: s.size }));
      positionsRef.current = pos;

      // Constellation lines between chronological siblings.
      ctx.strokeStyle = 'rgba(245, 230, 200, 0.18)';
      ctx.lineWidth = 1;
      for (const members of groups) {
        ctx.beginPath();
        members.forEach((m, i) => {
          const p = pos.get(m.working_id);
          if (!p) return;
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        });
        ctx.stroke();
      }

      // Ghost tethers: hidden duplicate → its keeper.
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = 'rgba(245, 230, 200, 0.12)';
      for (const s of stars) {
        if (!s.duplicateOf) continue;
        const from = pos.get(s.working_id);
        const to = pos.get(s.duplicateOf);
        if (!from || !to) continue;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Stars — seeded twinkle, ghosts dim.
      stars.forEach((s, i) => {
        const p = pos.get(s.working_id);
        if (!p) return;
        const twinkle = 0.75 + 0.25 * Math.sin((now / 700) * (1 + (i % 3) * 0.3) + i * 1.7);
        if (!s.ghost) {
          ctx.globalAlpha = s.alpha * twinkle * 0.15;
          ctx.fillStyle = s.hue;
          ctx.beginPath();
          ctx.arc(p.x, p.y, s.size * 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = s.alpha * twinkle;
        ctx.fillStyle = s.hue;
        ctx.beginPath();
        ctx.arc(p.x, p.y, s.size, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      if (hover) {
        const p = pos.get(hover.star.working_id);
        if (p) {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(p.x, p.y, hover.star.size + 3, 0, Math.PI * 2);
          ctx.stroke();
        }
      }

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [stars, groups, hover]);

  const pick = (clientX: number, clientY: number): { star: Star; x: number; y: number } | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const mx = clientX - rect.left;
    const my = clientY - rect.top;
    let best: { star: Star; d: number; x: number; y: number } | null = null;
    for (const s of stars) {
      const p = positionsRef.current.get(s.working_id);
      if (!p) continue;
      const d = Math.hypot(mx - p.x, my - p.y);
      if (d <= s.size + 5 && (!best || d < best.d)) best = { star: s, d, x: p.x, y: p.y };
    }
    return best;
  };

  if (stars.length === 0) {
    return (
      <div
        data-testid="sky-empty"
        className="rounded-lg border border-amber-500/20 bg-amber-950/20 px-4 py-6 text-center text-sm text-amber-200/70"
      >
        No sittings yet — seal one from Command Center and it becomes a star here.
      </div>
    );
  }

  return (
    <div className="relative rounded-lg border border-amber-500/20 bg-amber-950/20">
      <canvas
        ref={canvasRef}
        data-testid="sittings-constellation"
        className="block h-[280px] w-full"
        style={{ cursor: hover ? 'pointer' : 'default' }}
        onMouseMove={(e) => setHover(pick(e.clientX, e.clientY))}
        onMouseLeave={() => setHover(null)}
        onClick={() => hover && onSelect(hover.star.working_id)}
      />
      {hover && (
        <div
          className="pointer-events-none absolute z-10 max-w-[260px] rounded-md border border-amber-500/30 bg-black/85 px-2 py-1.5 text-[10px] font-mono leading-relaxed text-amber-100"
          style={{ left: Math.min(hover.x + 12, 9999), top: hover.y - 10 }}
        >
          <div className="truncate text-amber-200">{hover.star.intention}</div>
          <div className="text-amber-100/60">{hover.star.dials}</div>
          <div className="text-amber-100/60">
            {relativeSealTime(hover.star.sealedAt)}
            {hover.star.multiplier > 1 ? ` · merit ×${hover.star.multiplier.toLocaleString('en-US')}` : ''}
            {hover.star.ghost ? ' · duplicate (hidden)' : ''}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the component test to verify it passes**

Run (in `frontend/`): `npx vitest run src/__tests__/components/SittingsConstellation.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Write the failing page test**

Create `frontend/src/__tests__/components/Workings.sky.test.tsx`:

```tsx
/**
 * Workings page mounts the constellation hero and feeds it the
 * hidden-inclusive ledger (the sky always renders the full truth,
 * independent of the list's "Show hidden" toggle).
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider } from 'antd';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

const noop = () => {};
const stubCtx = () =>
  ({
    clearRect: noop, beginPath: noop, arc: noop, fill: noop, stroke: noop,
    moveTo: noop, lineTo: noop, fillText: noop, setLineDash: noop,
    measureText: () => ({ width: 10 }) as TextMetrics,
    save: noop, restore: noop, setTransform: noop,
  }) as unknown as CanvasRenderingContext2D;

const SKY = { workings: [{ working_id: 'wrk_a', intention: 'peace', target: 'all beings', sealed_at: '2026-08-16T00:00:00Z', rate_values: [1, 2, 3, 4, 5], source: 'command-center' }] };

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(stubCtx());
  let frames = 0;
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    frames += 1;
    if (frames <= 2) setTimeout(() => cb(performance.now()), 0);
    return frames;
  });
  vi.stubGlobal('cancelAnimationFrame', noop);
  globalThis.fetch = vi.fn().mockImplementation(() =>
    Promise.resolve({ ok: true, status: 200, json: async () => SKY } as Response),
  );
});
afterEach(() => {
  vi.unstubAllMocks();
  vi.restoreAllMocks();
});

describe('Workings page — sittings sky', () => {
  it('renders the constellation hero from the hidden-inclusive fetch', async () => {
    const { default: WorkingsPage } = await import('../../routes/Workings');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ConfigProvider>
          <MemoryRouter initialEntries={['/workings']}>
            <Routes>
              <Route path="/workings" element={<WorkingsPage />} />
            </Routes>
          </MemoryRouter>
        </ConfigProvider>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(container.querySelector('[data-testid="sittings-constellation"]')).not.toBeNull();
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.map((c) => String(c[0]));
    expect(calls.some((url) => url.includes('include_hidden=true'))).toBe(true);
  }, 30000);
});
```

- [ ] **Step 6: Run to verify it fails**

Run (in `frontend/`): `npx vitest run src/__tests__/components/Workings.sky.test.tsx`
Expected: FAIL — no canvas testid on the page yet.

- [ ] **Step 7: Mount on the Workings page**

Edit `frontend/src/routes/Workings/index.tsx`:

Add import (after the existing component imports):

```tsx
import SittingsConstellation from '../../components/Workings/SittingsConstellation';
```

Extend `WorkingSummary` (after `has_witness?: boolean;`):

```tsx
  planetary_hour?: string | null;
  moon_phase?: string | null;
  saka_dawa_multiplier?: number | null;
  duplicate_of?: string | null;
```

Add sky state + fetch (after `const [showInstrument, setShowInstrument] = useState(true);`):

```tsx
  const [sky, setSky] = useState<WorkingSummary[]>([]);

  const refreshSky = () => {
    fetch(apiUrl('/operator/workings?limit=50&include_hidden=true'))
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('sky failed'))))
      .then((data: { workings?: WorkingSummary[] }) => {
        setSky(Array.isArray(data.workings) ? data.workings : []);
      })
      .catch(() => undefined);
  };
```

Call `refreshSky()` everywhere the list refreshes — in the mount effect and after each mutation. Change the effect:

```tsx
  useEffect(() => {
    refreshList();
    refreshSky();
  }, [showHidden]);
```

And inside `patchWorking`, `deleteWorking`, and `collapseDuplicates`, add `refreshSky();` immediately after each existing `refreshList();` call.

Mount the hero (immediately after the `{collapseMsg && ...}` line, before the filter row `<div className="flex flex-wrap items-center gap-4">`):

```tsx
      <SittingsConstellation workings={sky} onSelect={(id) => setOpenId(id)} />
```

- [ ] **Step 8: Run the page test and the full frontend gates**

Run (in `frontend/`):

```powershell
npx vitest run src/__tests__/components/Workings.sky.test.tsx; if ($?) { npx vitest run }
```

Expected: page test PASS; full suite PASS (425+ tests — 423 prior + 2 component + 2 page + star tests, and `no-orphan-components` green because the component is route-imported).

- [ ] **Step 9: Commit**

```powershell
$env:GIT_MASTER='1'; git add frontend/src/components/Workings/SittingsConstellation.tsx frontend/src/routes/Workings/index.tsx frontend/src/__tests__/components/SittingsConstellation.test.tsx frontend/src/__tests__/components/Workings.sky.test.tsx; if ($?) { git commit -m "feat(workings): sittings constellation hero - stars by seal time and moon band" -m "Ultraworked with [Sisyphus](https://github.com/code-yeongyu/oh-my-openagent)" -m "Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>" }
```

---

### Task 4: Full verification + push

**Files:** none created — verification only.

- [ ] **Step 1: Backend gates**

```powershell
python -m ruff check .; if ($?) { python -m pytest tests/ -m "not slow" --ignore=tests/e2e --tb=short -q }
```

Expected: ruff clean; pytest all PASS (1263+1 new = 1264).

- [ ] **Step 2: Frontend gates**

```powershell
npx vitest run; if ($?) { npm run build }
```

Expected: full suite PASS; production build green.

- [ ] **Step 3: Push**

```powershell
$env:GIT_MASTER='1'; git push
```

- [ ] **Step 4: Live gate (either machine)**

`python run.py full` → Workings page: the collapsed ledger shows as 2 bright stars + 14 ghost stars tethered; hover peeks a folio; click opens it in the right panel. Then seal one new sitting in Command Center → revisit Workings → its star appears at the right edge in the correct moon band.

---

## Self-Review (performed, fixes applied inline)

1. **Spec coverage:** backend fields → Task 1; pure mapping → Task 2; stars/bands/size/hue/ghosts/lines/tethers/ribbon/hover/click/empty state → Task 3; verify + live gate → Task 4. Ribbon is vertical (left edge, aligned with bands) per spec correction. ✓
2. **Placeholders:** none — every step carries complete code/commands. ✓
3. **Type consistency:** `StarSummaryInput` keys match Task 1's JSON exactly (`saka_dawa_multiplier`, `duplicate_of`, snake_case); `summaryToStar(summary, index, all)` signature consistent across Tasks 2-3; component consumes `Star`/`constellationGroups` as exported. ✓
4. **Orphan-guard hazard:** component creation and route mount are deliberately one task. ✓
