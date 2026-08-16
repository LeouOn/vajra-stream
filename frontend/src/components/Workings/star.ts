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
