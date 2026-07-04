import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Card, Row, Col, Tag, Button, Space, Progress, Statistic, Tooltip } from 'antd';
import { Play, Pause, RotateCw, Heart, Sparkles, Volume2, Bookmark, ChevronDown } from 'lucide-react';

type ChakraKey = 'heart' | 'crown' | 'third_eye' | 'throat' | 'solar_plexus' | 'sacral' | 'root';

interface Dharani {
  id: string;
  name: string;
  sanskrit: string;
  tradition: string;
  deity: string;
  mantra: string;
  freq: number;
  mala: number;
  chakra: ChakraKey | string;
}

interface LogEntry {
  id: number;
  mantra: string;
  deity: string;
  count: number;
  completed: string;
  frequency: number;
}

const DHARANIS: Dharani[] = [
  { id:'great_compassion', name:'Great Compassion', sanskrit:'Nīlakaṇṭha Dhāraṇī', tradition:'Mahayana', deity:'Avalokiteshvara', mantra:'Namo Ratna Trayāya… Oṃ Sarva-bhaya-śodhanāya…', freq:528, mala:108, chakra:'heart' },
  { id:'ushnisha_vijaya', name:'Ushnisha Vijaya', sanskrit:'Uṣṇīṣa Vijaya', tradition:'Mahayana', deity:'Namgyalma', mantra:'Oṃ Viśodhaya Viśodhaya…', freq:741, mala:108, chakra:'crown' },
  { id:'vajrasattva', name:'Vajrasattva 100-Syllable', sanskrit:'Śatākṣara', tradition:'Vajrayana', deity:'Vajrasattva', mantra:'Oṃ Vajrasattva Samayam…', freq:396, mala:108, chakra:'crown' },
  { id:'cundi', name:'Cundi Dharani', sanskrit:'Cundī Dhāraṇī', tradition:'Mahayana', deity:'Cundi Bodhisattva', mantra:'Oṃ Cale Cule Cundī Svāhā', freq:639, mala:108, chakra:'third_eye' },
  { id:'medicine_buddha', name:'Medicine Buddha', sanskrit:'Bhaiṣajyaguru', tradition:'Mahayana', deity:'Medicine Buddha', mantra:'Tadyathā: Oṃ Bhaiṣajye…', freq:528, mala:108, chakra:'heart' },
  { id:'amitabha', name:'Amitabha Rebirth', sanskrit:'Amitābha Dhāraṇī', tradition:'Pure Land', deity:'Amitabha', mantra:'Namo Amitābhāya… Oṃ Amṛte…', freq:963, mala:108, chakra:'crown' },
  { id:'green_tara', name:'Green Tara', sanskrit:'Ārya Tārā', tradition:'Vajrayana', deity:'Green Tara', mantra:'Oṃ Tāre Tuttāre Ture Svāhā', freq:639, mala:108, chakra:'heart' },
  { id:'guru_rinpoche', name:'Vajra Guru', sanskrit:'Padmasambhava', tradition:'Vajrayana', deity:'Guru Rinpoche', mantra:'Oṃ Āḥ Hūṃ Vajra Guru Padma Siddhi Hūṃ', freq:417, mala:108, chakra:'crown' },
  { id:'heart_sutra', name:'Heart Sutra', sanskrit:'Prajñāpāramitā', tradition:'Mahayana', deity:'Prajnaparamita', mantra:'Gate Gate Pāragate Pārasaṃgate Bodhi Svāhā', freq:852, mala:108, chakra:'third_eye' },
  { id:'manjushri', name:'Manjushri Wisdom', sanskrit:'Mañjuśrī', tradition:'Mahayana', deity:'Manjushri', mantra:'Oṃ A Ra Pa Ca Na Dhīḥ', freq:852, mala:108, chakra:'third_eye' },
  { id:'shurangama', name:'Shurangama Opening', sanskrit:'Śūraṅgama', tradition:'Mahayana', deity:'Shakyamuni', mantra:'Namaḥ Sarva-tathāgatāya…', freq:852, mala:108, chakra:'crown' },
];

const CHAKRA_COLORS: Record<string, string> = { heart:'#22c55e', crown:'#a855f7', third_eye:'#6366f1', throat:'#06b6d4', solar_plexus:'#fbbf24', sacral:'#f97316', root:'#ef4444' };

interface MandalaVisualProps {
  count: number;
  total: number;
  frequency: number;
  isReciting: boolean;
  chakra: ChakraKey | string;
}

