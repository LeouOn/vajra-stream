/**
 * Operations Panel — multi-system orchestration dashboard.
 * Unified view for the divination suite (tarot / I Ching / geomancy).
 * @component
 */
import React, { useState } from 'react';
import { 
  Sparkles, Compass, RefreshCw, Layers
} from 'lucide-react';
import { Card, Tag, message } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { createLogger } from '../../utils/logger';

const log = createLogger('OperationsPanel');

interface TarotCard {
  id: string | number;
  name: string;
  svg: string;
  reversed?: boolean;
  keywords?: string[];
  meaning?: string;
  position?: { name?: string; [key: string]: unknown };
  [key: string]: unknown;
}

interface TarotDrawResponse {
  cards: TarotCard[];
  spread?: Array<{ name?: string; [key: string]: unknown }>;
  [key: string]: unknown;
}

interface IchingLeg {
  name: string;
  meaning: string;
  [key: string]: unknown;
}

interface IchingCast {
  svg: string;
  primary: IchingLeg;
  relating: IchingLeg;
  has_changes?: boolean;
  changing_lines?: number[];
  [key: string]: unknown;
}

interface GeomancyFigure {
  name: string;
  translation: string;
  element: string;
  [key: string]: unknown;
}

interface GeomancyChart {
  svg: string;
  figures: Record<string, GeomancyFigure>;
  [key: string]: unknown;
}

interface GeoBalance {
  geomancy_elements?: Record<string, number>;
  western_elements?: Record<string, number>;
  harmony_score?: number;
  harmony_quality?: string;
  judge?: { name?: string; meaning?: string; [key: string]: unknown };
  [key: string]: unknown;
}

type DivinationSystem = 'tarot' | 'iching' | 'geomancy';

// Face-down card back: a symmetric neon mandala that matches the deck aesthetic.
const TAROT_CARD_BACK = `<svg viewBox="0 0 240 380" xmlns="http://www.w3.org/2000/svg" style="background:#0b132b; border-radius:16px;">
  <defs>
    <filter id="back-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect x="10" y="10" width="220" height="360" rx="12" fill="none" stroke="#a855f7" stroke-width="2" filter="url(#back-glow)"/>
  <rect x="18" y="18" width="204" height="344" rx="9" fill="none" stroke="#a855f7" stroke-width="1" opacity="0.4"/>
  <circle cx="120" cy="190" r="60" fill="none" stroke="#06b6d4" stroke-width="1.5" opacity="0.7" filter="url(#back-glow)"/>
  <circle cx="120" cy="190" r="42" fill="none" stroke="#a855f7" stroke-width="1.2" opacity="0.6"/>
  <circle cx="120" cy="190" r="24" fill="none" stroke="#06b6d4" stroke-width="1" opacity="0.8"/>
  <g transform="translate(120 190)">
    <line x1="0" y1="-70" x2="0" y2="-24" stroke="#a855f7" stroke-width="1" opacity="0.5"/>
    <line x1="0" y1="24" x2="0" y2="70" stroke="#a855f7" stroke-width="1" opacity="0.5"/>
    <line x1="-70" y1="0" x2="-24" y2="0" stroke="#06b6d4" stroke-width="1" opacity="0.5"/>
    <line x1="24" y1="0" x2="70" y2="0" stroke="#06b6d4" stroke-width="1" opacity="0.5"/>
  </g>
  <polygon points="120,170 124,186 140,186 127,196 132,212 120,202 108,212 113,196 100,186 116,186" fill="none" stroke="#06b6d4" stroke-width="1.4" filter="url(#back-glow)"/>
  <circle cx="120" cy="190" r="5" fill="#a855f7" opacity="0.8"/>
  <text x="120" y="330" fill="#a855f7" font-size="9" font-family="monospace" text-anchor="middle" letter-spacing="3" opacity="0.7">VAJRA STREAM</text>
</svg>`;

