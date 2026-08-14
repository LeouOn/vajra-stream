/**
 * WorkingInstrument — tactile board for a sealed folio.
 *
 * The folio used to print dial numbers as text. This mounts the same
 * RateDial knobs used on Broadcast, a carrier-wave + kamea witness,
 * and a thin Rothko field. Load onto board writes the five rates into
 * the shared rate store so Broadcast and Rate Tuner move with the sitting.
 */
import React, { useEffect, useMemo, useState } from 'react';
import RateDial from '../UI/RateDial';
import RitualVisualization from '../UI/RitualVisualization';
import RothkoGenerator from '../2D/RothkoGenerator';
import { useRateStore } from '../../stores/rateStore';
import { audioFeedback } from '../../utils/audioFeedback';
import type { PaletteName } from '../2D/RothkoGenerator';

const DIAL_META = [
  { name: 'Physical', color: '#2dd4bf' },
  { name: 'Astral', color: '#818cf8' },
  { name: 'Mental', color: '#c084fc' },
  { name: 'Causal', color: '#f472b6' },
  { name: 'Spiritual', color: '#22d3ee' },
] as const;

const SATURN_KAMEA: number[][] = [
  [8, 1, 6],
  [3, 5, 7],
  [4, 9, 2],
];

export interface WorkingInstrumentFolio {
  working_id?: string;
  intention?: string;
  rate_values?: number[];
  frequencies?: number[];
  solfeggio_names?: string[];
  source?: string;
  chart_name?: string;
  hour_stamp?: { planetary_hour?: string | null; moon_phase?: string | null };
  saka_dawa?: { is_saka_dawa?: boolean; multiplier?: number };
}

export function rateToKameaCoords(values: number[]): Array<{ x: number; y: number; value: number }> {
  return values.slice(0, 5).map((raw) => {
    const n = ((Math.round(Number(raw) || 0) % 9) + 9) % 9 || 9;
    for (let y = 0; y < 3; y += 1) {
      for (let x = 0; x < 3; x += 1) {
        if (SATURN_KAMEA[y][x] === n) return { x, y, value: n };
      }
    }
    return { x: 1, y: 1, value: n };
  });
}

export function paletteForFolio(folio: WorkingInstrumentFolio): PaletteName {
  if ((folio.saka_dawa?.multiplier || 1) >= 100000) return 'transcendence';
  if (folio.saka_dawa?.is_saka_dawa) return 'compassion';
  return 'peace';
}

function useSweptRates(targets: number[]): number[] {
  const key = targets.join(',');
  const [shown, setShown] = useState<number[]>(() => targets.map(() => 0));

  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const from = targets.map(() => 0);
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 900);
      const ease = 1 - (1 - t) ** 3;
      setShown(targets.map((v, i) => Math.round(from[i] + (v - from[i]) * ease)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps -- sweep only when the sealed rates change

  return shown;
}

export function WitnessPlate({
  children,
  label,
}: {
  children: React.ReactNode;
  label?: string;
}): React.ReactElement {
  return (
    <div
      data-testid="witness-plate"
      className="relative rounded-lg border border-amber-500/30 bg-black/50 p-2"
    >
      <span className="pointer-events-none absolute left-1.5 top-1 text-[8px] font-mono uppercase tracking-[0.18em] text-amber-400/50">
        {label || 'Witness plate'}
      </span>
      <span className="pointer-events-none absolute left-1 top-1 h-2 w-2 border-l border-t border-amber-400/50" />
      <span className="pointer-events-none absolute right-1 top-1 h-2 w-2 border-r border-t border-amber-400/50" />
      <span className="pointer-events-none absolute bottom-1 left-1 h-2 w-2 border-b border-l border-amber-400/50" />
      <span className="pointer-events-none absolute bottom-1 right-1 h-2 w-2 border-b border-r border-amber-400/50" />
      <div className="pt-3">{children}</div>
    </div>
  );
}

export default function WorkingInstrument({ folio }: { folio: WorkingInstrumentFolio }): React.ReactElement | null {
  const values = (folio.rate_values || []).slice(0, 5).map((v) => Math.max(0, Math.min(100, Math.round(Number(v) || 0))));
  const swept = useSweptRates(values);
  const loadWorkingRates = useRateStore((s) => s.loadWorkingRates);
  const coords = useMemo(() => rateToKameaCoords(values), [values.join(',')]);
  const hour = folio.hour_stamp?.planetary_hour;
  const moon = folio.hour_stamp?.moon_phase;
  const planet = hour || 'venus';

  if (values.length === 0) return null;

  const loadBoard = () => {
    loadWorkingRates(values, {
      name: folio.intention || 'Working',
      working_id: folio.working_id,
    });
    audioFeedback.playSuccess();
  };

  return (
    <div data-testid="working-instrument" className="space-y-3">
      <div className="h-[72px] overflow-hidden rounded-lg border border-white/5">
        <RothkoGenerator
          palette={paletteForFolio(folio)}
          transitionSpeed={90}
          isPlaying
        />
      </div>

      <div className="grid grid-cols-5 gap-1 place-items-center" data-testid="working-dials">
        {values.map((_, i) => (
          <RateDial
            key={DIAL_META[i]?.name || i}
            value={swept[i] ?? 0}
            disabled
            size={64}
            color={DIAL_META[i]?.color}
            label={DIAL_META[i]?.name}
            showValue
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
        {(folio.solfeggio_names || []).slice(0, 5).map((name, i) => (
          <span
            key={`${name}-${i}`}
            className="rounded-full border border-cyan-500/25 bg-cyan-950/40 px-2 py-0.5 text-cyan-200"
          >
            {name}
            {folio.frequencies?.[i] != null ? ` · ${Math.round(folio.frequencies[i])} Hz` : ''}
          </span>
        ))}
        {hour && (
          <span className="rounded-full border border-amber-500/25 bg-amber-950/40 px-2 py-0.5 text-amber-200">
            Hour of {hour}
          </span>
        )}
        {moon && (
          <span className="rounded-full border border-amber-500/25 bg-amber-950/40 px-2 py-0.5 text-amber-200">
            {moon}
          </span>
        )}
        {folio.source && (
          <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-slate-300">
            {folio.source}
          </span>
        )}
      </div>

      <RitualVisualization
        sigil={{
          kamea: 'saturn',
          reduced: values.join('-'),
          coordinates: coords,
        }}
        rates={{
          signature: {
            values,
            name: folio.intention || 'sealed working',
          },
        }}
        genre="healing"
        kameaPlanet={planet}
      />
      <p className="text-[10px] text-slate-500 leading-relaxed">
        Kamea trace maps the five sealed dials onto Saturn&apos;s 3×3 square.
        It is a geometric witness of this sitting, not a second oracle.
      </p>

      <button
        type="button"
        data-testid="load-onto-board"
        onClick={loadBoard}
        className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-cyan-500/30 text-cyan-200 hover:bg-cyan-500/10"
      >
        Load onto board
      </button>
    </div>
  );
}
