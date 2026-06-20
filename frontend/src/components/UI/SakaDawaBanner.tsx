/**
 * SakaDawaBanner — holy month indicator and quick-start banner.
 *
 * Checks if the current date falls within the Saka Dawa holy month
 * (4th Tibetan month ≈ May-June) and renders a prominent banner
 * with the 100,000x merit multiplier, practice description, and
 * a one-click button to start a Saka Dawa blessing session.
 *
 * Subscribes to the SAKA_DAWA_CHECK WebSocket broadcast via
 * useWebSocketStable (no REST polling). Only renders when in the
 * Saka Dawa window. Callers may still override with a `sakaDawa`
 * prop; otherwise the WS value is used.
 *
 * @component
 */
import React from 'react';
import { Moon, Sparkles, Zap, ChevronRight, Clock } from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';

interface SakaDawaPractice {
  description: string;
  tradition: string;
  genre: string;
  preferred_hours?: string[];
  blessing_prompt: string;
}

export interface SakaDawaBannerData {
  in_saka_dawa_window: boolean;
  practice: SakaDawaPractice;
  [key: string]: unknown;
}

interface SakaDawaBannerProps {
  sakaDawa?: SakaDawaBannerData | null;
}

export default function SakaDawaBanner({ sakaDawa: sakaDawaProp }: SakaDawaBannerProps) {
  const { sakaDawa: sakaDawaWS } = useWebSocketStable();
  const wsData = sakaDawaWS as unknown as SakaDawaBannerData | null;
  const data: SakaDawaBannerData | null = sakaDawaProp || wsData;

  // No data yet (WS hasn't delivered a SAKA_DAWA_CHECK frame) — hide banner.
  if (!data) return null;
  // Only show when in Saka Dawa window
  if (!data?.in_saka_dawa_window) return null;

  const handleQuickStart = () => {
    audioFeedback.playTelemetry();
    // Navigate to Command Center with pre-filled Saka Dawa prompt
    const msg = `Run the Saka Dawa Blessing — ${data.practice.blessing_prompt}`;
    window.history.pushState(null, '', '/command-center');
    window.dispatchEvent(new CustomEvent('vajra:quick-command', { detail: { command: msg } }));
  };

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-950/60 via-yellow-950/40 to-orange-950/50 border border-amber-400/30 shadow-[0_0_40px_rgba(251,191,36,0.1)]">
      {/* Animated background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(251,191,36,0.15),transparent_50%),radial-gradient(ellipse_at_bottom_left,rgba(249,115,22,0.1),transparent_50%)]" />
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-400/5 rounded-full blur-3xl animate-pulse" />

      <div className="relative p-5 md:p-6">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-5">
          {/* Icon */}
          <div className="flex-shrink-0">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-[0_0_25px_rgba(251,191,36,0.4)]">
                <Moon className="w-7 h-7 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-red-500 border-2 border-slate-900 flex items-center justify-center">
                <span className="text-[8px] font-bold text-white">100k</span>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl md:text-2xl font-bold text-amber-200 tracking-tight">
                🌕 Saka Dawa Holy Month
              </h2>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-red-500/20 border border-red-500/30 text-red-300 text-[10px] font-mono font-bold uppercase">
                <Zap className="w-3 h-3" />
                Merit ×100,000
              </span>
            </div>

            <p className="text-sm text-amber-300/80 leading-relaxed max-w-2xl">
              {data.practice.description}
            </p>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-900/30 border border-amber-500/20 text-amber-300">
                <Clock className="w-3 h-3" />
                {data.practice.tradition} — {data.practice.genre}
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-900/30 border border-purple-500/20 text-purple-300">
                <Sparkles className="w-3 h-3" />
                Best during {data.practice.preferred_hours?.join(', ')} hours
              </span>
            </div>
          </div>

          {/* Action */}
          <button
            onClick={handleQuickStart}
            className="flex-shrink-0 group flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white font-bold text-sm shadow-lg shadow-amber-500/25 transition-all duration-300 hover:scale-105"
          >
            <Sparkles className="w-4 h-4" />
            Generate Saka Dawa Blessing
            <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>

        {/* Prompt Preview */}
        <div className="mt-4 p-3 rounded-lg bg-black/30 border border-amber-500/10">
          <p className="text-[10px] text-amber-400/60 font-mono uppercase tracking-wider mb-1">Blessing Prompt</p>
          <p className="text-xs text-slate-400 italic leading-relaxed line-clamp-2">
            "{data.practice.blessing_prompt}"
          </p>
        </div>
      </div>
    </div>
  );
}
