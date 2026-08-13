/**
 * SakaDawaBanner — holy month indicator and upcoming-Duchen notice.
 *
 * Saka Dawa is the 4th Tibetan month after Losar. The banner reads the
 * Losar-anchored payload from the SAKA_DAWA_CHECK WebSocket frame
 * (`is_saka_dawa`, `saka_dawa_duchen`, …). During the month it shows the
 * full 10,000× / 100,000× card; the rest of the year it shows the next
 * full-moon Duchen so the date is always visible.
 */
import React from 'react';
import { Moon, Sparkles, Zap, ChevronRight, Clock } from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import type { SakaDawaResult } from '../../types';

interface SakaDawaBannerProps {
  sakaDawa?: SakaDawaResult | null;
}

function formatCivilDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const day = iso.slice(0, 10);
  const parsed = new Date(`${day}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return day;
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function isActiveWindow(data: SakaDawaResult): boolean {
  return Boolean(data.is_saka_dawa);
}

export default function SakaDawaBanner({ sakaDawa: sakaDawaProp }: SakaDawaBannerProps) {
  const { sakaDawa: sakaDawaWS } = useWebSocketStable();
  const data: SakaDawaResult | null = sakaDawaProp ?? sakaDawaWS;

  if (!data) return null;

  const practice = data.practice;
  const duchenLabel = formatCivilDate(data.saka_dawa_duchen);
  const startLabel = formatCivilDate(data.saka_dawa_month_start);
  const endLabel = formatCivilDate(data.saka_dawa_month_end);
  const active = isActiveWindow(data);
  const duchen = Boolean(data.is_duchen);

  const handleQuickStart = () => {
    audioFeedback.playTelemetry();
    const prompt = practice?.blessing_prompt
      ?? 'Generate an epic three-part sutra for Saka Dawa, dedicating merit to all beings.';
    const msg = `Run the Saka Dawa Blessing — ${prompt}`;
    window.history.pushState(null, '', '/command-center');
    window.dispatchEvent(new CustomEvent('vajra:quick-command', { detail: { command: msg } }));
  };

  if (!active) {
    return (
      <div
        data-testid="saka-dawa-upcoming"
        className="relative overflow-hidden rounded-xl border border-amber-500/20 bg-amber-950/30 px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
            <Moon className="w-4 h-4 text-amber-300" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-amber-200">
              Next Saka Dawa Duchen{duchenLabel ? `: ${duchenLabel}` : ''}
            </p>
            <p className="text-xs text-amber-300/70">
              4th Tibetan month after Losar
              {startLabel && endLabel ? ` · ${startLabel} – ${endLabel}` : ''}
              {data.days_until_duchen != null ? ` · ${data.days_until_duchen} days` : ''}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleQuickStart}
          className="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-500/30 text-amber-200 text-xs font-semibold hover:bg-amber-500/10 transition-colors"
        >
          Prepare blessing
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div
      data-testid="saka-dawa-active"
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-950/60 via-yellow-950/40 to-orange-950/50 border border-amber-400/30 shadow-[0_0_40px_rgba(251,191,36,0.1)]"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(251,191,36,0.15),transparent_50%),radial-gradient(ellipse_at_bottom_left,rgba(249,115,22,0.1),transparent_50%)]" />
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-400/5 rounded-full blur-3xl animate-pulse" />

      <div className="relative p-5 md:p-6">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-5">
          <div className="flex-shrink-0">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-[0_0_25px_rgba(251,191,36,0.4)]">
                <Moon className="w-7 h-7 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-red-500 border-2 border-slate-900 flex items-center justify-center">
                <span className="text-[8px] font-bold text-white">{duchen ? '100k' : '10k'}</span>
              </div>
            </div>
          </div>

          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl md:text-2xl font-bold text-amber-200 tracking-tight">
                {duchen ? '🌕 Saka Dawa Duchen' : '🌕 Saka Dawa Holy Month'}
              </h2>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-red-500/20 border border-red-500/30 text-red-300 text-[10px] font-mono font-bold uppercase">
                <Zap className="w-3 h-3" />
                Merit ×{duchen ? '100,000' : '10,000'}
              </span>
            </div>

            <p className="text-sm text-amber-300/80 leading-relaxed max-w-2xl">
              {practice?.description
                ?? 'The 4th Tibetan month after Losar. Actions of body, speech, and mind are multiplied.'}
            </p>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-900/30 border border-amber-500/20 text-amber-300">
                <Clock className="w-3 h-3" />
                {startLabel && endLabel ? `${startLabel} – ${endLabel}` : 'Holy month'}
                {duchenLabel ? ` · Duchen ${duchenLabel}` : ''}
              </span>
              {practice?.tradition && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-900/30 border border-purple-500/20 text-purple-300">
                  <Sparkles className="w-3 h-3" />
                  {practice.tradition}
                  {practice.preferred_hours?.length
                    ? ` — best during ${practice.preferred_hours.join(', ')} hours`
                    : ''}
                </span>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={handleQuickStart}
            className="flex-shrink-0 group flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white font-bold text-sm shadow-lg shadow-amber-500/25 transition-all duration-300 hover:scale-105"
          >
            <Sparkles className="w-4 h-4" />
            Generate Saka Dawa Blessing
            <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>

        {practice?.blessing_prompt && (
          <div className="mt-4 p-3 rounded-lg bg-black/30 border border-amber-500/10">
            <p className="text-[10px] text-amber-400/60 font-mono uppercase tracking-wider mb-1">Blessing Prompt</p>
            <p className="text-xs text-slate-400 italic leading-relaxed line-clamp-2">
              &ldquo;{practice.blessing_prompt}&rdquo;
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
