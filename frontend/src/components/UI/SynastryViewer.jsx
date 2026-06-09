import React, { useState, useEffect, useMemo } from 'react';
import { Award, Compass, Heart, RefreshCw, AlertTriangle, Sparkles, ShieldAlert, Minus } from 'lucide-react';
import { Card, Button, Select, Space, Row, Col, Progress, Table, Tag } from 'antd';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { API_BASE } from '../../utils/api';
import { planetGlyph } from '../../lib/astroHelpers';
import { audioFeedback } from '../../utils/audioFeedback';

const PLANET_GLYPHS = {
  sun:'☉', moon:'☽', mercury:'☿', venus:'♀', mars:'♂',
  jupiter:'♃', saturn:'♄', uranus:'♅', neptune:'♆', pluto:'♇',
  north_node:'☊', south_node:'☋', chiron: '⚷', mean_node: '☊'
};

const ASPECT_COLORS = {
  conjunction: '#10b981',
  trine: '#3b82f6',
  sextile: '#a855f7',
  square: '#ef4444',
  opposition: '#f97316',
  quincunx: '#64748b',
  quintile: '#64748b',
};

const ASPECT_LABEL_COLORS = {
  conjunction: 'green',
  trine: 'blue',
  sextile: 'purple',
  square: 'red',
  opposition: 'volcano',
  quincunx: 'default',
  quintile: 'default',
};

const HARMONIOUS = new Set(['trine', 'sextile', 'conjunction']);
const CHALLENGING = new Set(['square', 'opposition']);

const ASPECT_GLYPHS = {
  conjunction: '☌',
  sextile: '⚹',
  square: '□',
  trine: '△',
  opposition: '☍',
  quincunx: '⚻',
  quintile: '⛶',
};

const aspectCategory = (name) => {
  const n = (name || '').toLowerCase();
  if (HARMONIOUS.has(n)) return 'harmonious';
  if (CHALLENGING.has(n)) return 'challenging';
  return 'minor';
};

const aspectGlyph = (name) => ASPECT_GLYPHS[(name || '').toLowerCase()] || '○';