export default function OperationsPanel() {
  const [divinationSystem, setDivinationSystem] = useState<DivinationSystem>('tarot');

  // Divination state
  const [tarotDrawCount, setTarotDrawCount] = useState<number>(3);
  const [tarotResult, setTarotResult] = useState<TarotCard[] | null>(null);
  const [tarotSpread, setTarotSpread] = useState<Array<{ name?: string; [key: string]: unknown }>>([]);
  const [tarotFlipped, setTarotFlipped] = useState<boolean[]>([]);
  const [ichingResult, setIchingResult] = useState<IchingCast | null>(null);
  const [geomancyResult, setGeomancyResult] = useState<GeomancyChart | null>(null);
  const [geoBalance, setGeoBalance] = useState<GeoBalance | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleDrawTarot = async (): Promise<void> => {
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch(`/api/v1/divination/tarot/draw`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: tarotDrawCount })
      });
      if (response.ok) {
        const data = await response.json() as TarotDrawResponse;
        setTarotResult(data.cards);
        setTarotSpread(data.spread || []);
        // Start with all cards face-down, then stagger-reveal each one.
        setTarotFlipped(new Array(data.cards.length).fill(false));
        audioFeedback.playSuccess();
        data.cards.forEach((_, idx) => {
          setTimeout(() => {
            setTarotFlipped(prev => {
              const next = [...prev];
              next[idx] = true;
              return next;
            });
          }, 350 + idx * 220);
        });
      }
    } catch (e) {
      log.error(e);
      audioFeedback.playError();
      message.error('Could not draw tarot: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  const handleCastIChing = async (): Promise<void> => {
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch(`/api/v1/divination/iching/cast`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = (await response.json()) as { cast: IchingCast };
        setIchingResult(data.cast);
        audioFeedback.playSuccess();
      }
    } catch (e) {
      log.error(e);
      audioFeedback.playError();
      message.error('Could not cast I Ching: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  const handleCastGeomancy = async (): Promise<void> => {
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch(`/api/v1/divination/geomancy/shield`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = (await response.json()) as { chart: GeomancyChart };
        setGeomancyResult(data.chart);
        // Also fetch elemental balance comparison (let outer catch handle errors)
        const balRes = await fetch(`/api/v1/divination/geomancy/elemental-balance`);
        if (balRes.ok) setGeoBalance(await balRes.json() as GeoBalance);
        audioFeedback.playSuccess();
      }
    } catch (e) {
      log.error(e);
      audioFeedback.playError();
      message.error('Could not cast geomancy: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">

      {/* ==================== DIVINATION SUITE ==================== */}
      <div className="space-y-6">
        <div className="flex justify-between items-center bg-gray-950/40 p-4 rounded-xl border border-white/5">
          <div className="flex gap-2">
            {(['tarot', 'iching', 'geomancy'] as const).map(system => (
              <button
                key={system}
                onClick={() => { setDivinationSystem(system); audioFeedback.playClick(); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-300 ${
                  divinationSystem === system
                    ? 'bg-purple-900 border border-purple-500/30 text-white'
                    : 'bg-white/5 border border-transparent text-gray-400 hover:text-white'
                }`}
              >
                {system === 'tarot' ? '🃏 Tarot Cards' : system === 'iching' ? '☯️ I Ching' : '👁 Geomancy'}
              </button>
            ))}
          </div>
        </div>

        {/* TAROT CARD DRAWER */}
        {divinationSystem === 'tarot' && (
          <div className="space-y-4">
            <div className="bg-gray-800/40 border border-white/5 rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                  Rider-Waite 78-Card Tarot Spread
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Uses high-entropy entropy pools to map archetypal nodes to your active query.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={tarotDrawCount}
                  onChange={(e) => setTarotDrawCount(Number(e.target.value))}
                  className="bg-gray-900 border border-white/10 rounded px-2.5 py-1.5 text-xs text-white"
                >
                  <option value={1}>1 Card (Direct Focus)</option>
                  <option value={3}>3 Cards (Past/Present/Future)</option>
                  <option value={10}>10 Cards (Celtic Cross)</option>
                </select>

                <button
                  onClick={handleDrawTarot}
                  disabled={loading}
                  className="px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white rounded text-xs font-semibold shadow flex items-center gap-2"
                >
                  {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Draw Spread'}
                </button>
              </div>
            </div>

            {tarotResult && (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 pt-4">
                {tarotResult.map((card, idx) => {
                  const position = card.position || tarotSpread[idx];
                  const isFlipped = tarotFlipped[idx];
                  const isReversed = card.reversed;
                  return (
                    <Card
                      key={`${card.id}-${idx}`}
                      hoverable
                      size="small"
                      className="text-center bg-gray-950/60 border-white/10 hover:border-purple-500/40 transition-all duration-300"
                      styles={{ body: { padding: '10px 8px' } }}
                    >
                      {/* Spread position label */}
                      {position && (
                        <Tag color="cyan" className="text-[9px] mb-1 block text-center">{position.name}</Tag>
                      )}

                      {/* 3D flip card — face-down back reveals to the actual card */}
                      <div className="tarot-perspective w-20 h-32 mx-auto mb-2">
                        <div className={`tarot-flip-container w-full h-full ${isFlipped ? 'flipped' : ''}`}>
                          <div
                            className="tarot-face tarot-front rounded-lg overflow-hidden"
                            dangerouslySetInnerHTML={{ __html: TAROT_CARD_BACK }}
                          />
                          <div
                            className="tarot-face tarot-back rounded-lg overflow-hidden"
                            dangerouslySetInnerHTML={{ __html: card.svg }}
                          />
                        </div>
                      </div>

                      {/* Card index + reversed indicator */}
                      <div className="flex items-center justify-center gap-1 mb-1 flex-wrap">
                        <Tag color="purple" className="text-[9px]">#{idx + 1}</Tag>
                        {isReversed && (
                          <Tag color="red" className="text-[9px]">↩ Reversed</Tag>
                        )}
                      </div>

                      <h4 className={`text-xs font-bold text-white mb-0.5 ${isReversed ? 'opacity-70 italic' : ''}`}>
                        {card.name}
                      </h4>

                      {/* Keyword tags — revealed once flipped */}
                      {isFlipped && card.keywords && card.keywords.length > 0 && (
                        <div className="flex flex-wrap gap-0.5 justify-center mb-1">
                          {card.keywords.slice(0, 3).map(kw => (
                            <span
                              key={kw}
                              className="text-[8px] px-1 py-0.5 bg-purple-900/40 text-purple-200 rounded border border-purple-500/20"
                            >
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Meaning — hidden until the card is flipped face-up */}
                      {isFlipped ? (
                        <p className="text-[10px] text-purple-300/80 italic leading-tight line-clamp-2">{card.meaning}</p>
                      ) : (
                        <p className="text-[10px] text-gray-600 italic leading-tight">Concealed…</p>
                      )}
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* I CHING CASTING */}
        {divinationSystem === 'iching' && (
          <div className="space-y-4">
            <div className="bg-gray-800/40 border border-white/5 rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-cyan-400" />
                  I Ching (Book of Changes) Cast
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Casts six lines using traditional yarrow-stalk probability distribution to reveal changing vectors.
                </p>
              </div>
              <button
                onClick={handleCastIChing}
                disabled={loading}
                className="px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white rounded text-xs font-semibold shadow flex items-center gap-2"
              >
                {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Cast Hexagram'}
              </button>
            </div>

            {ichingResult && (
              <div className="flex flex-col md:flex-row gap-6 bg-gray-950/40 p-6 rounded-xl border border-white/10">
                <div className="w-full md:w-80 flex justify-center items-center">
                  <div dangerouslySetInnerHTML={{ __html: ichingResult.svg }} className="w-full max-w-sm" />
                </div>

                <div className="flex-1 space-y-4">
                  <div>
                    <h4 className="text-md font-bold text-vajra-cyan">Primary Hexagram</h4>
                    <h5 className="text-sm font-semibold text-white mt-0.5">{ichingResult.primary.name}</h5>
                    <p className="text-xs text-gray-300 mt-1">{ichingResult.primary.meaning}</p>
                  </div>

                  {ichingResult.has_changes && (
                    <div className="pt-2 border-t border-white/5">
                      <h4 className="text-md font-bold text-vajra-purple">Relating Hexagram</h4>
                      <h5 className="text-sm font-semibold text-white mt-0.5">{ichingResult.relating.name}</h5>
                      <p className="text-xs text-gray-300 mt-1">{ichingResult.relating.meaning}</p>
                      <div className="text-[10px] bg-purple-950/40 text-purple-300 border border-purple-500/20 px-2.5 py-1 rounded mt-2.5 font-mono">
                        CHANGING LINES: {ichingResult.changing_lines.join(', ')}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* GEOMANCY SHIELD CAST */}
        {divinationSystem === 'geomancy' && (
          <div className="space-y-4">
            <div className="bg-gray-800/40 border border-white/5 rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Compass className="w-5 h-5 text-yellow-400" />
                  Geomantic Shield Chart & 12 Astrological Houses
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Casts binary line states to calculate Mothers, Daughters, Nieces, Witnesses, and the Judge.
                </p>
              </div>
              <button
                onClick={handleCastGeomancy}
                disabled={loading}
                className="px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white rounded text-xs font-semibold shadow flex items-center gap-2"
              >
                {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Cast Shield'}
              </button>
            </div>

            {geomancyResult && (
              <div className="space-y-4 pt-4">
                <div className="flex flex-col xl:flex-row gap-6">
                  <div className="bg-gray-950/40 p-4 rounded-xl border border-white/10 flex justify-center items-center flex-1">
                    <div dangerouslySetInnerHTML={{ __html: geomancyResult.svg }} className="w-full max-w-lg" />
                  </div>
                  <div className="w-full xl:w-80 bg-gray-950/60 p-4 rounded-xl border border-white/10 max-h-[400px] overflow-y-auto space-y-3">
                    <h4 className="text-xs font-bold font-mono text-gray-400 tracking-wider">RESOLVED FIGURES</h4>
                    {['Mother 1', 'Daughter 1', 'Niece 1', 'Right Witness', 'Left Witness', 'Judge'].map(key => {
                      const fig = geomancyResult.figures[key];
                      if (!fig) return null;
                      return (
                        <div key={key} className="flex justify-between items-center p-2.5 bg-white/5 border border-white/5 rounded-lg text-xs">
                          <div>
                            <span className="text-[10px] text-gray-500 font-mono block leading-none">{key.toUpperCase()}</span>
                            <span className="font-bold text-white mt-0.5 block">{fig.name} ({fig.translation})</span>
                          </div>
                          <span className="text-[10px] bg-yellow-950/40 text-yellow-300 border border-yellow-500/20 px-2 py-0.5 rounded uppercase">
                            {fig.element}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Elemental Balance Comparison */}
                {geoBalance && (
                  <div className="bg-gray-950/60 rounded-xl border border-purple-500/15 p-4">
                    <h4 className="text-xs font-bold font-mono text-gray-400 tracking-wider mb-3">
                      ELEMENTAL BALANCE — Shield vs. Sky
                    </h4>
                    <div className="grid grid-cols-4 gap-3 mb-3">
                      {['Fire','Water','Air','Earth'].map(elem => {
                        const geo = geoBalance.geomancy_elements?.[elem] || 0;
                        const west = geoBalance.western_elements?.[elem] || 0;
                        const colors: Record<string, string> = {Fire:'text-rose-400',Water:'text-blue-400',Air:'text-cyan-400',Earth:'text-amber-400'};
                        return (
                          <div key={elem} className="text-center">
                            <div className={`text-xs font-bold ${colors[elem]}`}>{elem}</div>
                            <div className="flex justify-center gap-1 text-[10px] mt-1">
                              <span className="text-yellow-400">{geo}</span>
                              <span className="text-gray-600">|</span>
                              <span className="text-purple-300">{west}</span>
                            </div>
                            <div className="text-[9px] text-gray-500">shield | sky</div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex items-center justify-between text-xs border-t border-white/5 pt-3">
                      <span className="text-gray-400">Harmony: <span className={
                        geoBalance.harmony_score > 0.7 ? 'text-green-400' :
                        geoBalance.harmony_score > 0.4 ? 'text-yellow-400' : 'text-red-400'
                      }>{Math.round(geoBalance.harmony_score * 100)}% {geoBalance.harmony_quality}</span></span>
                      <span className="text-gray-500">Judge: <span className="text-white font-bold">{geoBalance.judge?.name}</span> — {geoBalance.judge?.meaning?.slice(0,40)}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
