import React, { useState, useEffect } from 'react';
import { Clock, ArrowRight, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../../utils/api';

const SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];

const PLANET_GLYPHS = {
  sun:'☀️', moon:'🌙', mercury:'☿', venus:'♀', mars:'♂',
  jupiter:'♃', saturn:'♄', uranus:'⛢', neptune:'♆', pluto:'♇',
};

const PLANET_COLORS = {
  sun:'#fbbf24', moon:'#e2e8f0', mercury:'#94a3b8', venus:'#f472b6',
  mars:'#ef4444', jupiter:'#f59e0b', saturn:'#e2c97e',
  uranus:'#22d3ee', neptune:'#3b82f6', pluto:'#a78bfa',
};

function computeTransits(positions) {
  if (!positions) return [];
  return Object.entries(positions)
    .filter(([name]) => !['ascendant','midheaven','north_node'].includes(name))
    .map(([name, pos]) => {
      const currentSignIdx = SIGNS.indexOf(pos.sign);
      const nextSignIdx = (currentSignIdx + 1) % 12;
      const degInSign = pos.degree || 0;
      const speed = Math.abs(pos.speed || 1);
      const degRemaining = 30 - degInSign;
      const daysUntil = speed > 0 ? degRemaining / speed : 999;
      const hoursUntil = daysUntil * 24;

      return {
        name,
        glyph: PLANET_GLYPHS[name] || '●',
        color: PLANET_COLORS[name] || '#fff',
        currentSign: pos.sign,
        nextSign: SIGNS[nextSignIdx],
        degree: degInSign.toFixed(1),
        retrograde: pos.retrograde || false,
        speed: speed.toFixed(2),
        degRemaining: degRemaining.toFixed(1),
        daysUntil: Math.round(daysUntil),
        hoursUntil: Math.round(hoursUntil),
        urgency: daysUntil < 3 ? 'soon' : daysUntil < 10 ? 'medium' : 'distant',
      };
    })
    .sort((a, b) => a.daysUntil - b.daysUntil);
}

export default function TransitTimeline() {
  const [transits, setTransits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await fetch(`${API_BASE}/astrology/current?latitude=37.7749&longitude=-122.4194`);
        if (res.ok) {
          const data = await res.json();
          setTransits(computeTransits(data.astrology?.western?.positions || {}));
        }
      } catch {}
      setLoading(false);
    };
    fetch();
  }, []);

  if (loading) {
    return (
      <div className="bg-gray-900/60 rounded-xl p-4 border border-purple-500/15">
        <div className="flex items-center gap-2 text-gray-400 text-xs">
          <Clock className="w-3.5 h-3.5 animate-spin" />
          Computing transit timeline...
        </div>
      </div>
    );
  }

  if (!transits.length) {
    return null;
  }

  const soonTransits = transits.filter(t => t.urgency === 'soon');
  const nextTransit = transits[0];

  return (
    <div className="bg-gray-900/60 rounded-xl border border-purple-500/15 overflow-hidden">
      <div className="bg-gradient-to-r from-amber-900/20 to-orange-900/20 p-3 border-b border-amber-500/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wider">Transit Timeline</h3>
        </div>
        <span className="text-[10px] text-gray-500 font-mono">
          Next: {nextTransit?.glyph} → {nextTransit?.nextSign} in {nextTransit?.daysUntil}d
        </span>
      </div>

      {/* Urgent banner */}
      {soonTransits.length > 0 && (
        <div className="px-3 py-2 bg-red-950/20 border-b border-red-500/10">
          <div className="flex items-center gap-1.5 text-[10px] text-red-400">
            <AlertTriangle className="w-3 h-3" />
            {soonTransits.length} planet{soonTransits.length > 1 ? 's' : ''} changing sign{soonTransits.length > 1 ? '' : 's'} soon
          </div>
        </div>
      )}

      {/* Transit bars */}
      <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
        {transits.slice(0, 10).map((t) => (
          <div key={t.name} className="flex items-center gap-2 text-xs group">
            {/* Planet glyph */}
            <span className="text-sm w-6 text-center">{t.glyph}</span>

            {/* Current → Next */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-gray-300 font-medium capitalize">{t.name}</span>
                <span className="text-[10px] text-gray-500">{t.currentSign} {t.degree}°</span>
                <ArrowRight className="w-3 h-3 text-gray-600" />
                <span className="text-purple-300 font-medium">{t.nextSign}</span>
                {t.retrograde && <span className="text-[10px] text-red-400 font-bold">℞</span>}
              </div>

              {/* Progress bar */}
              <div className="mt-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, (t.degree / 30) * 100)}%`,
                    backgroundColor: t.color,
                    opacity: t.retrograde ? 0.5 : 0.8,
                  }}
                />
              </div>

              {/* Time remaining */}
              <div className="flex justify-between mt-0.5 text-[9px]">
                <span className="text-gray-600">{t.speed}°/day{t.retrograde ? ' (rx)' : ''}</span>
                <span className={t.urgency === 'soon' ? 'text-amber-400 font-bold' : 'text-gray-500'}>
                  {t.daysUntil}d {t.hoursUntil % 24}h
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
