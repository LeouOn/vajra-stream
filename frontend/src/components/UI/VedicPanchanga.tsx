import React from 'react';
import { Card, Row, Col, Tag, Statistic, Space, Progress, Tooltip } from 'antd';
import { Moon, Star, Sun, Activity } from 'lucide-react';

const RASHI_COLORS: Record<string, string> = {
  'Mesha': '#ef4444','Vrishabha':'#22c55e','Mithuna':'#a855f7',
  'Karka': '#e2e8f0','Simha':'#fbbf24','Kanya':'#a78bfa',
  'Tula': '#f472b6','Vrischika':'#ef4444','Dhanu':'#f59e0b',
  'Makara': '#3b82f6','Kumbha':'#06b6d4','Meena':'#6366f1',
};

const NAKSHATRA_SYMBOLS: Record<string, string> = {
  'Ashwini':'🐴','Bharani':'♈','Krittika':'🔥','Rohini':'🌹','Mrigashira':'🦌',
  'Ardra':'💧','Punarvasu':'🏹','Pushya':'🥛','Ashlesha':'🐍','Magha':'👑',
  'Purva Phalguni':'🛏️','Uttara Phalguni':'📜','Hasta':'✋','Chitra':'💎',
  'Swati':'🌬️','Vishakha':'🏆','Anuradha':'🤝','Jyeshtha':'⭐',
  'Mula':'🌱','Purva Ashadha':'🐘','Uttara Ashadha':'🐘','Shravana':'👂',
  'Dhanishta':'🥁','Shatabhisha':'💊','Purva Bhadrapada':'⚔️',
  'Uttara Bhadrapada':'🐍','Revati':'🐟',
};

interface PanchangaEntry {
  name?: string;
  paksha?: string;
  progress?: number;
  number?: number;
}

interface Panchanga {
  tithi?: PanchangaEntry;
  nakshatra?: PanchangaEntry;
  yoga?: PanchangaEntry;
  karana?: PanchangaEntry;
  vara?: PanchangaEntry;
}

interface SiderealPosition {
  rashi?: string;
  rashi_name?: string;
  degree?: number;
}

interface IndianData {
  panchanga?: Panchanga;
  sidereal_positions?: Record<string, SiderealPosition>;
  [key: string]: unknown;
}

interface VedicPanchangaProps {
  indianData?: IndianData | null;
}

interface PanchangaRowItem {
  label: string;
  value: string;
  sub?: string;
  icon: typeof Moon;
  color: string;
  symbol?: string;
}

export default function VedicPanchanga({ indianData }: VedicPanchangaProps) {
  if (!indianData) return null;
  const panchanga: Panchanga = indianData.panchanga || {};
  const positions: Record<string, SiderealPosition> = indianData.sidereal_positions || {};

  return (
    <Card
      title={<span className="text-amber-400 font-mono text-xs tracking-wider uppercase"><Moon className="w-4 h-4 inline mr-2" />II. Vedic Sidereal Astrology (Panchanga)</span>}
      extra={<Tag color="gold" className="font-mono text-[8px]">LAHIRI AYANAMSA</Tag>}
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '20px' } }}
    >
      {/* Panchanga Dashboard */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {([
          { label: 'Tithi', value: panchanga.tithi?.name || '—', sub: panchanga.tithi?.paksha, icon: Moon, color: '#c084fc' },
          { label: 'Nakshatra', value: panchanga.nakshatra?.name || '—', sub: `${(panchanga.nakshatra?.progress ? panchanga.nakshatra.progress * 100 : 0).toFixed(0)}% through`, icon: Star, color: '#22d3ee', symbol: panchanga.nakshatra?.name ? NAKSHATRA_SYMBOLS[panchanga.nakshatra.name] : undefined },
          { label: 'Yoga', value: panchanga.yoga?.name || '—', sub: 'auspicious union', icon: Activity, color: '#f59e0b' },
          { label: 'Karana', value: panchanga.karana?.name || '—', sub: 'half-lunar day', icon: Sun, color: '#f472b6' },
          { label: 'Vara', value: panchanga.vara?.name || '—', sub: 'weekday lord', icon: Activity, color: '#34d399' },
        ] as PanchangaRowItem[]).map(({ label, value, sub, icon: Icon, color, symbol }) => (
          <Col xs={12} sm={8} md={6} lg={24/5} key={label}>
            <Card size="small" className="bg-purple-950/10 border-purple-500/10" styles={{ body: { padding: '12px' } }}>
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-3.5 h-3.5" style={{ color }} />
                <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">{label}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-white">{value}</span>
                {symbol && <span className="text-sm">{symbol}</span>}
              </div>
              <div className="text-[9px] text-gray-500 mt-0.5">{sub}</div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Nakshatra Progress Bar */}
      {panchanga.nakshatra && (
        <div className="bg-black/30 rounded-lg p-3 border border-white/5 mb-4">
          <div className="flex items-center justify-between mb-1.5 text-[10px]">
            <span className="text-gray-500">Nakshatra Transit</span>
            <span className="text-cyan-400 font-mono">{panchanga.nakshatra.name}</span>
            <span className="text-gray-600">Next: {Object.keys(NAKSHATRA_SYMBOLS)[(panchanga.nakshatra.number || 1) % 27]}</span>
          </div>
          <Progress
            percent={Math.round((panchanga.nakshatra.progress || 0) * 100)}
            strokeColor={{ '0%': '#06b6d4', '100%': '#a855f7' }}
            railColor="rgba(255,255,255,0.05)"
            size="small"
            showInfo={false}
          />
        </div>
      )}

      {/* Sidereal Positions */}
      <Row gutter={[8, 8]}>
        {Object.entries(positions).map(([name, pos]) => {
          const rashiName = (pos.rashi_name || pos.rashi || '').split(' ')[0];
          const rashiColor = RASHI_COLORS[rashiName] || '#94a3b8';
          return (
            <Col xs={12} sm={8} md={6} lg={4} key={name}>
              <Tooltip title={`${pos.rashi || ''} · ${pos.degree?.toFixed(2)}°`}>
                <div className="p-2 bg-white/3 hover:bg-white/8 rounded-lg border border-white/5 transition-colors text-center">
                  <div className="text-[9px] text-gray-500 capitalize mb-0.5">{name.replace('_',' ')}</div>
                  <div className="text-xs font-bold" style={{ color: rashiColor }}>
                    {rashiName}
                  </div>
                  <div className="text-[9px] text-gray-500 font-mono">{pos.degree?.toFixed(1)}°</div>
                </div>
              </Tooltip>
            </Col>
          );
        })}
      </Row>
    </Card>
  );
}
