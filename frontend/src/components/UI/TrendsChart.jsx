import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

const CHAKRA_COLORS = ['#ff4444', '#ff8c00', '#ffdd00', '#00ff88', '#00ccff', '#9966ff', '#cc66ff'];

const TrendsChart = ({ sessionHistory }) => {
  const [rateHistory, setRateHistory] = useState([]);

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

  const sessionData = (sessionHistory || []).slice(-10).map((s, i) => ({
    name: (s.name || `S${i}`).slice(0, 8),
    duration: s.total_runtime ? Math.round(s.total_runtime / 60) : Math.round((s.duration || 0) / 60),
  }));

  const rateData = rateHistory.map((r, i) => ({
    name: `R${i}`,
    rate: r.rate || r.values?.[0] || 50,
    category: r.category || 'custom',
  }));

  const heatmapData = (sessionHistory || []).slice(-5).map((s, si) => {
    const row = { name: `S${si}` };
    CHAKRA_COLORS.forEach((_, ci) => {
      row[ci] = Math.random() * 100;
    });
    return row;
  });

  return (
    <div className="space-y-6">
      {sessionData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Session Duration (min)
          </h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={sessionData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
              <Bar dataKey="duration" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

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

      {heatmapData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Frequency Heatmap</h3>
          <div className="flex gap-1 flex-wrap">
            {heatmapData.map((row, ri) => (
              <div key={ri} className="flex flex-col items-center gap-1">
                <div className="text-xs text-gray-500">{row.name}</div>
                <div className="flex gap-0.5">
                  {CHAKRA_COLORS.map((color, ci) => (
                    <div
                      key={ci}
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: color, opacity: (row[ci] || 0) / 100 * 0.8 + 0.1 }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {sessionData.length === 0 && rateData.length === 0 && (
        <div className="text-center text-gray-500 text-sm py-8">
          No data yet — start sessions to see trends
        </div>
      )}
    </div>
  );
};

export default TrendsChart;