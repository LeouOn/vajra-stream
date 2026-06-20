import React, { useState, useEffect, useMemo } from 'react';
import { Card } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { useWebSocket } from '../../hooks/useWebSocket';

interface AttunementDataPoint {
  time: string;
  timestamp: number;
  coherence: string;
  entropy: string;
  fn_score: string;
  coherenceNum?: number;
  entropyNum?: number;
}

interface Props {}

const MAX_DATA_POINTS = 30; // About 90 seconds of data (1 point per 3s)

export const AttunementChart: React.FC<Props> = (_props: Props) => {
  const { rngData } = useWebSocket();
  const [data, setData] = useState<AttunementDataPoint[]>([]);

  useEffect(() => {
    if (rngData) {
      const now = new Date();
      setData(prevData => {
        const newData: AttunementDataPoint[] = [...prevData, {
          time: now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' }),
          timestamp: now.getTime(),
          coherence: Number(rngData.coherence || 0).toFixed(3),
          entropy: Number(rngData.entropy || 0).toFixed(3),
          fn_score: Number(rngData.floating_needle_score || 0).toFixed(1)
        }];
        
        // Keep only the last N points
        if (newData.length > MAX_DATA_POINTS) {
          return newData.slice(newData.length - MAX_DATA_POINTS);
        }
        return newData;
      });
    }
  }, [rngData]);

  // Calculate moving averages for visual smoothing
  const chartData = useMemo<AttunementDataPoint[]>(() => {
    return data.map(d => ({
      ...d,
      coherenceNum: parseFloat(d.coherence),
      entropyNum: parseFloat(d.entropy)
    }));
  }, [data]);

  return (
    <Card 
      title={<div className="flex items-center gap-2">
        <span className="text-xl">✨</span> 
        <span className="font-semibold text-purple-100">Live Attunement Metrics</span>
      </div>}
      size="small" 
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '16px', height: '280px' } }}
    >
      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis 
              dataKey="time" 
              stroke="#64748b" 
              fontSize={11} 
              tickMargin={10}
              minTickGap={20}
            />
            <YAxis 
              yAxisId="left"
              domain={[0, 1]} 
              stroke="#64748b" 
              fontSize={11} 
              tickCount={5}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              domain={['auto', 'auto']}
              stroke="#64748b" 
              fontSize={11}
              hide
            />
            <Tooltip 
              contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(168, 85, 247, 0.4)', borderRadius: '8px' }}
              itemStyle={{ color: '#e2e8f0' }}
              labelStyle={{ color: '#94a3b8', marginBottom: '4px' }}
            />
            <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />
            
            <ReferenceLine y={0.3} yAxisId="left" stroke="#ef4444" strokeDasharray="3 3" opacity={0.5} label={{ position: 'insideTopLeft', value: 'Low', fill: '#ef4444', fontSize: 10, opacity: 0.5 }} />
            <ReferenceLine y={0.8} yAxisId="left" stroke="#22c55e" strokeDasharray="3 3" opacity={0.5} label={{ position: 'insideBottomLeft', value: 'High', fill: '#22c55e', fontSize: 10, opacity: 0.5 }} />
            
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="coherenceNum" 
              name="Coherence" 
              stroke="#a855f7" 
              strokeWidth={2} 
              dot={false}
              activeDot={{ r: 6, fill: "#a855f7", stroke: "#fff", strokeWidth: 2 }}
              isAnimationActive={false}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="entropyNum" 
              name="Entropy" 
              stroke="#0ea5e9" 
              strokeWidth={2} 
              dot={false}
              activeDot={{ r: 4, fill: "#0ea5e9" }}
              isAnimationActive={false}
              opacity={0.6}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-full flex items-center justify-center text-gray-500 flex-col gap-3">
          <div className="animate-pulse flex gap-1">
            <div className="w-2 h-2 bg-purple-500/50 rounded-full"></div>
            <div className="w-2 h-2 bg-purple-500/50 rounded-full animation-delay-200"></div>
            <div className="w-2 h-2 bg-purple-500/50 rounded-full animation-delay-400"></div>
          </div>
          <p className="text-sm">Awaiting RNG attunement data...</p>
        </div>
      )}
    </Card>
  );
};
