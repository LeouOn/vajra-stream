import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Download, Copy, FileJson, FileText, Check, Square, RefreshCw, Package, CheckCircle2, XCircle } from 'lucide-react';
import { Card, Button, Tag, Tooltip, Segmented, Switch, Row, Col } from 'antd';
import { toMarkdown as toMarkdownImpl, applyFieldSelection as applyFieldSelectionImpl, planetGlyph } from '../../lib/astroHelpers';
import { audioFeedback } from '../../utils/audioFeedback';
import { useUIStore } from '../../stores/uiStore';

interface FieldDef {
  key: string;
  label: string;
  required?: boolean;
}

const FIELD_GROUPS: FieldDef[] = [
  { key: 'name', label: 'Name', required: true },
  { key: 'birth_time_iso', label: 'Birth Time' },
  { key: 'city', label: 'City' },
  { key: 'latitude', label: 'Latitude' },
  { key: 'longitude', label: 'Longitude' },
  { key: 'timezone', label: 'Timezone' },
  { key: 'description', label: 'Description' },
  { key: 'tags', label: 'Tags' },
  { key: 'notes', label: 'Notes' },
  { key: 'cached_data', label: 'Cached Chart Data' },
];

const TOP_LEVEL_FIELDS: FieldDef[] = [
  { key: 'version', label: 'Version', required: true },
  { key: 'exported_at', label: 'Export Timestamp', required: true },
  { key: 'system', label: 'System Tag' },
  { key: 'charts', label: 'Charts', required: true },
];

type ExportFormat = 'json' | 'markdown';
type CopyState = 'idle' | 'done' | 'error';

interface ChartRecord {
  id: number;
  name?: string;
  birth_time_iso?: string;
  city?: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  description?: string;
  tags?: string;
  notes?: string;
  cached_data?: Record<string, unknown>;
  [key: string]: unknown;
}

interface ExportPayload {
  version?: string;
  exported_at?: string;
  system?: string;
  charts: ChartRecord[];
  [key: string]: unknown;
}

