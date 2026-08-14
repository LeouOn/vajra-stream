/**
 * RenderMessageWidgets — renders tool-call widgets emitted by the orchestrator.
 *
 * Extracted verbatim from `components/UI/CommandCenter.jsx` (lines 28-189) as
 * part of the CommandCenter decomposition (Task 3.3). Pure presentational
 * component: props-only, zero coupling to CommandCenter state. Renders the
 * success widgets for forge_sigil, cast_tarot_spread, cast_i_ching, and
 * cast_geomancy tool calls, each delegating zoom-out to `onZoomItemClick`.
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import { apiUrl } from '../../utils/api';

// ---------------------------------------------------------------------------
// Divination payload types
//
// These describe the shapes produced by the backend orchestrator tools. The
// shared `ZoomItem` (and its sub-types) are imported by `ZoomModal` to type
// the detail-modal payload; both files consume the same orchestrator output.
// ---------------------------------------------------------------------------

/** A single tarot card drawn by `cast_tarot_spread`. */
export interface TarotCard {
  id: string;
  name: string;
  svg: string;
  orientation: string;
  element?: string;
  ruler?: string;
  hebrew?: string;
  meaning?: string;
}

/** A hexagram (primary or relating) returned by `cast_i_ching`. */
export interface IChingHexagram {
  name?: string;
  meaning?: string;
}

/** The full payload of an I Ching cast. */
export interface IChingCast {
  svg?: string;
  primary?: IChingHexagram;
  relating?: IChingHexagram;
  has_changes?: boolean;
  changing_lines: string[];
}

/** A single geomantic figure (Judge / Witness / house figure). */
export interface GeomancyFigure {
  name?: string;
  meaning?: string;
  element?: string;
  ruler?: string;
}

/** The full payload of a `cast_geomancy` cast. */
export interface GeomancyChart {
  svg?: string;
  figures?: Record<string, GeomancyFigure | undefined>;
  houses?: Record<number, GeomancyFigure>;
}

/** The `forge_sigil` result payload. */
export interface SigilResult {
  intention?: string;
  svg?: string;
  ai_image?: string;
}

/**
 * Discriminated payload for the zoom modal. The `type` discriminates which
 * optional sub-object (`card` / `cast` / `chart`) carries the detail data.
 */
export interface ZoomItem {
  type: 'sigil' | 'sigil_ai' | 'tarot' | 'iching' | 'geomancy' | 'image';
  title: string;
  svg?: string;
  intention?: string;
  ai_image?: string;
  image_data_url?: string;
  prompt?: string;
  model?: string;
  cost_usd?: number;
  provider_used?: string;
  cached?: boolean;
  revised_prompt?: string;
  card?: TarotCard;
  cast?: IChingCast;
  chart?: GeomancyChart;
}

/**
 * A tool-call result envelope. `result` is a superset of every tool's output
 * (only the fields relevant to `tool_name` are populated at runtime).
 */
export interface ToolCall {
  status: string;
  tool_name: string;
  result?: {
    intention?: string;
    svg?: string;
    ai_image?: string;
    image_data_url?: string;
    model?: string;
    cost_usd?: number;
    provider_used?: string;
    cached?: boolean;
    revised_prompt?: string;
    prompt_tokens?: number;
    cards?: TarotCard[];
    primary?: IChingHexagram;
    relating?: IChingHexagram;
    has_changes?: boolean;
    changing_lines?: string[];
    figures?: Record<string, GeomancyFigure | undefined>;
    houses?: Record<number, GeomancyFigure>;
    narrative?: string;
    working_id?: string;
    target?: string;
    rate_values?: number[];
    solfeggio_names?: string[];
    frequencies?: number[];
    spoken_charge?: string;
    image_prompt?: string;
    saka_dawa?: {
      multiplier?: number;
      saka_dawa_duchen?: string;
      days_until_duchen?: number | null;
      is_saka_dawa?: boolean;
    };
    broadcast?: { status?: string; error?: string } | null;
    witness?: {
      status?: string;
      image_data_url?: string;
      error?: string;
      model?: string;
    };
    spoken?: { status?: string; error?: string; audio_path?: string };
    video?: { status?: string; error?: string; task_id?: string };
  } | null;
}

interface RenderMessageWidgetsProps {
  /** Tool call results from the LLM chat response. */
  toolCalls: ToolCall[];
  /** Callback invoked with a zoom-modal payload. */
  onZoomItemClick?: (item: ZoomItem) => void;
}

