/**
 * Time Cycles — planetary hour, moon phase, and meridian clock.
 * Shows current astrological timing and dharma calendar events
 * for session scheduling recommendations.
 * @component
 */
import React, { useState, useEffect } from 'react';
import { HelpCircle, Play, RefreshCw, Compass, Moon, Sun, Clock, Calendar, Check, AlertTriangle } from 'lucide-react';
import { message } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';

interface TimeCycleEvent {
  id: string;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  [key: string]: unknown;
}

interface TimeCycleServiceStatus {
  [key: string]: unknown;
}

type BroadcastLogType = 'info' | 'success' | 'error' | 'pending';

interface BroadcastLogEntry {
  timestamp: string;
  message: string;
  type: BroadcastLogType;
}

interface BroadcastAction {
  type: string;
  status?: string;
  data?: string;
  mantras?: number;
  targets?: number;
  duration?: number;
  intention?: string;
  [key: string]: unknown;
}

interface BroadcastResponse {
  actions?: BroadcastAction[];
  [key: string]: unknown;
}

interface EventsResponse {
  events?: TimeCycleEvent[];
  [key: string]: unknown;
}

export default function TimeCycles() {
  const [events, setEvents] = useState<TimeCycleEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>("");
  const [stepDays, setStepDays] = useState<number>(1);
  const [durationPerDay, setDurationPerDay] = useState<number>(5);
  const [createVisualizations, setCreateVisualizations] = useState<boolean>(true);

  // Operation state
  const [loading, setLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [currentDate, setCurrentDate] = useState<string>("");
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [broadcastLogs, setBroadcastLogs] = useState<BroadcastLogEntry[]>([]);
  const [totalMantrasSent, setTotalMantrasSent] = useState<number>(0);
  const [serviceStatus, setServiceStatus] = useState<TimeCycleServiceStatus | null>(null);

  useEffect(() => {
    fetchEvents();
    fetchStatus();
  }, []);

  const fetchEvents = async () => {
    try {
      const res = await fetch(`/api/v1/time-cycles/events`);
      if (res.ok) {
        const data: EventsResponse = await res.json();
        setEvents(data.events || []);
        if (data.events && data.events.length > 0) {
          setSelectedEventId(data.events[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch historical periods:", e);
      message.error('Could not load archetypal events: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch(`/api/v1/time-cycles/status`);
      if (res.ok) {
        const data: TimeCycleServiceStatus = await res.json();
        setServiceStatus(data);
      }
    } catch (e) {
      console.error(e);
      message.error('Could not load time-cycles status: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  const getActiveEvent = (): TimeCycleEvent | undefined => {
    return events.find(e => e.id === selectedEventId);
  };

  const addBroadcastLog = (msg: string, type: BroadcastLogType = 'info') => {
    setBroadcastLogs(prev => [
      {
        timestamp: new Date().toLocaleTimeString(),
        message: msg,
        type
      },
      ...prev
    ]);
  };

  // Run the full cycle sequence simulated day by day
  const handleExecuteCycle = async () => {
    const event = getActiveEvent();
    if (!event || isRunning) return;

    setIsRunning(true);
    setBroadcastLogs([]);
    setTotalMantrasSent(0);
    setProgressPercent(0);
    audioFeedback.playSuccess();

    addBroadcastLog(`Starting symbolic healing cycle for: "${event.name}"`, 'success');
    addBroadcastLog(`Period: ${event.start_date} to ${event.end_date}. Step size: ${stepDays} day(s).`, 'info');

    // Parse dates
    const start = new Date(event.start_date);
    const end = new Date(event.end_date);
    const totalDuration = end.getTime() - start.getTime();
    
    let current = new Date(start);

    // Run day by day loop
    while (current <= end && isRunning) {
      const dateStr = current.toISOString().split('T')[0];
      setCurrentDate(dateStr);
      
      const elapsed = current.getTime() - start.getTime();
      const pct = totalDuration > 0 ? Math.min(100, Math.round((elapsed / totalDuration) * 100)) : 100;
      setProgressPercent(pct);

      addBroadcastLog(`Focusing carrier wave aspect on target date: ${current.toLocaleDateString(undefined, { dateStyle: 'long' })}`, 'pending');
      audioFeedback.playTelemetry();

      try {
        const res = await fetch(`/api/v1/time-cycles/broadcast`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_id: event.id,
            target_date: dateStr,
            duration_seconds: durationPerDay,
            create_visualization: createVisualizations
          })
        });

        if (res.ok) {
          const data: BroadcastResponse = await res.json();
          // Print logs for each successful action
          (data.actions || []).forEach(action => {
            if (action.type === 'astrocartography' && action.status === 'success') {
              addBroadcastLog(`  ✓ Astro transits locked: ${action.data}`, 'info');
            } else if (action.type === 'blessing_dedication' && action.status === 'success') {
              addBroadcastLog(`  ✓ Dedicated ${action.mantras} mantras to ${action.targets} victims`, 'info');
              setTotalMantrasSent(prev => prev + (action.mantras || 0));
            } else if (action.type === 'radionics_broadcast') {
              addBroadcastLog(`  ✓ Radionics scalar broadcast completed for ${action.duration}s. Intention: "${action.intention}"`, 'success');
            }
          });
        } else {
          addBroadcastLog(`  ⚠ API error broadcasting to date ${dateStr}`, 'error');
        }
      } catch (err) {
        addBroadcastLog(`  ⚠ Connection failure for ${dateStr}: ${(err as Error).message}`, 'error');
      }

      // Wait for duration per day
      await new Promise<void>(resolve => setTimeout(resolve, durationPerDay * 1000));

      // Advance by stepDays
      current.setDate(current.getDate() + stepDays);
    }

    setProgressPercent(100);
    setIsRunning(false);
    audioFeedback.playSuccess();
    addBroadcastLog(`Time cycle broadcast complete for "${event.name}". Total mantras dedicated: ${totalMantrasSent}.`, 'success');
  };

  const activeEvent = getActiveEvent();

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      
      {/* Left Column: Events selection and specifications */}
      <div className="xl:col-span-1 bg-gray-950/40 p-5 rounded-xl border border-purple-500/15 space-y-5 flex flex-col justify-between">
        <div className="space-y-4">
          <div>
            <h3 className="text-md font-bold text-vajra-cyan glow-cyan flex items-center gap-2">
              ⏳ Archetypal Healing Cycles
            </h3>
            <p className="text-xs text-gray-400">Select a symbolic cycle for compassionate dedication</p>
          </div>

          {/* Event dropdown */}
          <div className="space-y-1.5">
            <label className="text-xs text-gray-400 block">Archetypal Cycle</label>
            <select
              value={selectedEventId}
              onChange={(e) => { setSelectedEventId(e.target.value); audioFeedback.playClick(); }}
              disabled={isRunning}
              className="w-full bg-gray-900 border border-white/10 rounded px-2.5 py-1.5 text-xs text-white"
            >
              {events.map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
          </div>

          {activeEvent && (
            <div className="bg-white/5 border border-white/5 p-3 rounded-lg space-y-2 text-xs">
              <div className="flex justify-between items-center border-b border-white/5 pb-1.5 text-[10px]">
                <span className="text-gray-500 font-mono">ID: {activeEvent.id.toUpperCase()}</span>
                <span className="text-purple-300 font-bold uppercase font-mono">Archetype</span>
              </div>
              <p className="text-gray-300 leading-normal">{activeEvent.description}</p>
              <div className="pt-2 flex justify-between gap-4 text-[10px] text-gray-400 font-mono">
                <span>Start: {activeEvent.start_date}</span>
                <span>End: {activeEvent.end_date}</span>
              </div>
            </div>
          )}

          {/* Parameter Configuration */}
          <div className="space-y-3 pt-3 border-t border-white/5">
            <h4 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Parameters</h4>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="space-y-1">
                <label className="text-gray-500">Step Size (Days)</label>
                <select
                  value={stepDays}
                  onChange={(e) => setStepDays(Number(e.target.value))}
                  disabled={isRunning}
                  className="w-full bg-gray-900 border border-white/10 rounded px-2 py-1 text-white font-mono"
                >
                  <option value={1}>1 Day (Detail)</option>
                  <option value={7}>7 Days (Weekly)</option>
                  <option value={30}>30 Days (Monthly)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-gray-500">Simulated Day duration</label>
                <select
                  value={durationPerDay}
                  onChange={(e) => setDurationPerDay(Number(e.target.value))}
                  disabled={isRunning}
                  className="w-full bg-gray-900 border border-white/10 rounded px-2 py-1 text-white font-mono"
                >
                  <option value={2}>2s / Day</option>
                  <option value={5}>5s / Day</option>
                  <option value={10}>10s / Day</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs pt-1.5">
              <input
                type="checkbox"
                id="create_viz"
                checked={createVisualizations}
                onChange={(e) => setCreateVisualizations(e.target.checked)}
                disabled={isRunning}
                className="rounded border-white/10 bg-gray-900 text-purple-600 focus:ring-0 focus:ring-offset-0"
              />
              <label htmlFor="create_viz" className="text-gray-400 select-none">Generate Daily Rothko Art</label>
            </div>
          </div>
        </div>

        {/* Trigger Button */}
        <button
          onClick={handleExecuteCycle}
          disabled={isRunning || !selectedEventId}
          className="w-full py-2 bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white rounded font-bold text-xs shadow flex items-center justify-center gap-2 disabled:bg-gray-800 disabled:from-gray-800 disabled:to-gray-800"
        >
          <Play className="w-3.5 h-3.5" />
          {isRunning ? 'Broadcast Running...' : 'Begin Symbolic Cycle'}
        </button>
      </div>

      {/* Right Column: Live Monitor and Logs */}
      <div className="xl:col-span-2 bg-gray-950/40 p-5 rounded-xl border border-purple-500/15 flex flex-col justify-between space-y-4">
        
        {/* Progress Grid */}
        <div className="space-y-3">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Symbolic Cycle Status</span>
          
          <div className="p-4 bg-black/60 border border-white/5 rounded-xl space-y-4 shadow-inner">
            <div className="flex justify-between items-center text-xs">
              <div>
                <span className="text-[10px] text-gray-500 font-mono block">CURRENT SYMBOLIC NODE</span>
                <span className="text-base font-bold text-white font-mono">{currentDate || "IDLE"}</span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-gray-500 font-mono block">DEDICATIONS OFFERED</span>
                <span className="text-base font-bold text-cyan-300 font-mono">{totalMantrasSent}</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden border border-white/10">
                <div 
                  className="bg-gradient-to-r from-cyan-500 to-purple-500 h-full shadow-[0_0_8px_rgba(0,245,255,0.4)] transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="flex justify-between text-[9px] text-gray-500 font-mono">
                <span>START</span>
                <span>{progressPercent}% RESOLVED</span>
                <span>END</span>
              </div>
            </div>
          </div>
        </div>

        {/* Real-time telemetry log */}
        <div className="flex-1 flex flex-col min-h-[220px]">
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block border-b border-white/5 pb-1">
            Broadcast Telemetry Log
          </span>
          
          <div className="flex-1 overflow-y-auto mt-2 space-y-2 max-h-[260px] scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
            {broadcastLogs.length > 0 ? (
              broadcastLogs.map((log, idx) => (
                <div key={idx} className="flex gap-2.5 items-start text-[10px] font-mono leading-normal">
                  <span className="text-gray-500 whitespace-nowrap">[{log.timestamp}]</span>
                  <span className={`flex-1 ${
                    log.type === 'success' ? 'text-green-400 font-semibold' :
                    log.type === 'error' ? 'text-red-400 font-bold' :
                    log.type === 'pending' ? 'text-cyan-300 animate-pulse' : 'text-gray-300'
                  }`}>
                    {log.message}
                  </span>
                </div>
              ))
            ) : (
              <span className="text-[10px] text-gray-500 italic block py-6 text-center">Telemetry log clear. Ready to initialize.</span>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
