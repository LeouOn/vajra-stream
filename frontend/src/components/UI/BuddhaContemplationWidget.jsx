/**
 * BuddhaContemplationWidget — 88-Buddha random contemplation & recitation.
 *
 * Displays a randomly selected Buddha from the 88-Buddha collection with
 * name (Chinese, pinyin, Sanskrit), meaning, realm, emanated light, and
 * a contemplation narrative. Provides controls for single-name recitation
 * and continuous mala-synchronized recitation loop with live progress.
 *
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles, RefreshCw, Volume2, Play, Square, Activity,
  BookOpen, Compass, Zap, Clock, Settings
} from 'lucide-react';
import { API_BASE } from '../../utils/api';
import { audioFeedback } from '../../utils/audioFeedback';
import TTSSettingsPanel from './TTSSettingsPanel';

const CATEGORY_LABELS = {
  past: '53 Past Buddhas',
  confession: '35 Confession Buddhas',
};
const CATEGORY_COLORS = {
  past: 'border-amber-500/30 text-amber-400',
  confession: 'border-cyan-500/30 text-cyan-400',
};

export default function BuddhaContemplationWidget({ buddhaStatus }) {
  const [buddha, setBuddha] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loopStatus, setLoopStatus] = useState(null);
  const [loopLoading, setLoopLoading] = useState(false);
  const pollRef = useRef(null);

  const fetchRandomBuddha = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/operator/buddhas/random`);
      if (res.ok) {
        const data = await res.json();
        if (data.buddha) setBuddha(data);
      }
    } catch {}
    setLoading(false);
  };

  const fetchLoopStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/operator/buddhas/recitation/status`);
      if (res.ok) setLoopStatus(await res.json());
    } catch {}
  };

  useEffect(() => {
    fetchRandomBuddha();
    fetchLoopStatus();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    if (buddhaStatus) {
      setLoopStatus(buddhaStatus);
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    if (loopStatus?.running) {
      pollRef.current = setInterval(fetchLoopStatus, 2000);
    } else {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loopStatus?.running, buddhaStatus]);

  const handleRecite = async () => {
    if (!buddha?.buddha?.name_chinese) return;
    audioFeedback.playTelemetry();
    const name = buddha.buddha.name_chinese;
    const text = name.startsWith('南無') ? name : `南無${name}`;
    // Play via the unified TTS stream endpoint (Qwen3-TTS or Edge)
    const audio = new Audio();
    try {
      const res = await fetch(`${API_BASE}/tts/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          role: 'buddhist_chant',
          rate: '-30%',
        }),
      });
      if (!res.ok) throw new Error('TTS request failed');
      const mime = res.headers.get('Content-Type') || 'audio/mpeg';
      const blob = await res.blob();
      const url = URL.createObjectURL(new Blob([blob], { type: mime }));
      audio.src = url;
      audio.onended = () => URL.revokeObjectURL(url);
      audio.onerror = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (e) {
      // Fall back to the legacy dispatch tool path (server-side render only)
      try {
        await fetch(`${API_BASE}/operator/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool_name: 'recite_buddha_name',
            arguments: { buddha_name: name, role: 'buddhist_chant' },
          }),
        });
      } catch {}
    }
  };

  const handleToggleLoop = async () => {
    setLoopLoading(true);
    audioFeedback.playTelemetry();
    try {
      if (loopStatus?.running) {
        await fetch(`${API_BASE}/operator/buddhas/recitation/stop`, { method: 'POST' });
      } else {
        await fetch(`${API_BASE}/operator/buddhas/recitation/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intention: '愿一切众生离苦得乐', interval_seconds: 3.0 }),
        });
      }
      await fetchLoopStatus();
    } catch {}
    setLoopLoading(false);
  };

  const catColor = CATEGORY_COLORS[buddha?.buddha?.category] || CATEGORY_COLORS.confession;
  const catLabel = CATEGORY_LABELS[buddha?.buddha?.category] || '';

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-amber-950/30 via-slate-900/60 to-cyan-950/20 border border-amber-500/15 shadow-xl">
      {/* Ambient glow */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-amber-500/3 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-32 h-32 bg-cyan-500/3 rounded-full blur-2xl" />

      <div className="relative p-5 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-900/40 border border-amber-500/20 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-amber-300">88-Buddha Contemplation</h3>
              <p className="text-[10px] text-slate-500 font-mono">八十八佛大懺悔文</p>
            </div>
          </div>
          <button
            onClick={fetchRandomBuddha}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-700 text-xs text-slate-300 transition-all"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            New Buddha
          </button>
        </div>

        {/* Buddha Display */}
        {buddha ? (
          <>
            {/* Name and Identity */}
            <div className="bg-black/30 rounded-xl border border-white/5 p-4 space-y-3">
              {/* Chinese Name */}
              <div className="text-center">
                <h2 className="text-2xl font-bold text-amber-200 tracking-wider">
                  {buddha.buddha.name_chinese}
                </h2>
                <div className="flex items-center justify-center gap-2 mt-1">
                  <span className="text-xs text-slate-400 font-mono">{buddha.buddha.name_pinyin}</span>
                  <span className="w-1 h-1 rounded-full bg-slate-600" />
                  <span className="text-[10px] text-slate-500 italic font-mono max-w-[200px] truncate">
                    {buddha.buddha.name_sanskrit}
                  </span>
                </div>
              </div>

              {/* Attributes */}
              <div className="flex flex-wrap justify-center gap-2">
                <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[10px] font-semibold ${catColor}`}>
                  {catLabel}
                </span>
                {buddha.buddha.meaning && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border border-purple-500/20 bg-purple-950/30 text-purple-300 text-[10px]">
                    <Sparkles className="w-2.5 h-2.5" />
                    {buddha.buddha.meaning}
                  </span>
                )}
                {buddha.buddha.realm && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border border-indigo-500/20 bg-indigo-950/30 text-indigo-300 text-[10px]">
                    <Compass className="w-2.5 h-2.5" />
                    {buddha.buddha.realm}
                  </span>
                )}
                {buddha.buddha.light && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border border-yellow-500/20 bg-yellow-950/30 text-yellow-300 text-[10px]">
                    <Zap className="w-2.5 h-2.5" />
                    {buddha.buddha.light}
                  </span>
                )}
              </div>

              {/* Contemplation Narrative */}
              {buddha.narrative && (
                <div className="bg-amber-950/10 rounded-lg border border-amber-500/10 p-3.5">
                  <p className="text-xs text-slate-300 leading-relaxed italic">
                    "{buddha.narrative}"
                  </p>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleRecite}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-900/40 hover:bg-cyan-900/60 border border-cyan-500/20 text-xs text-cyan-300 font-medium transition-all"
              >
                <Volume2 className="w-3.5 h-3.5" />
                Recite Name
              </button>
              <button
                onClick={handleToggleLoop}
                disabled={loopLoading}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg border text-xs font-medium transition-all ${
                  loopStatus?.running
                    ? 'bg-red-900/30 hover:bg-red-900/50 border-red-500/20 text-red-300'
                    : 'bg-emerald-900/30 hover:bg-emerald-900/50 border-emerald-500/20 text-emerald-300'
                }`}
              >
                {loopStatus?.running ? (
                  <>
                    <Square className="w-3.5 h-3.5" />
                    Stop Loop
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    Start 88-Buddha Loop
                  </>
                )}
              </button>
            </div>

            {/* Loop Status */}
            {loopStatus?.running && (
              <div className="bg-emerald-950/20 border border-emerald-500/15 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                    <span className="text-[10px] text-emerald-400 font-mono uppercase tracking-wider">Recitation Active</span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    Cycle {loopStatus.current_cycle || 0}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <div className="text-lg font-bold text-emerald-300 font-mono">{loopStatus.total_recited || 0}</div>
                    <div className="text-[9px] text-slate-500 uppercase">Recited</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-amber-300 font-mono">{loopStatus.dedications || 0}</div>
                    <div className="text-[9px] text-slate-500 uppercase">Dedications</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold text-purple-300 font-mono">{loopStatus.mala_count || 0}</div>
                    <div className="text-[9px] text-slate-500 uppercase">Mala Count</div>
                  </div>
                </div>
                {loopStatus.total_buddhas > 0 && (
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-500"
                      style={{ width: `${Math.min(100, ((loopStatus.current_index || 0) / loopStatus.total_buddhas) * 100)}%` }}
                    />
                  </div>
                )}
                {loopStatus.current_buddha?.name_chinese && (
                  <p className="text-[10px] text-slate-400 text-center truncate">
                    Now: <span className="text-amber-300 font-medium">{loopStatus.current_buddha.name_chinese}</span>
                  </p>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-slate-600 animate-spin" />
          </div>
        )}

        {/* TTS Settings (collapsible) */}
        <details className="mt-4 border-t border-white/5 pt-3">
          <summary className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 cursor-pointer select-none">
            <Settings className="w-3.5 h-3.5" />
            TTS Voice Settings
          </summary>
          <div className="mt-3">
            <TTSSettingsPanel compact />
          </div>
        </details>
      </div>
    </div>
  );
}
