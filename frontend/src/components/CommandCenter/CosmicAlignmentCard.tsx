/**
 * CosmicAlignmentCard — the "COSMIC ALIGNMENT" sidebar card.
 *
 * Extracted verbatim from `components/UI/CommandCenter.jsx` (lines 662-720) as
 * part of the CommandCenter decomposition (Task 3.3, item 5). Pure
 * presentational component: props-only, zero coupling to CommandCenter state.
 *
 * Renders the planetary hour, Vedic panchang (tithi/nakshatra/yoga) and
 * Chinese lunar (zodiac/lunar date/shichen) summary. Shows a placeholder when
 * astronomical data has not yet loaded.
 *
 * @component
 */
import React from 'react';
import { Card } from 'antd';
import { Moon } from 'lucide-react';

/** Planetary-hour sub-payload from `/astrology/current`. */
interface PlanetaryHours {
  current_planetary_hour?: string;
  day_planet?: string;
}

/** Vedic panchang sub-payload. */
interface Panchang {
  tithi?: { name?: string };
  nakshatra?: { name?: string };
  yoga?: { name?: string };
}

/** Indian (Vedic) sub-payload. */
interface IndianPayload {
  panchanga?: Panchang;
}

/** Chinese lunar sub-payload. */
interface ChinesePayload {
  zodiac_animal?: string;
  lunar_date?: { month?: number; day?: number };
  shichen?: { name?: string; branch?: string };
}

/** Astrology payload from `/astrology/current`. */
export interface AstroData {
  planetary_hours?: PlanetaryHours;
  indian?: IndianPayload;
  chinese?: ChinesePayload;
}

interface CosmicAlignmentCardProps {
  /** Astrology payload from `/astrology/current`, or null while loading. */
  astroData: AstroData | null;
}

export default function CosmicAlignmentCard({ astroData }: CosmicAlignmentCardProps) {
  return (
    <Card
      title={<span className="text-white text-sm tracking-wider font-bold"><Moon className="w-4 h-4 text-cyan-400 inline mr-2" />COSMIC ALIGNMENT</span>}
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '16px' } }}
    >

      {astroData ? (
        <div className="space-y-4 text-xs">

          {/* Planetary Hour */}
          <div className="p-3 bg-yellow-950/20 border border-yellow-500/20 rounded-xl flex items-center justify-between">
            <div>
              <span className="text-[10px] text-yellow-400 font-mono tracking-wider block uppercase">PLANETARY HOUR</span>
              <span className="text-sm font-bold text-white mt-0.5 block">{astroData.planetary_hours?.current_planetary_hour} hour</span>
            </div>
            <span className="text-xs font-mono text-gray-400">Day: {astroData.planetary_hours?.day_planet}</span>
          </div>

          {/* Vedic Panchang */}
          <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-xl space-y-1.5">
            <span className="text-[10px] text-purple-400 font-mono tracking-wider block uppercase">VEDIC PANCHANG</span>
            <div className="flex justify-between">
              <span className="text-gray-400">Tithi:</span>
              <span className="text-gray-200 font-bold">{astroData.indian?.panchanga?.tithi?.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Nakshatra:</span>
              <span className="text-gray-200 font-bold">{astroData.indian?.panchanga?.nakshatra?.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Yoga:</span>
              <span className={`font-bold ${astroData.indian?.panchanga?.yoga?.name === 'Vajra' ? 'text-yellow-300 animate-pulse glow-text' : 'text-gray-200'}`}>
                {astroData.indian?.panchanga?.yoga?.name}
              </span>
            </div>
          </div>

          {/* Chinese Pillar summary */}
          <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-xl space-y-1.5">
            <span className="text-[10px] text-cyan-400 font-mono tracking-wider block uppercase">CHINESE LUNAR</span>
            <div className="flex justify-between">
              <span className="text-gray-400">Zodiac:</span>
              <span className="text-gray-200 font-bold">{astroData.chinese?.zodiac_animal} (Year)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Lunar Date:</span>
              <span className="text-gray-200 font-bold">Month {astroData.chinese?.lunar_date?.month} Day {astroData.chinese?.lunar_date?.day}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Shichen:</span>
              <span className="text-gray-200 font-bold">{astroData.chinese?.shichen?.name} ({astroData.chinese?.shichen?.branch})</span>
            </div>
          </div>

        </div>
      ) : (
        <div className="text-xs text-gray-500 italic py-2 text-center">Tuning astronomical clocks...</div>
      )}
    </Card>
  );
}