export default function SynastryViewer({
  charts,
  subjectA,
  subjectB,
  onSetSubjectA,
  onSetSubjectB
}) {
  const [loading, setLoading] = useState(false);
  const [synastryData, setSynastryData] = useState(null);

  const fetchSynastry = async () => {
    if (!subjectA || !subjectB) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/astrology/charts/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chart_id_a: subjectA.id,
          chart_id_b: subjectB.id
        })
      });
      if (response.ok) {
        const result = await response.json();
        setSynastryData(result);
        audioFeedback.playSuccess();
      } else {
        audioFeedback.playError();
      }
    } catch (e) {
      console.error(e);
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (subjectA && subjectB) {
      fetchSynastry();
    }
  }, [subjectA, subjectB]);

  const selectOptions = charts.map(c => ({
    value: c.id,
    label: `${c.name} (${c.city})`
  }));

  const handleSelectA = (id) => {
    const selected = charts.find(c => c.id === id);
    onSetSubjectA(selected);
    audioFeedback.playClick();
  };

  const handleSelectB = (id) => {
    const selected = charts.find(c => c.id === id);
    onSetSubjectB(selected);
    audioFeedback.playClick();
  };

  const aspects = synastryData?.data?.aspects || [];
  const scoring = synastryData?.data?.scoring || {};

  const distribution = useMemo(() => {
    const counts = {};
    for (const a of aspects) {
      const k = (a.aspect || '').toLowerCase();
      counts[k] = (counts[k] || 0) + 1;
    }
    return Object.entries(counts)
      .map(([name, count]) => ({
        name,
        label: name.charAt(0).toUpperCase() + name.slice(1),
        count,
        category: aspectCategory(name),
        glyph: aspectGlyph(name),
      }))
      .sort((a, b) => b.count - a.count);
  }, [aspects]);

  const harmonyRatio = useMemo(() => {
    if (!aspects.length) return { harmonious: 0, challenging: 0, neutral: 0 };
    let h = 0, c = 0, m = 0;
    for (const a of aspects) {
      const cat = aspectCategory(a.aspect);
      if (cat === 'harmonious') h++;
      else if (cat === 'challenging') c++;
      else m++;
    }
    const total = h + c + m;
    return {
      harmonious: total ? Math.round((h / total) * 100) : 0,
      challenging: total ? Math.round((c / total) * 100) : 0,
      neutral: total ? Math.round((m / total) * 100) : 0,
    };
  }, [aspects]);

  const columns = [
    {
      title: 'Subject A Planet',
      dataIndex: 'person_a_planet',
      key: 'person_a_planet',
      render: (text) => (
        <span className="capitalize font-mono flex items-center gap-1.5 text-xs text-purple-300">
          <span className="text-sm font-sans">{planetGlyph(text)}</span> {text.replace('_', ' ')}
        </span>
      )
    },
    {
      title: 'Aspect',
      dataIndex: 'aspect',
      key: 'aspect',
      render: (text) => {
        const key = (text || '').toLowerCase();
        return (
          <Tag color={ASPECT_LABEL_COLORS[key] || 'default'} className="font-mono text-[9px] uppercase font-bold">
            <span className="mr-1">{aspectGlyph(key)}</span>{text}
          </Tag>
        );
      }
    },
    {
      title: 'Subject B Planet',
      dataIndex: 'person_b_planet',
      key: 'person_b_planet',
      render: (text) => (
        <span className="capitalize font-mono flex items-center gap-1.5 text-xs text-cyan-300">
          <span className="text-sm font-sans">{planetGlyph(text)}</span> {text.replace('_', ' ')}
        </span>
      )
    },
    {
      title: 'Orb',
      dataIndex: 'orb',
      key: 'orb',
      render: (val) => <span className="font-mono text-[10px] text-gray-400">{(val ?? 0).toFixed(2)}°</span>
    }
  ];

  return (
    <Card
      title={
        <span className="text-cyan-400 font-mono text-xs tracking-wider uppercase flex items-center gap-1.5">
          <Heart className="w-4 h-4 text-cyan-400" />
          SYNASTRY COMPARISON (COMPATIBILITY)
        </span>
      }
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '20px' } }}
    >
      <div className="space-y-6">
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={10}>
            <label className="text-[10px] text-gray-500 font-mono block mb-1 uppercase font-bold">
              Subject A (Natal Focus)
            </label>
            <Select
              className="w-full"
              placeholder="Select Subject A"
              value={subjectA?.id}
              onChange={handleSelectA}
              options={selectOptions}
              classNames={{ popup: { root: 'bg-gray-950 border-gray-800 text-white' } }}
            />
          </Col>
          <Col xs={24} sm={4} className="text-center pt-4">
            <Heart className="w-6 h-6 text-red-500 animate-pulse mx-auto" />
          </Col>
          <Col xs={24} sm={10}>
            <label className="text-[10px] text-gray-500 font-mono block mb-1 uppercase font-bold">
              Subject B (Partner/Comparison)
            </label>
            <Select
              className="w-full"
              placeholder="Select Subject B"
              value={subjectB?.id}
              onChange={handleSelectB}
              options={selectOptions}
              classNames={{ popup: { root: 'bg-gray-950 border-gray-800 text-white' } }}
            />
          </Col>
        </Row>

        {subjectA && subjectB ? (
          loading ? (
            <div className="text-center italic text-gray-500 text-xs py-12 animate-pulse">
              Measuring synastry alignments...
            </div>
          ) : (
            <div className="space-y-6 pt-4 border-t border-white/5">
              {scoring.compatibility_score !== undefined && (
                <Row gutter={[20, 20]} align="middle">
                  <Col xs={24} md={6} className="text-center">
                    <Progress
                      type="circle"
                      percent={scoring.compatibility_score}
                      strokeColor={{
                        '0%': '#10b981',
                        '100%': '#8b5cf6',
                      }}
                      width={100}
                      format={(percent) => (
                        <div className="text-white font-mono">
                          <div className="text-xl font-bold">{percent}%</div>
                          <div className="text-[8px] text-gray-400">Harmony</div>
                        </div>
                      )}
                    />
                  </Col>
                  <Col xs={24} md={18} className="space-y-2.5">
                    <h4 className="text-sm font-bold text-slate-200">
                      Elemental Synergy: {scoring.element_a} & {scoring.element_b}
                    </h4>
                    <p className="text-xs text-gray-300 leading-relaxed mb-0">
                      {scoring.description}
                    </p>
                    <Row gutter={[12, 12]} className="pt-2">
                      <Col xs={8}>
                        <div className="p-2.5 bg-emerald-950/20 border border-emerald-500/25 rounded-lg text-center">
                          <Sparkles className="w-3.5 h-3.5 text-emerald-400 mx-auto mb-0.5" />
                          <div className="text-xl font-bold text-emerald-300 font-mono leading-none">
                            {scoring.harmony_count ?? 0}
                          </div>
                          <div className="text-[9px] text-emerald-400/70 font-mono uppercase tracking-wider mt-1">
                            Harmonious
                          </div>
                        </div>
                      </Col>
                      <Col xs={8}>
                        <div className="p-2.5 bg-rose-950/20 border border-rose-500/25 rounded-lg text-center">
                          <ShieldAlert className="w-3.5 h-3.5 text-rose-400 mx-auto mb-0.5" />
                          <div className="text-xl font-bold text-rose-300 font-mono leading-none">
                            {scoring.tension_count ?? 0}
                          </div>
                          <div className="text-[9px] text-rose-400/70 font-mono uppercase tracking-wider mt-1">
                            Challenging
                          </div>
                        </div>
                      </Col>
                      <Col xs={8}>
                        <div className={`p-2.5 border rounded-lg text-center ${
                          (scoring.harmony_count ?? 0) - (scoring.tension_count ?? 0) > 0
                            ? 'bg-cyan-950/20 border-cyan-500/25'
                            : (scoring.harmony_count ?? 0) - (scoring.tension_count ?? 0) < 0
                              ? 'bg-orange-950/20 border-orange-500/25'
                              : 'bg-gray-950/30 border-white/10'
                        }`}>
                          <Minus className="w-3.5 h-3.5 text-gray-400 mx-auto mb-0.5" />
                          <div className={`text-xl font-bold font-mono leading-none ${
                            (scoring.harmony_count ?? 0) - (scoring.tension_count ?? 0) > 0
                              ? 'text-cyan-300'
                              : (scoring.harmony_count ?? 0) - (scoring.tension_count ?? 0) < 0
                                ? 'text-orange-300'
                                : 'text-gray-300'
                          }`}>
                            {(scoring.harmony_count ?? 0) - (scoring.tension_count ?? 0) > 0 ? '+' : ''}
                            {(scoring.harmony_count ?? 0) - (scoring.tension_count ?? 0)}
                          </div>
                          <div className="text-[9px] text-gray-400 font-mono uppercase tracking-wider mt-1">
                            Net Energy
                          </div>
                        </div>
                      </Col>
                    </Row>
                  </Col>
                </Row>
              )}

              {distribution.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-0">
                    Aspect Distribution
                  </h4>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} md={16}>
                      <div className="bg-black/35 border border-white/5 rounded-xl p-3" style={{ height: 200 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={distribution} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
                            <XAxis
                              dataKey="label"
                              stroke="#94a3b8"
                              fontSize={10}
                              tickLine={false}
                              axisLine={{ stroke: '#334155' }}
                            />
                            <YAxis
                              stroke="#94a3b8"
                              fontSize={10}
                              tickLine={false}
                              axisLine={{ stroke: '#334155' }}
                              allowDecimals={false}
                            />
                            <Tooltip
                              contentStyle={{
                                background: '#0f172a',
                                border: '1px solid #1e293b',
                                borderRadius: 8,
                                fontSize: 11,
                                fontFamily: 'monospace',
                                color: '#e2e8f0',
                              }}
                              cursor={{ fill: 'rgba(148, 163, 184, 0.08)' }}
                              formatter={(value, _name, props) => [
                                `${value} aspect${value === 1 ? '' : 's'}`,
                                props.payload.label,
                              ]}
                            />
                            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                              {distribution.map((entry, idx) => (
                                <Cell
                                  key={`cell-${idx}`}
                                  fill={ASPECT_COLORS[entry.name] || '#64748b'}
                                />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </Col>
                    <Col xs={24} md={8}>
                      <div className="bg-black/35 border border-white/5 rounded-xl p-4 h-full flex flex-col justify-center space-y-3">
                        <div className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">
                          Energy Breakdown
                        </div>
                        <div>
                          <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                            <span className="flex items-center gap-1.5 text-emerald-300">
                              <Sparkles className="w-3 h-3" /> Harmonious
                            </span>
                            <span className="text-emerald-300">{harmonyRatio.harmonious}%</span>
                          </div>
                          <div className="h-2 bg-emerald-950/30 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all"
                              style={{ width: `${harmonyRatio.harmonious}%` }}
                            />
                          </div>
                        </div>
                        <div>
                          <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                            <span className="flex items-center gap-1.5 text-rose-300">
                              <ShieldAlert className="w-3 h-3" /> Challenging
                            </span>
                            <span className="text-rose-300">{harmonyRatio.challenging}%</span>
                          </div>
                          <div className="h-2 bg-rose-950/30 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-rose-500 to-rose-400 transition-all"
                              style={{ width: `${harmonyRatio.challenging}%` }}
                            />
                          </div>
                        </div>
                        {harmonyRatio.neutral > 0 && (
                          <div>
                            <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                              <span className="flex items-center gap-1.5 text-gray-400">
                                <Minus className="w-3 h-3" /> Minor
                              </span>
                              <span className="text-gray-400">{harmonyRatio.neutral}%</span>
                            </div>
                            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-gray-500 to-gray-400 transition-all"
                                style={{ width: `${harmonyRatio.neutral}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </Col>
                  </Row>
                </div>
              )}

              <div className="space-y-2.5">
                <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-0">
                  Synastry Aspects List
                </h4>
                <div className="overflow-x-auto">
                  <Table
                    dataSource={aspects.map((a, i) => ({ ...a, key: i }))}
                    columns={columns}
                    pagination={{ pageSize: 5 }}
                    size="small"
                    className="bg-black/35 rounded-xl border border-white/5"
                    locale={{ emptyText: 'No significant synastry aspects found' }}
                  />
                </div>
              </div>
            </div>
          )
        ) : (
          <div className="bg-black/35 border border-white/5 rounded-xl p-8 text-center text-xs text-gray-500 italic">
            Please select both Subject A and Subject B profiles to load compatibility calculations.
          </div>
        )}
      </div>
    </Card>
  );
}
