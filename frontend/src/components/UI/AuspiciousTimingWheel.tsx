/**
 * Auspicious Timing Wheel — 24-Hour Planetary Mandala & Practice Window Indicator
 *
 * Interactive polar clock rendering:
 * - 24 planetary hour sectors (12 day + 12 night) in Chaldean sequence.
 * - Active planetary hour highlighted with glowing radial pulse.
 * - Moon phase, tithi, and nakshatra middle ring.
 * - Center hub with current ruler, element, and Saka Dawa merit multipliers.
 * - Interactive Practice Genre filter highlighting upcoming green windows.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Compass,
  Moon,
  Sun,
  Sparkles,
  Clock,
  RefreshCw,
  Info,
  Shield,
  Heart,
  Flame,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import { Card, Tag, Button, Space, Segmented, Tooltip, Row, Col } from 'antd';
import { apiUrl } from '../../utils/api';
import { audioFeedback } from '../../utils/audioFeedback';
import {
  HourlySlice,
  TimingWheelResponse,
  PLANET_COLORS,
  PLANET_SYMBOLS,
  GENRE_COLORS,
  describeWedge,
  polarToCartesian,
  formatHourTime,
} from './timingWheelHelpers';

interface Props {
  className?: string;
  onSelectGenre?: (genre: string) => void;
  compact?: boolean;
  initialData?: TimingWheelResponse | null;
}

const GENRE_LIST = [
  { label: 'All', value: 'all' },
  { label: 'Healing', value: 'healing' },
  { label: 'Wisdom', value: 'wisdom' },
  { label: 'Purify', value: 'purification' },
  { label: 'Compassion', value: 'compassion' },
  { label: 'Protection', value: 'protection' },
  { label: 'Prosperity', value: 'prosperity' },
  { label: 'Victory', value: 'victory' },
  { label: 'Creativity', value: 'creativity' },
];

export default function AuspiciousTimingWheel({
  className = '',
  onSelectGenre,
  compact = false,
  initialData = null,
}: Props): React.ReactElement {
  const [data, setData] = useState<TimingWheelResponse | null>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedGenre, setSelectedGenre] = useState<string>('all');
  const [hoveredSlice, setHoveredSlice] = useState<HourlySlice | null>(null);
  const [pinnedSlice, setPinnedSlice] = useState<HourlySlice | null>(null);

  const fetchTimingWheel = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl('/astrology/timing-wheel'));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: TimingWheelResponse = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!initialData) {
      fetchTimingWheel();
    }
  }, [fetchTimingWheel, initialData]);

  const currentSlice = useMemo(
    () => data?.hourly_slices.find((s) => s.is_current) || null,
    [data],
  );

  const activeInspectSlice = pinnedSlice || hoveredSlice || currentSlice;

  // Geometry dimensions
  const size = compact ? 280 : 380;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = size / 2 - 16;
  const innerR = size / 2 - (compact ? 52 : 68);
  const moonOuterR = innerR - 4;
  const moonInnerR = innerR - (compact ? 24 : 32);
  const hubRadius = moonInnerR - 4;

  const currentGenreWindow = useMemo(() => {
    if (!data || selectedGenre === 'all') return null;
    return data.genre_windows?.[selectedGenre] || null;
  }, [data, selectedGenre]);

  return (
    <Card
      size="small"
      className={`bg-gray-950/80 border-amber-500/20 backdrop-blur shadow-2xl rounded-2xl overflow-hidden ${className}`}
      styles={{ body: { padding: compact ? '12px' : '18px' } }}
      title={
        <div className="flex items-center justify-between">
          <Space size={8}>
            <Compass className="w-4 h-4 text-amber-400 animate-spin-slow" />
            <span className="text-amber-300 font-mono text-xs tracking-widest uppercase font-semibold">
              Auspicious Timing Wheel
            </span>
          </Space>
          <Space orientation="horizontal" size={6}>
            {data?.saka_dawa?.is_saka_dawa && (
              <Tag color="gold" className="font-mono text-[10px] m-0 border-amber-400/40">
                <Sparkles className="w-3 h-3 inline mr-1" />
                Saka Dawa ×{data.saka_dawa.multiplier?.toLocaleString()}
              </Tag>
            )}
            <Button
              type="text"
              size="small"
              icon={<RefreshCw className={`w-3.5 h-3.5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />}
              onClick={() => {
                audioFeedback.playClick();
                fetchTimingWheel();
              }}
              title="Refresh Timing"
            />
          </Space>
        </div>
      }
    >
      {/* Genre Filter Bar */}
      <div className="mb-3">
        <Segmented
          size="small"
          options={GENRE_LIST}
          value={selectedGenre}
          onChange={(val) => {
            setSelectedGenre(val as string);
            audioFeedback.playTabChange();
            if (onSelectGenre && val !== 'all') onSelectGenre(val as string);
          }}
          block
          className="bg-black/50 border border-white/5 text-[11px] font-mono"
        />
      </div>

      <div className="flex flex-col lg:flex-row items-center justify-center gap-6">
        {/* Polar Clock SVG */}
        <div className="relative flex items-center justify-center select-none" style={{ width: size, height: size }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
            <defs>
              <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#d97706" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#000000" stopOpacity="0.8" />
              </radialGradient>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Background disc */}
            <circle cx={cx} cy={cy} r={outerR + 4} fill="#090d16" stroke="rgba(245, 158, 11, 0.15)" strokeWidth="1.5" />

            {/* 24 Planetary Hour Wedges */}
            {data?.hourly_slices.map((slice, i) => {
              const startAngle = i * 15;
              const endAngle = (i + 1) * 15;
              const midAngle = startAngle + 7.5;
              const isSelected = activeInspectSlice?.index === slice.index;
              const isCurrent = slice.is_current;

              // Genre affinity filtering
              let opacity = 0.85;
              let strokeColor = 'rgba(255,255,255,0.08)';
              let strokeWidth = 1;

              if (selectedGenre !== 'all') {
                const aff = slice.affinities?.[selectedGenre];
                if (aff === 'favorable') {
                  opacity = 1.0;
                  strokeColor = GENRE_COLORS[selectedGenre] || '#10B981';
                  strokeWidth = 2;
                } else if (aff === 'neutral') {
                  opacity = 0.45;
                } else {
                  opacity = 0.15;
                }
              }

              if (isCurrent) {
                strokeColor = '#F59E0B';
                strokeWidth = 2.5;
                opacity = 1.0;
              }

              if (isSelected) {
                strokeWidth = 2.5;
                strokeColor = '#38BDF8';
              }

              const pathData = describeWedge(cx, cy, innerR, outerR, startAngle, endAngle);
              const symbolPos = polarToCartesian(cx, cy, (innerR + outerR) / 2, midAngle);
              const planetColor = PLANET_COLORS[slice.ruler] || '#FFFFFF';

              return (
                <g
                  key={slice.index}
                  className="cursor-pointer transition-all duration-300"
                  onMouseEnter={() => setHoveredSlice(slice)}
                  onMouseLeave={() => setHoveredSlice(null)}
                  onClick={() => {
                    audioFeedback.playClick();
                    setPinnedSlice(pinnedSlice?.index === slice.index ? null : slice);
                  }}
                >
                  <path
                    d={pathData}
                    fill={planetColor}
                    fillOpacity={opacity * 0.35}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    filter={isCurrent ? 'url(#glow)' : undefined}
                  />
                  {/* Planet symbol glyph */}
                  <text
                    x={symbolPos.x}
                    y={symbolPos.y}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill={planetColor}
                    fontSize={compact ? 10 : 12}
                    fontWeight="bold"
                    opacity={opacity}
                  >
                    {PLANET_SYMBOLS[slice.ruler] || slice.ruler[0]}
                  </text>
                </g>
              );
            })}

            {/* Middle Moon & Tithi Track */}
            <circle cx={cx} cy={cy} r={moonOuterR} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
            <circle cx={cx} cy={cy} r={moonInnerR} fill="#0d1322" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
            
            {/* Center Hub */}
            <circle cx={cx} cy={cy} r={hubRadius} fill="url(#hubGlow)" stroke="rgba(245, 158, 11, 0.3)" strokeWidth="1.5" />

            {/* Center Content */}
            <text x={cx} y={cy - 22} textAnchor="middle" fontSize={compact ? 18 : 24} fill="#F59E0B">
              {data?.moon?.glyph || '🌕'}
            </text>
            <text
              x={cx}
              y={cy - 2}
              textAnchor="middle"
              fontSize={compact ? 11 : 13}
              fontWeight="bold"
              fill={activeInspectSlice ? PLANET_COLORS[activeInspectSlice.ruler] || '#F3F4F6' : '#F3F4F6'}
              className="font-mono"
            >
              {activeInspectSlice ? `${activeInspectSlice.ruler} Hour` : 'Planetary Hour'}
            </text>
            <text x={cx} y={cy + 16} textAnchor="middle" fontSize={compact ? 9 : 10} fill="#9CA3AF" className="font-mono">
              {activeInspectSlice ? `${activeInspectSlice.period.toUpperCase()} #${activeInspectSlice.hour_number}` : ''}
            </text>
            <text x={cx} y={cy + 30} textAnchor="middle" fontSize={compact ? 8 : 9} fill="#D97706" className="font-mono">
              {activeInspectSlice ? `${formatHourTime(activeInspectSlice.start_time)} - ${formatHourTime(activeInspectSlice.end_time)}` : ''}
            </text>
          </svg>
        </div>

        {/* Informational Panel & Transmutation guidance */}
        <div className="flex-1 w-full space-y-3">
          {/* Current Hour / Inspected Hour Summary */}
          {activeInspectSlice && (
            <div className="bg-black/40 border border-white/5 rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="text-lg"
                    style={{ color: PLANET_COLORS[activeInspectSlice.ruler] || '#FFD700' }}
                  >
                    {PLANET_SYMBOLS[activeInspectSlice.ruler] || '☉'}
                  </span>
                  <span className="font-semibold text-gray-200 text-sm">
                    {activeInspectSlice.ruler} Planetary Hour
                  </span>
                  {activeInspectSlice.is_current && (
                    <Tag color="success" className="font-mono text-[9px] uppercase">Active Now</Tag>
                  )}
                </div>
                <span className="text-xs font-mono text-gray-400">
                  {formatHourTime(activeInspectSlice.start_time)} – {formatHourTime(activeInspectSlice.end_time)}
                </span>
              </div>

              {/* Moon & Nakshatra detail */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono text-gray-300 pt-1 border-t border-white/5">
                <div>
                  <span className="text-gray-500">Tithi: </span>
                  <span>{data?.moon?.tithi || 'Shukla'}</span>
                </div>
                <div>
                  <span className="text-gray-500">Nakshatra: </span>
                  <span title={data?.moon?.nakshatra_quality}>{data?.moon?.nakshatra || 'Pushya'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Genre Assessment / Transmutation Card */}
          {selectedGenre !== 'all' && currentGenreWindow && (
            <div
              className="rounded-xl p-3.5 border text-xs space-y-2 transition-all"
              style={{
                backgroundColor: currentGenreWindow.quality === 'excellent' || currentGenreWindow.quality === 'good'
                  ? 'rgba(16, 185, 129, 0.08)'
                  : 'rgba(245, 158, 11, 0.08)',
                borderColor: currentGenreWindow.quality === 'excellent' || currentGenreWindow.quality === 'good'
                  ? 'rgba(16, 185, 129, 0.3)'
                  : 'rgba(245, 158, 11, 0.3)',
              }}
            >
              <div className="flex items-center justify-between">
                <Space size={6}>
                  {currentGenreWindow.quality === 'excellent' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  ) : currentGenreWindow.quality === 'good' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  )}
                  <span className="font-semibold capitalize text-gray-200">
                    {selectedGenre} Practice Window:{' '}
                    <span
                      className={
                        currentGenreWindow.quality === 'excellent'
                          ? 'text-emerald-400'
                          : currentGenreWindow.quality === 'good'
                          ? 'text-emerald-400'
                          : 'text-amber-400'
                      }
                    >
                      {currentGenreWindow.quality.toUpperCase()}
                    </span>
                  </span>
                </Space>
                {currentGenreWindow.wait_minutes > 0 && (
                  <span className="text-[10px] font-mono text-gray-400">
                    Next optimal in ~{currentGenreWindow.wait_minutes}m ({currentGenreWindow.next_favorable_hour})
                  </span>
                )}
              </div>

              <p className="text-gray-300 leading-relaxed m-0 text-[11px]">
                {currentGenreWindow.message}
              </p>

              {currentGenreWindow.transmutation && (
                <div className="pt-2 border-t border-white/5 space-y-1">
                  <div className="text-amber-400 text-[10px] font-semibold flex items-center gap-1">
                    <Flame className="w-3 h-3" /> Transmutation Guidance:
                  </div>
                  <div className="text-gray-300 text-[11px] italic">
                    {currentGenreWindow.transmutation}
                  </div>
                  {currentGenreWindow.transmutation_mantra && (
                    <div className="text-amber-300 font-mono text-[10px] bg-amber-950/40 p-1.5 rounded border border-amber-500/20">
                      Mantra: {currentGenreWindow.transmutation_mantra}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Upcoming Green Windows List */}
          {selectedGenre !== 'all' && data?.next_optimal_windows?.[selectedGenre] && (
            <div className="bg-black/30 border border-white/5 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between text-[11px] text-gray-400 font-mono">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3 h-3 text-emerald-400" /> Upcoming Green Hours ({selectedGenre})
                </span>
                <span className="text-[10px]">{data.next_optimal_windows[selectedGenre].length} windows today</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.next_optimal_windows[selectedGenre].slice(0, 6).map((win, idx) => (
                  <Tag
                    key={idx}
                    color={win.is_current ? 'success' : 'default'}
                    className="font-mono text-[10px] m-0 border border-white/10"
                  >
                    {win.period === 'day' ? '☀️' : '🌙'} {win.ruler}{' '}
                    <span className="text-gray-400">({formatHourTime(win.start_time)})</span>
                  </Tag>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
