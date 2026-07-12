/**
 * AdvancedAstrologyPanel — exposes 10 hidden backend astrology endpoints
 * (Solar Return, Progressions, Year Ahead, Profection, Solar Arc,
 *  Astrocartography, Lots, Fixed Stars, Midpoints, Antiscia) behind a
 *  single tabbed UI.
 *
 * Optional ``activeChart`` prop: when the parent (AstrologyPanel) has a
 * chart selected in the wheel tab above, pass it down here so the user
 * doesn't have to re-type natal data. Falls back to the previous hardcoded
 * defaults (NYC 1990-01-01) when no chart is selected — preserves
 * backward compatibility for any caller that mounts this without a parent.
 */
import React, { useState, useCallback, useEffect } from 'react';
import {
  Card, Segmented, Button, Input, InputNumber, Select, Tag, message,
  Row, Col, Space,
} from 'antd';
import {
  Satellite, Globe, Calendar, Copy, Activity, Compass, Sun, MapPin,
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import { createLogger } from '../../utils/logger';
import type { SavedChart } from './SavedChartsDrawer';

const log = createLogger('AdvancedAstrologyPanel');

type TechniqueKey =
  | 'solar-return'
  | 'progressions'
  | 'year-ahead'
  | 'profection'
  | 'solar-arc'
  | 'astrocartography'
  | 'lots'
  | 'fixed-stars'
  | 'midpoints'
  | 'antiscia';

interface EndpointConfig {
  path: string;
  buildBody: (s: FormState) => Record<string, unknown>;
  extraFields?: TechniqueField[];
}

interface TechniqueField {
  key: string;
  label: string;
  type: 'number' | 'select' | 'datetime';
  defaultValue?: number | string;
  options?: Array<{ label: string; value: string }>;
  step?: number;
  span?: number;
}

interface FormState {
  // Shared natal data
  natal_date_iso: string;
  natal_lat: number;
  natal_lon: number;
  // For endpoints that don't take natal_* (astrocartography uses date_iso,
  // lots/fixed-stars/midpoints/antiscia also use date_iso + lat + lon)
  date_iso: string;
  lat: number;
  lon: number;
  // Technique-specific
  return_year: number;
  target_year: number;
  target_date_iso: string;
  start_date_iso: string;
  end_date_iso: string;
  step_degrees: number;
  orb: number;
  sect: 'day' | 'night';
}

const NOW_YEAR = new Date().getFullYear();

// datetime-local input format: ``YYYY-MM-DDTHH:mm`` (16 chars, no seconds, no tz).
// Backend's ``toIso`` (line 96) appends ``:00`` seconds before sending.
const toDatetimeLocal = (d: Date): string => d.toISOString().slice(0, 16);

// Defaults for the year-ahead range — previously both fields were empty
// strings, which silently fell through to the backend's "natal_dt as
// start, +365 days as end" default. That made the UI confusing because
// the empty inputs didn't communicate what would actually be queried.
// Now we default to ``now`` → ``now + 1 year`` so the user sees exactly
// what window will be scanned.
const todayForDefaults = new Date();
const nextYearForDefaults = new Date(todayForDefaults);
nextYearForDefaults.setFullYear(todayForDefaults.getFullYear() + 1);
const DEFAULT_START_ISO = toDatetimeLocal(todayForDefaults);
const DEFAULT_END_ISO = toDatetimeLocal(nextYearForDefaults);

const initialState: FormState = {
  natal_date_iso: '1990-01-01T12:00',
  natal_lat: 40.7128,
  natal_lon: -74.0060,
  date_iso: toDatetimeLocal(new Date()),
  lat: 40.7128,
  lon: -74.0060,
  return_year: NOW_YEAR + 1,
  target_year: NOW_YEAR + 1,
  target_date_iso: toDatetimeLocal(new Date()),
  start_date_iso: DEFAULT_START_ISO,
  end_date_iso: DEFAULT_END_ISO,
  step_degrees: 5.0,
  orb: 1.0,
  sect: 'day',
};

/**
 * Build a partial FormState override from a SavedChart — only the natal
 * fields that exist on the chart are returned; missing fields fall through
 * to ``initialState`` via the spread in the caller.
 *
 * The SavedChart interface types ``latitude``/``longitude`` as ``unknown``
 * via the catch-all ``[key: string]: unknown`` index signature, so we
 * coerce defensively. The backend always persists them as floats.
 */
function formOverrideFromChart(chart: SavedChart | null | undefined): Partial<FormState> {
  if (!chart) return {};
  const out: Partial<FormState> = {};
  if (typeof chart.birth_time_iso === 'string' && chart.birth_time_iso.length > 0) {
    // datetime-local wants YYYY-MM-DDTHH:mm (16 chars). Backend stores
    // full ISO 8601 with seconds + tz offset; slice works for both
    // ``1990-01-06T12:00:00+00:00`` and ``1990-01-06T12:00`` shapes.
    out.natal_date_iso = chart.birth_time_iso.slice(0, 16);
  }
  const lat = chart.latitude;
  if (typeof lat === 'number' && Number.isFinite(lat)) {
    out.natal_lat = lat;
    out.lat = lat;
  }
  const lon = chart.longitude;
  if (typeof lon === 'number' && Number.isFinite(lon)) {
    out.natal_lon = lon;
    out.lon = lon;
  }
  return out;
}

// Iso-8601 normalization: datetime-local produces YYYY-MM-DDTHH:mm.
// Backend pydantic accepts that, but we add :00 seconds for symmetry.
const toIso = (s: string): string => {
  if (!s) return s;
  // Already has seconds?
  if (/T\d{2}:\d{2}:\d{2}/.test(s)) return s;
  // Has only HH:mm?
  if (/T\d{2}:\d{2}$/.test(s)) return `${s}:00`;
  return s;
};

const ENDPOINTS: Record<TechniqueKey, EndpointConfig> = {
  'solar-return': {
    path: '/api/v1/astrology/solar-return',
    buildBody: (s) => ({
      natal_date_iso: toIso(s.natal_date_iso),
      natal_lat: Number(s.natal_lat),
      natal_lon: Number(s.natal_lon),
      return_year: Number(s.return_year),
    }),
    extraFields: [
      { key: 'return_year', label: 'Return Year', type: 'number', defaultValue: NOW_YEAR + 1 },
    ],
  },
  'progressions': {
    path: '/api/v1/astrology/secondary-progressions',
    buildBody: (s) => ({
      natal_date_iso: toIso(s.natal_date_iso),
      natal_lat: Number(s.natal_lat),
      natal_lon: Number(s.natal_lon),
      target_date_iso: toIso(s.target_date_iso),
    }),
    extraFields: [
      { key: 'target_date_iso', label: 'Target Date', type: 'datetime', defaultValue: '' },
    ],
  },
  'year-ahead': {
    path: '/api/v1/astrology/year-ahead',
    buildBody: (s) => {
      const body: Record<string, unknown> = {
        natal_date_iso: toIso(s.natal_date_iso),
        natal_lat: Number(s.natal_lat),
        natal_lon: Number(s.natal_lon),
        orb: Number(s.orb),
      };
      if (s.start_date_iso) body.start_date_iso = toIso(s.start_date_iso);
      if (s.end_date_iso) body.end_date_iso = toIso(s.end_date_iso);
      return body;
    },
    extraFields: [
      { key: 'start_date_iso', label: 'Start Date', type: 'datetime' },
      { key: 'end_date_iso', label: 'End Date', type: 'datetime' },
      { key: 'orb', label: 'Orb (degrees)', type: 'number', defaultValue: 1.0, step: 0.1 },
    ],
  },
  'profection': {
    path: '/api/v1/astrology/profection',
    buildBody: (s) => ({
      natal_date_iso: toIso(s.natal_date_iso),
      target_year: Number(s.target_year),
    }),
    extraFields: [
      { key: 'target_year', label: 'Target Year', type: 'number', defaultValue: NOW_YEAR + 1 },
    ],
  },
  'solar-arc': {
    path: '/api/v1/astrology/solar-arc',
    buildBody: (s) => ({
      natal_date_iso: toIso(s.natal_date_iso),
      natal_lat: Number(s.natal_lat),
      natal_lon: Number(s.natal_lon),
      target_date_iso: toIso(s.target_date_iso),
    }),
    extraFields: [
      { key: 'target_date_iso', label: 'Target Date', type: 'datetime' },
    ],
  },
  'astrocartography': {
    path: '/api/v1/astrology/astrocartography',
    buildBody: (s) => ({
      date_iso: toIso(s.date_iso),
      step_degrees: Number(s.step_degrees),
    }),
    extraFields: [
      { key: 'step_degrees', label: 'Step Degrees', type: 'number', defaultValue: 5.0, step: 0.5 },
    ],
  },
  'lots': {
    path: '/api/v1/astrology/lots',
    buildBody: (s) => ({
      date_iso: toIso(s.date_iso),
      lat: Number(s.lat),
      lon: Number(s.lon),
      sect: s.sect,
    }),
    extraFields: [
      {
        key: 'sect', label: 'Sect', type: 'select', defaultValue: 'day',
        options: [{ label: 'Day (Sun above horizon)', value: 'day' }, { label: 'Night (Sun below horizon)', value: 'night' }],
      },
    ],
  },
  'fixed-stars': {
    path: '/api/v1/astrology/fixed-stars',
    buildBody: (s) => ({
      date_iso: toIso(s.date_iso),
      lat: Number(s.lat),
      lon: Number(s.lon),
      orb: Number(s.orb),
    }),
    extraFields: [
      { key: 'orb', label: 'Orb (degrees)', type: 'number', defaultValue: 1.5, step: 0.1 },
    ],
  },
  'midpoints': {
    path: '/api/v1/astrology/midpoints',
    buildBody: (s) => ({
      date_iso: toIso(s.date_iso),
      lat: Number(s.lat),
      lon: Number(s.lon),
      orb: Number(s.orb),
    }),
    extraFields: [
      { key: 'orb', label: 'Orb (degrees)', type: 'number', defaultValue: 1.5, step: 0.1 },
    ],
  },
  'antiscia': {
    path: '/api/v1/astrology/antiscia',
    buildBody: (s) => ({
      date_iso: toIso(s.date_iso),
      lat: Number(s.lat),
      lon: Number(s.lon),
    }),
    extraFields: [],
  },
};

// Techniques whose shared input is the standard natal trio (date+lat+lon),
// not the transit-mode trio. Astrocartography uses date_iso only.
const USES_NATAL = new Set<TechniqueKey>([
  'solar-return', 'progressions', 'year-ahead', 'profection', 'solar-arc',
]);
// Techniques that take lat+lon (shared transit location, not natal).
const USES_TRANSIT_LOCATION = new Set<TechniqueKey>([
  'lots', 'fixed-stars', 'midpoints', 'antiscia',
]);

interface AdvancedAstrologyPanelProps {
  /** When the parent AstrologyPanel has a chart selected in the wheel tab,
   *  pass it here so the user doesn't have to re-type natal data. Falls
   *  back to the hardcoded defaults (NYC 1990-01-01) when null/undefined. */
  activeChart?: SavedChart | null;
}

const AdvancedAstrologyPanel: React.FC<AdvancedAstrologyPanelProps> = ({ activeChart }) => {
  const [technique, setTechnique] = useState<TechniqueKey>('solar-return');
  const [form, setForm] = useState<FormState>(() => ({
    ...initialState,
    ...formOverrideFromChart(activeChart),
  }));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Re-sync natal fields when the parent's active chart changes (e.g. user
  // picks a different chart in the wheel tab above). Only touches the
  // natal_* fields — leaves technique-specific fields (orb, step_degrees,
  // return_year, etc.) alone so the user's in-flight edits aren't lost.
  // Keying on activeChart?.id (not the object reference) avoids re-runs
  // when the parent re-renders with a new object for the same chart.
  const activeChartId = activeChart?.id;
  useEffect(() => {
    if (!activeChartId) return;
    setForm((prev) => ({
      ...prev,
      ...formOverrideFromChart(activeChart),
    }));
    audioFeedback.playClick();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeChartId]);

  const updateField = useCallback(<K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleCalculate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    audioFeedback.playClick();

    const cfg = ENDPOINTS[technique];
    const body = cfg.buildBody(form);

    try {
      const res = await fetch(cfg.path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const errBody = await res.json();
          detail = errBody?.detail || errBody?.message || detail;
        } catch { /* leave default */ }
        message.error(`${technique} failed: ${detail}`);
        setError(detail);
        audioFeedback.playError();
        return;
      }
      const data: Record<string, unknown> = await res.json();
      setResult(data);
      message.success(`${technique} calculated`);
      audioFeedback.playSuccess();
      log.info(`${technique} response received`, { keys: Object.keys(data) });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      message.error(`Request failed: ${msg}`);
      setError(msg);
      audioFeedback.playError();
      log.error(`${technique} request failed`, e);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      message.success('Result copied to clipboard');
      audioFeedback.playSuccess();
    } catch (e) {
      message.error('Copy failed: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  const cfg = ENDPOINTS[technique];
  const usesNatal = USES_NATAL.has(technique);
  const usesTransitLoc = USES_TRANSIT_LOCATION.has(technique);

  // ----- Render helpers -----
  const renderField = (field: TechniqueField) => {
    const value = form[field.key as keyof FormState];
    const onVal = (v: unknown) => updateField(field.key as keyof FormState, v as never);
    if (field.type === 'number') {
      return (
        <Col xs={24} sm={field.span ?? 12} key={field.key}>
          <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">{field.label}</label>
          <InputNumber
            value={typeof value === 'number' ? value : Number(value) || field.defaultValue || 0}
            onChange={(v) => onVal(v ?? 0)}
            step={field.step ?? 1}
            className="w-full"
            style={{ width: '100%' }}
          />
        </Col>
      );
    }
    if (field.type === 'select') {
      return (
        <Col xs={24} sm={field.span ?? 12} key={field.key}>
          <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">{field.label}</label>
          <Select
            value={String(value ?? field.defaultValue ?? '')}
            onChange={(v) => onVal(v)}
            options={field.options}
            className="w-full"
            style={{ width: '100%' }}
          />
        </Col>
      );
    }
    // datetime
    return (
      <Col xs={24} sm={field.span ?? 12} key={field.key}>
        <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">{field.label}</label>
        <Input
          type="datetime-local"
          value={String(value ?? '')}
          onChange={(e) => onVal(e.target.value)}
          className="w-full"
        />
      </Col>
    );
  };

  // Determine which "shared" data block to render
  const renderSharedData = () => {
    if (usesNatal) {
      return (
        <Card
          size="small"
          className="bg-gray-800/60 border-white/5"
          styles={{ body: { padding: '16px' } }}
          title={
            <span className="text-cyan-400 font-mono text-[10px] tracking-widest uppercase">
              <Calendar className="w-3.5 h-3.5 inline mr-2" />Natal Data
            </span>
          }
        >
          {/* Data-source banner — tells the user whether the natal fields
              above were pre-filled from the wheel tab's active chart or
              are using the default (NYC 1990-01-01). When a chart is
              active, also shows its name so the user can confirm they
              picked the right one. */}
          {activeChart ? (
            <div className="mb-3 p-2 rounded-lg bg-cyan-950/30 border border-cyan-500/20 flex items-center gap-2">
              <Compass className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
              <span className="text-[10px] text-cyan-300 font-mono">
                Pre-filled from active chart: <strong>{activeChart.name}</strong>
                {activeChart.city ? ` (${activeChart.city})` : ''}
              </span>
            </div>
          ) : (
            <div className="mb-3 p-2 rounded-lg bg-amber-950/30 border border-amber-500/20 flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span className="text-[10px] text-amber-300 font-mono">
                Using default natal data — select a chart in the wheel tab above to pre-fill.
              </span>
            </div>
          )}
          <Row gutter={[12, 12]}>
            <Col xs={24} md={12}>
              <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">Birth Date / Time</label>
              <Input
                type="datetime-local"
                value={form.natal_date_iso}
                onChange={(e) => updateField('natal_date_iso', e.target.value)}
              />
            </Col>
            <Col xs={12} md={6}>
              <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">Latitude</label>
              <InputNumber
                value={form.natal_lat}
                onChange={(v) => updateField('natal_lat', Number(v ?? 0))}
                step={0.01}
                className="w-full"
                style={{ width: '100%' }}
              />
            </Col>
            <Col xs={12} md={6}>
              <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">Longitude</label>
              <InputNumber
                value={form.natal_lon}
                onChange={(v) => updateField('natal_lon', Number(v ?? 0))}
                step={0.01}
                className="w-full"
                style={{ width: '100%' }}
              />
            </Col>
          </Row>
        </Card>
      );
    }
    if (usesTransitLoc || technique === 'astrocartography') {
      return (
        <Card
          size="small"
          className="bg-gray-800/60 border-white/5"
          styles={{ body: { padding: '16px' } }}
          title={
            <span className="text-purple-400 font-mono text-[10px] tracking-widest uppercase">
              <Globe className="w-3.5 h-3.5 inline mr-2" />Transit / Event Data
            </span>
          }
        >
          <Row gutter={[12, 12]}>
            <Col xs={24} md={12}>
              <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">Date / Time</label>
              <Input
                type="datetime-local"
                value={form.date_iso}
                onChange={(e) => updateField('date_iso', e.target.value)}
              />
            </Col>
            {usesTransitLoc && (
              <>
                <Col xs={12} md={6}>
                  <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">Latitude</label>
                  <InputNumber
                    value={form.lat}
                    onChange={(v) => updateField('lat', Number(v ?? 0))}
                    step={0.01}
                    className="w-full"
                    style={{ width: '100%' }}
                  />
                </Col>
                <Col xs={12} md={6}>
                  <label className="text-[10px] text-gray-400 font-mono block uppercase mb-1">Longitude</label>
                  <InputNumber
                    value={form.lon}
                    onChange={(v) => updateField('lon', Number(v ?? 0))}
                    step={0.01}
                    className="w-full"
                    style={{ width: '100%' }}
                  />
                </Col>
              </>
            )}
          </Row>
        </Card>
      );
    }
    return null;
  };

  // Pretty-render `chart` or `positions` if the response has them.
  const renderResultHighlights = (): React.ReactNode => {
    if (!result) return null;
    const chart = result.chart;
    const positions = result.positions;
    const summary = result.summary;
    if (!chart && !positions && !summary) return null;
    const hasChart = chart !== null && typeof chart === 'object';
    const hasPositions = positions !== null && typeof positions === 'object';
    const hasSummary = summary !== null && typeof summary === 'object';
    return (
      <Card
        size="small"
        className="bg-purple-950/20 border-purple-500/20"
        styles={{ body: { padding: '14px' } }}
      >
        {hasChart && (
          <div className="mb-2">
            <span className="text-[9px] text-amber-400 font-mono block uppercase">Chart Highlight</span>
            <pre className="text-[10px] text-slate-200 font-mono whitespace-pre-wrap break-words m-0 mt-1">
              {JSON.stringify(chart, null, 2)}
            </pre>
          </div>
        )}
        {hasPositions && (
          <div className="mb-2">
            <span className="text-[9px] text-cyan-400 font-mono block uppercase">Positions</span>
            <pre className="text-[10px] text-slate-200 font-mono whitespace-pre-wrap break-words m-0 mt-1">
              {JSON.stringify(positions, null, 2)}
            </pre>
          </div>
        )}
        {hasSummary && (
          <div>
            <span className="text-[9px] text-emerald-400 font-mono block uppercase">Summary</span>
            <pre className="text-[10px] text-slate-200 font-mono whitespace-pre-wrap break-words m-0 mt-1">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </div>
        )}
      </Card>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-900/30 via-purple-900/30 to-cyan-900/30 rounded-xl p-4 border border-purple-500/20">
        <Space size={10} align="center">
          <Satellite className="w-5 h-5 text-cyan-400" />
          <div>
            <h3 className="text-base font-bold text-white tracking-wide m-0">Advanced Astrology Techniques</h3>
            <p className="text-[10px] text-gray-400 font-mono m-0">
              10 hidden backend endpoints — Solar Return, Progressions, Year Ahead, Profection, Solar Arc,
              Astrocartography, Lots, Fixed Stars, Midpoints, Antiscia
            </p>
          </div>
        </Space>
      </div>

      {/* Technique selector */}
      <Card
        size="small"
        className="bg-gray-900/60 border-white/5"
        styles={{ body: { padding: '14px' } }}
      >
        <Segmented<TechniqueKey>
          options={[
            { label: 'Solar Return', value: 'solar-return' },
            { label: 'Progressions', value: 'progressions' },
            { label: 'Year Ahead', value: 'year-ahead' },
            { label: 'Profection', value: 'profection' },
            { label: 'Solar Arc', value: 'solar-arc' },
            { label: 'Astrocartography', value: 'astrocartography' },
            { label: 'Lots', value: 'lots' },
            { label: 'Fixed Stars', value: 'fixed-stars' },
            { label: 'Midpoints', value: 'midpoints' },
            { label: 'Antiscia', value: 'antiscia' },
          ]}
          value={technique}
          onChange={(val) => {
            setTechnique(val as TechniqueKey);
            setResult(null);
            setError(null);
            audioFeedback.playTabChange();
          }}
          block
          className="bg-black/40 border border-white/5"
        />
        <div className="mt-3 flex flex-wrap gap-2 items-center text-[10px] font-mono">
          <Tag color="cyan" className="font-mono">Endpoint</Tag>
          <span className="text-gray-300">{cfg.path}</span>
          <Tag color="purple" className="font-mono ml-2">Method</Tag>
          <span className="text-gray-300">POST</span>
        </div>
      </Card>

      {/* Shared data block (natal or transit) */}
      {renderSharedData()}

      {/* Technique-specific extra fields */}
      {cfg.extraFields && cfg.extraFields.length > 0 && (
        <Card
          size="small"
          className="bg-gray-800/40 border-white/5"
          styles={{ body: { padding: '14px' } }}
          title={
            <span className="text-emerald-400 font-mono text-[10px] tracking-widest uppercase">
              <Sun className="w-3.5 h-3.5 inline mr-2" />Technique Parameters
            </span>
          }
        >
          <Row gutter={[12, 12]}>
            {/* Range presets — only for year-ahead */}
            {technique === 'year-ahead' && (
              <Col xs={24}>
                <Space size="small" style={{ marginBottom: 8 }} wrap>
                  <Button size="small" onClick={() => {
                    const now = new Date();
                    const start = now.toISOString().slice(0, 16);
                    const end = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
                    updateField('start_date_iso', start);
                    updateField('end_date_iso', end);
                    audioFeedback.playClick();
                  }}>📅 Week</Button>
                  <Button size="small" onClick={() => {
                    const now = new Date();
                    const start = now.toISOString().slice(0, 16);
                    const end = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
                    updateField('start_date_iso', start);
                    updateField('end_date_iso', end);
                    audioFeedback.playClick();
                  }}>📆 Month</Button>
                  <Button size="small" onClick={() => {
                    const now = new Date();
                    const start = now.toISOString().slice(0, 16);
                    const end = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
                    updateField('start_date_iso', start);
                    updateField('end_date_iso', end);
                    audioFeedback.playClick();
                  }}>🗓️ Year</Button>
                </Space>
              </Col>
            )}
            {cfg.extraFields.map(renderField)}
          </Row>
        </Card>
      )}

      {/* Calculate button + status */}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="primary"
          loading={loading}
          onClick={handleCalculate}
          icon={<Activity className="w-4 h-4" />}
          size="large"
          style={{
            background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
            border: 'none',
            fontWeight: 600,
          }}
        >
          Calculate {technique.replace(/-/g, ' ')}
        </Button>
        {error && (
          <Tag color="red" className="font-mono text-[10px]">
            <Compass className="w-3 h-3 inline mr-1" />
            {error}
          </Tag>
        )}
        {result && !error && (
          <Tag color="green" className="font-mono text-[10px]">
            <MapPin className="w-3 h-3 inline mr-1" />
            Result ready
          </Tag>
        )}
      </div>

      {/* Result display */}
      {(result || error) && (
        <Card
          size="small"
          className="bg-gray-900/80 border-cyan-500/20"
          styles={{ body: { padding: '14px' } }}
          title={
            <Space size={8}>
              <span className="text-cyan-400 font-mono text-[10px] tracking-widest uppercase">Response</span>
              {result && (
                <Button
                  size="small"
                  type="text"
                  icon={<Copy className="w-3 h-3" />}
                  onClick={handleCopy}
                  className="text-[10px]"
                >
                  Copy JSON
                </Button>
              )}
            </Space>
          }
        >
          {renderResultHighlights()}
          {/* Formatted timeline for year-ahead results */}
          {result && Array.isArray((result as Record<string, unknown>).events) && (
            <div style={{ maxHeight: 400, overflowY: 'auto' }} className="mt-3 space-y-2">
              {Object.entries(
                ((result as Record<string, unknown>).events as unknown as Array<Record<string, unknown>>).reduce<Record<string, Array<Record<string, unknown>>>>((acc, ev) => {
                  const dateKey = typeof ev.date === 'string' ? ev.date.slice(0, 10) : 'Unknown';
                  if (!acc[dateKey]) acc[dateKey] = [];
                  acc[dateKey].push(ev);
                  return acc;
                }, {})
              ).map(([date, events]) => (
                <div key={date} className="border border-white/5 rounded-lg p-2 bg-black/30">
                  <div className="text-[10px] font-mono text-amber-400 mb-1">
                    {new Date(date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                  </div>
                  {events.map((ev, idx) => {
                    const aspectType = typeof ev.aspect_type === 'string' ? ev.aspect_type : '';
                    const evType = typeof ev.type === 'string' ? ev.type : '';
                    const isHarmonious = aspectType === 'Trine' || aspectType === 'Sextile' || aspectType === 'Conjunction';
                    const isChallenging = aspectType === 'Square' || aspectType === 'Opposition';
                    const colorClass = isHarmonious ? 'text-emerald-400' : isChallenging ? 'text-rose-400' : 'text-cyan-400';
                    const typeIcon = evType === 'lunar_phase' ? '🌑🌕' : evType === 'ingress' ? '➡️' : '⚡';
                    const orb = typeof ev.orb === 'number' ? ev.orb : null;
                    return (
                      <div key={idx} className={`text-[10px] font-mono ${colorClass} flex items-center gap-2`}>
                        <span>{typeIcon}</span>
                        <span className="font-bold">{typeof ev.body === 'string' ? ev.body : ''}</span>
                        <span className="text-gray-500">{typeof ev.sign === 'string' ? ev.sign : ''}</span>
                        {typeof ev.aspect_to_natal === 'string' && ev.aspect_to_natal && (
                          <span className={colorClass}>{ev.aspect_to_natal}</span>
                        )}
                        {aspectType && (
                          <Tag style={{ fontSize: 8, margin: 0 }} color={isHarmonious ? 'green' : isChallenging ? 'red' : 'blue'}>
                            {aspectType}
                          </Tag>
                        )}
                        {orb !== null && orb !== 0 && (
                          <span className="text-gray-600">{orb}°</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
          {/* Fallback: raw JSON for other techniques / error display */}
          {(!result || !Array.isArray((result as Record<string, unknown>).events)) && (
            <pre
              className="text-[10px] text-slate-200 font-mono whitespace-pre-wrap break-words m-0 mt-3 p-3 bg-black/45 border border-white/5 rounded-lg overflow-auto"
              style={{ maxHeight: '400px' }}
            >
              {result ? JSON.stringify(result, null, 2) : `// ${error}`}
            </pre>
          )}
        </Card>
      )}
    </div>
  );
};

export default AdvancedAstrologyPanel;