/**
 * Astrology Panel — Western, Vedic, and Chinese astrology display.
 *
 * Renders comprehensive astrological data including planetary positions,
 * aspects, elemental balance, Vedic panchanga (tithi, nakshatra, yoga,
 * karana), Chinese BaZi pillars and sheng xiao, and Chaldean planetary
 * hours. Supports location-aware calculations with auto-detection.
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import { 
  Compass, Moon, Sun, Shield, Sparkles, Activity, 
  RotateCw, RefreshCw, Layers, Award, Info, Calendar, MapPin, User, Clock, ChevronRight
} from 'lucide-react';
import { Card, Row, Col, Tag, Progress, Statistic, Button, Space, Segmented, Input, Descriptions } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { useAudioStore } from '../../stores/audioStore';
import SacredMandala from '../3D/SacredMandala';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';

import { API_BASE } from '../../utils/api';

const getOrdinalSuffix = (num) => {
  if (!num) return '';
  const s = ["th", "st", "nd", "rd"];
  const v = num % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
};

export default function AstrologyPanel() {
  const { isPlaying, frequency } = useAudioStore();
  const [loading, setLoading] = useState(false);
  const [liveData, setLiveData] = useState(null);
  const [customData, setCustomData] = useState(null);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [activeSystem, setActiveSystem] = useState('all'); // all, western, vedic, chinese

  // Natal Chart / Calculator state
  const [birthDate, setBirthDate] = useState(() => {
    const d = new Date();
    // format as YYYY-MM-DDTHH:MM
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  });
  const [latitude, setLatitude] = useState('37.7749');
  const [longitude, setLongitude] = useState('-122.4194');
  const [chartLabel, setChartLabel] = useState('Current Transit');

  const fetchLiveAstrology = async () => {
    if (!isLiveMode) return;
    const doFetch = async (lat, lon) => {
      try {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const localTime = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        
        const params = new URLSearchParams();
        params.append('datetime_str', localTime);
        if (lat !== null && lon !== null) {
          params.append('latitude', lat.toString());
          params.append('longitude', lon.toString());
        }
        
        const response = await fetch(`${API_BASE}/astrology/current?${params.toString()}`);
        if (response.ok) {
          const result = await response.json();
          setLiveData(result.astrology);
        }
      } catch (e) {
        console.error("Error in live astrology fetch:", e);
      }
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          doFetch(position.coords.latitude, position.coords.longitude);
        },
        () => {
          doFetch(null, null);
        },
        { timeout: 5000 }
      );
    } else {
      doFetch(null, null);
    }
  };

  // Poll for live transits
  useEffect(() => {
    fetchLiveAstrology();
    const interval = setInterval(() => {
      if (isLiveMode) fetchLiveAstrology();
    }, 15000);
    return () => clearInterval(interval);
  }, [isLiveMode]);

  // Handle manual calculations (natal charts)
  const handleCalculateCustom = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    audioFeedback.playTelemetry();
    try {
      const query = new URLSearchParams({
        datetime_str: birthDate,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude)
      }).toString();
      
      const response = await fetch(`${API_BASE}/astrology/current?${query}`);
      if (response.ok) {
        const result = await response.json();
        setCustomData(result.astrology);
        setIsLiveMode(false);
        setChartLabel(`Natal: ${latitude}N, ${longitude}E`);
        audioFeedback.playSuccess();
      } else {
        audioFeedback.playError();
      }
    } catch (e) {
      console.error("Error calculating custom chart:", e);
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  const handleResetToLive = () => {
    setIsLiveMode(true);
    setChartLabel('Current Transit');
    audioFeedback.playClick();
    fetchLiveAstrology();
  };

  const setLocationPreset = (lat, lon, label) => {
    setLatitude(lat);
    setLongitude(lon);
    audioFeedback.playTick();
  };

  const activeData = isLiveMode ? liveData : customData;

  // Element color mappings for Chinese Wu Xing
  const getElementColorClass = (elementStr) => {
    if (!elementStr) return 'text-gray-400';
    const clean = elementStr.toLowerCase();
    if (clean.includes('wood') || clean.includes('木')) return 'text-emerald-400';
    if (clean.includes('fire') || clean.includes('火')) return 'text-rose-500';
    if (clean.includes('earth') || clean.includes('土')) return 'text-amber-500';
    if (clean.includes('metal') || clean.includes('金')) return 'text-slate-300';
    if (clean.includes('water') || clean.includes('水')) return 'text-blue-400';
    return 'text-gray-400';
  };

  // Chinese Wu Xing Counter
  const countWuXing = () => {
    const counts = { Wood: 0, Fire: 0, Earth: 0, Metal: 0, Water: 0 };
    if (!activeData?.chinese?.bazi) return counts;
    
    const charMap = {
      '木': 'Wood',
      '火': 'Fire',
      '土': 'Earth',
      '金': 'Metal',
      '水': 'Water'
    };
    
    Object.values(activeData.chinese.bazi).forEach(val => {
      const match = val.match(/\(([^)]+)\)/);
      if (match && match[1]) {
        const elementsStr = match[1];
        for (let char of elementsStr) {
          const engName = charMap[char];
          if (engName) counts[engName]++;
        }
      }
    });
    
    return counts;
  };

  const wuXingCounts = countWuXing();

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6 bg-transparent">
      
      {/* Header and Controls */}
      <Card 
        className="bg-gray-900/80 border-purple-500/20"
        styles={{ body: { padding: '20px' } }}
      >
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} md={14}>
            <Space align="start" size={12}>
              <Compass className="w-6 h-6 text-cyan-400" style={{ animation: 'spin 8s linear infinite' }} />
              <div>
                <h2 className="text-xl font-bold text-cyan-300 tracking-wider font-mono" style={{ margin: 0 }}>
                  Cosmic Clockwork System
                </h2>
                <p className="text-xs text-gray-400 mt-1" style={{ margin: 0 }}>
                  Precision planetary transits, sidereal Indian Rashi Kundali grids, and BaZi Wu Xing pillars.
                </p>
              </div>
            </Space>
          </Col>
          <Col xs={24} md={10}>
            <Space wrap size={8} style={{ justifyContent: 'flex-end', width: '100%' }}>
              <Segmented
                size="small"
                value={isLiveMode ? 'live' : 'static'}
                onChange={(val) => {
                  if (val === 'live') handleResetToLive();
                  else setIsLiveMode(false);
                }}
                options={[
                  { label: '🔴 LIVE', value: 'live' },
                  { label: 'STATIC / NATAL', value: 'static' }
                ]}
              />
              <Segmented
                size="small"
                value={activeSystem}
                onChange={(val) => { setActiveSystem(val); audioFeedback.playClick(); }}
                options={[
                  { label: 'All', value: 'all' },
                  { label: 'Western', value: 'western' },
                  { label: 'Vedic', value: 'vedic' },
                  { label: 'Chinese', value: 'chinese' }
                ]}
              />
              <Button
                size="small"
                icon={<RefreshCw className={loading ? 'animate-spin' : ''} style={{ width: 14, height: 14 }} />}
                onClick={() => {
                  audioFeedback.playTelemetry();
                  if (isLiveMode) fetchLiveAstrology();
                  else handleCalculateCustom();
                }}
                disabled={loading}
                type="default"
                ghost
              />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Natal/Custom Calculator Input Panel */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card
            title={<span className="text-purple-400 font-mono text-xs tracking-wider uppercase"><Calendar className="w-4 h-4 inline mr-2" />NATAL CHART CALCULATOR</span>}
            className="bg-gray-900/80 border-purple-500/20"
            styles={{ body: { padding: '16px' } }}
          >
            <form onSubmit={handleCalculateCustom}>
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <div>
                  <label className="text-gray-400 text-xs font-semibold block mb-1"><Clock className="w-3 h-3 text-cyan-400 inline mr-1" />Event Date & Time (Local)</label>
                  <Input
                    type="datetime-local"
                    value={birthDate}
                    onChange={(e) => { setBirthDate(e.target.value); audioFeedback.playType(); }}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
                <Row gutter={8}>
                  <Col span={12}>
                    <label className="text-gray-400 text-xs font-semibold block mb-1"><MapPin className="w-3 h-3 text-rose-400 inline mr-1" />Latitude</label>
                    <Input
                      type="number"
                      step="0.0001"
                      value={latitude}
                      onChange={(e) => { setLatitude(e.target.value); audioFeedback.playType(); }}
                      className="bg-gray-800 border-gray-700 text-white"
                      placeholder="37.7749"
                    />
                  </Col>
                  <Col span={12}>
                    <label className="text-gray-400 text-xs font-semibold block mb-1"><MapPin className="w-3 h-3 text-rose-400 inline mr-1" />Longitude</label>
                    <Input
                      type="number"
                      step="0.0001"
                      value={longitude}
                      onChange={(e) => { setLongitude(e.target.value); audioFeedback.playType(); }}
                      className="bg-gray-800 border-gray-700 text-white"
                      placeholder="-122.4194"
                    />
                  </Col>
                </Row>
                <div>
                  <span className="text-[10px] text-gray-500 block uppercase font-bold mb-1">Quick Presets</span>
                  <Space wrap size={4}>
                    {[
                      { name: 'San Francisco', lat: '37.7749', lon: '-122.4194' },
                      { name: 'London', lat: '51.5074', lon: '-0.1278' },
                      { name: 'New Delhi', lat: '28.6139', lon: '77.2090' },
                      { name: 'Beijing', lat: '39.9042', lon: '116.4074' },
                      { name: 'Tokyo', lat: '35.6762', lon: '139.6503' }
                    ].map((p) => (
                      <Button
                        key={p.name}
                        size="small"
                        type="default"
                        ghost
                        onClick={() => setLocationPreset(p.lat, p.lon, p.name)}
                        style={{ fontSize: '9px', padding: '0 6px' }}
                      >
                        {p.name}
                      </Button>
                    ))}
                  </Space>
                </div>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  icon={<Compass style={{ width: 14, height: 14 }} />}
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none' }}
                >
                  Calculate Natal Chart
                </Button>
              </Space>
            </form>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card
            className="bg-gray-900/80 border-purple-500/20"
            styles={{ body: { padding: '20px' } }}
          >
            <Row justify="space-between" align="top" style={{ marginBottom: 16 }}>
              <Col>
                <Tag color="purple" className="font-mono text-[9px]">ACTIVE FRAME</Tag>
              </Col>
              <Col>
                <span className="text-[10px] text-gray-500 font-mono">COORD MODE: GEOCENTRIC</span>
              </Col>
            </Row>

            <h3 className="text-xl font-bold text-white tracking-wide font-mono" style={{ margin: '0 0 4px 0' }}>
              {isLiveMode ? '🪐 LIVE CELESTIAL TRANSITS' : '🔮 NATAL DETAILS'}
            </h3>
            <p className="text-xs text-gray-400 font-mono" style={{ margin: '0 0 16px 0' }}>
              Time: {activeData ? new Date(activeData.datetime).toLocaleString() : 'Loading...'}
            </p>

            <Row gutter={[12, 12]}>
              <Col xs={12} sm={6}>
                <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                  <Statistic
                    title={<span className="text-[9px] text-gray-500 font-mono">PLANETARY HOUR</span>}
                    value={activeData?.planetary_hours?.current_planetary_hour || '—'}
                    valueStyle={{ color: '#facc15', fontSize: '14px', fontWeight: 'bold' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                  <Statistic
                    title={<span className="text-[9px] text-gray-500 font-mono">VEDIC TITHI</span>}
                    value={activeData?.indian?.panchanga?.tithi?.name || '—'}
                    valueStyle={{ color: '#c084fc', fontSize: '14px', fontWeight: 'bold' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                  <Statistic
                    title={<span className="text-[9px] text-gray-500 font-mono">CHINESE BAZI YEAR</span>}
                    value={activeData?.chinese?.bazi?.year?.split(' ')[0] || '—'}
                    valueStyle={{ color: '#34d399', fontSize: '14px', fontWeight: 'bold' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" className="bg-gray-800/60 border-white/5" styles={{ body: { padding: '10px' } }}>
                  <Statistic
                    title={<span className="text-[9px] text-gray-500 font-mono">MOON ILLUMINATION</span>}
                    value={activeData?.moon_phase?.illumination?.toFixed(1) + '%' || '—'}
                    valueStyle={{ color: '#22d3ee', fontSize: '14px', fontWeight: 'bold' }}
                  />
                </Card>
              </Col>
            </Row>

            <Row justify="space-between" align="middle" style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <Col>
                <span className="text-[10px] text-gray-500 font-mono">Ephemeris: SwissEph v2.10 Offline</span>
              </Col>
              <Col>
                <Space size={4}>
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" style={{ display: 'inline-block', animation: 'ping 1.5s ease-in-out infinite' }} />
                  <span className="text-[10px] text-gray-500 font-mono">Tuned and aligned</span>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {activeData ? (
        <div className="space-y-6">
          
          {/* ===================== SYSTEM SECTIONS ===================== */}

          {/* WESTERN ASTROLOGY */}
          {(activeSystem === 'all' || activeSystem === 'western') && (
            <Card
              title={<span className="text-cyan-400 font-mono text-xs tracking-wider uppercase"><Sun className="w-4 h-4 inline mr-2" />I. Western Tropical Astrology (Transit Wheel)</span>}
              extra={<Tag color="purple" className="font-mono text-[9px]">TROPICAL / PLACIDUS HOUSES</Tag>}
              className="bg-gray-900/80 border-purple-500/20"
              styles={{ body: { padding: '20px' } }}
            >

              {/* Celestial Trinity (Big Three) */}
              <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
                <Col xs={24} md={8}>
                  <Card size="small" className="bg-purple-950/20 border-purple-500/20 hover:border-purple-500/40" styles={{ body: { padding: '12px' } }}>
                    <Space align="start" size={12}>
                      <div className="p-2 bg-yellow-500/10 rounded-lg text-yellow-400"><Sun className="w-5 h-5" /></div>
                      <div>
                        <span className="text-[10px] text-yellow-400 font-mono font-bold tracking-wider block uppercase">☀️ SUN SIGN</span>
                        <span className="text-base font-bold text-white block mt-0.5">{activeData.western?.positions?.sun?.sign || 'Unknown'}</span>
                        <span className="text-[10px] text-gray-400 block font-mono">Degree: {activeData.western?.positions?.sun?.degree?.toFixed(2)}° | {activeData.western?.positions?.sun?.house ? `${activeData.western.positions.sun.house}${getOrdinalSuffix(activeData.western.positions.sun.house)} House` : 'No House'}</span>
                      </div>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} md={8}>
                  <Card size="small" className="bg-purple-950/20 border-purple-500/20 hover:border-purple-500/40" styles={{ body: { padding: '12px' } }}>
                    <Space align="start" size={12}>
                      <div className="p-2 bg-slate-400/10 rounded-lg text-slate-300"><Moon className="w-5 h-5" /></div>
                      <div>
                        <span className="text-[10px] text-slate-300 font-mono font-bold tracking-wider block uppercase">🌙 MOON SIGN</span>
                        <span className="text-base font-bold text-white block mt-0.5">{activeData.western?.positions?.moon?.sign || 'Unknown'}</span>
                        <span className="text-[10px] text-gray-400 block font-mono">Degree: {activeData.western?.positions?.moon?.degree?.toFixed(2)}° | {activeData.western?.positions?.moon?.house ? `${activeData.western.positions.moon.house}${getOrdinalSuffix(activeData.western.positions.moon.house)} House` : 'No House'}</span>
                      </div>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} md={8}>
                  <Card size="small" className="bg-purple-950/20 border-purple-500/20 hover:border-purple-500/40" styles={{ body: { padding: '12px' } }}>
                    <Space align="start" size={12}>
                      <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-400"><Compass className="w-5 h-5" /></div>
                      <div>
                        <span className="text-[10px] text-cyan-400 font-mono font-bold tracking-wider block uppercase">🏹 ASCENDANT (RISING)</span>
                        <span className="text-base font-bold text-white block mt-0.5">{activeData.western?.positions?.ascendant?.sign || 'Unknown'}</span>
                        <span className="text-[10px] text-gray-400 block font-mono">Degree: {activeData.western?.positions?.ascendant?.degree?.toFixed(2)}° | First House Cusp</span>
                      </div>
                    </Space>
                  </Card>
                </Col>
              </Row>

              <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
                <Col xs={24} xl={8}>
                  {/* Chart Wheel Visualizer */}
                  <div className="flex flex-col items-center justify-center p-4 bg-black/55 border border-white/5 rounded-xl min-h-[350px]">
                    <h4 className="text-[10px] font-bold text-gray-500 mb-4 font-mono tracking-widest uppercase">
                      ASTROLOGICAL TRANSIT WHEEL (ASC ROTATED)
                    </h4>
                    <WesternChartWheel positions={activeData.western?.positions} aspects={activeData.western?.aspects} />
                  </div>
                </Col>
                <Col xs={24} xl={8}>
                  {/* Positions and Details */}
                  <div className="space-y-4 font-mono">
                    <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase">
                      PLANETARY COORDINATES
                    </h4>
                    <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto pr-1">
                      {Object.entries(activeData.western?.positions || {}).map(([planet, pos]) => {
                        const label = planet.replace('_', ' ').toUpperCase();
                        return (
                          <div key={planet} className="p-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg flex justify-between items-center text-xs transition-colors">
                            <span className="font-semibold text-purple-300">{label}</span>
                            <span className="text-gray-200">
                              {pos.formatted} {pos.house ? `(${pos.house}${getOrdinalSuffix(pos.house)} House)` : ''}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </Col>
                <Col xs={24} xl={8}>
                  {/* Aspects and Elemental Balance */}
                  <div className="space-y-4 font-mono">
                    <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase">
                      ELEMENTS & ACTIVE ASPECTS
                    </h4>
                    
                    {/* Element gauges */}
                    <div className="grid grid-cols-4 gap-2 text-center text-xs bg-black/45 p-3 rounded-xl border border-white/5">
                      {Object.entries(activeData.western?.elements || {}).map(([elem, weight]) => {
                        let color = 'text-gray-400';
                        if (elem === 'Fire') color = 'text-rose-400';
                        else if (elem === 'Earth') color = 'text-amber-400';
                        else if (elem === 'Air') color = 'text-sky-400';
                        else if (elem === 'Water') color = 'text-emerald-400';
                        
                        return (
                          <div key={elem}>
                            <span className="text-[9px] text-gray-500 font-mono block leading-none">{elem.toUpperCase()}</span>
                            <span className={`font-bold mt-1.5 block ${color}`}>{weight} pts</span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Aspect scrolling block */}
                    <div className="bg-black/45 border border-white/5 rounded-xl p-3 max-h-[195px] overflow-y-auto space-y-2">
                      <span className="text-[9px] text-gray-500 font-mono block mb-1">ACTIVE TRANSIT ASPECTS</span>
                      {activeData.western?.aspects && activeData.western.aspects.length > 0 ? (
                        activeData.western.aspects.map((asp, idx) => (
                          <div key={idx} className="flex justify-between items-center text-[10px] p-2 bg-white/5 border border-white/5 rounded-lg">
                            <span className="font-medium text-gray-300">{asp.description}</span>
                            <Tag color={asp.aspect === 'Conjunction' || asp.aspect === 'Trine' || asp.aspect === 'Sextile' ? 'blue' : 'red'} className="font-mono text-[8px]">
                              {asp.aspect}
                            </Tag>
                          </div>
                        ))
                      ) : (
                        <div className="text-xs text-gray-500 italic py-2 text-center">No active aspects in orb</div>
                      )}
                    </div>
                  </div>
                </Col>
              </Row>
            </Card>
          )}

          {/* Sacred Mandala — Planetary Resonance Visualization */}
          {(activeSystem === 'all' || activeSystem === 'western') && (
            <Card
              title={<span className="text-purple-400 font-mono text-xs tracking-wider uppercase">🌀 Sacred Mandala — Planetary Resonance Field</span>}
              className="bg-gray-900/80 border-purple-500/20"
              styles={{ body: { padding: '0', height: '360px' } }}
            >
              <Canvas camera={{ position: [0, 0, 12], fov: 55 }}>
                <ambientLight intensity={0.4} />
                <pointLight position={[10, 10, 10]} intensity={0.8} />
                <Stars radius={100} depth={40} count={3000} factor={3} saturation={0.1} fade speed={0.6} />
                <SacredMandala
                  isPlaying={isPlaying}
                  frequency={frequency}
                  pattern="sri-yantra"
                  chakra="third-eye"
                  complexity="medium"
                />
                <OrbitControls enableZoom={true} enablePan={false} enableRotate={true} autoRotate={true} autoRotateSpeed={0.3} />
                <Environment preset="sunset" />
              </Canvas>
            </Card>
          )}

          {/* VEDIC ASTROLOGY */}
          {(activeSystem === 'all' || activeSystem === 'vedic') && (
            <Card
              title={<span className="text-cyan-400 font-mono text-xs tracking-wider uppercase"><Shield className="w-4 h-4 inline mr-2 text-purple-400" />II. Indian Vedic Astrology (Panchang & Kundali)</span>}
              extra={<Tag color="purple" className="font-mono text-[9px]">SIDEREAL / LAHIRI AYANAMSA</Tag>}
              className="bg-gray-900/80 border-purple-500/20"
              styles={{ body: { padding: '20px' } }}
            >

              <Row gutter={[16, 16]}>
                <Col xs={24} xl={12}>
                  {/* Vedic Chart / Kundali */}
                  <div className="flex flex-col items-center justify-center p-4 bg-black/55 border border-white/5 rounded-xl min-h-[350px]">
                    <h4 className="text-[10px] font-bold text-gray-500 mb-4 font-mono tracking-widest uppercase">
                      NORTH INDIAN RASHI KUNDALI
                    </h4>
                    <VedicKundali siderealPositions={activeData.indian?.sidereal_positions} />
                  </div>
                </Col>
                <Col xs={24} xl={12}>
                  {/* Panchanga Elements */}
                  <div className="space-y-4 font-mono">
                <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase">
                  PANCHA MAHABHUTA / FIVE LIMBS OF TIME
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  {/* Tithi */}
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl flex flex-col justify-between space-y-2.5">
                    <div>
                      <span className="text-[9px] text-purple-400 font-bold tracking-wider block uppercase">TITHI (Lunar Day)</span>
                      <span className="text-sm font-bold text-white block mt-1">{activeData.indian?.panchanga?.tithi?.name}</span>
                      <span className="text-[10px] text-gray-400 block">{activeData.indian?.panchanga?.tithi?.paksha} Paksha</span>
                    </div>
                    <div className="w-full bg-black/60 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-purple-500 h-1.5" style={{ width: `${(activeData.indian?.panchanga?.tithi?.progress || 0) * 100}%` }} />
                    </div>
                  </div>

                  {/* Nakshatra */}
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl flex flex-col justify-between space-y-2.5">
                    <div>
                      <span className="text-[9px] text-cyan-400 font-bold tracking-wider block uppercase">NAKSHATRA (Lunar Mansion)</span>
                      <span className="text-sm font-bold text-white block mt-1">{activeData.indian?.panchanga?.nakshatra?.name}</span>
                      <span className="text-[10px] text-gray-400 block">Limb of Vitality / Life Force</span>
                    </div>
                    <div className="w-full bg-black/60 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-cyan-500 h-1.5" style={{ width: `${(activeData.indian?.panchanga?.nakshatra?.progress || 0) * 100}%` }} />
                    </div>
                  </div>

                  {/* Yoga */}
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl flex flex-col justify-between space-y-2.5">
                    <div>
                      <span className="text-[9px] text-yellow-400 font-bold tracking-wider block uppercase">YOGA (Solar-Lunar Union)</span>
                      <span className={`text-sm font-bold block mt-1 ${activeData.indian?.panchanga?.yoga?.name === 'Vajra' ? 'text-yellow-300 font-serif glow-text animate-pulse' : 'text-white'}`}>
                        {activeData.indian?.panchanga?.yoga?.name}
                      </span>
                      <span className="text-[10px] text-gray-400 block">Limb of Synergy and Relationship</span>
                    </div>
                    <div className="w-full bg-black/60 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-yellow-500 h-1.5" style={{ width: `${(activeData.indian?.panchanga?.yoga?.progress || 0) * 100}%` }} />
                    </div>
                  </div>

                  {/* Karana & Vara */}
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-[9px] text-gray-500 font-bold tracking-wider block uppercase">KARANA (Half Tithi)</span>
                      <span className="text-xs font-bold text-white mt-1 block">{activeData.indian?.panchanga?.karana?.name}</span>
                      <span className="text-[9px] text-gray-400 block">Limb of Action</span>
                    </div>
                    <div className="border-l border-white/5 pl-3">
                      <span className="text-[9px] text-gray-500 font-bold tracking-wider block uppercase">VARA (Solar Day)</span>
                      <span className="text-xs font-bold text-white mt-1 block">{activeData.indian?.panchanga?.vara?.name.split(' ')[0]}</span>
                      <span className="text-[9px] text-gray-400 block">Starts at Sunrise</span>
                    </div>
                  </div>
                </div>

                {/* Sidereal positions details list */}
                <div className="pt-2">
                  <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-2">
                    SIDEREAL POSITIONS (GRAHAS)
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                    {Object.entries(activeData.indian?.sidereal_positions || {}).map(([planet, info]) => (
                      <div key={planet} className="p-2 bg-black/25 border border-white/5 rounded-lg flex justify-between items-center">
                        <span className="text-purple-300 font-semibold capitalize">{planet}</span>
                        <span className="text-gray-300 text-[11px] font-mono">{info.formatted}</span>
                      </div>
                    ))}
                  </div>
                </div>

                </div>
              </Col>
            </Row>
            </Card>
          )}

          {/* CHINESE ASTROLOGY */}
          {(activeSystem === 'all' || activeSystem === 'chinese') && (
            <Card
              title={<span className="text-cyan-400 font-mono text-xs tracking-wider uppercase"><Compass className="w-4 h-4 inline mr-2 text-emerald-400" />III. Chinese Lunisolar Astrology & BaZi</span>}
              extra={<Tag color="purple" className="font-mono text-[9px]">Bazi Four Pillars / Wu Xing</Tag>}
              className="bg-gray-900/80 border-purple-500/20"
              styles={{ body: { padding: '20px' } }}
            >

              {/* BaZi Four Pillars */}
              <div className="xl:col-span-2 space-y-4">
                <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase">
                  FOUR PILLARS OF DESTINY (BAZI GRID)
                </h4>
                
                <div className="grid grid-cols-4 gap-3 md:gap-4">
                  {['Year', 'Month', 'Day', 'Hour'].map((pillar) => {
                    const key = pillar.toLowerCase();
                    const value = activeData.chinese?.bazi?.[key] || '';
                    const parts = value.split(' ');
                    const stemBranch = parts[0] || 'Unknown';
                    const element = parts[1] ? parts[1].replace(/[()]/g, '') : '';
                    
                    return (
                      <div key={pillar} className="p-4 bg-black/55 border border-white/10 rounded-2xl text-center flex flex-col justify-between h-36 shadow-lg hover:border-cyan-500/20 transition-all">
                        <span className="text-[9px] text-gray-500 font-mono font-bold tracking-widest block uppercase">{pillar}</span>
                        
                        <div className="my-2">
                          <span className="text-2xl font-bold text-white block font-serif tracking-wider">{stemBranch}</span>
                          <span className={`text-[10px] mt-1 block font-mono font-bold uppercase tracking-wider ${getElementColorClass(element)}`}>
                            {element}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Shichen and Solar Term */}
              <div className="space-y-4 font-mono">
                <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase">
                  WU XING / COSMIC ENERGY BALANCE
                </h4>

                <div className="space-y-3">
                  {/* Five elements balance bars */}
                  <div className="p-4 bg-black/45 border border-white/5 rounded-2xl space-y-2 text-xs">
                    {Object.entries(wuXingCounts).map(([elem, count]) => {
                      const percentage = (count / 8) * 100;
                      let barColor = 'bg-gray-500';
                      let textColor = 'text-gray-400';
                      if (elem === 'Wood') { barColor = 'bg-emerald-500'; textColor = 'text-emerald-400'; }
                      else if (elem === 'Fire') { barColor = 'bg-rose-500'; textColor = 'text-rose-400'; }
                      else if (elem === 'Earth') { barColor = 'bg-amber-500'; textColor = 'text-amber-400'; }
                      else if (elem === 'Metal') { barColor = 'bg-slate-300'; textColor = 'text-slate-200'; }
                      else if (elem === 'Water') { barColor = 'bg-blue-500'; textColor = 'text-blue-400'; }
                      
                      return (
                        <div key={elem} className="space-y-1">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className={`font-bold ${textColor}`}>{elem.toUpperCase()}</span>
                            <span className="text-gray-400">{count} / 8 ({percentage.toFixed(0)}%)</span>
                          </div>
                          <div className="w-full bg-black/60 rounded-full h-1.5 overflow-hidden">
                            <div className={`h-1.5 ${barColor}`} style={{ width: `${percentage}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Shichen and Solar term summary */}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3.5 bg-white/5 border border-white/5 rounded-xl flex flex-col justify-between">
                      <span className="text-[9px] text-gray-500 block uppercase font-bold">SHICHEN</span>
                      <span className="font-bold text-white mt-1.5 block">{activeData.chinese?.shichen?.name}</span>
                    </div>
                    <div className="p-3.5 bg-white/5 border border-white/5 rounded-xl flex flex-col justify-between">
                      <span className="text-[9px] text-gray-500 block uppercase font-bold">SOLAR TERM</span>
                      <span className="font-bold text-white mt-1.5 block truncate">{activeData.chinese?.solar_term}</span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          )}

        </div>
      ) : (
        <div className="bg-gray-900/60 p-8 border border-white/5 rounded-xl text-center italic text-gray-400 font-mono text-xs">
          Computing ephemeris coordinates from planetary databases...
        </div>
      )}
    </div>
  );
}

// =========================================================================
// SVG CHART DRAWING HELPERS
// =========================================================================

const WesternChartWheel = ({ positions, aspects }) => {
  if (!positions) return <div className="w-60 h-60 rounded-full border border-dashed border-gray-700 animate-pulse flex items-center justify-center text-xs text-gray-600">No positions calculated</div>;

  const cx = 160;
  const cy = 160;
  const r = 130;
  const midR = 105;
  const innerR = 85;

  // Align 0 relative degrees to Ascendant (left horizon / 180 deg)
  const ascLon = positions.ascendant?.longitude || 0;

  // Convert longitude to coordinate
  const getCoordinates = (lon, radius) => {
    const rad = ((lon - ascLon - 180) * Math.PI) / 180;
    const x = cx + radius * Math.cos(rad);
    const y = cy + radius * Math.sin(rad);
    return { x, y };
  };

  // Pre-calculate coordinates for all planets
  const planetCoords = {};
  Object.entries(positions).forEach(([planet, info]) => {
    if (planet !== 'ascendant' && planet !== 'midheaven') {
      planetCoords[planet] = getCoordinates(info.longitude, innerR - 8);
    }
  });

  const signGlyphs = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
  const planetGlyphs = {
    sun: '☉',
    moon: '☽',
    mercury: '☿',
    venus: '♀',
    mars: '♂',
    jupiter: '♃',
    saturn: '♄',
    uranus: '♅',
    neptune: '♆',
    pluto: '♇',
    north_node: '☊',
  };

  return (
    <svg width="320" height="320" className="select-none font-mono">
      {/* Concentric circles */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="3" />
      <circle cx={cx} cy={cy} r={midR} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1.5" />
      <circle cx={cx} cy={cy} r={innerR} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />

      {/* Draw Zodiac spokes (12 signs ring) */}
      {Array.from({ length: 12 }).map((_, idx) => {
        const deg = idx * 30;
        const pInner = getCoordinates(deg, midR);
        const pOuter = getCoordinates(deg, r);
        return (
          <line
            key={idx}
            x1={pInner.x}
            y1={pInner.y}
            x2={pOuter.x}
            y2={pOuter.y}
            stroke="rgba(255,255,255,0.15)"
            strokeWidth="1"
          />
        );
      })}

      {/* Draw Zodiac Sign glyphs inside the outer ring */}
      {Array.from({ length: 12 }).map((_, idx) => {
        const deg = idx * 30 + 15;
        const pGlyph = getCoordinates(deg, (midR + r) / 2);
        const colors = ['#f87171', '#fbbf24', '#60a5fa', '#34d399']; // Fire, Earth, Air, Water
        const color = colors[idx % 4];
        return (
          <text
            key={idx}
            x={pGlyph.x}
            y={pGlyph.y + 4}
            textAnchor="middle"
            fontSize="13px"
            fill={color}
            fontWeight="bold"
            className="font-sans"
          >
            {signGlyphs[idx]}
          </text>
        );
      })}

      {/* Draw Equal Houses spokes inside */}
      {Array.from({ length: 12 }).map((_, idx) => {
        const deg = idx * 30;
        const pInner = getCoordinates(ascLon + deg, innerR - 15);
        return (
          <g key={idx}>
            <line
              x1={cx}
              y1={cy}
              x2={pInner.x}
              y2={pInner.y}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="1"
              strokeDasharray="2,3"
            />
            {/* House Number Label */}
            {(() => {
              const labelCoord = getCoordinates(ascLon + deg + 15, innerR - 22);
              return (
                <text
                  x={labelCoord.x}
                  y={labelCoord.y + 3}
                  textAnchor="middle"
                  fontSize="7px"
                  fill="rgba(255,255,255,0.25)"
                  fontWeight="bold"
                >
                  {idx + 1}
                </text>
              );
            })()}
          </g>
        );
      })}

      {/* Draw Aspect Lines in center */}
      {aspects && aspects.map((asp, idx) => {
        const coord1 = planetCoords[asp.planet1];
        const coord2 = planetCoords[asp.planet2];
        if (!coord1 || !coord2) return null;
        
        let color = 'rgba(255,255,255,0.08)';
        let strokeDash = 'none';
        if (asp.aspect === 'Conjunction') color = 'rgba(34,197,94,0.45)'; // green
        else if (asp.aspect === 'Trine') color = 'rgba(59,130,246,0.45)'; // blue
        else if (asp.aspect === 'Sextile') {
          color = 'rgba(168,85,247,0.45)'; // purple
          strokeDash = '2,2';
        }
        else if (asp.aspect === 'Square') color = 'rgba(239,68,68,0.45)'; // red
        else if (asp.aspect === 'Opposition') {
          color = 'rgba(249,115,22,0.45)'; // orange
          strokeDash = '4,4';
        }

        return (
          <line
            key={idx}
            x1={coord1.x}
            y1={coord1.y}
            x2={coord2.x}
            y2={coord2.y}
            stroke={color}
            strokeWidth={1 + asp.exactness * 1.5}
            strokeDasharray={strokeDash}
          />
        );
      })}

      {/* Plot planets */}
      {Object.entries(positions).map(([planet, info]) => {
        if (planet === 'ascendant' || planet === 'midheaven') return null;
        const coord = planetCoords[planet];
        if (!coord) return null;

        const glyph = planetGlyphs[planet] || planet.substring(0, 2).toUpperCase();

        let color = '#a855f7'; // fallback purple
        if (planet === 'sun') color = '#fbbf24';      // Gold
        else if (planet === 'moon') color = '#e2e8f0'; // Silver
        else if (planet === 'mercury') color = '#38bdf8'; // Blue
        else if (planet === 'venus') color = '#f472b6';   // Pink
        else if (planet === 'mars') color = '#f87171';    // Red
        else if (planet === 'jupiter') color = '#c084fc'; // Purple
        else if (planet === 'saturn') color = '#fb923c';  // Orange
        else if (planet === 'uranus') color = '#2dd4bf';  // Teal
        else if (planet === 'neptune') color = '#818cf8'; // Indigo
        else if (planet === 'pluto') color = '#94a3b8';   // Slate
        else if (planet === 'north_node') color = '#34d399'; // Emerald

        return (
          <g key={planet} className="group">
            <circle
              cx={coord.x}
              cy={coord.y}
              r="8"
              fill="rgba(0, 0, 0, 0.7)"
              stroke={color}
              strokeWidth="1.2"
              className="cursor-help hover:scale-125 transition-transform duration-300"
            />
            <text
              x={coord.x}
              y={coord.y + 3.5}
              textAnchor="middle"
              fontSize="9px"
              fill={color}
              fontWeight="bold"
              className="pointer-events-none select-none font-sans"
            >
              {glyph}
            </text>
            <title>{planet.toUpperCase()}: {info.formatted}</title>
          </g>
        );
      })}

      {/* Axis Lines (ASC/DSC horizontal, MC vertical-ish) */}
      <line 
        x1={cx - r - 12} 
        y1={cy} 
        x2={cx + r + 12} 
        y2={cy} 
        stroke="rgba(6,182,212,0.4)" 
        strokeWidth="1.5" 
        strokeDasharray="3,3" 
      />
      {positions.midheaven && (() => {
        const pMc = getCoordinates(positions.midheaven.longitude, r + 12);
        const pIc = getCoordinates((positions.midheaven.longitude + 180) % 360, r + 12);
        return (
          <line
            x1={pMc.x}
            y1={pMc.y}
            x2={pIc.x}
            y2={pIc.y}
            stroke="rgba(6,182,212,0.4)"
            strokeWidth="1.5"
            strokeDasharray="3,3"
          />
        );
      })()}

      {/* Axis Labels */}
      <text x={cx - r - 20} y={cy + 4} fill="rgb(6,182,212)" fontSize="8px" fontWeight="bold" textAnchor="middle">ASC</text>
      <text x={cx + r + 20} y={cy + 4} fill="rgb(6,182,212)" fontSize="8px" fontWeight="bold" textAnchor="middle">DSC</text>
      
      {positions.midheaven && (() => {
        const mcLabelCoord = getCoordinates(positions.midheaven.longitude, r + 18);
        return (
          <text x={mcLabelCoord.x} y={mcLabelCoord.y + 3} fill="rgb(6,182,212)" fontSize="8px" fontWeight="bold" textAnchor="middle">MC</text>
        );
      })()}
    </svg>
  );
};

const VedicKundali = ({ siderealPositions }) => {
  if (!siderealPositions) return <div className="w-60 h-60 border border-dashed border-gray-700 animate-pulse flex items-center justify-center text-xs text-gray-600">No sidereal positions calculated</div>;

  const w = 300;
  const h = 300;
  const S = siderealPositions.ascendant?.rashi_number || 1;

  const planetAbbrevs = {
    sun: 'Su',
    moon: 'Mo',
    mars: 'Ma',
    mercury: 'Me',
    jupiter: 'Ju',
    venus: 'Ve',
    saturn: 'Sa',
    rahu: 'Ra',
    ketu: 'Ke',
  };

  // Group planets by house index (0-indexed, Houses 1 to 12)
  const housePlanets = Array.from({ length: 12 }, () => []);
  
  Object.entries(siderealPositions).forEach(([name, info]) => {
    if (name === 'ascendant') return;
    const abbrev = planetAbbrevs[name];
    if (!abbrev) return;
    const P = info.rashi_number;
    if (!P) return;
    const H = ((P - S + 12) % 12) + 1;
    housePlanets[H - 1].push(abbrev);
  });

  const houseLayout = {
    1: { sx: 150, sy: 65, px: 150, py: 90 },     // House 1 (Top center diamond)
    2: { sx: 78, sy: 30, px: 78, py: 50 },       // House 2 (Top left inner)
    3: { sx: 35, sy: 75, px: 35, py: 95 },       // House 3 (Top left outer)
    4: { sx: 76, sy: 140, px: 76, py: 165 },     // House 4 (Left center diamond)
    5: { sx: 35, sy: 225, px: 35, py: 245 },     // House 5 (Bottom left outer)
    6: { sx: 78, sy: 265, px: 78, py: 285 },     // House 6 (Bottom left inner)
    7: { sx: 150, sy: 215, px: 150, py: 240 },   // House 7 (Bottom center diamond)
    8: { sx: 221, sy: 265, px: 221, py: 285 },   // House 8 (Bottom right inner)
    9: { sx: 265, sy: 225, px: 265, py: 245 },   // House 9 (Bottom right outer)
    10: { sx: 223, sy: 140, px: 223, py: 165 },  // House 10 (Right center diamond)
    11: { sx: 265, sy: 75, px: 265, py: 95 },    // House 11 (Right top outer)
    12: { sx: 221, sy: 30, px: 221, py: 50 },    // House 12 (Right top inner)
  };

  return (
    <svg width={w} height={h} className="select-none text-white font-mono shadow-inner bg-black/60 rounded-xl border border-white/5">
      {/* Outer Boundary Square */}
      <rect x="10" y="10" width={w - 20} height={h - 20} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
      
      {/* Diagonal intersection lines */}
      <line x1="10" y1="10" x2={w - 10} y2={h - 10} stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
      <line x1={w - 10} y1="10" x2="10" y2={h - 10} stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />

      {/* Internal diamond path */}
      <path
        d={`M 150 10 L ${w - 10} 150 L 150 ${h - 10} L 10 150 Z`}
        fill="none"
        stroke="rgba(255,255,255,0.15)"
        strokeWidth="1.5"
      />

      {/* Render each of the 12 houses */}
      {Array.from({ length: 12 }).map((_, idx) => {
        const H = idx + 1;
        const signNum = ((S - 1 + idx) % 12) + 1;
        const layout = houseLayout[H];
        const planets = housePlanets[idx] || [];
        const isLagna = H === 1;

        return (
          <g key={H}>
            {/* Draw Rashi Sign Number */}
            <text
              x={layout.sx}
              y={layout.sy}
              textAnchor="middle"
              fontSize="10px"
              fill={isLagna ? 'rgb(168,85,247)' : 'rgba(255,255,255,0.4)'}
              fontWeight={isLagna ? 'bold' : 'normal'}
            >
              {signNum}
            </text>

            {/* Draw Planets List */}
            {planets.length > 0 && (
              <text
                x={layout.px}
                y={layout.py}
                textAnchor="middle"
                fontSize="11px"
                fill="#facc15"
                fontWeight="bold"
              >
                {planets.join(' ')}
              </text>
            )}

            {/* Lagna marker in House 1 */}
            {isLagna && (
              <text
                x={layout.sx}
                y={layout.sy - 12}
                textAnchor="middle"
                fontSize="7px"
                fill="rgb(168,85,247)"
                fontWeight="bold"
                letterSpacing="1"
              >
                LAGNA
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};
