/**
 * TrendsChart — blessing and session analytics chart.
 *
 * Hand-rolled SVG (no recharts) so 10-20 point datasets render in
 * <1ms instead of the 20-50ms recharts ResponsiveContainer overhead.
 * Wrapped in React.memo so Dashboard re-renders (WebSocket updates,
 * 5s automation polling) do not re-render this tree.
 *
 * The LLM-powered /operator/trends fetch fires once on mount and
 * only on explicit user click of the Refresh button. This removes
 * the cascading re-fetch that was a major contributor to lag on
 * low-power hardware.
 *
 * @component
 */
import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { TrendingUp, Sparkles, Loader2, RefreshCw } from 'lucide-react';
import { API_BASE } from '../../utils/api';

const CHART_W = 320;
const CHART_H = 96;
const CHART_PAD = 4;

const COLOR_BAR = '#22d3ee';
const COLOR_BAR_FILL = 'rgba(34, 211, 238, 0.18)';
const COLOR_LINE = '#a855f7';
const COLOR_AXIS = '#1e293b';
const COLOR_LABEL = '#64748b';

function BarChart({ data, valueKey, nameKey }) {
  if (!data || data.length === 0) return null;
  const values = data.map((d) => d[valueKey] || 0);
  const max = Math.max(...values, 1);
  const barW = (CHART_W - CHART_PAD * 2) / Math.max(data.length, 1);
  const innerH = CHART_H - CHART_PAD * 2;
  const usableH = innerH - 12;

  return (
    <svg
      viewBox={`0 0 ${CHART_W} ${CHART_H}`}
      width="100%"
      height={CHART_H}
      preserveAspectRatio="none"
      style={{ display: 'block' }}
      role="img"
      aria-label="Bar chart"
    >
      <rect x={CHART_PAD} y={CHART_PAD} width={CHART_W - CHART_PAD * 2} height={innerH} fill={COLOR_BAR_FILL} />
      {data.map((d, i) => {
        const h = (d[valueKey] || 0) / max * usableH;
        const x = CHART_PAD + i * barW + barW * 0.1;
        const w = barW * 0.8;
        const y = CHART_PAD + innerH - h - 12;
        return (
          <g key={i}>
            <rect x={x} y={y} width={w} height={h} fill={COLOR_BAR} rx={2}>
              <title>{`${d[nameKey]}: ${d[valueKey]}`}</title>
            </rect>
          </g>
        );
      })}
      {data.map((d, i) => {
        const x = CHART_PAD + i * barW + barW / 2;
        return (
          <text
            key={`l-${i}`}
            x={x}
            y={CHART_H - 2}
            textAnchor="middle"
            fontSize={9}
            fill={COLOR_LABEL}
            style={{ fontFamily: 'monospace' }}
          >
            {d[nameKey]}
          </text>
        );
      })}
    </svg>
  );
}

function LineChartSimple({ data, valueKey, nameKey, min, max }) {
  if (!data || data.length === 0) return null;
  const lo = min ?? Math.min(...data.map((d) => d[valueKey] || 0), 0);
  const hi = max ?? Math.max(...data.map((d) => d[valueKey] || 0), 100);
  const range = hi - lo || 1;
  const innerH = CHART_H - CHART_PAD * 2;
  const usableH = innerH - 12;
  const innerW = CHART_W - CHART_PAD * 2;
  const stepX = data.length > 1 ? innerW / (data.length - 1) : innerW;

  const points = data.map((d, i) => {
    const x = CHART_PAD + i * stepX;
    const y = CHART_PAD + innerH - ((d[valueKey] || 0) - lo) / range * usableH - 12;
    return { x, y, v: d[valueKey] };
  });
  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

  return (
    <svg
      viewBox={`0 0 ${CHART_W} ${CHART_H}`}
      width="100%"
      height={CHART_H}
      preserveAspectRatio="none"
      style={{ display: 'block' }}
      role="img"
      aria-label="Line chart"
    >
      <path
        d={pathD}
        fill="none"
        stroke={COLOR_LINE}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={2} fill={COLOR_LINE}>
          <title>{`${data[i][nameKey]}: ${p.v}`}</title>
        </circle>
      ))}
      {data.map((d, i) => {
        const x = CHART_PAD + i * stepX;
        return (
          <text
            key={`l-${i}`}
            x={x}
            y={CHART_H - 2}
            textAnchor="middle"
            fontSize={9}
            fill={COLOR_LABEL}
            style={{ fontFamily: 'monospace' }}
          >
            {d[nameKey]}
          </text>
        );
      })}
    </svg>
  );
}

