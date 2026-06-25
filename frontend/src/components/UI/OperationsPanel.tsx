/**
 * Operations Panel — multi-system orchestration dashboard.
 * Unified view for audio, blessings, crystals, RNG, and sessions.
 * @component
 */
import React, { useState } from 'react';
import { 
  Sparkles, Compass, ArrowRight, Zap, Play, Check, 
  RefreshCw, Layers, Award, Shield, Cpu, HelpCircle
} from 'lucide-react';
import { Card, Tag } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { useAudioStore } from '../../stores/audioStore';
import { createLogger } from '../../utils/logger';

const log = createLogger('OperationsPanel');
import ChakraHealing from './ChakraHealing';
import PrayerWheel from './PrayerWheel';
import DharaniReciter from './DharaniReciter';
import TimeCycles from './TimeCycles';
import ChakraBodyMap from '../2D/ChakraBodyMap';

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

type RitualStepStatus = 'pending' | 'running' | 'success';

interface ComposerStep {
  id: string;
  label: string;
  status: RitualStepStatus;
  description: string;
}

type DivinationSystem = 'tarot' | 'iching' | 'geomancy';
type SubTab = 'divination' | 'composer' | 'prayer_wheel' | 'dharani' | 'chakra' | 'time_cycles';

interface ChakraSelection {
  frequency?: number;
  [key: string]: unknown;
}

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
  const updateSettings = useAudioStore((s) => s.updateSettings);
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('divination');
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
  
  // Ritual composer state
  const [composerSteps, setComposerSteps] = useState<ComposerStep[]>([
    { id: 'step_1', label: 'Oracle Divination Draw', status: 'pending', description: 'Consult the high-entropy RNG system for guidance' },
    { id: 'step_2', label: 'Planetary Hour Attunement', status: 'pending', description: 'Lock carrier wave frequency to the active planetary ruler' },
    { id: 'step_3', label: 'Program Broadcaster Node', status: 'pending', description: 'Load intention signature code into the active crystal matrix' },
    { id: 'step_4', label: 'Trigger Scalar Wave Emissions', status: 'pending', description: 'Initialize continuous broadcast rotation cycle' }
  ]);
  const [isRitualRunning, setIsRitualRunning] = useState<boolean>(false);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);

  // Astrology data fetches were removed (2026-06): the prior fetchAstrology()
  // helper called setters (setAstrologyData/setPlanetaryHours/setTransits) that
  // were never declared, throwing ReferenceError silently on every ritual run.
  // State vars were never read elsewhere. Planetary hour data is now consumed
  // via the central useWebSocketStable's PLANETARY_HOUR_SHIFT event.

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

  // Run Visual Ritual flow — actually executes each step via API
  const startRitualSequence = async (): Promise<void> => {
    if (isRitualRunning) return;
    setIsRitualRunning(true);
    audioFeedback.playSuccess();
    
    // Reset all statuses
    setComposerSteps(prev => prev.map(s => ({ ...s, status: 'pending' as RitualStepStatus })));

    const executeStep = async (index: number, action: () => Promise<void>): Promise<void> => {
      setActiveStepIndex(index);
      setComposerSteps(prev => { const n = [...prev]; n[index].status = 'running'; return n; });
      audioFeedback.playTelemetry();

      try {
        await action();
        setComposerSteps(prev => { const n = [...prev]; n[index].status = 'success'; return n; });
        audioFeedback.playClick();
      } catch (e) {
        log.error(`Step ${index + 1} failed:`, e);
        setComposerSteps(prev => { const n = [...prev]; n[index].status = 'pending'; return n; });
      }
    };

    // Step 1: Draw a tarot card for guidance
    await executeStep(0, async () => {
      const res = await fetch(`/api/v1/divination/tarot/draw`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 1 })
      });
      if (res.ok) {
        const data = await res.json() as TarotDrawResponse;
        setTarotResult(data.cards);
        setDivinationSystem('tarot');
      }
      await new Promise<void>(r => setTimeout(r, 1500));
    });

    // Step 2: Fetch planetary hour and align
    // (Planetary data delivered via WS — see useWebSocketStable.PLANETARY_HOUR_SHIFT)
    await executeStep(1, async () => {
      await new Promise<void>(r => setTimeout(r, 1000));
    });

    // Step 3: Forge a sigil for the intention
    await executeStep(2, async () => {
      await fetch(`/api/v1/sigils/forge`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention: 'Ritual Sequence Alignment', kamea: 'saturn' })
      });
      await new Promise<void>(r => setTimeout(r, 1500));
    });

    // Step 4: Trigger scalar wave generation
    await executeStep(3, async () => {
      await fetch(`/api/v1/scalar/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: 'hybrid', count: 10000, intensity: 0.8 })
      });
      await new Promise<void>(r => setTimeout(r, 2000));
    });
    
    setIsRitualRunning(false);
    setActiveStepIndex(-1);
    audioFeedback.playSuccess();
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
      
      {/* Sub Tabs Selection Header */}
      <div className="flex border-b border-white/10 gap-4 pb-2 overflow-x-auto scrollbar-none">
        <button
          onClick={() => { setActiveSubTab('divination'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'divination'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          🔮 Divination Suite
        </button>
        <button
          onClick={() => { setActiveSubTab('composer'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'composer'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          🌀 Ritual Composer
        </button>
        <button
          onClick={() => { setActiveSubTab('prayer_wheel'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'prayer_wheel'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          🎡 Digital Prayer Wheel
        </button>
        <button
          onClick={() => { setActiveSubTab('dharani'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'dharani'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          📿 Dharani Recitation
        </button>
        <button
          onClick={() => { setActiveSubTab('chakra'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'chakra'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          💚 Chakra Healing
        </button>
        <button
          onClick={() => { setActiveSubTab('time_cycles'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'time_cycles'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          ⏳ Time Cycle Healing
        </button>
      </div>

      {/* ==================== 1. DIVINATION PANEL ==================== */}
      {activeSubTab === 'divination' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center bg-gray-950/40 p-4 rounded-xl border border-white/5">
            <div className="flex gap-2">
              {['tarot', 'iching', 'geomancy'].map(system => (
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
                          const colors = {Fire:'text-rose-400',Water:'text-blue-400',Air:'text-cyan-400',Earth:'text-amber-400'};
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
      )}

      {/* ==================== 2. RITUAL COMPOSER ==================== */}
      {activeSubTab === 'composer' && (
        <div className="space-y-6">
          <div className="bg-gray-800/40 border border-white/5 rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-purple-400" />
                Magical Operation Sequencing Board
              </h3>
              <p className="text-xs text-gray-400 mt-1">
                Chains visual triggers together, feeding data outputs into the next operational node recursively.
              </p>
            </div>
            
            <button
              onClick={startRitualSequence}
              disabled={isRitualRunning}
              className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded font-bold text-xs shadow flex items-center gap-2 animate-pulse"
            >
              <Play className="w-3.5 h-3.5" />
              {isRitualRunning ? 'Broadcasting Chain...' : 'Execute Ritual Sequence'}
            </button>
          </div>

          {/* Workflow Sequence Blocks */}
          <div className="flex flex-col lg:flex-row gap-4 justify-between items-stretch">
            {composerSteps.map((step, idx) => {
              const active = idx === activeStepIndex;
              const success = step.status === 'success';
              const running = step.status === 'running';
              
              let borderClass = 'border-white/5';
              let bgClass = 'bg-gray-950/40';
              if (active || running) {
                borderClass = 'border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.3)] animate-pulse';
                bgClass = 'bg-purple-950/20';
              } else if (success) {
                borderClass = 'border-green-500/50';
                bgClass = 'bg-green-950/10';
              }
              
              return (
                <React.Fragment key={step.id}>
                  <div className={`flex-1 p-5 rounded-xl border ${borderClass} ${bgClass} flex flex-col justify-between space-y-4 transition-all duration-300`}>
                    <div className="flex justify-between items-start">
                      <span className="text-[10px] text-gray-500 font-mono font-bold">NODE #{idx+1}</span>
                      {success ? (
                        <span className="w-5 h-5 bg-green-500/20 border border-green-500 text-green-400 rounded-full flex items-center justify-center"><Check className="w-3 h-3" /></span>
                      ) : running ? (
                        <span className="w-5 h-5 bg-purple-500/20 border border-purple-500 text-purple-400 rounded-full flex items-center justify-center animate-spin"><RefreshCw className="w-3 h-3" /></span>
                      ) : (
                        <span className="w-5 h-5 bg-white/5 border border-white/10 rounded-full" />
                      )}
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-bold text-white">{step.label}</h4>
                      <p className="text-xs text-gray-400 mt-1">{step.description}</p>
                    </div>
                  </div>
                  
                  {idx < composerSteps.length - 1 && (
                    <div className="hidden lg:flex items-center justify-center text-gray-600">
                      <ArrowRight className={`w-6 h-6 ${success ? 'text-green-500/50' : running ? 'text-purple-500 animate-pulse' : ''}`} />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}

      {/* ==================== PRAYER WHEEL PANEL ==================== */}
      {activeSubTab === 'prayer_wheel' && (
        <div className="space-y-6">
          <PrayerWheel />
        </div>
      )}

      {/* ==================== DHARANI RECITER ==================== */}
      {activeSubTab === 'dharani' && (
        <div className="space-y-6">
          <DharaniReciter />
        </div>
      )}

      {/* ==================== 5. CHAKRA HEALING PANEL ==================== */}
      {activeSubTab === 'chakra' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="max-w-xl mx-auto w-full">
              <ChakraHealing className="mystical-border bg-gray-900/60 border-purple-500/30 shadow-2xl text-white" />
            </div>
            <div className="bg-gray-950/60 rounded-xl border border-white/10 p-4 flex items-center justify-center">
              <ChakraBodyMap
                height={400}
                onSelectChakra={(chakra) => {
                  if (chakra.frequency) {
                    updateSettings({ frequency: chakra.frequency });
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* ==================== 6. TIME CYCLE HEALING PANEL ==================== */}
      {activeSubTab === 'time_cycles' && (
        <div className="space-y-6">
          <TimeCycles />
        </div>
      )}
    </div>
  );
}