export type WorkingResult = NonNullable<ToolCall['result']>;

export function WorkingFolioCard({
  initial,
  onZoomItemClick,
  autoSpeak = false,
  autoManifest = false,
}: {
  initial: WorkingResult;
  onZoomItemClick?: (item: ZoomItem) => void;
  autoSpeak?: boolean;
  autoManifest?: boolean;
}) {
  const [folio, setFolio] = useState<WorkingResult>(initial);
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [videoBusy, setVideoBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chargeRev, setChargeRev] = useState(0);

  const dials = (folio.rate_values || []).join(' · ');
  const duchen = folio.saka_dawa?.saka_dawa_duchen;
  const days = folio.saka_dawa?.days_until_duchen;
  const witnessUrl = folio.witness?.image_data_url;

  const applyFolio = (data: unknown) => {
    if (data && typeof data === 'object') {
      setFolio(data as WorkingResult);
    }
  };

  const speakCharge = async () => {
    if (!folio.working_id || speaking) return;
    setSpeaking(true);
    setError(null);
    try {
      const res = await fetch(apiUrl(`/operator/workings/${folio.working_id}/speak`), { method: 'POST' });
      const data: unknown = await res.json();
      if (!res.ok) {
        setError('Could not speak the charge');
        return;
      }
      applyFolio(data);
      setChargeRev((n) => n + 1);
    } catch {
      setError('Could not speak the charge');
    } finally {
      setSpeaking(false);
    }
  };

  const submitVideo = async () => {
    if (!folio.working_id || videoBusy) return;
    setVideoBusy(true);
    setError(null);
    try {
      const res = await fetch(apiUrl(`/operator/workings/${folio.working_id}/video`), { method: 'POST' });
      const data: unknown = await res.json();
      if (!res.ok) {
        setError('Video submit failed');
        return;
      }
      applyFolio(data);
    } catch {
      setError('Video submit failed');
    } finally {
      setVideoBusy(false);
    }
  };

  const forgeWitness = async () => {
    if (!folio.working_id || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(apiUrl(`/operator/workings/${folio.working_id}/manifest`), { method: 'POST' });
      const data: unknown = await res.json();
      if (!res.ok) {
        setError('Manifestation image failed');
        return;
      }
      applyFolio(data);
    } catch {
      setError('Manifestation image failed');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!autoSpeak || !initial.working_id || initial.spoken?.status === 'ok') return;
    void speakCharge();
    // Speak once when a newly sealed working is shown in chat.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSpeak, initial.working_id]);

  useEffect(() => {
    if (!autoManifest || !initial.working_id || initial.witness?.image_data_url) return;
    void forgeWitness();
    // Manifestation image is the cheap default visual for a new working.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoManifest, initial.working_id]);

  return (
    <div data-testid="working-folio" className="bg-black/60 p-4 rounded-xl border border-amber-500/25 space-y-3">
      <div className="flex items-center justify-between gap-2 text-amber-300 text-xs font-semibold uppercase font-mono">
        <span>✦ Working sealed</span>
        <span className="text-[10px] text-amber-200/70 normal-case">{folio.working_id}</span>
      </div>
      <p className="text-sm text-white leading-relaxed">{folio.intention}</p>
      <p className="text-xs text-amber-200/80">For {folio.target || 'all beings'}</p>
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="rounded-lg bg-amber-950/40 border border-amber-500/20 px-2 py-1.5">
          <div className="text-amber-400/70 uppercase tracking-wider text-[9px]">Dials</div>
          <div className="font-mono text-amber-100">{dials || '—'}</div>
        </div>
        <div className="rounded-lg bg-amber-950/40 border border-amber-500/20 px-2 py-1.5">
          <div className="text-amber-400/70 uppercase tracking-wider text-[9px]">Next Duchen</div>
          <div className="text-amber-100">{duchen || '—'}{days != null ? ` · ${days}d` : ''}</div>
        </div>
      </div>
      {folio.spoken_charge && (
        <p className="text-xs italic text-slate-300 border-l-2 border-amber-500/40 pl-3">{folio.spoken_charge}</p>
      )}
      {folio.broadcast?.status && (
        <p className="text-[10px] font-mono text-amber-400/80">Broadcast: {folio.broadcast.status}</p>
      )}
      {witnessUrl && (
        <img
          src={witnessUrl}
          alt="Manifestation image"
          className="w-full max-h-64 object-contain rounded-lg border border-amber-500/20 cursor-zoom-in"
          onClick={() => onZoomItemClick?.({
            type: 'image',
            title: folio.intention || 'Manifestation',
            image_data_url: witnessUrl,
          })}
        />
      )}
      {folio.witness?.error && (
        <p className="text-[11px] text-red-300">{folio.witness.error}</p>
      )}
      {error && <p className="text-[11px] text-red-300">{error}</p>}
      {folio.spoken?.status === 'ok' && folio.working_id && (
        <audio
          key={chargeRev}
          controls
          className="w-full"
          src={apiUrl(`/operator/workings/${folio.working_id}/charge`)}
        />
      )}
      {folio.video?.status && (
        <p className="text-[10px] font-mono text-amber-400/80">
          Video: {folio.video.status}
          {folio.video.task_id ? ` · ${folio.video.task_id}` : ''}
          {folio.video.error ? ` · ${folio.video.error}` : ''}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => { void speakCharge(); }}
          disabled={speaking}
          className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-amber-500/30 text-amber-200 hover:bg-amber-500/10 disabled:opacity-50"
        >
          {speaking ? 'Speaking…' : 'Speak charge'}
        </button>
        <button
          type="button"
          onClick={() => { void forgeWitness(); }}
          disabled={busy}
          className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-amber-500/30 text-amber-200 hover:bg-amber-500/10 disabled:opacity-50"
        >
          {busy ? 'Painting manifestation…' : witnessUrl ? 'Re-paint manifestation' : 'Manifestation image'}
        </button>
        <button
          type="button"
          onClick={() => { void submitVideo(); }}
          disabled={videoBusy}
          className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-amber-500/30 text-amber-200 hover:bg-amber-500/10 disabled:opacity-50"
        >
          {videoBusy ? 'Submitting video…' : 'Manifestation video'}
        </button>
      </div>
    </div>
  );
}

const COORD_RE = /\(\s*(\d+)\s*,\s*(\d+)\s*\)/g;

interface ExtractedSigilState {
  svg: string;
  kamea: string;
}

/**
 * Detect ``(x, y)`` coordinate pairs in a narrative string and render the
 * extracted kamea sigil SVG by calling ``/api/v1/sigils/extract_from_text``.
 *
 * Exported so CommandCenter chat messages can render sigils embedded in
 * orchestrator-generated outlook narratives.
 */
export const NarrativeSigilExtractor = ({ narrative }: { narrative: string }) => {
  const [sigil, setSigil] = useState<ExtractedSigilState | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!narrative || !COORD_RE.test(narrative)) return;
    COORD_RE.lastIndex = 0;

    const controller = new AbortController();
    fetch(apiUrl('/sigils/extract_from_text'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ narrative }),
      signal: controller.signal,
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (cancelled) return;
        if (data && data.status === 'success' && data.svg) {
          setSigil({ svg: data.svg, kamea: data.kamea || 'saturn' });
        }
      })
      .catch(() => {});

    return () => { cancelled = true; controller.abort(); };
  }, [narrative]);

  if (!sigil) return null;

  return (
    <div className="mt-2 bg-black/40 p-3 rounded-lg border border-cyan-500/20">
      <div className="text-[10px] text-cyan-400 font-mono font-semibold uppercase mb-1">🔮 Extracted Sigil</div>
      <div
        dangerouslySetInnerHTML={{ __html: sigil.svg }}
        className="w-full max-w-[180px] mx-auto"
      />
      <div className="text-[9px] text-gray-500 font-mono text-center mt-1">{sigil.kamea} grid</div>
    </div>
  );
};