function TrendsChartInner({ sessionHistory }) {
  const [rateHistory, setRateHistory] = useState([]);
  const [llmTrends, setLlmTrends] = useState(null);
  const [trendsLoading, setTrendsLoading] = useState(false);
  const fetchedOnceRef = useRef(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('rate-storage');
      if (stored) {
        const parsed = JSON.parse(stored);
        const history = parsed?.state?.rateHistory || [];
        setRateHistory(history.slice(0, 20));
      }
    } catch {}
  }, []);

  const sessionData = useMemo(
    () => (sessionHistory || []).slice(-10).map((s, i) => ({
      name: (s.config?.name || s.name || `S${i}`).slice(0, 8),
      duration: s.config?.duration
        ? Math.round(s.config.duration / 60)
        : s.total_runtime
          ? Math.round(s.total_runtime / 60)
          : Math.round((s.duration || 0) / 60),
    })),
    [sessionHistory]
  );

  const rateData = useMemo(
    () => rateHistory.map((r, i) => ({
      name: `R${i}`,
      rate: r.rate || r.values?.[0] || 50,
    })),
    [rateHistory]
  );

  const chartData = useMemo(() => {
    const labels = llmTrends?.chart_data?.labels || sessionData.map((d) => d.name);
    const values = llmTrends?.chart_data?.values || sessionData.map((d) => d.duration);
    return labels.map((label, i) => ({
      name: typeof label === 'string' ? label.slice(0, 8) : `S${i}`,
      duration: values[i] || 0,
    }));
  }, [llmTrends, sessionData]);

  const fetchTrends = useCallback(async () => {
    setTrendsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/operator/trends`);
      if (res.ok) {
        const data = await res.json();
        setLlmTrends(data);
      }
    } catch {}
    setTrendsLoading(false);
  }, []);

  useEffect(() => {
    if (fetchedOnceRef.current) return;
    fetchedOnceRef.current = true;
    fetchTrends();
  }, [fetchTrends]);

  const hasAnyData = chartData.length > 0 || rateData.length > 0 || llmTrends;

  return (
    <div className="space-y-6">
      {llmTrends?.analysis && (
        <div className="bg-gradient-to-r from-indigo-900/20 to-purple-900/20 rounded-lg p-4 border border-indigo-500/20">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-xs text-indigo-300 font-semibold mb-1">AI Trend Analysis</div>
              <div className="text-sm text-gray-300 leading-relaxed">{llmTrends.analysis}</div>
              {llmTrends.patterns && llmTrends.patterns.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {llmTrends.patterns.map((p, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 bg-indigo-950/40 border border-indigo-500/20 rounded-full text-indigo-300">
                      {p}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {trendsLoading && !llmTrends && (
        <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          Analyzing trends...
        </div>
      )}

      {llmTrends?.recommendations && llmTrends.recommendations.length > 0 && (
        <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/50">
          <div className="text-xs text-gray-400 font-semibold mb-2">Recommendations</div>
          {llmTrends.recommendations.map((r, i) => (
            <div key={i} className="text-xs text-gray-300 flex items-start gap-1.5 py-0.5">
              <span className="text-purple-400">•</span> {r}
            </div>
          ))}
        </div>
      )}

      {chartData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Session Duration (min)
          </h3>
          <BarChart data={chartData} valueKey="duration" nameKey="name" />
        </div>
      )}

      {rateData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            Rate History
          </h3>
          <LineChartSimple data={rateData} valueKey="rate" nameKey="name" min={0} max={100} />
        </div>
      )}

      {llmTrends?.most_used_frequency && (
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="text-gray-500 mb-1">Most Used Frequency</div>
            <div className="text-cyan-400 font-bold text-lg">{llmTrends.most_used_frequency} Hz</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="text-gray-500 mb-1">Common Theme</div>
            <div className="text-purple-400 font-bold">{llmTrends.most_common_intention_theme || 'healing'}</div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={fetchTrends}
          disabled={trendsLoading}
          className="flex items-center gap-1.5 text-[10px] font-mono text-gray-400 hover:text-cyan-300 disabled:text-gray-600 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${trendsLoading ? 'animate-spin' : ''}`} />
          {trendsLoading ? 'Refreshing...' : 'Refresh AI insights'}
        </button>
      </div>

      {!hasAnyData && !trendsLoading && (
        <div className="text-center text-gray-500 text-sm py-8">
          No data yet — start sessions to see trends
        </div>
      )}
    </div>
  );
}

const TrendsChart = React.memo(TrendsChartInner);
export default TrendsChart;
