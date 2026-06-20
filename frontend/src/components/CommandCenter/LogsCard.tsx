/**
 * LogsCard — the "LOGS" sidebar card with TOOLS / LLM DEBUG tabs.
 *
 * Extracted verbatim from `components/UI/CommandCenter.jsx` (lines 723-780) as
 * part of the CommandCenter decomposition (Task 3.3, item 6). Pure
 * presentational component: props-only, zero coupling to CommandCenter state
 * (setters are passed in as callbacks).
 *
 * @component
 */
import React from 'react';
import { Card, Tabs, Button } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

/** A single tool-execution log entry. */
interface ToolLog {
  timestamp: string;
  type: string;
  status?: string;
  message: string;
}

/** The two tab keys surfaced inside the LogsCard. */
type LogTab = 'tools' | 'debug';

interface LogsCardProps {
  /** Currently active tab key. */
  activeLogTab: LogTab;
  /** Tool-execution log entries. */
  toolLogs: ToolLog[];
  /** LLM debug telemetry payload (JSON-stringified in the debug tab). */
  debugPayload: unknown;
  /** Ref attached to the log scroll sentinel. */
  logEndRef: React.RefObject<HTMLDivElement>;
  /** Fired when the active tab changes. */
  onTabChange?: (key: string) => void;
  /** Fired when the CLEAR button is pressed. */
  onClearLogs?: () => void;
  /** Fired when the RESET button is pressed. */
  onResetDebug?: () => void;
}

export default function LogsCard({
  activeLogTab,
  toolLogs,
  debugPayload,
  logEndRef,
  onTabChange,
  onClearLogs,
  onResetDebug
}: LogsCardProps) {
  return (
    <Card
      className="flex-1 min-h-[220px] bg-gray-900/80 border-purple-500/20 font-mono"
      styles={{ body: { padding: '12px', display: 'flex', flexDirection: 'column', flex: 1 } }}
      title={
        <Tabs
          size="small"
          activeKey={activeLogTab}
          onChange={(key: string) => { onTabChange?.(key); audioFeedback.playClick(); }}
          style={{ marginBottom: 0 }}
          items={[
            { key: 'tools', label: 'TOOLS' },
            { key: 'debug', label: 'LLM DEBUG' }
          ]}
        />
      }
      extra={
        activeLogTab === 'tools' ? (
          <Button size="small" type="text" onClick={() => { onClearLogs?.(); audioFeedback.playClick(); }} style={{ color: '#9ca3af', fontSize: '10px' }}>CLEAR</Button>
        ) : (
          <Button size="small" type="text" onClick={() => { onResetDebug?.(); audioFeedback.playClick(); }} style={{ color: '#9ca3af', fontSize: '10px' }}>RESET</Button>
        )
      }
    >

      {activeLogTab === 'tools' ? (
        <div className="flex-1 overflow-y-auto space-y-2 text-[11px] leading-relaxed scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
          {toolLogs.map((log, i) => (
            <div key={i} className="flex items-start gap-1">
              <span className="text-gray-600 select-none">[{log.timestamp}]</span>
              <span className={`font-bold select-none ${
                log.type === 'tool' ? 'text-cyan-400' :
                log.type === 'llm' ? 'text-purple-400' :
                log.type === 'system' ? 'text-yellow-400' : 'text-gray-500'
              }`}>
                {log.type.toUpperCase()}:
              </span>
              <span className={`
                ${log.status === 'success' ? 'text-green-400' :
                  log.status === 'error' ? 'text-red-400' :
                  log.status === 'pending' ? 'text-yellow-400 animate-pulse' : 'text-gray-300'
                }
              `}>
                {log.message}
              </span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto text-[10px] font-mono leading-normal text-cyan-300/90 whitespace-pre scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent bg-black/45 p-2 rounded border border-white/5 select-text selection:bg-purple-950/80">
          {debugPayload ? (
            JSON.stringify(debugPayload, null, 2)
          ) : (
            <span className="text-gray-500 italic">No telemetry data. Enable "Debug Payload" checkbox and submit a query.</span>
          )}
        </div>
      )}
    </Card>
  );
}
