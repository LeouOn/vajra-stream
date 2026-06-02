import React, { useState, useEffect } from 'react';
import { Award, Compass, Heart, RefreshCw, AlertTriangle } from 'lucide-react';
import { Card, Button, Select, Space, Row, Col, Progress, Table, Tag } from 'antd';
import { API_BASE } from '../../utils/api';
import { audioFeedback } from '../../utils/audioFeedback';

const PLANET_GLYPHS = {
  sun:'☉', moon:'☽', mercury:'☿', venus:'♀', mars:'♂',
  jupiter:'♃', saturn:'♄', uranus:'♅', neptune:'♆', pluto:'♇',
  north_node:'☊', south_node:'☋', Chiron: '⚷', mean_node: '☊'
};

const ASPECT_COLORS = {
  Conjunction: 'blue',
  Trine: 'geekblue',
  Sextile: 'purple',
  Square: 'red',
  Opposition: 'volcano',
};

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

  const columns = [
    {
      title: 'Subject A Planet',
      dataIndex: 'person_a_planet',
      key: 'person_a_planet',
      render: (text) => (
        <span className="capitalize font-mono flex items-center gap-1.5 text-xs text-purple-300">
          <span className="text-sm font-sans">{PLANET_GLYPHS[text] || '●'}</span> {text.replace('_', ' ')}
        </span>
      )
    },
    {
      title: 'Aspect',
      dataIndex: 'aspect',
      key: 'aspect',
      render: (text) => (
        <Tag color={ASPECT_COLORS[text] || 'default'} className="font-mono text-[9px] uppercase font-bold">
          {text}
        </Tag>
      )
    },
    {
      title: 'Subject B Planet',
      dataIndex: 'person_b_planet',
      key: 'person_b_planet',
      render: (text) => (
        <span className="capitalize font-mono flex items-center gap-1.5 text-xs text-cyan-300">
          <span className="text-sm font-sans">{PLANET_GLYPHS[text] || '●'}</span> {text.replace('_', ' ')}
        </span>
      )
    },
    {
      title: 'Orb',
      dataIndex: 'orb',
      key: 'orb',
      render: (val) => <span className="font-mono text-[10px] text-gray-400">{val.toFixed(2)}°</span>
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
        {/* Dropdowns for Subjects */}
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
              dropdownClassName="bg-gray-950 border-gray-800 text-white"
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
              dropdownClassName="bg-gray-950 border-gray-800 text-white"
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
              {/* Compatibility Score */}
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
                  <Col xs={24} md={18} className="space-y-2">
                    <h4 className="text-sm font-bold text-slate-200">
                      Elemental Synergy: {scoring.element_a} & {scoring.element_b}
                    </h4>
                    <p className="text-xs text-gray-300 leading-relaxed mb-0">
                      {scoring.description}
                    </p>
                    <div className="flex gap-4 text-[10px] font-mono text-gray-500 pt-1.5">
                      <span>Harmonies: <span className="text-green-400">{scoring.harmony_count}</span></span>
                      <span>Tensions: <span className="text-red-400">{scoring.tension_count}</span></span>
                    </div>
                  </Col>
                </Row>
              )}

              {/* Aspects Table */}
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
