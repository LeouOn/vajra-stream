import React from 'react';
import { Card, Row, Col, Tag, Space } from 'antd';
import { Sun, Moon, Calendar } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

const WU_XING_COLORS: Record<string, string> = { Wood: '#10b981', Fire: '#ef4444', Earth: '#f59e0b', Metal: '#94a3b8', Water: '#3b82f6' };
const WU_XING_ICONS: Record<string, string> = { Wood: '🌳', Fire: '🔥', Earth: '⛰️', Metal: '⚔️', Water: '💧' };

interface ChineseLunarDate {
  [key: string]: unknown;
}

interface ChineseShichen {
  name?: string;
  branch?: string;
  [key: string]: unknown;
}

interface ChineseData {
  bazi?: Record<string, string>;
  lunar_date?: ChineseLunarDate;
  shichen?: ChineseShichen;
  zodiac_animal?: string;
  solar_term?: string;
  [key: string]: unknown;
}

interface PillarDef {
  label: string;
  icon: LucideIcon;
  color: string;
  description: string;
}

interface Props {
  chineseData?: ChineseData | null;
}

const ChineseBaZi: React.FC<Props> = ({ chineseData }) => {
  if (!chineseData) return null;
  const bazi: Record<string, string> = chineseData.bazi || {};
  const lunar: ChineseLunarDate = chineseData.lunar_date || {};
  const shichen: ChineseShichen = chineseData.shichen || {};
  const zodiac = chineseData.zodiac_animal || '—';

  // Extract Wu Xing from BaZi pillars
  const countWuXing = () => {
    const counts: Record<string, number> = { Wood: 0, Fire: 0, Earth: 0, Metal: 0, Water: 0 };
    const charMap: Record<string, string> = { '木': 'Wood', '火': 'Fire', '土': 'Earth', '金': 'Metal', '水': 'Water' };
    Object.values(bazi).forEach((val: string) => {
      const match = typeof val === 'string' ? val.match(/\(([^)]+)\)/) : null;
      if (match && match[1]) {
        for (let char of match[1]) {
          const engName = charMap[char];
          if (engName) counts[engName]++;
        }
      }
    });
    return counts;
  };

  const wuXing = countWuXing();
  const total = Object.values(wuXing).reduce((a, b) => a + b, 0) || 1;

  const PILLAR_NAMES: Record<string, PillarDef> = {
    year: { label: 'Year Pillar', icon: Calendar, color: '#fbbf24', description: 'Ancestral · Destiny · Outer Self' },
    month: { label: 'Month Pillar', icon: Sun, color: '#f59e0b', description: 'Career · Parents · Middle Age' },
    day: { label: 'Day Pillar', icon: Sun, color: '#ef4444', description: 'Self · Marriage · Core Being' },
    hour: { label: 'Hour Pillar', icon: Moon, color: '#3b82f6', description: 'Children · Legacy · Inner Self' },
  };

  const getWuXingFromPillar = (pillarStr: string) => {
    const match = typeof pillarStr === 'string' ? pillarStr.match(/\(([^)]+)\)/) : null;
    if (!match) return '';
    return match[1].split('').map(c => ({ '木': 'W', '火': 'F', '土': 'E', '金': 'M', '水': 'Wa' }[c] || '?')).join('');
  };

  return (
    <Card
      title={<span className="text-emerald-400 font-mono text-xs tracking-wider uppercase"><Calendar className="w-4 h-4 inline mr-2" />III. Chinese Lunisolar Astrology (BaZi / 八字)</span>}
      extra={<Tag color="green" className="font-mono text-[8px]">SHENG XIAO SYSTEM</Tag>}
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '20px' } }}
    >
      {/* Zodiac + Solar Term Banner */}
      <div className="bg-gradient-to-r from-emerald-950/20 to-amber-950/20 rounded-lg p-4 border border-emerald-500/10 mb-5">
        <Row justify="space-between" align="middle">
          <Col>
            <div className="flex items-center gap-3">
              <span className="text-2xl">{zodiac}</span>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider">Zodiac Animal</div>
                <div className="text-lg font-bold text-amber-300">{zodiac}</div>
              </div>
            </div>
          </Col>
          <Col>
            <div className="text-right">
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">Solar Term</div>
              <div className="text-sm font-bold text-emerald-300">{chineseData.solar_term || '—'}</div>
            </div>
          </Col>
          <Col>
            <div className="text-right">
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">Shichen (Hour)</div>
              <div className="text-sm font-bold text-cyan-300">{shichen.name || shichen.branch || '—'}</div>
            </div>
          </Col>
        </Row>
      </div>

      {/* Four Pillars */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {Object.entries(PILLAR_NAMES).map(([key, { label, icon: Icon, color, description }]) => {
          const pillarValue = bazi[key] || '—';
          const wuXingShort = getWuXingFromPillar(pillarValue);
          return (
            <Col xs={12} sm={6} key={key}>
              <Card size="small" className="bg-black/20 border-white/5 hover:border-emerald-500/20 transition-colors" styles={{ body: { padding: '12px' } }}>
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-3.5 h-3.5" style={{ color }} />
                  <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">{label}</span>
                </div>
                <div className="text-sm font-bold text-white mb-1">{pillarValue}</div>
                <div className="flex gap-1 mb-1">
                  {wuXingShort.split('').map((c, i) => (
                    <span key={i} className="text-[9px] px-1 rounded" style={{ 
                      background: `${WU_XING_COLORS[Object.keys(WU_XING_COLORS)[['W','F','E','M','Wa'].indexOf(c)] || 'Metal']}20`,
                      color: WU_XING_COLORS[Object.keys(WU_XING_COLORS)[['W','F','E','M','Wa'].indexOf(c)] || 'Metal']
                    }}>{c === 'W' ? '木' : c === 'F' ? '火' : c === 'E' ? '土' : c === 'M' ? '金' : '水'}</span>
                  ))}
                </div>
                <div className="text-[9px] text-gray-600">{description}</div>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* Wu Xing Element Balance */}
      <div className="bg-black/30 rounded-lg p-4 border border-white/5">
        <div className="text-[10px] font-bold text-gray-400 font-mono uppercase tracking-wider mb-3">
          Five Element Balance (五行)
        </div>
        <Row gutter={[12, 8]}>
          {Object.entries(wuXing).map(([element, count]) => {
            const pct = Math.round((count / total) * 100);
            const color = WU_XING_COLORS[element] || '#94a3b8';
            return (
              <Col xs={24/5} key={element}>
                <div className="text-center">
                  <div className="text-xl mb-1">{WU_XING_ICONS[element]}</div>
                  <div className="text-[10px] font-bold" style={{ color }}>{element}</div>
                  <div className="text-lg font-bold text-white">{count}</div>
                  <div className="w-full bg-gray-800 rounded-full h-1.5 mt-1.5">
                    <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>
                  <div className="text-[9px] text-gray-500 mt-0.5">{pct}%</div>
                </div>
              </Col>
            );
          })}
        </Row>
      </div>
    </Card>
  );
};

export default ChineseBaZi;
