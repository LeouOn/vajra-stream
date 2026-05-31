import React, { useMemo } from 'react';
import { Sparkles, Sun, Moon, Star, Compass } from 'lucide-react';

const SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];

const RULING_HOUSES = {
  sun: 'Self · vitality · purpose',
  moon: 'Emotions · home · inner world',
  mercury: 'Communication · mind · travel',
  venus: 'Love · beauty · values',
  mars: 'Action · drive · courage',
  jupiter: 'Growth · luck · wisdom',
  saturn: 'Discipline · limits · structure',
};

const TRANSIT_ADVICE = {
  conjunction: { brief: 'intense focus', advice: 'Channel this concentrated energy into a single important task today.' },
  trine: { brief: 'flowing harmony', advice: 'Today favors creative work and collaboration. Let things unfold naturally.' },
  sextile: { brief: 'subtle opportunity', advice: 'Small efforts yield big results now. Reach out, make a connection.' },
  square: { brief: 'productive tension', advice: 'Friction points reveal where growth is needed. Meet the challenge with patience.' },
  opposition: { brief: 'mirror moment', advice: 'Relationships and balance are highlighted. Seek compromise, not victory.' },
};

function generateHoroscope(astrologyData) {
  if (!astrologyData) return null;

  const western = astrologyData.western || {};
  const positions = western.positions || {};
  const aspects = western.aspects || [];
  const elements = western.elements || {};
  const panchanga = astrologyData.indian?.panchanga || {};
  const chinese = astrologyData.chinese || {};
  const planetaryHour = astrologyData.planetary_hours?.current_planetary_hour || 'Unknown';

  const sunSign = positions.sun?.sign || 'Aries';
  const moonSign = positions.moon?.sign || 'Aries';
  const ascSign = positions.ascendant?.sign || 'Aries';
  const moonPhase = astrologyData.moon_phase?.phase_name || '';
  const topAspects = (aspects || []).slice(0, 3);
  const domElem = western.dominant_element || 'Fire';
  const tithi = panchanga.tithi?.name || '';
  const nakshatra = panchanga.nakshatra?.name || '';
  const vara = panchanga.vara?.name || '';
  const zodiacAnimal = chinese.zodiac_animal || '—';
  const solarTerm = chinese.solar_term || '';
  const themeAspect = topAspects[0];
  const themeAdvice = themeAspect ? (TRANSIT_ADVICE[themeAspect.aspect?.toLowerCase()] || TRANSIT_ADVICE.conjunction) : null;

  return {
    date: new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }),
    sunSign, moonSign, ascSign, moonPhase, planetaryHour,
    domElem, tithi, nakshatra, vara, zodiacAnimal, solarTerm,
    topAspects: topAspects.map(a => ({
      text: `${a.planet1} ${a.aspect} ${a.planet2}`,
      exactness: a.exactness,
      advice: TRANSIT_ADVICE[a.aspect?.toLowerCase()] || null,
    })),
    themeAdvice,
    focusPlanet: topAspects[0]?.planet1 || 'jupiter',
    focusHouse: RULING_HOUSES[topAspects[0]?.planet1] || RULING_HOUSES.sun,
  };
}

export default function DailyHoroscope({ astrologyData }) {
  const horoscope = useMemo(() => generateHoroscope(astrologyData), [astrologyData]);
  if (!horoscope) return null;

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-950/20 via-purple-950/20 to-indigo-950/30 border border-amber-500/15">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,theme(colors.amber.900/0.1),transparent_70%)]" />
      <div className="relative p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-amber-300 uppercase tracking-wider">Daily Cosmic Outlook</h3>
              <p className="text-[10px] text-slate-500">{horoscope.date}</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/10 border border-purple-500/20 rounded-full text-[10px] text-purple-300 font-mono">
            <Compass className="w-3 h-3" /> {horoscope.planetaryHour} hour
          </div>
        </div>

        {/* Big Three */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: 'Sun', sign: horoscope.sunSign, icon: Sun, color: 'text-amber-400', bg: 'bg-amber-500/10' },
            { label: 'Moon', sign: horoscope.moonSign, icon: Moon, color: 'text-slate-300', bg: 'bg-slate-500/10' },
            { label: 'Rising', sign: horoscope.ascSign, icon: Compass, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
          ].map(({ label, sign, icon: Icon, color, bg }) => (
            <div key={label} className={`${bg} rounded-xl border border-white/5 p-3 text-center`}>
              <Icon className={`w-4 h-4 mx-auto mb-1.5 ${color}`} />
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
              <div className="text-sm font-bold text-white mt-0.5">{sign}</div>
            </div>
          ))}
        </div>

        {/* Theme */}
        {horoscope.themeAdvice && (
          <div className="bg-white/5 rounded-xl border border-white/10 p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Star className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Today's Theme</span>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">{horoscope.themeAdvice.advice}</p>
            <p className="text-[10px] text-amber-400/70 mt-2 font-mono">
              {horoscope.topAspects[0]?.text} · {horoscope.themeAdvice.brief}
            </p>
          </div>
        )}

        {/* Active Aspects */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
          {horoscope.topAspects.map((asp, i) => (
            <div key={i} className="bg-white/5 rounded-lg border border-white/5 p-2.5">
              <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Transit {i + 1}</div>
              <div className="text-[10px] text-slate-300 font-mono capitalize mb-1">{asp.text}</div>
              <div className="w-full bg-slate-800 rounded-full h-1">
                <div className="h-1 rounded-full bg-gradient-to-r from-amber-500 to-purple-500"
                  style={{ width: `${Math.round((asp.exactness || 0.5) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>

        {/* Bottom row: tri-tradition summary */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] border-t border-white/5 pt-3">
          <div className="flex items-center gap-3">
            <span className="text-slate-500">🌙 Tithi: <span className="text-purple-300 font-medium">{horoscope.tithi}</span></span>
            <span className="text-slate-500">⭐ Nakshatra: <span className="text-cyan-300 font-medium">{horoscope.nakshatra}</span></span>
            <span className="text-slate-500">📅 Vara: <span className="text-amber-300 font-medium">{horoscope.vara}</span></span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-slate-500">🐉 <span className="text-emerald-300 font-medium">{horoscope.zodiacAnimal}</span></span>
            <span className="text-slate-500">☀️ <span className="text-yellow-300 font-medium">{horoscope.solarTerm}</span></span>
            <span className="text-slate-500">Element: <span className={`font-bold ${horoscope.domElem === 'Fire' ? 'text-rose-400' : horoscope.domElem === 'Water' ? 'text-blue-400' : horoscope.domElem === 'Air' ? 'text-cyan-400' : 'text-amber-400'}`}>{horoscope.domElem}</span></span>
            <span className="text-slate-600">{horoscope.moonPhase}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
