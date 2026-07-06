import React, { useState, useEffect, useMemo } from 'react';
import { Clock, RefreshCw, ShieldAlert, Sparkles, Clipboard, RotateCcw, AlertTriangle, AlertOctagon, Hexagon } from 'lucide-react';
import { Card, DatePicker, Button, Tag, Segmented, Progress, Empty, Modal, message, Select } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { audioFeedback } from '../../utils/audioFeedback';
import {
  aspectCategory, aspectGlyph, planetGlyph,
  isHouseCusp, natalDisplayName,
} from '../../lib/astroHelpers';
import { formatTransitReportMarkdown, formatTransitReportJSON } from '../../lib/astrologyExport';
import type { SavedChart } from './SavedChartsDrawer';
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
type AspectFilter = 'all' | 'harmonious' | 'challenging' | 'minor' | 'cusp';
type ExportFormat = 'markdown' | 'json';

interface TransitComparisonProps {
  chart?: TransitChart | null;
  /**
   * Saved charts from the parent. When provided alongside
   * ``onSelectChart``, an inline AntD ``Select`` dropdown is rendered in the
   * header (and inside the empty-state) so users can switch the active
   * transit chart without opening the Saved Charts drawer. Mirrors the
   * pattern already used in ``SynastryViewer.tsx``.
   */
  charts?: SavedChart[];
  onSelectChart?: (chart: SavedChart) => void;
}

