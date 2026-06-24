import React, { useState, useEffect, useMemo } from 'react';
import { Clock, RefreshCw, ShieldAlert, Sparkles, Clipboard, RotateCcw } from 'lucide-react';
import { Card, DatePicker, Button, Tag, Segmented, Progress, Empty, message } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { audioFeedback } from '../../utils/audioFeedback';
import {
  aspectCategory, aspectGlyph, planetGlyph,
  isHouseCusp, natalDisplayName,
} from '../../lib/astroHelpers';
import { formatTransitReportMarkdown, formatTransitReportJSON } from '../../lib/astrologyExport';
import { createLogger } from '../../utils/logger';

const ASPECT_COLORS: Record<string, string> = {
  conjunction: 'text-green-400 border-green-500/20 bg-green-500/10',
  trine: 'text-blue-400 border-blue-500/20 bg-blue-500/10',
  sextile: 'text-purple-400 border-purple-500/20 bg-purple-500/10',
  square: 'text-red-400 border-red-500/20 bg-red-500/10',
  opposition: 'text-orange-400 border-orange-500/20 bg-orange-500/10',
};

// Color legend for the aspect category filter — shows users what each color means.
const ASPECT_LEGEND: Array<{ key: string; label: string; color: string }> = [
  { key: 'conjunction', label: 'Conjunction (0°)', color: 'bg-green-500' },
  { key: 'trine', label: 'Trine (120°)', color: 'bg-blue-500' },
  { key: 'sextile', label: 'Sextile (60°)', color: 'bg-purple-500' },
  { key: 'square', label: 'Square (90°)', color: 'bg-red-500' },
  { key: 'opposition', label: 'Opposition (180°)', color: 'bg-orange-500' },
];

const GOCHARA_DESCRIPTIONS: Record<number, string> = {
  1: "Focus on health, self-projection, and personal initiative.",
  2: "Financial developments, family affairs, and speech dynamics.",
  3: "Initiative, courage, mental agility, and communication.",
  4: "Domestic peace, mother's health, and emotional comfort.",
  5: "Creative pursuits, romance, intellect, and spiritual practices.",
  6: "Victory over challenges, health focus, and daily routines.",
  7: "Partnerships, marital affairs, and public relationships.",
  8: "Transformation, secrets, research, and longevity factors.",
  9: "Luck, wisdom teachings, travel, and religious growth.",
  10: "Career achievements, public standing, and actions.",
  11: "Gains, desires fulfilled, friendships, and networks.",
  12: "Expenses, spiritual retreat, sleep patterns, and isolation."
};


const PILLAR_ORDER = ['Year', 'Month', 'Day', 'Hour'];
const PILLAR_LABELS: Record<string, string> = {
  'Year': 'Year Pillar (ancestry, social)',
  'Month': 'Month Pillar (parents, work)',
  'Day': 'Day Pillar (self, spouse)',
  'Hour': 'Hour Pillar (children, old age)',
};

interface TransitChart {
  id: string;
  name: string;
  [key: string]: unknown;
}

interface TransitAspect {
  transit_planet: string;
  natal_planet: string;
  aspect: string;
  orb: number;
  exactness: number;
  [key: string]: unknown;
}

interface GocharaEntry {
  gochara_house: number;
  transit_rashi: string;
  transit_degree: number;
  [key: string]: unknown;
}

interface BaziInteraction {
  type: string;
  pillar: string;
  description: string;
  [key: string]: unknown;
}

interface BaziClashes {
  interactions?: BaziInteraction[];
  [key: string]: unknown;
}

interface TransitDataPayload {
  aspects?: TransitAspect[];
  gochara?: Record<string, GocharaEntry>;
  bazi_clashes?: BaziClashes;
  [key: string]: unknown;
}

type TransitTab = 'Western' | 'Vedic Gochara' | 'Chinese Pillars';
type AspectFilter = 'all' | 'harmonious' | 'challenging';
type ExportFormat = 'markdown' | 'json';

interface TransitComparisonProps {
  chart?: TransitChart | null;
}

