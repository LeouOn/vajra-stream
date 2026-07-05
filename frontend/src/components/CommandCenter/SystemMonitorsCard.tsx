/**
 * SystemMonitorsCard — focused "FIELD READINGS" panel for scalar / aura /
 * attunement. Previously also hosted the link / audio / crystal status rows
 * and the active-blessing-rotation list; both moved out during the
 * CommandCenter cleanup:
 *
 *   - Link / Audio / Crystal status → compact header pill bar in CommandCenter.
 *   - Active Blessing Rotations      → collapsible panel in CommandCenter.
 *
 * Keeping this card purely about *field readings* reduces vertical weight and
 * matches the calmer, less-control-room aesthetic the operator wanted.
 *
 * Pure presentational component: props-only, zero coupling to CommandCenter
 * state (auraCoherence is now the only value it reads live).
 *
 * @component
 * @param {Object}      props
 * @param {number}      props.auraCoherence  - 0-100 coherence value for the VU meter.
 * @param {Object}      props.scalarStatus   - scalar array status object (read for `.rate`).
 */
import React from 'react';
import { Card } from 'antd';
import { Activity } from 'lucide-react';

import ScalarWaveVisualizer from '../2D/ScalarWaveVisualizer';
import { AttunementChart } from '../UI/AttunementChart';

function SystemMonitorsCardInner({
  auraCoherence,
  scalarStatus
}) {
  return (
    <Card
      title={<span className="text-white text-sm tracking-wider font-bold"><Activity className="w-4 h-4 text-purple-400 inline mr-2" />FIELD READINGS</span>}
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

        {/* Scalar status (the one scalar reading still anchored here) */}
        <div className="flex justify-between items-center bg-white/5 px-3 py-2.5 rounded-lg border border-white/5">
          <span className="text-xs text-gray-400 font-medium">Scalar Array Rate</span>
          <span className="text-xs font-mono text-indigo-300 font-bold bg-indigo-950/40 px-2 py-0.5 border border-indigo-500/20 rounded">
            {scalarStatus?.rate || '0.00 / 0.00'}
          </span>
        </div>
      </div>

    </Card>
  );
}

// Memoize — SystemMonitorsCard renders ScalarWaveVisualizer (heavy RAF loop)
// and re-renders whenever CommandCenter's auraCoherence state changes (1Hz).
// Without memo, the entire card + visualizer re-mounts on every tick.
const SystemMonitorsCard = React.memo(SystemMonitorsCardInner);
export default SystemMonitorsCard;