// toMarkdown/applyFieldSelection are defined locally for reference but the
// component uses the imported astroHelpers implementations (*Impl).
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function toMarkdown(payload: ExportPayload, selectedFieldKeys: Set<string>): string {
  const lines: string[] = [];
  lines.push('# Saved Natal Charts Export');
  lines.push('');
  if (selectedFieldKeys.has('exported_at') && payload.exported_at) {
    lines.push(`**Exported**: ${payload.exported_at}`);
  }
  if (selectedFieldKeys.has('system')) {
    lines.push(`**System**: ${payload.system || 'vajra-stream-astrology'}`);
  }
  if (selectedFieldKeys.has('version')) {
    lines.push(`**Schema version**: ${payload.version}`);
  }
  lines.push(`**Charts in this export**: ${payload.charts?.length || 0}`);
  lines.push('');
  lines.push('---');
  lines.push('');

  for (const c of payload.charts || []) {
    lines.push(`## ${c.name || 'Unnamed'}`);
    lines.push('');
    if (selectedFieldKeys.has('birth_time_iso') && c.birth_time_iso) {
      lines.push(`- **Born**: ${c.birth_time_iso}`);
    }
    const loc: string[] = [];
    if (selectedFieldKeys.has('city') && c.city) loc.push(c.city);
    if (selectedFieldKeys.has('latitude') && c.latitude != null) loc.push(`${c.latitude.toFixed(4)}°`);
    if (selectedFieldKeys.has('longitude') && c.longitude != null) loc.push(`${c.longitude.toFixed(4)}°`);
    if (selectedFieldKeys.has('timezone') && c.timezone) loc.push(c.timezone);
    if (loc.length) lines.push(`- **Location**: ${loc.join(' · ')}`);
    if (selectedFieldKeys.has('description') && c.description) {
      lines.push(`- **Description**: ${c.description}`);
    }
    if (selectedFieldKeys.has('tags') && c.tags) {
      lines.push(`- **Tags**: ${c.tags}`);
    }
    if (selectedFieldKeys.has('notes') && c.notes) {
      lines.push(`- **Notes**: ${c.notes}`);
    }
    if (selectedFieldKeys.has('cached_data') && c.cached_data && typeof c.cached_data === 'object') {
      const cd = c.cached_data as Record<string, unknown>;
      if (cd.datetime) lines.push(`- **Chart datetime**: ${cd.datetime}`);
      const western = (cd.western as Record<string, unknown>) || {};
      const positions = (western.positions as Record<string, any>) || {};
      const planetLines = Object.entries(positions)
        .filter(([k]) => !['ascendant', 'midheaven', 'north_node', 'south_node'].includes(k))
        .map(([k, v]) => `  - ${k.charAt(0).toUpperCase() + k.slice(1)} (${planetGlyph(k)}): ${v.formatted || `${v.degree?.toFixed(2)}° ${v.sign || ''}`}`);
      if (planetLines.length) {
        lines.push('');
        lines.push('**Western planets**:');
        lines.push(...planetLines);
      }
      const angles = ['ascendant', 'midheaven', 'north_node']
        .filter((k) => positions[k])
        .map((k) => `  - ${k.replace('_', ' ')}: ${positions[k].formatted}`);
      if (angles.length) {
        lines.push('');
        lines.push('**Angles**:');
        lines.push(...angles);
      }
      const houses = (western.houses as Record<string, any>) || {};
      const houseLines = Object.entries(houses)
        .sort(([a], [b]) => Number(a.replace('house_', '')) - Number(b.replace('house_', '')))
        .map(([k, v]) => `  - ${k}: ${v.formatted}`);
      if (houseLines.length) {
        lines.push('');
        lines.push('**House cusps**:');
        lines.push(...houseLines);
      }
      if (western.dominant_element) {
        lines.push('');
        lines.push(`**Dominant element**: ${western.dominant_element} · **Dominant modality**: ${western.dominant_modality}`);
      }
    }
    lines.push('');
    lines.push('---');
    lines.push('');
  }
  return lines.join('\n');
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function applyFieldSelection(
  payload: ExportPayload,
  selectedChartIds: Set<number>,
  selectedFieldKeys: Set<string>,
  _topLevelFields: FieldDef[] = TOP_LEVEL_FIELDS,
  _fieldGroups: FieldDef[] = FIELD_GROUPS,
): Record<string, unknown> {
  const filteredCharts = (payload.charts || []).filter((c) => selectedChartIds.has(c.id));
  const topLevel: Record<string, unknown> = {};
  for (const f of TOP_LEVEL_FIELDS) {
    if (selectedFieldKeys.has(f.key) && payload[f.key] !== undefined) {
      topLevel[f.key] = payload[f.key];
    }
  }
  const charts = filteredCharts.map((c) => {
    const out: Record<string, unknown> = { id: c.id };
    for (const f of FIELD_GROUPS) {
      if (selectedFieldKeys.has(f.key) && c[f.key] !== undefined) {
        out[f.key] = c[f.key];
      }
    }
    return out;
  });
  return { ...topLevel, charts };
}

interface ExportPanelProps {
  charts?: ChartRecord[];
}

const ExportPanel: React.FC<ExportPanelProps> = ({ charts: _chartsProp = [] }) => {
  const addToast = useUIStore((s) => s.addToast);
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState<ExportPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [format, setFormat] = useState<ExportFormat>('json');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set([
    'name', 'birth_time_iso', 'city', 'latitude', 'longitude', 'timezone',
    'description', 'tags', 'notes', 'cached_data',
    'version', 'exported_at', 'system', 'charts',
  ]));
  const [copyState, setCopyState] = useState<CopyState>('idle');

  const fetchExport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/v1/astrology/charts/export`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: ExportPayload = await resp.json();
      setPayload(data);
      setSelectedIds(new Set((data.charts || []).map((c) => c.id)));
      audioFeedback.playSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExport();
  }, [fetchExport]);

  const projected = useMemo(() => {
    if (!payload) return null;
    return applyFieldSelectionImpl(payload, selectedIds, selectedFields);
  }, [payload, selectedIds, selectedFields]);

  const rendered = useMemo(() => {
    if (!projected) return '';
    if (format === 'json') {
      return JSON.stringify(projected, null, 2);
    }
    return toMarkdownImpl(projected, selectedFields);
  }, [projected, format, selectedFields]);

  const toggleId = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set((payload?.charts || []).map((c) => c.id)));
  const selectNone = () => setSelectedIds(new Set());

  const toggleField = (key: string) => {
    setSelectedFields((prev) => {
      const next = new Set(prev);
      const topReq = TOP_LEVEL_FIELDS.find((f) => f.key === key);
      const chartReq = FIELD_GROUPS.find((f) => f.key === key);
      if ((topReq && topReq.required) || (chartReq && chartReq.required)) return prev;
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const download = () => {
    if (!rendered) return;
    const blob = new Blob([rendered], { type: format === 'json' ? 'application/json' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    a.download = `astrology-export-${stamp}.${format === 'json' ? 'json' : 'md'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    audioFeedback.playSuccess();
  };

  const copyToClipboard = async () => {
    if (!rendered) return;
    try {
      await navigator.clipboard.writeText(rendered);
      setCopyState('done');
      audioFeedback.playSuccess();
      addToast({ type: 'success', title: 'Copied to clipboard', duration: 3 });
      setTimeout(() => setCopyState('idle'), 2000);
    } catch {
      setCopyState('error');
      audioFeedback.playError();
      addToast({ type: 'error', title: 'Copy failed', duration: 5 });
      setTimeout(() => setCopyState('idle'), 2000);
    }
  };

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 font-mono">
          <span className="text-cyan-400 text-xs tracking-wider uppercase flex items-center gap-1.5">
            <Package className="w-4 h-4 text-cyan-400" />
            EXPORT SAVED CHARTS
          </span>
          <Button
            size="small"
            type="primary"
            onClick={fetchExport}
            loading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            style={{ background: 'linear-gradient(135deg, #06b6d4, #0891b2)', border: 'none' }}
          >
            Refresh
          </Button>
        </div>
      }
      className="bg-gray-900/80 border-cyan-500/20"
      styles={{ body: { padding: '20px' } }}
    >
      {error ? (
        <div className="p-4 bg-rose-950/20 border border-rose-500/25 rounded-xl text-rose-300 text-xs font-mono flex items-center gap-2">
          <XCircle className="w-4 h-4 flex-shrink-0" /> {error}
        </div>
      ) : loading && !payload ? (
        <div className="text-center italic text-gray-500 text-xs py-12 animate-pulse">
          Loading export from /api/v1/astrology/charts/export ...
        </div>
      ) : payload ? (
        <div className="space-y-5">
          <Row gap={16} className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <div className="bg-black/35 border border-white/5 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider font-bold">
                    Format
                  </span>
                  <Segmented
                    size="small"
                    value={format}
                    onChange={(v) => { audioFeedback.playTabChange(); setFormat(v as ExportFormat); }}
                    options={[
                      { label: <span className="flex items-center gap-1.5"><FileJson className="w-3 h-3" /> JSON</span>, value: 'json' },
                      { label: <span className="flex items-center gap-1.5"><FileText className="w-3 h-3" /> Markdown</span>, value: 'markdown' },
                    ]}
                  />
                </div>
                <div className="text-[10px] text-gray-500 font-mono leading-relaxed">
                  {format === 'json'
                    ? 'Raw JSON dump — suitable for backup or programmatic re-import.'
                    : 'Human-readable Markdown — sections per chart with planet positions, angles, and house cusps.'}
                </div>
              </div>

              <div className="bg-black/35 border border-white/5 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider font-bold">
                    Charts ({selectedIds.size} / {payload.charts.length})
                  </span>
                  <div className="flex gap-2 text-[9px] font-mono">
                    <button
                      type="button"
                      onClick={selectAll}
                      className="text-cyan-400 hover:text-cyan-300"
                    >
                      all
                    </button>
                    <span className="text-gray-700">·</span>
                    <button
                      type="button"
                      onClick={selectNone}
                      className="text-gray-400 hover:text-gray-300"
                    >
                      none
                    </button>
                  </div>
                </div>
                <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1">
                  {payload.charts.map((c) => {
                    const selected = selectedIds.has(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => toggleId(c.id)}
                        className={`w-full text-left p-2.5 border rounded-lg flex items-center gap-2.5 transition-colors ${
                          selected
                            ? 'bg-cyan-950/20 border-cyan-500/30 hover:border-cyan-400/50'
                            : 'bg-black/30 border-white/5 hover:border-white/15'
                        }`}
                      >
                        {selected
                          ? <CheckCircle2 className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                          : <Square className="w-4 h-4 text-gray-600 flex-shrink-0" />
                        }
                        <div className="min-w-0 flex-1">
                          <div className="text-xs font-bold text-slate-200 truncate">{c.name}</div>
                          <div className="text-[9px] text-gray-500 font-mono">
                            id={c.id} · {c.city || 'no city'}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                  {payload.charts.length === 0 && (
                    <div className="text-center text-[10px] text-gray-500 italic py-6">
                      No saved charts to export.
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-black/35 border border-white/5 rounded-xl p-4 space-y-2.5">
                <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider font-bold block">
                  Fields
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {FIELD_GROUPS.map((f) => {
                    const enabled = selectedFields.has(f.key);
                    const required = f.required;
                    return (
                      <Tooltip key={f.key} title={required ? 'required' : enabled ? 'click to exclude' : 'click to include'}>
                        <Tag
                          onClick={() => !required && toggleField(f.key)}
                          className={`cursor-${required ? 'not-allowed' : 'pointer'} text-[9px] font-mono m-0 ${
                            enabled
                              ? 'bg-cyan-950/30 border-cyan-500/30 text-cyan-300'
                              : 'bg-black/30 border-white/10 text-gray-500'
                          }`}
                        >
                          {f.label}
                          {required && ' *'}
                        </Tag>
                      </Tooltip>
                    );
                  })}
                </div>
                <div className="text-[9px] text-gray-600 font-mono italic">
                  Top-level required fields (version, exported_at, charts) are always included.
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  type="primary"
                  icon={<Download className="w-3.5 h-3.5" />}
                  onClick={download}
                  disabled={!rendered || selectedIds.size === 0}
                  className="flex-1"
                  style={{ background: 'linear-gradient(135deg, #10b981, #059669)', border: 'none' }}
                >
                  Download
                </Button>
                <Button
                  icon={copyState === 'done' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  onClick={copyToClipboard}
                  disabled={!rendered || selectedIds.size === 0}
                >
                  {copyState === 'done' ? 'Copied' : 'Copy'}
                </Button>
              </div>
              {selectedIds.size === 0 && (
                <div className="text-[10px] text-amber-400/80 font-mono italic">
                  Select at least one chart to enable export.
                </div>
              )}
            </div>

            <div className="lg:col-span-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider font-bold">
                  Preview
                </span>
                <span className="text-[9px] text-gray-600 font-mono">
                  {(String(rendered).length / 1024).toFixed(1)} KB · {String(rendered).split('\n').length} lines
                </span>
              </div>
              <pre className="bg-black/55 border border-white/5 rounded-xl p-4 text-[10px] font-mono text-slate-300 max-h-[560px] overflow-auto whitespace-pre-wrap break-words leading-relaxed">
                {rendered || '—'}
              </pre>
            </div>
          </Row>
        </div>
      ) : null}
    </Card>
  );
};

export default ExportPanel;