export default function TransitComparison({ chart }: TransitComparisonProps) {
  const [transitTime, setTransitTime] = useState<Dayjs>(() => dayjs());
  const [loading, setLoading] = useState<boolean>(false);
  const [transitData, setTransitData] = useState<TransitDataPayload | null>(null);
  const [activeTab, setActiveTab] = useState<TransitTab>('Western');
  const [aspectFilter, setAspectFilter] = useState<AspectFilter>('all');
  const [exportFormat, setExportFormat] = useState<ExportFormat>('markdown');
  const [exporting, setExporting] = useState<boolean>(false);
  const log = createLogger('TransitComparison');

  const transitTimeIso = transitTime.toISOString();

  const fetchTransits = async () => {
    if (!chart) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/astrology/charts/${chart.id}/transits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transit_time_iso: transitTimeIso })
      });
      if (response.ok) {
        const result = await response.json();
        setTransitData(result.data as TransitDataPayload);
        audioFeedback.playSuccess();
      } else {
        audioFeedback.playError();
        message.error(`Failed to load transits: HTTP ${response.status}`);
      }
    } catch (e) {
      log.error(e);
      audioFeedback.playError();
      message.error('Could not load transits: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (chart) {
      fetchTransits();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chart]);

  const handleExport = async () => {
    if (!transitData || !chart) return;
    setExporting(true);
    try {
      const response = await fetch(`/api/v1/astrology/charts/${chart.id}/transit-export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // BUG FIX: send transit_time_iso so the export reflects the user's
        // selected time, not "now" (backend fell back to datetime.now()).
        body: JSON.stringify({ transit_time_iso: transitTimeIso })
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      const data = result.data || result;
      const formatted = exportFormat === 'json'
        ? formatTransitReportJSON(data)
        : formatTransitReportMarkdown(data);
      await navigator.clipboard.writeText(formatted);
      message.success('Copied to clipboard!');
    } catch (e) {
      message.error('Export failed: ' + (e as Error).message);
    } finally {
      setExporting(false);
    }
  };

  // Quick-set helpers for transit exploration
  const setNow = () => setTransitTime(dayjs());
  const shiftDays = (n: number) => setTransitTime((prev) => prev.add(n, 'day'));

  const aspects = useMemo<TransitAspect[]>(() => {
    const raw = transitData?.aspects || [];
    if (aspectFilter === 'all') return raw;
    if (aspectFilter === 'minor') {
      // 'minor' means non-harmonious AND non-challenging (semisquare, sesquiquadrate, quincunx, etc.)
      return raw.filter((a) => {
        const c = aspectCategory(a.aspect);
        return c !== 'harmonious' && c !== 'challenging';
      });
    }
    return raw.filter((a) => aspectCategory(a.aspect) === aspectFilter);
  }, [transitData, aspectFilter]);

  const aspectStats = useMemo(() => {
    const all = transitData?.aspects || [];
    let harmonious = 0, challenging = 0, minor = 0;
    for (const a of all) {
      const c = aspectCategory(a.aspect);
      if (c === 'harmonious') harmonious++;
      else if (c === 'challenging') challenging++;
      else minor++;
    }
    return { total: all.length, harmonious, challenging, minor };
  }, [transitData]);

  const baziInteractions: BaziInteraction[] = transitData?.bazi_clashes?.interactions || [];

  const baziByPillar = useMemo<Record<string, BaziInteraction[]>>(() => {
    const groups: Record<string, BaziInteraction[]> = { 'Year': [], 'Month': [], 'Day': [], 'Hour': [] };
    for (const ix of baziInteractions) {
      const label = ix.pillar || '';
      // Match canonical pillar prefixes ("Year-Year", "Month-Day", etc.)
      const m = label.match(/^(Year|Month|Day|Hour)/);
      const key = m ? m[1] : null;
      if (key) groups[key].push(ix);
    }
    return groups;
  }, [baziInteractions]);

  if (!chart) {
    return (
      <Card className="bg-gray-900/80 border-purple-500/20">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="space-y-2 py-2">
              <p className="text-sm text-amber-400 font-mono">No natal chart selected</p>
              <p className="text-xs text-gray-500 italic max-w-md mx-auto">
                Open the Saved Charts drawer and click the "Use for Transit" button on a saved chart
                to begin comparing current planetary transits to your natal placements.
              </p>
            </div>
          }
        />
      </Card>
    );
  }

  const gochara: Record<string, GocharaEntry> = transitData?.gochara || {};

  return (
    <Card
      title={
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono">
          <span className="text-amber-400 text-xs tracking-wider uppercase flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-amber-400" />
            TRANSITS TO NATAL: {chart.name}
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            <DatePicker
              showTime={{ format: 'HH:mm' }}
              format="YYYY-MM-DD HH:mm"
              value={transitTime}
              onChange={(val) => val && setTransitTime(val)}
              allowClear={false}
              size="small"
              className="!bg-gray-800 !border-gray-700 [&>input]:!text-white [&>input]:!text-xs"
              style={{ width: 170 }}
            />
            <Button
              size="small"
              icon={<RotateCcw className="w-3 h-3" />}
              onClick={setNow}
              title="Reset to current time"
              className="!text-[10px]"
            >
              Now
            </Button>
            <Button
              size="small"
              onClick={() => shiftDays(-1)}
              title="Shift transit time back 1 day"
              className="!text-[10px]"
            >
              −1d
            </Button>
            <Button
              size="small"
              onClick={() => shiftDays(1)}
              title="Shift transit time forward 1 day"
              className="!text-[10px]"
            >
              +1d
            </Button>
            <Button
              size="small"
              type="primary"
              onClick={fetchTransits}
              loading={loading}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', border: 'none' }}
            >
              Recalculate
            </Button>
          </div>
        </div>
      }
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '20px' } }}
    >
      <div className="flex justify-center mb-5">
        <Segmented
          options={['Western', 'Vedic Gochara', 'Chinese Pillars']}
          value={activeTab}
          onChange={(val) => { audioFeedback.playTabChange(); setActiveTab(val as TransitTab); }}
          className="bg-black/40 border border-white/5 p-1 text-xs"
        />
      </div>

      {transitData && (
        <div className="flex items-center justify-end gap-2 mb-4">
          <Segmented
            size="small"
            value={exportFormat}
            onChange={(v) => setExportFormat(v as ExportFormat)}
            options={[
              { label: 'Markdown', value: 'markdown' },
              { label: 'JSON', value: 'json' },
            ]}
            className="bg-black/40 border border-white/5 text-[10px]"
          />
          <Button
            size="small"
            icon={<Clipboard size={12} />}
            onClick={handleExport}
            loading={exporting}
            className="text-[10px]"
            style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', border: 'none', color: '#fff' }}
          >
            Copy for LLM
          </Button>
        </div>
      )}

      {loading ? (
        <div className="text-center italic text-gray-500 text-xs py-16 animate-pulse">
          Recalculating planetary geometries...
        </div>
      ) : (
        <div>
          {activeTab === 'Western' && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
                <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-0">
                  Active Transit-to-Natal Aspects
                </h4>
                <Segmented
                  size="small"
                  value={aspectFilter}
                  onChange={(v) => { audioFeedback.playTabChange(); setAspectFilter(v as AspectFilter); }}
                  options={[
                    { label: `All (${aspectStats.total})`, value: 'all' },
                    { label: `Harmonious (${aspectStats.harmonious})`, value: 'harmonious' },
                    { label: `Challenging (${aspectStats.challenging})`, value: 'challenging' },
                    { label: `Minor (${aspectStats.minor})`, value: 'minor' },
                  ]}
                  className="bg-black/40 border border-white/5 text-[10px]"
                />
              </div>
              {/* Aspect color legend — tells the user what each color means */}
              <div className="flex items-center gap-2 flex-wrap text-[9px] font-mono text-gray-500">
                <span className="text-gray-600 uppercase tracking-wider">Legend:</span>
                {ASPECT_LEGEND.map((legend) => (
                  <span key={legend.key} className="flex items-center gap-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${legend.color}`} />
                    <span>{legend.label}</span>
                  </span>
                ))}
              </div>
              {aspects.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[350px] overflow-y-auto pr-1">
                  {aspects.map((asp, idx) => {
                    const aspectColor = ASPECT_COLORS[asp.aspect] || 'bg-white/5 border-white/5 text-white';
                    const transitGlyph = planetGlyph(asp.transit_planet);
                    const natalGlyph = isHouseCusp(asp.natal_planet) ? '⌖' : planetGlyph(asp.natal_planet);
                    const aspectChar = aspectGlyph(asp.aspect);
                    const cuspFlag = isHouseCusp(asp.natal_planet);

                    return (
                      <div
                        key={`${asp.transit_planet}-${asp.natal_planet}-${asp.aspect}-${idx}`}
                        className={`p-3 border rounded-xl flex items-start justify-between gap-3 transition-colors ${aspectColor} ${
                          cuspFlag ? 'ring-1 ring-amber-500/30' : ''
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 mb-1 text-[11px] font-mono font-bold">
                            <span className="capitalize">{asp.transit_planet}</span>
                            <span className="text-[13px]">{aspectChar}</span>
                            {/* Bug fix: natalDisplayName already returns
                                'Natal Cusp H1' for cusps but 'sun' for plain
                                planets — adding 'Natal ' prefix here caused
                                'sun △ Natal sun' duplication. Only add
                                'Natal ' prefix for cusp targets. */}
                            <span className="capitalize text-slate-300">
                              {cuspFlag ? `Natal ${natalDisplayName(asp.natal_planet)}` : natalDisplayName(asp.natal_planet)}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Progress
                              percent={Math.round(asp.exactness * 100)}
                              size="small"
                              showInfo={false}
                              strokeColor="currentColor"
                              railColor="rgba(0,0,0,0.4)"
                              style={{ width: '60px', margin: 0 }}
                            />
                            <span className="text-[8px] font-mono leading-none">
                              {Math.round(asp.exactness * 100)}% exact · {asp.orb}° orb
                            </span>
                          </div>
                        </div>
                        {/* Bug fix: was `{aspectGlyph}` (no argument) which
                            always rendered the default ○ circle. Now uses
                            the already-computed `aspectChar` so the
                            watermark reflects the actual aspect type. */}
                        <div className="text-xl opacity-20 select-none font-sans font-bold pt-1">
                          {transitGlyph}{aspectChar}{natalGlyph}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty
                  description={
                    aspectFilter === 'all'
                      ? "No transit-to-natal aspects in orb."
                      : `No ${aspectFilter} aspects in orb.`
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </div>
          )}

          {activeTab === 'Vedic Gochara' && (
            <div className="space-y-4">
              <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-1">
                Gochara (Transit Grahas from Natal Moon)
              </h4>
              <p className="text-[10px] text-gray-500 italic leading-relaxed">
                In Vedic Jyotish, planetary transits are analyzed relative to the Rashi (sign) of the Moon at birth.
                Below are the active transit houses and their traditional focus points.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 max-h-[350px] overflow-y-auto pr-1">
                {Object.entries(gochara).map(([planet, data]) => {
                  const glyph = planetGlyph(planet);
                  return (
                    <div
                      key={planet}
                      className="p-3 bg-black/45 border border-white/5 rounded-xl space-y-1.5 hover:border-amber-500/20 transition-colors"
                    >
                      <div className="flex justify-between items-center">
                        <span className="capitalize text-xs font-bold text-slate-300 font-mono flex items-center gap-1.5">
                          <span className="text-amber-400 text-sm font-sans">{glyph}</span>
                          {planet}
                        </span>
                        <Tag color="gold" className="text-[9px] font-mono leading-none m-0">
                          H{data.gochara_house}
                        </Tag>
                      </div>
                      <div className="text-[9px] text-amber-500 font-mono">
                        {data.transit_rashi} ({data.transit_degree.toFixed(2)}°)
                      </div>
                      <p className="text-[10px] text-gray-400 leading-snug mb-0 pt-1 border-t border-white/5">
                        {GOCHARA_DESCRIPTIONS[data.gochara_house]}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'Chinese Pillars' && (
            <div className="space-y-4">
              <h4 className="text-[10px] font-bold text-gray-400 font-mono tracking-widest uppercase mb-1">
                BaZi Four Pillars: Transit × Natal Interactions
              </h4>
              <p className="text-[10px] text-gray-500 italic leading-relaxed">
                Each transit pillar (Year, Month, Day, Hour) is compared against its natal counterpart.
                Same-pillar pairs (Year-Year, Month-Month, Day-Day, Hour-Hour) and cross-pillar Day
                impacts on the other natal pillars are all evaluated for Clashes and Harmonies.
              </p>

              <div className="space-y-3">
                {PILLAR_ORDER.map((pillar) => {
                  const interactions = baziByPillar[pillar] || [];
                  return (
                    <div key={pillar} className="border border-white/5 rounded-xl overflow-hidden">
                      <div className="px-3 py-2 bg-black/50 border-b border-white/5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] text-amber-400 font-mono font-bold tracking-widest uppercase">
                            {pillar} Pillar
                          </span>
                          <span className="text-[9px] text-gray-500 italic">
                            {PILLAR_LABELS[pillar]}
                          </span>
                        </div>
                        <Tag
                          color={interactions.length === 0 ? 'default' : interactions.some(i => i.type === 'Clash') ? 'red' : 'green'}
                          className="text-[9px] font-mono leading-none m-0"
                        >
                          {interactions.length === 0
                            ? 'no interactions'
                            : `${interactions.length} ${interactions.length === 1 ? 'note' : 'notes'}`}
                        </Tag>
                      </div>
                      {interactions.length > 0 ? (
                        <div className="p-2 space-y-2">
                          {interactions.map((ix, idx) => (
                            <div
                              key={idx}
                              className={`p-3 border rounded-xl flex items-start gap-3 ${
                                ix.type === 'Clash'
                                  ? 'bg-rose-950/15 border-rose-500/20 text-rose-300'
                                  : 'bg-emerald-950/15 border-emerald-500/20 text-emerald-300'
                              }`}
                            >
                              {ix.type === 'Clash' ? (
                                <ShieldAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
                              ) : (
                                <Sparkles className="w-5 h-5 flex-shrink-0 mt-0.5" />
                              )}
                              <div>
                                <span className="font-bold text-xs block font-mono">
                                  {ix.type}: {ix.pillar}
                                </span>
                                <p className="text-[10px] text-gray-300 leading-relaxed mb-0 mt-1">
                                  {ix.description}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-3 text-center text-[10px] text-gray-500 italic font-mono">
                          No clashes or harmonies for the {pillar.toLowerCase()} pillar.
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
