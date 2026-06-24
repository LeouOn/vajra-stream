/**
 * Prayer Wheel — digital Tibetan prayer wheel interface.
 * Intention input, mantra selection, rotation tracking, TTS toggle,
 * frequency control, and continuous/interval mode switching.
 * @component
 */
import React, { useState, useEffect, useRef } from 'react';
import { HelpCircle, Play, RefreshCw, Award, Heart, Check, BookOpen } from 'lucide-react';
import { message } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { createLogger } from '../../utils/logger';

interface TraditionalMantra {
  mantra: string;
  deity: string;
  benefit: string;
}

interface PrayerSpinResponse {
  duration?: number;
  merit_generated?: number;
  rotations?: number;
  mantra?: string;
  [key: string]: unknown;
}

interface PrayerGenerateResponse {
  prayer: string;
  [key: string]: unknown;
}

interface SpinHistoryEntry {
  timestamp: string;
  mantra: string;
  rotations: number;
  merit: number;
  dedication: string;
}

const TRADITIONAL_MANTRAS: TraditionalMantra[] = [
  { mantra: "Om Mani Padme Hum", deity: "Chenrezig (Compassion)", benefit: "Purifies negative karma, develops infinite compassion" },
  { mantra: "Om Tare Tuttare Ture Soha", deity: "Green Tara (Protection)", benefit: "Overcomes fear, protects from obstacles and sickness" },
  { mantra: "Om Ah Ra Pa Tsa Na Dhih", deity: "Manjushri (Wisdom)", benefit: "Enhances memory, intelligence, and understanding" },
  { mantra: "Gate Gate Paragate Parasamgate Bodhi Svaha", deity: "Heart Sutra (Emptiness)", benefit: "Realization of ultimate wisdom, transcending suffering" },
  { mantra: "Tayata Om Bekanze Bekanze Maha Bekanze Radza Samudgate Soha", deity: "Medicine Buddha (Healing)", benefit: "Alleviates physical and mental illness, purifies disease" }
];

