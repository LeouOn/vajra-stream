import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Compass, Moon, Sun, ArrowRight, Zap, Play, Check, 
  RefreshCw, Layers, Award, Shield, Cpu, HelpCircle
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import ChakraHealing from './ChakraHealing';
import PrayerWheel from './PrayerWheel';
import TimeCycles from './TimeCycles';

import { API_BASE } from '../../utils/api';

export default function OperationsPanel() {
  const [activeSubTab, setActiveSubTab] = useState('divination');
  const [divinationSystem, setDivinationSystem] = useState('tarot');
  
  // Divination state
  const [tarotDrawCount, setTarotDrawCount] = useState(3);
  const [tarotResult, setTarotResult] = useState(null);
  const [ichingResult, setIchingResult] = useState(null);
  const [geomancyResult, setGeomancyResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Astrology state
  const [astrologyData, setAstrologyData] = useState(null);
  const [planetaryHours, setPlanetaryHours] = useState(null);
  const [transits, setTransits] = useState([]);
  
  // Ritual composer state
  const [composerSteps, setComposerSteps] = useState([
    { id: 'step_1', label: 'Oracle Divination Draw', status: 'pending', description: 'Consult the high-entropy RNG system for guidance' },
    { id: 'step_2', label: 'Planetary Hour Attunement', status: 'pending', description: 'Lock carrier wave frequency to the active planetary ruler' },
    { id: 'step_3', label: 'Program Broadcaster Node', status: 'pending', description: 'Load intention signature code into the active crystal matrix' },
    { id: 'step_4', label: 'Trigger Scalar Wave Emissions', status: 'pending', description: 'Initialize continuous broadcast rotation cycle' }
  ]);
  const [isRitualRunning, setIsRitualRunning] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(-1);

  // Fetch Astrology Data on Mount
  useEffect(() => {
    fetchAstrology();
  }, []);

  const fetchAstrology = async () => {
    try {
      const currentRes = await fetch(`${API_BASE}/astrology/current`);
      if (currentRes.ok) {
        const d = await currentRes.json();
        setAstrologyData(d.astrology);
      }
      
      const hoursRes = await fetch(`${API_BASE}/astrology/planetary-hours`);
      if (hoursRes.ok) {
        const d = await hoursRes.json();
        setPlanetaryHours(d);
      }

      const transitsRes = await fetch(`${API_BASE}/astrology/transits`);
      if (transitsRes.ok) {
        const d = await transitsRes.json();
        setTransits(d.transits || []);
      }
    } catch (e) {
      console.error("Astrology fetch error:", e);
    }
  };

  const handleDrawTarot = async () => {
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch(`${API_BASE}/divination/tarot/draw`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: tarotDrawCount })
      });
      if (response.ok) {
        const data = await response.json();
        setTarotResult(data.cards);
        audioFeedback.playSuccess();
      }
    } catch (e) {
      console.error(e);
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  const handleCastIChing = async () => {
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch(`${API_BASE}/divination/iching/cast`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        setIchingResult(data.cast);
        audioFeedback.playSuccess();
      }
    } catch (e) {
      console.error(e);
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  const handleCastGeomancy = async () => {
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch(`${API_BASE}/divination/geomancy/shield`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        setGeomancyResult(data.chart);
        audioFeedback.playSuccess();
      }
    } catch (e) {
      console.error(e);
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  // Run Visual Ritual flow — actually executes each step via API
  const startRitualSequence = async () => {
    if (isRitualRunning) return;
    setIsRitualRunning(true);
    audioFeedback.playSuccess();
    
    // Reset all statuses
    setComposerSteps(prev => prev.map(s => ({ ...s, status: 'pending' })));

    const executeStep = async (index, action) => {
      setActiveStepIndex(index);
      setComposerSteps(prev => { const n = [...prev]; n[index].status = 'running'; return n; });
      audioFeedback.playTelemetry();

      try {
        await action();
        setComposerSteps(prev => { const n = [...prev]; n[index].status = 'success'; return n; });
        audioFeedback.playClick();
      } catch (e) {
        console.error(`Step ${index + 1} failed:`, e);
        setComposerSteps(prev => { const n = [...prev]; n[index].status = 'pending'; return n; });
      }
    };

    // Step 1: Draw a tarot card for guidance
    await executeStep(0, async () => {
      const res = await fetch(`${API_BASE}/divination/tarot/draw`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 1 })
      });
      if (res.ok) {
        const data = await res.json();
        setTarotResult(data.cards);
        setDivinationSystem('tarot');
      }
      await new Promise(r => setTimeout(r, 1500));
    });

    // Step 2: Fetch planetary hour and align
    await executeStep(1, async () => {
      await fetchAstrology();
      await new Promise(r => setTimeout(r, 1000));
    });

    // Step 3: Forge a sigil for the intention
    await executeStep(2, async () => {
      await fetch(`${API_BASE}/sigils/forge`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention: 'Ritual Sequence Alignment', kamea: 'saturn' })
      });
      await new Promise(r => setTimeout(r, 1500));
    });

    // Step 4: Trigger scalar wave generation
    await executeStep(3, async () => {
      await fetch(`${API_BASE}/scalar/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: 'hybrid', count: 10000, intensity: 0.8 })
      });
      await new Promise(r => setTimeout(r, 2000));
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
          onClick={() => { setActiveSubTab('astrology'); audioFeedback.playClick(); }}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeSubTab === 'astrology'
              ? 'border-vajra-cyan text-vajra-cyan'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          🪐 Astrology & Transits
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
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 pt-4">
                  {tarotResult.map((card, idx) => (
                    <div key={card.id} className="flex flex-col items-center bg-gray-950/40 p-3 rounded-xl border border-white/10 shadow-2xl hover:border-purple-500/20 transition-all duration-300 transform hover:-translate-y-1">
                      <div className="w-32 h-48 flex items-center justify-center relative overflow-hidden rounded-lg">
                        <div dangerouslySetInnerHTML={{ __html: card.svg }} className="divination-card-container w-full h-full flex justify-center" />
                      </div>
                      <div className="text-center mt-2 space-y-0.5">
                        <span className="text-[10px] font-mono font-bold text-gray-500">CARD #{idx+1}</span>
                        <h4 className="text-xs font-bold text-white">{card.name}</h4>
                        <p className="text-[10px] text-purple-300 italic leading-tight">{card.meaning}</p>
                      </div>
                    </div>
                  ))}
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
                <div className="flex flex-col xl:flex-row gap-6 pt-4">
                  {/* Visual Shield Chart SVG */}
                  <div className="bg-gray-950/40 p-4 rounded-xl border border-white/10 flex justify-center items-center flex-1">
                    <div dangerouslySetInnerHTML={{ __html: geomancyResult.svg }} className="w-full max-w-lg" />
                  </div>

                  {/* Interpretive sidebar figures */}
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
              )}
            </div>
          )}
        </div>
      )}

      {/* ==================== 2. ASTROLOGY PANEL ==================== */}
      {activeSubTab === 'astrology' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Active Planetary Hour */}
          <div className="bg-gray-950/40 p-5 rounded-xl border border-white/10 flex flex-col justify-between space-y-4">
            <div>
              <h3 className="text-md font-bold text-white flex items-center gap-2">
                <Sun className="w-5 h-5 text-yellow-500" />
                Planetary Hour Timeline
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Traditional Chaldean order hourly energetic rulers.</p>
            </div>

            {planetaryHours ? (
              <div className="space-y-4">
                <div className="p-4 bg-yellow-950/20 border border-yellow-500/20 rounded-xl flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-yellow-400 font-mono tracking-widest block uppercase">CURRENT HOUR RULER</span>
                    <span className="text-xl font-bold text-white mt-1 block">{planetaryHours.current_planetary_hour}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-gray-400 font-mono block">DAY OF THE WEEK</span>
                    <span className="text-sm font-semibold text-gray-300 block">{planetaryHours.day_of_week} (Day of {planetaryHours.day_planet})</span>
                  </div>
                </div>

                <div className="text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Ruler Influence:</span>
                    <span className="text-gray-200 font-medium">{planetaryHours.description}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Local Hour Index:</span>
                    <span className="text-gray-200 font-mono">{planetaryHours.hour_of_day}:00</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic">Calculating planetary hours ephemeris...</div>
            )}
          </div>

          {/* Lunar Phase Status */}
          <div className="bg-gray-950/40 p-5 rounded-xl border border-white/10 space-y-4">
            <div>
              <h3 className="text-md font-bold text-white flex items-center gap-2">
                <Moon className="w-5 h-5 text-cyan-400" />
                Lunar Coherence Ring
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Lunar phase aspecting, nakshatras and daily tides.</p>
            </div>

            {astrologyData?.moon_phase ? (
              <div className="flex items-center gap-6">
                <div className="relative w-24 h-24 rounded-full bg-black/60 border border-white/5 flex items-center justify-center overflow-hidden">
                  {/* Neon moon crescent simulation using CSS borders */}
                  <div className="absolute w-20 h-20 rounded-full border-r-4 border-cyan-400/30 animate-pulse" />
                  <div className="absolute w-16 h-16 rounded-full border-r-4 border-cyan-300" />
                  <div className="text-xs text-cyan-300 font-bold select-none">{Math.round(astrologyData.moon_phase.illumination)}%</div>
                </div>

                <div className="flex-1 space-y-1.5 text-xs">
                  <div>
                    <span className="text-gray-500 block leading-none">PHASE NAME</span>
                    <span className="font-bold text-white mt-0.5 block">{astrologyData.moon_phase.phase_name}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block leading-none">ANGLE DEGREE</span>
                    <span className="font-mono text-gray-300 block">{astrologyData.moon_phase.phase_angle.toFixed(1)}°</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic">Calculating lunar illumination cycle...</div>
            )}
          </div>

          {/* Current Transits aspects */}
          <div className="bg-gray-950/40 p-5 rounded-xl border border-white/10 lg:col-span-2 space-y-4">
            <h3 className="text-md font-bold text-white">Active Planetary Transits & Aspect Triggers</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {transits.length > 0 ? (
                transits.map((transit, idx) => (
                  <div key={idx} className="p-3 bg-white/5 border border-white/5 rounded-lg flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-purple-300">{transit.planet}</span>
                        <span className="text-[9px] bg-purple-950 text-purple-400 px-1.5 py-0.2 rounded border border-purple-500/20 uppercase font-mono">{transit.type}</span>
                      </div>
                      <p className="text-[10px] text-gray-400 mt-2">{transit.influence}</p>
                    </div>
                    {transit.aspecting_planet && (
                      <span className="text-[9px] font-mono text-cyan-400 mt-2 block">Aspect: {transit.aspecting_planet} (Orb: {transit.orb}°)</span>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-500 italic col-span-3 text-center py-6">No transit aspects retrieved. Running ephemeris sync.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ==================== 3. RITUAL COMPOSER ==================== */}
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

      {/* ==================== 4. PRAYER WHEEL PANEL ==================== */}
      {activeSubTab === 'prayer_wheel' && (
        <div className="space-y-6">
          <PrayerWheel />
        </div>
      )}

      {/* ==================== 5. CHAKRA HEALING PANEL ==================== */}
      {activeSubTab === 'chakra' && (
        <div className="space-y-6">
          <div className="max-w-xl mx-auto">
            <ChakraHealing className="mystical-border bg-gray-900/60 border-purple-500/30 shadow-2xl text-white" />
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
