/**
 * BodhicittaBanner — awakened heart inspiration panel.
 *
 * Displays rotating bodhicitta affirmations, the Four Immeasurables,
 * and quick-access practice buttons for generating bodhicitta blessings.
 * Polls auspicious timing to suggest the optimal practice for the current hour.
 *
 * The Four Immeasurables (Brahmaviharas):
 *   Maitri   — Loving-kindness    (may all beings have happiness)
 *   Karuna   — Compassion          (may all beings be free from suffering)
 *   Mudita   — Sympathetic Joy     (may all beings never be separated from happiness)
 *   Upeksha  — Equanimity          (may all beings abide in equanimity)
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import { Heart, Sparkles, Zap, Sun, Moon, Star, Flame, Wind, RefreshCw } from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';

const AFFIRMATIONS = [
  { text: "May all beings have happiness and the causes of happiness.", source: "Maitri — Loving-Kindness", icon: Heart, color: 'text-pink-400' },
  { text: "May all beings be free from suffering and the causes of suffering.", source: "Karuna — Compassion", icon: Flame, color: 'text-red-400' },
  { text: "May all beings never be separated from the supreme happiness which is without suffering.", source: "Mudita — Sympathetic Joy", icon: Sun, color: 'text-amber-400' },
  { text: "May all beings abide in equanimity, free from attachment and aversion.", source: "Upeksha — Equanimity", icon: Wind, color: 'text-cyan-400' },
  { text: "For as long as space endures, and for as long as living beings remain, until then may I too abide, to dispel the misery of the world.", source: "Shantideva — Bodhicaryavatara", icon: Star, color: 'text-purple-400' },
  { text: "May the precious bodhicitta arise where it has not arisen, and where it has arisen, may it never decrease but increase ever more.", source: "Bodhicitta Aspiration Prayer", icon: Sparkles, color: 'text-violet-400' },
  { text: "I take refuge until I am enlightened in the Buddha, the Dharma, and the Supreme Assembly. By the merit of practicing generosity and the other perfections, may I attain Buddhahood for the benefit of all beings.", source: "Atisha's Bodhisattva Vow", icon: Moon, color: 'text-indigo-400' },
  { text: "Just as the earth and elements serve countless beings in myriad ways, may I too become a source of benefit for all sentient beings throughout space.", source: "Shantideva — Bodhicaryavatara, Ch. 3", icon: Sun, color: 'text-emerald-400' },
  { text: "With a wish to free all beings, I shall always go for refuge to the Buddha, Dharma, and Sangha until the attainment of full enlightenment.", source: "Tibetan Bodhicitta Prayer", icon: Zap, color: 'text-orange-400' },
  { text: "Enthused by wisdom and compassion, today in the Buddha's presence I generate the mind of awakening for the benefit of all beings.", source: "Bodhisattva Vow Ceremony", icon: Sparkles, color: 'text-rose-400' },
];

const FOUR_IMMEASURABLES = [
  { name: 'Maitri', sanskrit: 'r^@j]_', english: 'Loving-Kindness', mantra: 'Om Maitri Ah Hum', wish: 'May all beings have happiness and its causes', practice: 'Generate the Four Immeasurables', color: '#ec4899' },
  { name: 'Karuna', sanskrit: 'j]j_', english: 'Compassion', mantra: 'Om Mani Padme Hum', wish: 'May all beings be free from suffering and its causes', practice: 'Generate the Four Immeasurables', color: '#ef4444' },
  { name: 'Mudita', sanskrit: 'r^@]_', english: 'Sympathetic Joy', mantra: 'Om Mudita Ah Hum', wish: 'May all beings never be separated from supreme happiness', practice: 'Generate the Four Immeasurables', color: '#f59e0b' },
  { name: 'Upeksha', sanskrit: '%_', english: 'Equanimity', mantra: 'Om Upeksha Ah Hum', wish: 'May all beings abide in equanimity, free from bias', practice: 'Generate the Four Immeasurables', color: '#06b6d4' },
];

export { AFFIRMATIONS, FOUR_IMMEASURABLES };

export default function BodhicittaBanner() {
  const [affIndex, setAffIndex] = useState(0);
  const [timing, setTiming] = useState(null);

  useEffect(() => {
    // Rotate affirmations every 15 seconds
    const interval = setInterval(() => {
      setAffIndex(prev => (prev + 1) % AFFIRMATIONS.length);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Check timing for bodhicitta practices
    const checkTiming = async () => {
      try {
        const res = await fetch(`/api/v1/operator/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_name: 'check_auspicious_timing', arguments: { genre: 'compassion' } }),
        });
        if (res.ok) setTiming(await res.json());
      } catch {}
    };
    checkTiming();
  }, []);

  const aff = AFFIRMATIONS[affIndex];
  const AffIcon = aff.icon;

  const handleQuickBlessing = (practice) => {
    audioFeedback.playTelemetry();
    window.dispatchEvent(new CustomEvent('vajra:quick-command', {
      detail: { command: `Run the ${practice} practice now` }
    }));
  };

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-pink-950/40 via-purple-950/30 to-rose-950/30 border border-pink-500/15 shadow-xl">
      {/* Ambient glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-pink-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-500/5 rounded-full blur-2xl" />

      <div className="relative p-5 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center shadow-[0_0_15px_rgba(236,72,153,0.3)]">
              <Heart className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-pink-200">Bodhicitta · 菩提心</h3>
              <p className="text-[10px] text-slate-400">The Awakened Heart of Compassion</p>
            </div>
          </div>
          {timing?.quality && (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-mono ${
              timing.quality === 'excellent' ? 'border-emerald-500/30 text-emerald-400' :
              timing.quality === 'good' ? 'border-cyan-500/30 text-cyan-400' :
              'border-purple-500/30 text-purple-400'
            }`}>
              {timing.planetary_hour} hour · {timing.quality}
            </span>
          )}
        </div>

        {/* Rotating Affirmation */}
        <div className="bg-black/30 rounded-xl border border-pink-500/10 p-4 transition-all duration-700">
          <div className="flex items-start gap-3">
            <div className={`flex-shrink-0 w-8 h-8 rounded-full bg-black/40 border flex items-center justify-center ${aff.color.replace('text-', 'border-')}/30`}>
              <AffIcon className={`w-4 h-4 ${aff.color}`} />
            </div>
            <div className="flex-1">
              <p className="text-sm text-white leading-relaxed italic font-serif">
                "{aff.text}"
              </p>
              <p className="text-[10px] text-slate-500 mt-1.5 font-mono">
                — {aff.source}
              </p>
            </div>
          </div>
        </div>

        {/* Four Immeasurables */}
        <div className="grid grid-cols-4 gap-1.5">
          {FOUR_IMMEASURABLES.map((im) => (
            <div
              key={im.name}
              className="flex flex-col items-center gap-1 p-2 rounded-lg bg-black/20 border border-white/5 hover:border-pink-500/20 transition-all cursor-pointer group"
              title={`${im.english}: ${im.wish}\n${im.mantra}`}
              onClick={() => handleQuickBlessing(im.practice)}
            >
              <span className="text-lg group-hover:scale-110 transition-transform">
                {im.name === 'Maitri' && '💗'}
                {im.name === 'Karuna' && '💖'}
                {im.name === 'Mudita' && '💛'}
                {im.name === 'Upeksha' && '💙'}
              </span>
              <span className="text-[9px] font-bold text-slate-300">{im.name}</span>
              <span className="text-[7px] text-slate-600 hidden sm:block">{im.english}</span>
              <span className="text-[7px] font-mono opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: im.color }}>{im.mantra}</span>
            </div>
          ))}
        </div>

        {/* Quick Practice Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleQuickBlessing('Bodhicitta Awakening — The Four Immeasurables')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-pink-600/20 hover:bg-pink-600/40 border border-pink-500/20 text-xs text-pink-300 font-medium transition-all"
          >
            <Heart className="w-3 h-3" />
            Bodhicitta Blessing
          </button>
          <button
            onClick={() => handleQuickBlessing('Vajra Energy — Unstoppable Drive & Power')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-600/20 hover:bg-orange-600/40 border border-orange-500/20 text-xs text-orange-300 font-medium transition-all"
          >
            <Zap className="w-3 h-3" />
            Energy & Drive
          </button>
          <button
            onClick={() => handleQuickBlessing('Heart Sutra — Emptiness Is Love')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/20 text-xs text-indigo-300 font-medium transition-all"
          >
            <Star className="w-3 h-3" />
            Heart Sutra
          </button>
        </div>
      </div>
    </div>
  );
}
