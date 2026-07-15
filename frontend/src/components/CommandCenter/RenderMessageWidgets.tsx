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
  type: 'sigil' | 'sigil_ai' | 'tarot' | 'iching' | 'geomancy';
  title: string;
  svg?: string;
  intention?: string;
  ai_image?: string;
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
    cards?: TarotCard[];
    primary?: IChingHexagram;
    relating?: IChingHexagram;
    has_changes?: boolean;
    changing_lines?: string[];
    figures?: Record<string, GeomancyFigure | undefined>;
    houses?: Record<number, GeomancyFigure>;
    narrative?: string;
  } | null;
}

interface RenderMessageWidgetsProps {
  /** Tool call results from the LLM chat response. */
  toolCalls: ToolCall[];
  /** Callback invoked with a zoom-modal payload. */
  onZoomItemClick?: (item: ZoomItem) => void;
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

        // 5. Narrative Sigil Extraction — for outlook narratives generated
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
