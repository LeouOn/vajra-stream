/**
 * SystemMonitorsCard — the "SYSTEM MONITORS" sidebar card.
 *
 * Extracted verbatim from `components/UI/CommandCenter.jsx` (lines 547-659) as
 * part of the CommandCenter decomposition (Task 3.3, item 4). Pure
 * presentational component: props-only, zero coupling to CommandCenter state.
 *
 * Renders the scalar-wave visualizer, the Aura Field Coherence VU meter, the
 * live Attunement metrics chart, and a stack of link/carrier/crystal/scalar/
 * session status rows.
 *
 * @component
 * @param {Object}      props
 * @param {number}      props.auraCoherence  - 0-100 coherence value for the VU meter.
 * @param {boolean}     props.isConnected    - websocket link status.
 * @param {boolean}     props.isPlaying      - audio carrier running.
 * @param {number}      props.frequency      - current carrier frequency in Hz.
 * @param {Object}      props.crystalStatus  - crystal broadcaster status object.
 * @param {Object}      props.scalarStatus   - scalar array status object.
 * @param {Object}      props.sessions       - active blessing sessions keyed by id.
 */
import React from 'react';
import { Card } from 'antd';
import { Activity, Wifi } from 'lucide-react';

import ScalarWaveVisualizer from '../2D/ScalarWaveVisualizer';
import { AttunementChart } from '../UI/AttunementChart';

export default function SystemMonitorsCard({
  auraCoherence,
  isConnected,
  isPlaying,
  frequency,
  crystalStatus,
  scalarStatus,
  sessions
}) {
  return (
    <Card
      title={<span className="text-white text-sm tracking-wider font-bold"><Activity className="w-4 h-4 text-purple-400 inline mr-2" />SYSTEM MONITORS</span>}
      className="bg-gray-900/80 border-purple-500/20"
      styles={{ body: { padding: '16px' } }}
    >

      <div className="space-y-4">

        {/* Scalar Wave Interference Visualizer */}
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-gray-400 font-medium">Scalar Wave Field</span>
          <div className="h-20">
            <ScalarWaveVisualizer />
          </div>
        </div>

        {/* Aura Field Coherence VU Meter */}
        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <div className="flex justify-between items-center text-xs text-gray-400 font-medium mb-1.5">
            <span>Aura Field Coherence</span>
            <span className="text-purple-400 font-mono font-bold animate-pulse">{auraCoherence}%</span>
          </div>
          <div className="flex gap-0.5 h-2.5 bg-black/60 rounded p-0.5 overflow-hidden border border-white/5">
            {Array.from({ length: 20 }).map((_, idx) => {
              const threshold = (idx / 20) * 100;
              const active = auraCoherence > threshold;
              let color = "bg-purple-950";
              if (active) {
                if (idx < 12) color = "bg-purple-500 shadow-[0_0_4px_rgba(168,85,247,0.7)]";
                else if (idx < 17) color = "bg-cyan-400 shadow-[0_0_4px_rgba(34,211,238,0.7)]";
                else color = "bg-yellow-400 shadow-[0_0_4px_rgba(250,204,21,0.7)]";
              }
              return <div key={idx} className={`flex-1 rounded-sm transition-all duration-300 ${color}`} />;
            })}
          </div>
          <div className="flex justify-between text-[8px] text-gray-500 font-mono mt-1 select-none">
            <span>MIN (0.0)</span>
            <span>CALIBRATED (1.0)</span>
            <span>PEAK</span>
          </div>
        </div>

        {/* Live Attunement Metrics Chart */}
        <div className="mt-2">
          <AttunementChart />
        </div>

        {/* Connection Status */}
        <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
          <span className="text-xs text-gray-400 font-medium">Link Status</span>
          <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full flex items-center gap-1.5 ${
            isConnected
              ? 'bg-green-950/80 border border-green-500/30 text-green-400'
              : 'bg-red-950/80 border border-red-500/30 text-red-400'
          }`}>
            <Wifi className="w-3 h-3" />
            {isConnected ? 'LIVE CONNECTED' : 'OFFLINE'}
          </span>
        </div>

        {/* Freq generator status */}
        <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
          <span className="text-xs text-gray-400 font-medium">Audio Carrier</span>
          <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full flex items-center gap-1.5 ${
            isPlaying
              ? 'bg-cyan-950/80 border border-cyan-500/30 text-cyan-400 animate-pulse'
              : 'bg-gray-800/80 border border-white/10 text-gray-400'
          }`}>
            {isPlaying ? `${frequency.toFixed(1)} Hz` : 'INACTIVE'}
          </span>
        </div>

        {/* Crystal Broadcaster Grid status */}
        <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
          <span className="text-xs text-gray-400 font-medium">Crystal Broadcaster</span>
          <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
            crystalStatus?.is_programmed
              ? 'bg-yellow-950/80 border border-yellow-500/30 text-yellow-400'
              : 'bg-gray-800/80 border border-white/10 text-gray-400'
          }`}>
            {crystalStatus?.is_programmed ? 'PROGRAMMED' : 'STANDBY'}
          </span>
        </div>

        {/* Scalar status */}
        <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
          <span className="text-xs text-gray-400 font-medium">Scalar Array Rate</span>
          <span className="text-xs font-mono text-indigo-300 font-bold bg-indigo-950/40 px-2 py-0.5 border border-indigo-500/20 rounded">
            {scalarStatus?.rate || '0.00 / 0.00'}
          </span>
        </div>

        {/* Active session count */}
        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <div className="text-xs text-gray-400 font-medium mb-2">Active Blessing Rotations</div>
          {Object.keys(sessions).length > 0 ? (
            <div className="space-y-1.5 max-h-24 overflow-y-auto">
              {Object.values(sessions).map(session => (
                <div key={session.id} className="flex justify-between items-center text-xs">
                  <span className="text-purple-300 truncate max-w-[70%]">{session.name}</span>
                  <span className="text-[10px] bg-green-950 text-green-400 border border-green-500/30 px-1.5 py-0.2 rounded-full uppercase">
                    {session.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">No operations active</div>
          )}
        </div>
      </div>

    </Card>
  );
}
