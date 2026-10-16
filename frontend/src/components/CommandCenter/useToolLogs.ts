/**
 * useToolLogs — the tool-execution log shown in LogsCard. Starts with the
 * "online" line; entries are timestamped with the local time when added.
 */
import { useState } from 'react';
import type { AddToolLog, ToolLogEntry } from './commandCenterTypes';

export function useToolLogs() {
  const [toolLogs, setToolLogs] = useState<ToolLogEntry[]>([
    {
      timestamp: new Date().toLocaleTimeString(),
      type: 'system',
      message: 'Quantum RNG & Attunement system online. Idle.'
    }
  ]);

  const addToolLog: AddToolLog = (type, message, status = 'info') => {
    setToolLogs(prev => [
      ...prev,
      {
        timestamp: new Date().toLocaleTimeString(),
        type,
        message,
        status
      }
    ]);
  };

  const clearToolLogs = () => setToolLogs([]);

  return { toolLogs, addToolLog, clearToolLogs };
}
