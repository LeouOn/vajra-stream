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
 * state.
 *
 * @component
 * @param {Object}      props
 * @param {boolean}     props.isPlaying      - whether prayer-bowl audio is playing.
 * @param {Object}      props.sessions       - active sessions keyed by id.
 * @param {Object}      props.scalarStatus   - scalar array status object (read for `.rate`).
 */
import React from 'react';
import { Card } from 'antd';
import { Activity } from 'lucide-react';

import ScalarWaveVisualizer from '../2D/ScalarWaveVisualizer';
import { AttunementChart } from '../UI/AttunementChart';

interface SystemMonitorsCardProps {
  isPlaying?: boolean;
  sessions?: Record<string, unknown>;
  scalarStatus?: { rate?: string | number } | null;
}

export function describePresence(
  isPlaying: boolean | undefined,
  sessions: Record<string, unknown> | undefined,
): { holding: boolean; label: string } {
  const sessionCount = sessions ? Object.keys(sessions).length : 0;
  const parts: string[] = [];
  if (isPlaying) parts.push('audio');
  if (sessionCount > 0) parts.push(`${sessionCount} session${sessionCount === 1 ? '' : 's'}`);
  return { holding: parts.length > 0, label: parts.length > 0 ? `Holding · ${parts.join(' + ')}` : 'Resting' };
}

function SystemMonitorsCardInner({
  isPlaying,
  sessions,
  scalarStatus
}: SystemMonitorsCardProps): React.ReactElement {
  const { holding, label: presenceLabel } = describePresence(isPlaying, sessions);
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

        {/* Field Presence — reflects real state only (audio + active sessions).
            It used to be a sin+random "Aura Field Coherence %" that read ~88%
            whenever audio played; no such measurement exists, so no number. */}
        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <div className="flex justify-between items-center gap-3 text-xs text-gray-400 font-medium mb-1.5">
            <span>Field Presence</span>
            <span className={`font-mono font-bold whitespace-nowrap ${holding ? 'text-purple-400' : 'text-gray-500'}`}>
              {presenceLabel}
            </span>
          </div>
          <div
            className={`flex gap-0.5 h-2.5 bg-black/60 rounded p-0.5 overflow-hidden border border-white/5 ${holding ? 'animate-pulse' : ''}`}
            aria-hidden="true"
          >
            {Array.from({ length: 20 }).map((_, idx) => {
              let color = "bg-purple-950";
              if (holding) {
                if (idx < 12) color = "bg-purple-500 shadow-[0_0_4px_rgba(168,85,247,0.7)]";
                else if (idx < 17) color = "bg-cyan-400 shadow-[0_0_4px_rgba(34,211,238,0.7)]";
                else color = "bg-yellow-400 shadow-[0_0_4px_rgba(250,204,21,0.7)]";
              }
              return <div key={idx} className={`flex-1 rounded-sm transition-all duration-300 ${color}`} />;
            })}
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

// Memoize — SystemMonitorsCard renders ScalarWaveVisualizer (heavy RAF loop);
// skip re-rendering it on unrelated CommandCenter state changes.
const SystemMonitorsCard = React.memo(SystemMonitorsCardInner);
export default SystemMonitorsCard;