export default function PrayerWheel() {
  const [mantra, setMantra] = useState<string>("Om Mani Padme Hum");
  const [isCustom, setIsCustom] = useState<boolean>(false);
  const [customMantra, setCustomMantra] = useState<string>("");
  const [rotations, setRotations] = useState<number>(108);
  const [speed, setSpeed] = useState<number>(1.0);
  const [dedication, setDedication] = useState<string>("May all beings be happy and free from suffering");
  
  // App state
  const [isSpinning, setIsSpinning] = useState<boolean>(false);
  const [meritTotal, setMeritTotal] = useState<number>(0);
  const [rotationsTotal, setRotationsTotal] = useState<number>(0);
  const [history, setHistory] = useState<SpinHistoryEntry[]>([]);
  const [countdown, setCountdown] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  
  // Custom prayer generation state
  const [intention, setIntention] = useState<string>("");
  const [generatingPrayer, setGeneratingPrayer] = useState<boolean>(false);

  const countdownInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const log = createLogger('PrayerWheel');

  const activeMantra = isCustom ? customMantra : mantra;

  useEffect(() => {
    return () => {
      if (countdownInterval.current) clearInterval(countdownInterval.current);
    };
  }, []);

  const handleGeneratePrayer = async (): Promise<void> => {
    if (!intention.trim()) return;
    setGeneratingPrayer(true);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`/api/v1/prayer-wheel/generate-prayer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention, use_llm: true, tradition: 'universal' })
      });
      if (res.ok) {
        const data = await res.json() as PrayerGenerateResponse;
        setIsCustom(true);
        setCustomMantra(data.prayer);
        audioFeedback.playSuccess();
      } else {
        audioFeedback.playError();
      }
    } catch (e) {
      log.error(e);
      audioFeedback.playError();
      message.error('Could not generate prayer: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setGeneratingPrayer(false);
    }
  };

  const handleSpin = async (): Promise<void> => {
    if (!activeMantra.trim() || isSpinning) return;
    
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`/api/v1/prayer-wheel/spin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mantra: activeMantra,
          rotations: Number(rotations),
          speed: Number(speed)
        })
      });
      if (res.ok) {
        const data = await res.json() as PrayerSpinResponse;
        const spinDuration = data.duration || 10;
        
        setIsSpinning(true);
        setCountdown(spinDuration);
        audioFeedback.playSuccess();

        // Start local countdown animation timer
        if (countdownInterval.current) clearInterval(countdownInterval.current);
        countdownInterval.current = setInterval(() => {
          setCountdown(prev => {
            if (prev <= 1) {
              if (countdownInterval.current) clearInterval(countdownInterval.current);
              setIsSpinning(false);
              setMeritTotal(m => m + (data.merit_generated || 0));
              setRotationsTotal(r => r + (data.rotations || 0));
              setHistory(h => [
                {
                  timestamp: new Date().toLocaleTimeString(),
                  mantra: data.mantra || activeMantra,
                  rotations: data.rotations || 0,
                  merit: data.merit_generated || 0,
                  dedication: dedication || "For the welfare of all sentient beings"
                },
                ...h
              ]);
              audioFeedback.playSuccess();
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } else {
        audioFeedback.playError();
      }
    } catch (e) {
      log.error(e);
      audioFeedback.playError();
      message.error('Could not start spin: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      
      {/* Visual Wheel & Accummulations */}
      <div className="xl:col-span-2 bg-gray-950/40 p-6 rounded-xl border border-purple-500/15 flex flex-col items-center justify-between min-h-[500px]">
        <div className="w-full flex justify-between items-center border-b border-white/5 pb-3">
          <div>
            <h3 className="text-lg font-bold text-vajra-cyan glow-cyan flex items-center gap-2">
              🌀 Digital Prayer Wheel
            </h3>
            <p className="text-xs text-gray-400">Computational mantra emanation engine</p>
          </div>
          <div className="flex gap-2">
            <span className="text-[10px] bg-purple-950 text-purple-300 border border-purple-500/20 px-2 py-1 rounded font-mono">
              ROTATIONS: {rotationsTotal}
            </span>
            <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-500/20 px-2 py-1 rounded font-mono">
              MERIT: {meritTotal.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Dynamic Spinning Mandala */}
        <div className="relative my-8 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-cyan-500/5 blur-3xl" />
          
          {/* Animated Outer Ring */}
          <div 
            className={`relative w-64 h-64 rounded-full border-2 border-dashed flex items-center justify-center transition-transform duration-1000 ${
              isSpinning ? 'border-cyan-400 animate-spin' : 'border-purple-500/30'
            }`}
            style={{ animationDuration: isSpinning ? `${8 / speed}s` : '60s' }}
          >
            <div className="absolute inset-2 rounded-full border border-purple-500/20" />
            <div className="absolute inset-6 rounded-full border border-cyan-500/10 flex items-center justify-center">
              {/* Symbolic center core */}
              <div className={`w-12 h-12 rounded-full bg-black/60 border border-cyan-500/30 flex items-center justify-center ${isSpinning ? 'scale-105 border-cyan-400' : ''}`}>
                <span className="text-cyan-400 text-lg font-serif glow-text select-none">🕉</span>
              </div>
            </div>
            
            {/* Visual Sanskrit glyph proxies */}
            {[0, 60, 120, 180, 240, 300].map((deg, i) => (
              <div 
                key={i}
                className="absolute text-[10px] font-mono text-purple-300 font-bold bg-gray-950/80 border border-white/5 px-1.5 py-0.5 rounded shadow-lg"
                style={{
                  transform: `rotate(${deg}deg) translate(95px) rotate(-${deg}deg)`
                }}
              >
                {TRADITIONAL_MANTRAS[i % TRADITIONAL_MANTRAS.length].mantra.split(" ")[0]}
              </div>
            ))}
          </div>

          {/* Core HUD status overlay */}
          {isSpinning && (
            <div className="absolute bg-black/85 border border-cyan-500/40 rounded-xl px-4 py-2.5 text-center flex flex-col items-center gap-1 shadow-2xl z-10 animate-pulse">
              <span className="text-[9px] text-cyan-400 font-mono tracking-widest uppercase">EMULATING ROTATION</span>
              <span className="text-xl font-bold text-white font-mono">{countdown}s</span>
              <span className="text-[9px] text-gray-500 font-mono max-w-[120px] truncate">{activeMantra}</span>
            </div>
          )}
        </div>

        {/* Live feedback text */}
        <div className="w-full bg-black/40 border border-white/5 rounded-lg p-3 text-center text-xs">
          {isSpinning ? (
            <div className="space-y-1">
              <span className="text-cyan-300 block font-semibold">Generating stream resonance...</span>
              <span className="text-[10px] text-gray-400 block italic">"May the sound waves carry this aspiration into all realms."</span>
            </div>
          ) : (
            <span className="text-gray-500 italic">Vessel ready. Load intention and spin to generate merit.</span>
          )}
        </div>
      </div>

      {/* Control Deck */}
      <div className="space-y-6 flex flex-col">
        
        {/* Mantra & Intention Settings */}
        <div className="bg-gray-950/40 p-5 rounded-xl border border-purple-500/15 space-y-4 flex-1">
          <h4 className="text-sm font-bold text-white uppercase tracking-wider border-b border-white/5 pb-2">
            Mantra Settings
          </h4>
          
          {/* Preset Selector */}
          <div className="space-y-1.5">
            <label className="text-xs text-gray-400 block">Traditional Presets</label>
            <div className="flex gap-2">
              <button
                onClick={() => { setIsCustom(false); audioFeedback.playClick(); }}
                className={`flex-1 py-1 px-2 rounded text-[10px] font-bold uppercase transition-all ${
                  !isCustom ? 'bg-purple-900 border border-purple-500 text-white' : 'bg-white/5 text-gray-400 hover:text-white'
                }`}
              >
                Traditional
              </button>
              <button
                onClick={() => { setIsCustom(true); audioFeedback.playClick(); }}
                className={`flex-1 py-1 px-2 rounded text-[10px] font-bold uppercase transition-all ${
                  isCustom ? 'bg-purple-900 border border-purple-500 text-white' : 'bg-white/5 text-gray-400 hover:text-white'
                }`}
              >
                Custom Intention
              </button>
            </div>
          </div>

          {!isCustom ? (
            <div className="space-y-2">
              <select
                value={mantra}
                onChange={(e) => { setMantra(e.target.value); audioFeedback.playClick(); }}
                className="w-full bg-gray-900 border border-white/10 rounded px-2 py-1.5 text-xs text-white"
              >
                {TRADITIONAL_MANTRAS.map((m) => (
                  <option key={m.mantra} value={m.mantra}>{m.mantra} ({m.deity})</option>
                ))}
              </select>
              <p className="text-[10px] text-gray-400 italic bg-white/5 p-2 rounded leading-relaxed border border-white/5">
                {TRADITIONAL_MANTRAS.find(m => m.mantra === mantra)?.benefit}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={customMantra}
                onChange={(e) => setCustomMantra(e.target.value)}
                placeholder="Type your custom prayer, aspiration, or mantra here..."
                rows={3}
                className="w-full bg-gray-900 border border-white/10 rounded p-2 text-xs text-white outline-none focus:border-purple-500 transition-colors"
              />
              
              {/* LLM Prayer Generator Option */}
              <div className="bg-black/50 p-2.5 rounded border border-purple-500/10 space-y-2">
                <span className="text-[10px] font-bold text-vajra-cyan block">AI Prayer Generator</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={intention}
                    onChange={(e) => setIntention(e.target.value)}
                    placeholder="e.g. compassion, mental focus, relief"
                    className="flex-1 bg-gray-900 border border-white/10 rounded px-2 py-1 text-[10px] text-white outline-none focus:border-purple-500"
                  />
                  <button
                    onClick={handleGeneratePrayer}
                    disabled={generatingPrayer || !intention.trim()}
                    className="px-2 py-1 bg-purple-900 hover:bg-purple-800 text-white rounded text-[10px] font-semibold disabled:bg-gray-800 flex items-center gap-1"
                  >
                    {generatingPrayer ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : <BookOpen className="w-2.5 h-2.5" />}
                    Generate
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Dedication block */}
          <div className="space-y-1.5 pt-2 border-t border-white/5">
            <label className="text-xs text-gray-400 block flex items-center gap-1">
              <Heart className="w-3.5 h-3.5 text-red-400" /> Merit Dedication
            </label>
            <input
              type="text"
              value={dedication}
              onChange={(e) => setDedication(e.target.value)}
              className="w-full bg-gray-900 border border-white/10 rounded px-2.5 py-1.5 text-xs text-white outline-none focus:border-purple-500"
              placeholder="May this benefit..."
            />
          </div>

          {/* Dials & Parameters */}
          <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/5">
            <div className="space-y-1.5">
              <label className="text-[11px] text-gray-400 block">Rotations (Mala)</label>
              <select
                value={rotations}
                onChange={(e) => setRotations(Number(e.target.value))}
                className="w-full bg-gray-900 border border-white/10 rounded px-2 py-1.5 text-xs text-white"
              >
                <option value={21}>21 rotations</option>
                <option value={108}>108 rotations</option>
                <option value={1008}>1,008 rotations</option>
              </select>
            </div>
            
            <div className="space-y-1.5">
              <label className="text-[11px] text-gray-400 block">Spin Speed multiplier</label>
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="w-full bg-gray-900 border border-white/10 rounded px-2 py-1.5 text-xs text-white"
              >
                <option value={0.5}>0.5x (Slow/Stable)</option>
                <option value={1.0}>1.0x (Standard)</option>
                <option value={2.0}>2.0x (Accelerated)</option>
                <option value={5.0}>5.0x (Quantum Burst)</option>
              </select>
            </div>
          </div>

          {/* Action Trigger */}
          <button
            onClick={handleSpin}
            disabled={isSpinning || loading || (isCustom && !customMantra.trim())}
            className="w-full mt-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded font-bold text-xs shadow flex items-center justify-center gap-2 disabled:bg-gray-800 disabled:from-gray-800 disabled:to-gray-800"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {isSpinning ? 'Wheel Spinning...' : 'Spin Prayer Wheel'}
          </button>
        </div>

        {/* Merit Dedication Log */}
        <div className="bg-gray-950/40 p-4 rounded-xl border border-purple-500/15 h-[160px] flex flex-col">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block border-b border-white/5 pb-1">
            Mantra Accumulation Log
          </span>
          <div className="flex-1 overflow-y-auto mt-2 space-y-2 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
            {history.length > 0 ? (
              history.map((h, idx) => (
                <div key={idx} className="bg-white/5 border border-white/5 p-2 rounded text-[10px] flex justify-between items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <span className="text-[8px] text-gray-500 font-mono block">{h.timestamp}</span>
                    <span className="font-bold text-white truncate block">{h.mantra} ({h.rotations} spins)</span>
                    <span className="text-[9px] text-purple-300 italic block mt-0.5">Dedication: {h.dedication}</span>
                  </div>
                  <div className="text-right whitespace-nowrap">
                    <span className="text-cyan-300 font-bold font-mono">+{h.merit} Merit</span>
                  </div>
                </div>
              ))
            ) : (
              <span className="text-[10px] text-gray-500 italic block py-4 text-center">No spins logged in this session</span>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