export const RenderMessageWidgets = ({ toolCalls, onZoomItemClick }: RenderMessageWidgetsProps) => {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="mt-3 space-y-3 border-t border-white/5 pt-3">
      {toolCalls.map((tc, idx) => {
        if (tc.status !== 'success') return null;

        if (tc.tool_name === 'run_working' || tc.tool_name === 'forge_witness') {
          const w = tc.result;
          if (!w || !w.working_id) return null;
          return (
            <WorkingFolioCard
              key={idx}
              initial={w}
              onZoomItemClick={onZoomItemClick}
              autoSpeak
              autoManifest
            />
          );
        }

        // 1. Forge Sigil Widget
        if (tc.tool_name === 'forge_sigil') {
          const sigil = tc.result;
          if (!sigil) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-cyan-500/20 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase font-mono">
                <span>🔮 SIGIL FORGED</span>
              </div>
              <div className="text-xs text-gray-300 font-medium">
                Intention: <span className="text-white italic">"{sigil.intention}"</span>
              </div>
              <div className="flex gap-4 items-center">
                {/* SVG Kamea */}
                <div
                  onClick={() => onZoomItemClick && onZoomItemClick({
                    type: 'sigil',
                    title: 'Forged Sigil',
                    intention: sigil.intention,
                    svg: sigil.svg,
                    ai_image: sigil.ai_image
                  })}
                  className="w-24 h-24 bg-gray-950 rounded-lg p-1 border border-white/5 flex items-center justify-center cursor-zoom-in hover:border-cyan-400 hover:scale-105 transition-all duration-300"
                >
                  <div dangerouslySetInnerHTML={{ __html: sigil.svg }} className="w-full h-full" />
                </div>
                {/* AI image if generated */}
                {sigil.ai_image && (
                  <div
                    onClick={() => onZoomItemClick && onZoomItemClick({
                      type: 'sigil_ai',
                      title: 'AI Sigil Image',
                      intention: sigil.intention,
                      ai_image: sigil.ai_image
                    })}
                    className="w-24 h-24 bg-gray-950 rounded-lg p-1 border border-white/5 overflow-hidden flex items-center justify-center cursor-zoom-in hover:border-cyan-400 hover:scale-105 transition-all duration-300"
                  >
                    <img src={sigil.ai_image} alt="AI Sigil" className="w-full h-full object-cover rounded-md" />
                  </div>
                )}
              </div>
            </div>
          );
        }

        // 2. Tarot Spread Widget
        if (tc.tool_name === 'cast_tarot_spread') {
          const cards = tc.result?.cards || [];
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-purple-500/20 space-y-3">
              <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold uppercase font-mono">
                <span>🃏 TAROT CARDS DRAWN</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {cards.map((card, cidx) => (
                  <div
                    key={card.id}
                    onClick={() => onZoomItemClick && onZoomItemClick({
                      type: 'tarot',
                      title: card.name,
                      svg: card.svg,
                      card: card
                    })}
                    className="bg-gray-950/80 p-2.5 rounded-lg border border-white/5 flex flex-col items-center hover:border-purple-500/50 hover:scale-105 cursor-zoom-in transition-all duration-300"
                  >
                    <div dangerouslySetInnerHTML={{ __html: card.svg }} className="divination-card-container w-20 h-32 flex justify-center" />
                    <span className="text-[10px] text-gray-400 font-bold mt-2 truncate max-w-full text-center">{card.name}</span>
                    <span className="text-[8px] text-purple-300 italic truncate max-w-full text-center">{card.orientation.toUpperCase()}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        }

        // 3. I Ching Widget
        if (tc.tool_name === 'cast_i_ching') {
          const cast = tc.result;
          if (!cast) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-cyan-500/20 space-y-3">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase font-mono">
                <span>☯️ I CHING HEXAGRAM CAST</span>
              </div>
              <div
                onClick={() => onZoomItemClick && onZoomItemClick({
                  type: 'iching',
                  title: 'I Ching Hexagram',
                  svg: cast.svg,
                  cast: cast as IChingCast
                })}
                className="flex flex-col sm:flex-row gap-4 items-center cursor-zoom-in hover:bg-white/5 p-2 rounded-lg transition-all duration-300"
              >
                <div dangerouslySetInnerHTML={{ __html: cast.svg }} className="divination-card-container w-full max-w-[200px]" />
                <div className="flex-1 text-xs space-y-1.5 text-gray-300">
                  <div>
                    <span className="font-bold text-white block">Primary: {cast.primary?.name}</span>
                    <span className="text-[10px] italic">{cast.primary?.meaning}</span>
                  </div>
                  {cast.has_changes && (
                    <div className="pt-1.5 border-t border-white/5">
                      <span className="font-bold text-purple-300 block">Relating: {cast.relating?.name}</span>
                      <span className="text-[10px] italic">{cast.relating?.meaning}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        }

        // 4. Geomancy Widget
        if (tc.tool_name === 'cast_geomancy') {
          const chart = tc.result;
          if (!chart) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-yellow-500/20 space-y-3">
              <div className="flex items-center gap-2 text-yellow-400 text-xs font-semibold uppercase font-mono">
                <span>👁 GEOMANTIC SHIELD CAST</span>
              </div>
              <div
                onClick={() => onZoomItemClick && onZoomItemClick({
                  type: 'geomancy',
                  title: 'Geomantic Shield',
                  svg: chart.svg,
                  chart: chart as GeomancyChart
                })}
                className="flex flex-col sm:flex-row gap-4 items-center cursor-zoom-in hover:bg-white/5 p-2 rounded-lg transition-all duration-300"
              >
                <div dangerouslySetInnerHTML={{ __html: chart.svg }} className="w-full max-w-[240px]" />
                <div className="flex-1 text-xs space-y-2 text-gray-300">
                  <div>
                    <span className="font-bold text-white block">The Judge: {chart.figures?.Judge?.name}</span>
                    <span className="text-[10px] italic">{chart.figures?.Judge?.meaning}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="px-2 py-0.5 bg-yellow-950 text-yellow-300 border border-yellow-500/20 rounded text-[9px] uppercase font-mono">
                      ELEMENT: {chart.figures?.Judge?.element}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-950 text-purple-300 border border-purple-500/20 rounded text-[9px] uppercase font-mono">
                      RULER: {chart.figures?.Judge?.ruler}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        }

        // 5. Image Generation Widget — generate_image tool result
        if (tc.tool_name === 'generate_image') {
          const img = tc.result;
          if (!img?.image_data_url) return null;
          return (
            <div key={idx} className="bg-black/60 p-4 rounded-xl border border-pink-500/20 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-pink-400 text-xs font-semibold uppercase font-mono">
                  <span>🎨 IMAGE GENERATED</span>
                </div>
                <div className="flex items-center gap-2">
                  {img.cached && (
                    <span className="px-1.5 py-0.5 bg-gray-800 text-gray-300 border border-white/5 rounded text-[9px] font-mono">
                      CACHED
                    </span>
                  )}
                  {img.provider_used && (
                    <span className="px-1.5 py-0.5 bg-purple-950 text-purple-300 border border-purple-500/20 rounded text-[9px] font-mono uppercase">
                      {img.provider_used}
                    </span>
                  )}
                  {img.model && (
                    <span className="px-1.5 py-0.5 bg-cyan-950 text-cyan-300 border border-cyan-500/20 rounded text-[9px] font-mono">
                      {img.model}
                    </span>
                  )}
                  {typeof img.cost_usd === 'number' && (
                    <span className="px-1.5 py-0.5 bg-emerald-950 text-emerald-300 border border-emerald-500/20 rounded text-[9px] font-mono">
                      ${img.cost_usd.toFixed(4)}
                    </span>
                  )}
                </div>
              </div>
              <div
                onClick={() => onZoomItemClick && onZoomItemClick({
                  type: 'image',
                  title: img.revised_prompt || 'Generated Image',
                  image_data_url: img.image_data_url,
                  model: img.model,
                  cost_usd: img.cost_usd,
                  provider_used: img.provider_used,
                  cached: img.cached,
                  revised_prompt: img.revised_prompt,
                })}
                className="cursor-zoom-in rounded-lg overflow-hidden border border-white/5 hover:border-pink-400/60 hover:scale-[1.01] transition-all duration-300"
              >
                <img
                  src={img.image_data_url}
                  alt={img.revised_prompt || 'Generated image'}
                  className="w-full max-h-[400px] object-contain bg-gray-950"
                />
              </div>
              {img.revised_prompt && (
                <div className="text-[11px] text-gray-400 italic border-l-2 border-pink-500/40 pl-2">
                  "{img.revised_prompt}"
                </div>
              )}
            </div>
          );
        }

        // 6. Narrative Sigil Extraction — for outlook narratives generated
        // via chat that embed (x,y) coordinate pairs in the Sigillum section.
        if (tc.tool_name === 'generate_outlook' || tc.tool_name === 'generate_single_outlook' || tc.tool_name === 'generate_epic_outlook') {
          const narrativeText = tc.result?.narrative;
          if (!narrativeText) return null;
          return (
            <div key={idx}>
              <NarrativeSigilExtractor narrative={narrativeText} />
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};