// ─── Sacred Syllable Mandala ───
const MandalaVisual: React.FC<MandalaVisualProps> = ({ count, total, frequency, isReciting, chakra }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const color = CHAKRA_COLORS[chakra] || '#a855f7';

  useEffect(() => {
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    const w = 200, h = 200;
    ctx.clearRect(0, 0, w, h);

    // Background glow
    const grad = ctx.createRadialGradient(w/2, h/2, 20, w/2, h/2, 100);
    grad.addColorStop(0, `${color}15`);
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad; ctx.fillRect(0, 0, w, h);

    // Mala beads around perimeter
    const beads = 108;
    const radius = 80;
    const cx = w/2, cy = h/2;
    for (let i = 0; i < beads; i++) {
      const angle = (i / beads) * Math.PI * 2 - Math.PI / 2;
      const bx = cx + Math.cos(angle) * radius;
      const by = cy + Math.sin(angle) * radius;
      ctx.beginPath();
      ctx.arc(bx, by, 2, 0, Math.PI * 2);
      ctx.fillStyle = i < count ? color : '#1e293b';
      ctx.fill();
    }

    // Center glow
    const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, 30 + count/108*15);
    cg.addColorStop(0, `${color}60`);
    cg.addColorStop(1, 'transparent');
    ctx.fillStyle = cg;
    ctx.beginPath(); ctx.arc(cx, cy, 35, 0, Math.PI*2); ctx.fill();

    // Count
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(count.toString(), cx, cy + 8);

    // Frequency ring
    if (isReciting) {
      ctx.beginPath();
      ctx.arc(cx, cy, 60, 0, Math.PI * 2);
      ctx.strokeStyle = `${color}40`;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [count, total, frequency, isReciting, color]);

  return <canvas ref={canvasRef} width={200} height={200} className="mx-auto" />;
}

const DharaniReciter: React.FC = () => {
  const [selected, setSelected] = useState<Dharani>(DHARANIS[0]);
  const [count, setCount] = useState(0);
  const [isReciting, setIsReciting] = useState(false);
  const [rounds, setRounds] = useState(0);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [speed, setSpeed] = useState(1.5);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const dharani = useMemo(() => {
    // Find dharani data from knowledge base if loaded
    return selected;
  }, [selected]);

  const progress = useMemo(() => Math.round((count / (dharani.mala || 108)) * 100), [count, dharani.mala]);

  useEffect(() => {
    if (isReciting) {
      intervalRef.current = setInterval(() => {
        setCount(c => {
          const next = c + 1;
          if (next >= (dharani.mala || 108)) {
            // Round complete
            setRounds(r => r + 1);
            setLog(l => [{ id: Date.now(), mantra: dharani.name, deity: dharani.deity, count: dharani.mala, completed: new Date().toLocaleTimeString(), frequency: dharani.freq }, ...l].slice(0, 50));
            return 0;
          }
          return next;
        });
      }, 1000 / speed);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isReciting, speed, dharani.mala, dharani.name, dharani.deity, dharani.freq]);

  const handleToggle = () => setIsReciting(!isReciting);

  const handleSelectDharani = (d: Dharani) => {
    setIsReciting(false);
    setCount(0);
    setSelected(d);
  };

  const totalAccumulation = useMemo(() => rounds * (dharani.mala || 108) + count, [rounds, count, dharani.mala]);
  const totalRounds = useMemo(() => log.reduce((s, l) => s + l.count, 0) + count, [log, count]);

  return (
    <div className="space-y-4">
      {/* Selector */}
      <Row gutter={[8, 8]}>
        {DHARANIS.map(d => (
          <Col key={d.id} xs={12} sm={8} md={6}>
            <button
              onClick={() => handleSelectDharani(d)}
              className={`w-full text-left p-2.5 rounded-lg border transition-all text-xs ${
                selected.id === d.id
                  ? 'bg-purple-500/10 border-purple-500/30 shadow-[0_0_8px_rgba(168,85,247,0.15)]'
                  : 'bg-white/3 border-white/5 hover:border-purple-500/20'
              }`}
            >
              <div className="font-bold text-white truncate">{d.name}</div>
              <div className="text-[9px] text-slate-500 font-mono mt-0.5">{d.tradition} · {d.deity}</div>
            </button>
          </Col>
        ))}
      </Row>

      {/* Main Reciter Card */}
      <Card
        className="bg-gray-900/80 border-purple-500/20"
        styles={{ body: { padding: '24px' } }}
      >
        <Row gutter={[24, 16]} align="middle">
          {/* Mandala Visual */}
          <Col xs={24} md={10} className="flex justify-center">
            <div className="text-center">
              <MandalaVisual count={count} total={dharani.mala || 108} frequency={dharani.freq} isReciting={isReciting} chakra={dharani.chakra} />
              <Space size={4} className="mt-2">
                <Tag color="purple" className="text-[9px] font-mono">{dharani.sanskrit}</Tag>
                <Tag color="gold" className="text-[9px] font-mono">{dharani.freq} Hz</Tag>
              </Space>
            </div>
          </Col>

          {/* Controls + Info */}
          <Col xs={24} md={14}>
            <div className="space-y-4">
              {/* Header */}
              <div>
                <h3 className="text-lg font-bold text-white">{dharani.name}</h3>
                <p className="text-xs text-slate-400 mt-1">{dharani.deity} · {dharani.tradition}</p>
              </div>

              {/* Mantra text */}
              <div className="bg-black/30 rounded-lg p-3 border border-white/5">
                <p className="text-[11px] text-slate-300 font-mono leading-relaxed italic line-clamp-3">
                  {dharani.mantra}
                </p>
              </div>

              {/* Progress */}
              <div>
                <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                  <span>Mala Progress</span>
                  <span className="text-purple-400 font-mono">{count}/{dharani.mala} · {progress}%</span>
                </div>
                <Progress
                  percent={progress}
                  strokeColor={{ '0%': CHAKRA_COLORS[dharani.chakra], '100%': '#a855f7' }}
                  railColor="rgba(255,255,255,0.05)"
                  showInfo={false}
                  size="small"
                />
              </div>

              {/* Stats */}
              <Row gutter={[12, 12]}>
                <Col span={8}>
                  <Statistic
                    title={<span className="text-[9px] text-slate-500">ROUNDS</span>}
                    value={rounds}
                    styles={{ content: { color: '#a855f7', fontSize: '18px', fontWeight: 'bold' } }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title={<span className="text-[9px] text-slate-500">ACCUMULATED</span>}
                    value={totalAccumulation.toLocaleString()}
                    styles={{ content: { color: '#22d3ee', fontSize: '18px', fontWeight: 'bold' } }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title={<span className="text-[9px] text-slate-500">SPEED</span>}
                    value={`${speed}x`}
                    styles={{ content: { color: '#fbbf24', fontSize: '18px', fontWeight: 'bold' } }}
                  />
                </Col>
              </Row>

              {/* Controls */}
              <Space size={8}>
                <Button
                  type="primary"
                  icon={isReciting ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  onClick={handleToggle}
                  style={{ background: isReciting ? '#dc2626' : 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none', fontWeight: 'bold' }}
                >
                  {isReciting ? `Stop · ${count}` : 'Begin Recitation'}
                </Button>
                <Button ghost size="small" onClick={() => { setCount(0); setIsReciting(false); }}>
                  <RotateCw className="w-3.5 h-3.5" />
                </Button>
                <Tooltip title="Recitation speed">
                  <Button ghost size="small" onClick={() => setSpeed(s => s >= 5 ? 0.5 : s + 0.5)}>
                    {speed}x
                  </Button>
                </Tooltip>
              </Space>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Accumulation Log */}
      {log.length > 0 && (
        <Card
          size="small"
          title={<span className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider"><Bookmark className="w-3.5 h-3.5 inline mr-1" />ACCUMULATION LOG</span>}
          className="bg-gray-900/80 border-purple-500/20"
          styles={{ body: { padding: '12px', maxHeight: '200px', overflowY: 'auto' } }}
        >
          <div className="space-y-1.5">
            {log.slice(0, 15).map((entry) => (
              <div key={entry.id} className="flex items-center justify-between text-[10px] px-2 py-1 bg-white/3 rounded-md border border-white/5">
                <div className="flex items-center gap-2">
                  <Heart className="w-3 h-3 text-rose-400" />
                  <span className="text-white font-medium">{entry.mantra}</span>
                  <span className="text-slate-500">· {entry.deity}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-purple-400 font-mono">{entry.count}×</span>
                  <span className="text-slate-600">{entry.completed}</span>
                  <span className="text-[9px] text-amber-400">{entry.frequency}Hz</span>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center text-[9px] text-slate-600 mt-2 py-1 border-t border-white/5">
            Total accumulated: {totalRounds.toLocaleString()} recitations · Dedicated to the liberation of all beings
          </div>
        </Card>
      )}
    </div>
  );
};

export default DharaniReciter;