export default function TransitComparison({ chart, charts, onSelectChart }: TransitComparisonProps) {
  const [transitTime, setTransitTime] = useState<Dayjs>(() => dayjs());
  const [loading, setLoading] = useState<boolean>(false);
  const [transitData, setTransitData] = useState<TransitDataPayload | null>(null);
  const [activeTab, setActiveTab] = useState<TransitTab>('Western');
  const [aspectFilter, setAspectFilter] = useState<AspectFilter>('all');
  const [exportFormat, setExportFormat] = useState<ExportFormat>('markdown');
  const [exporting, setExporting] = useState<boolean>(false);
  // When non-null, shows the export-preview Modal so users can SEE the result
  // of the markdown / JSON toggle (previously the toggle silently copied to
  // clipboard with no visible feedback, which made it feel broken).
  const [previewContent, setPreviewContent] = useState<string | null>(null);
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

  // Inline chart-picker options for the header dropdown (and empty state).
  // Pattern mirrors SynastryViewer.tsx:166-181.
  const chartPickerOptions = useMemo(
    () =>
      (charts ?? []).map((c) => ({
        value: c.id,
        label: `${c.name} (${c.city})`,
      })),
    [charts],
  );

  const handleSelectChart = (id: unknown) => {
    if (!onSelectChart || !charts) return;
    const picked = charts.find((c) => c.id === id);
    if (picked) {
      audioFeedback.playClick();
      onSelectChart(picked);
    }
  };

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
      // Show the formatted output in a Modal so users can see what the
      // markdown/JSON toggle produced. Still copy to clipboard for convenience.
      setPreviewContent(formatted);
      try {
        await navigator.clipboard.writeText(formatted);
        message.success('Copied to clipboard — preview shown below.');
      } catch {
        // Clipboard can fail in non-secure contexts; preview still shows.
        message.info('Preview shown below (clipboard copy failed).');
      }
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
    // Cusp aspects (natal target = house_N) get their own bucket so they don't
    // displace planet-to-planet aspects in the harmonious / challenging lists.
    if (aspectFilter === 'cusp') {
      return raw.filter((a) => isHouseCusp(String(a.natal_planet || '')));
    }
    // For all other filters, exclude cusps from the displayed list.
    const nonCusp = raw.filter((a) => !isHouseCusp(String(a.natal_planet || '')));
    if (aspectFilter === 'all') return nonCusp;
    if (aspectFilter === 'minor') {
      // 'minor' = non-harmonious AND non-challenging (semisquare, sesquiquadrate, quincunx, etc.)
      return nonCusp.filter((a) => {
        const c = aspectCategory(a.aspect);
        return c !== 'harmonious' && c !== 'challenging';
      });
    }
    return nonCusp.filter((a) => aspectCategory(a.aspect) === aspectFilter);
  }, [transitData, aspectFilter]);

  const aspectStats = useMemo(() => {
    const all = transitData?.aspects || [];
    let harmonious = 0, challenging = 0, minor = 0, cusp = 0;
    for (const a of all) {
      if (isHouseCusp(String(a.natal_planet || ''))) {
        cusp++;
        continue;
      }
      const c = aspectCategory(a.aspect);
      if (c === 'harmonious') harmonious++;
      else if (c === 'challenging') challenging++;
      else minor++;
    }
    return { total: all.length, harmonious, challenging, minor, cusp };
  }, [transitData]);

  const baziInteractions: BaziInteraction[] = transitData?.bazi_clashes?.interactions || [];

  // Split BaZi interactions into:
  //   - per-pillar groups (pair interactions keyed by their source pillar)
  //   - crossPillarPatterns (set-based interactions that span multiple pillars:
  //     Three-Harmony trines, three-way Punishments)
  // The pre-expansion engine only produced "Year-Year" / "Day→Month" style
  // labels, which the old /^(Year|Month|Day|Hour)/ regex matched. The expanded
  // engine also emits "Three-Harmony", "Three-Harmony (Partial)", and
  // "Three-Way Punishment" labels — those don't match the regex and were
  // silently dropped, which is why users saw only the same-pillar clashes.
  const { baziByPillar, baziCrossPillar } = useMemo<{
    baziByPillar: Record<string, BaziInteraction[]>;
    baziCrossPillar: BaziInteraction[];
  }>(() => {
    const groups: Record<string, BaziInteraction[]> = {
      'Year': [], 'Month': [], 'Day': [], 'Hour': [],
    };
    const crossPillar: BaziInteraction[] = [];
    for (const ix of baziInteractions) {
      const label = ix.pillar || '';
      // Set-based interactions go to a separate bucket — they span multiple
      // pillars simultaneously and don't belong to any single one.
      const isSetBased = /^Three[- ]/i.test(label);
      if (isSetBased) {
        crossPillar.push(ix);
        continue;
      }
      // Pair-based interactions: bucket by their SOURCE pillar (the one
      // before "-" or "→"). "Year-Year" → Year, "Day→Hour" → Day, etc.
      const m = label.match(/^(Year|Month|Day|Hour)/);
      if (m) groups[m[1]].push(ix);
      else crossPillar.push(ix);
    }
    return { baziByPillar: groups, baziCrossPillar: crossPillar };
  }, [baziInteractions]);

  // Pick the most "severe" color for a pillar's tag so users can scan quickly.
  // Severity order: Clash/Punishment > Harm > Harmony/Three-Harmony > none.
  function baziTagColor(interactions: BaziInteraction[]): string {
    if (interactions.length === 0) return 'default';
    const types = new Set(interactions.map((i) => i.type));
    if (types.has('Clash') || types.has('Punishment')) return 'red';
    if (types.has('Harm')) return 'orange';
    if (types.has('Harmony') || types.has('Three-Harmony')) return 'green';
    return 'default';
  }

  // Per-interaction rendering: icon + color classes.
  function baziInteractionStyle(type: string): { icon: typeof ShieldAlert; classes: string } {
    switch (type) {
      case 'Clash':
        return { icon: ShieldAlert, classes: 'bg-rose-950/15 border-rose-500/20 text-rose-300' };
      case 'Harm':
        return { icon: AlertTriangle, classes: 'bg-amber-950/15 border-amber-500/20 text-amber-300' };
      case 'Punishment':
        return { icon: AlertOctagon, classes: 'bg-red-950/15 border-red-500/20 text-red-300' };
      case 'Three-Harmony':
        return { icon: Hexagon, classes: 'bg-cyan-950/15 border-cyan-500/20 text-cyan-300' };
      case 'Three-Harmony (Partial)':
        return { icon: Hexagon, classes: 'bg-teal-950/15 border-teal-500/20 text-teal-300' };
      case 'Harmony':
      default:
        return { icon: Sparkles, classes: 'bg-emerald-950/15 border-emerald-500/20 text-emerald-300' };
    }
  }

  if (!chart) {
    return (
      <Card
        className="bg-gray-900/80 border-purple-500/20"
        title={
          <span className="text-amber-400 text-xs tracking-wider uppercase font-mono flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-amber-400" />
            TRANSITS TO NATAL
          </span>
        }
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="space-y-4 py-2">
              <p className="text-sm text-amber-400 font-mono">No natal chart selected</p>
              {chartPickerOptions.length > 0 && onSelectChart ? (
                <div className="flex flex-col items-center gap-2">
                  <p className="text-xs text-gray-500 italic">…or pick one from your saved charts:</p>
                  <Select
                    value={undefined}
                    onChange={handleSelectChart}
                    options={chartPickerOptions}
                    placeholder="Select a saved chart"
                    style={{ minWidth: 280 }}
                    classNames={{ popup: { root: 'bg-gray-950 border-gray-800 text-white' } }}
                  />
                </div>
              ) : (
                <p className="text-xs text-gray-500 italic max-w-md mx-auto">
                  Open the Saved Charts drawer and click the "Use for Transit" button on a saved chart
                  to begin comparing current planetary transits to your natal placements.
                </p>
              )}
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
            {chartPickerOptions.length > 0 && onSelectChart && (
              <Select
                size="small"
                value={chart?.id}
                onChange={handleSelectChart}
                options={chartPickerOptions}
                placeholder="Switch chart"
                style={{ minWidth: 180 }}
                classNames={{ popup: { root: 'bg-gray-950 border-gray-800 text-white' } }}
              />
            )}
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
                    { label: `Cusps (${aspectStats.cusp})`, value: 'cusp' },
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
              <p className="text-[10px] text-amber-500/70 leading-relaxed bg-amber-500/5 border border-amber-500/10 rounded px-2 py-1">
                <strong>Sidereal (Lahiri ayanamsa).</strong> Houses are counted whole-sign from the natal Moon rashi.
                The transit rashis here are therefore ~24° behind the Tropical placements shown in the Western tab —
                this is correct Vedic practise, not a sign mismatch.
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
                impacts on the other natal pillars are evaluated for Clashes (六冲), Harmonies (六合),
                Harms (相害), Punishments (相刑 — Zi-Mao mutual, Yin-Si-Shen, Chou-Xu-Wei three-way),
                and Three-Harmony Trines (三合 — full and partial).
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
                          color={baziTagColor(interactions)}
                          className="text-[9px] font-mono leading-none m-0"
                        >
                          {interactions.length === 0
                            ? 'no interactions'
                            : `${interactions.length} ${interactions.length === 1 ? 'note' : 'notes'}`}
                        </Tag>
                      </div>
                      {interactions.length > 0 ? (
                        <div className="p-2 space-y-2">
                          {interactions.map((ix, idx) => {
                            const { icon: Icon, classes } = baziInteractionStyle(ix.type);
                            return (
                              <div
                                key={idx}
                                className={`p-3 border rounded-xl flex items-start gap-3 ${classes}`}
                              >
                                <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                <div>
                                  <span className="font-bold text-xs block font-mono">
                                    {ix.type}: {ix.pillar}
                                  </span>
                                  <p className="text-[10px] text-gray-300 leading-relaxed mb-0 mt-1">
                                    {ix.description}
                                  </p>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="p-3 text-center text-[10px] text-gray-500 italic font-mono">
                          No clashes, harmonies, harms, or punishments for the {pillar.toLowerCase()} pillar.
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Cross-pillar set-based patterns: Three-Harmony trines and
                    three-way Punishments span multiple pillars at once, so
                    they don't belong to any single pillar card above. */}
                {baziCrossPillar.length > 0 && (
                  <div className="border border-white/5 rounded-xl overflow-hidden">
                    <div className="px-3 py-2 bg-black/50 border-b border-white/5 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] text-cyan-400 font-mono font-bold tracking-widest uppercase">
                          Cross-Pillar Patterns
                        </span>
                        <span className="text-[9px] text-gray-500 italic">
                          Three-Harmony trines &amp; three-way punishments
                        </span>
                      </div>
                      <Tag
                        color={baziTagColor(baziCrossPillar)}
                        className="text-[9px] font-mono leading-none m-0"
                      >
                        {baziCrossPillar.length} {baziCrossPillar.length === 1 ? 'note' : 'notes'}
                      </Tag>
                    </div>
                    <div className="p-2 space-y-2">
                      {baziCrossPillar.map((ix, idx) => {
                        const { icon: Icon, classes } = baziInteractionStyle(ix.type);
                        return (
                          <div
                            key={idx}
                            className={`p-3 border rounded-xl flex items-start gap-3 ${classes}`}
                          >
                            <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <div>
                              <span className="font-bold text-xs block font-mono">
                                {ix.type}: {ix.pillar}
                              </span>
                              <p className="text-[10px] text-gray-300 leading-relaxed mb-0 mt-1">
                                {ix.description}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Export preview — visible feedback for the markdown / JSON toggle.
          Previously the toggle changed format silently and only wrote to the
          clipboard, which made it feel broken. Now users can see the result. */}
      <Modal
        open={previewContent !== null}
        onCancel={() => setPreviewContent(null)}
        title={
          <span className="font-mono text-xs uppercase tracking-wider text-amber-400">
            Export Preview ({exportFormat})
          </span>
        }
        width={720}
        footer={[
          <Button key="close" onClick={() => setPreviewContent(null)}>
            Close
          </Button>,
          <Button
            key="copy"
            type="primary"
            onClick={async () => {
              if (previewContent == null) return;
              try {
                await navigator.clipboard.writeText(previewContent);
                message.success('Copied to clipboard!');
              } catch {
                message.error('Clipboard copy failed — select text manually.');
              }
            }}
          >
            Copy to clipboard
          </Button>,
        ]}
      >
        <pre className="text-[10px] leading-snug font-mono text-gray-200 bg-black/40 border border-white/5 rounded p-3 max-h-[60vh] overflow-auto whitespace-pre-wrap">
{previewContent ?? ''}
        </pre>
      </Modal>
    </Card>
  );
}
