import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, Sparkles, Loader2 } from 'lucide-react';
import { API_BASE } from '../../utils/api';

const CHAKRA_COLORS = ['#ff4444', '#ff8c00', '#ffdd00', '#00ff88', '#00ccff', '#9966ff', '#cc66ff'];

const TrendsChart = ({ sessionHistory }) => {
  const [rateHistory, setRateHistory] = useState([]);
  const [llmTrends, setLlmTrends] = useState(null);
  const [trendsLoading, setTrendsLoading] = useState(false);

  // Local rate history from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('rate-storage');
      if (stored) {
        const parsed = JSON.parse(stored);
        const history = parsed?.state?.rateHistory || [];
        setRateHistory(history.slice(0, 20));
      }
    } catch (e) {
    }
  }, []);

  // Fetch LLM-powered trend analysis
  useEffect(() => {
    const fetchTrends = async () => {
      setTrendsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/operator/trends`);
        if (res.ok) {
          const data = await res.json();
          setLlmTrends(data);
        }
      } catch {
        // Silently fail — fall back to basic charts
      }
      setTrendsLoading(false);
    };
    fetchTrends();
  }, [sessionHistory]);

  const sessionData = (sessionHistory || []).slice(-10).map((s, i) => ({
    name: (s.config?.name || s.name || `S${i}`).slice(0, 8),
    duration: s.config?.duration
      ? Math.round(s.config.duration / 60)
      : s.total_runtime
        ? Math.round(s.total_runtime / 60)
        : Math.round((s.duration || 0) / 60),
  }));

  const rateData = rateHistory.map((r, i) => ({
    name: `R${i}`,
    rate: r.rate || r.values?.[0] || 50,
    category: r.category || 'custom',
  }));

  // Use LLM chart data if available, otherwise use local data
  const chartLabels = llmTrends?.chart_data?.labels || sessionData.map(d => d.name);
  const chartValues = llmTrends?.chart_data?.values || sessionData.map(d => d.duration);

  const llmChartData = chartLabels.map((label, i) => ({
    name: typeof label === 'string' ? label.slice(0, 8) : `S${i}`,
    duration: chartValues[i] || 0,
  }));

  return (
    <div className="space-y-6">
      {/* LLM Analysis Banner */}
      {llmTrends?.analysis && (
        <div className="bg-gradient-to-r from-indigo-900/20 to-purple-900/20 rounded-lg p-4 border border-indigo-500/20">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
            <div>
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

      {/* Recommendations */}
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

      {/* Session Duration Chart */}
      {llmChartData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Session Duration (min)
          </h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={llmChartData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
              <Bar dataKey="duration" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Rate History */}
      {rateData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            Rate History
          </h3>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={rateData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} domain={[0, 100]} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
              <Line type="monotone" dataKey="rate" stroke="#a855f7" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Quick Stats */}
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

      {/* Empty state */}
      {sessionData.length === 0 && rateData.length === 0 && !llmTrends && (
        <div className="text-center text-gray-500 text-sm py-8">
          No data yet — start sessions to see trends
        </div>
      )}
    </div>
  );
};

export default TrendsChart;
