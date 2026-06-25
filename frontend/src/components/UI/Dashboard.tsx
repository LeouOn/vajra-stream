/**
 * Dashboard — system overview and real-time metrics display.
 *
 * Shows high-level Vajra.Stream status: active sessions, MOPS throughput,
 * WebSocket connection state, RNG coherence, current astrological
 * conditions, and recent blessing activity. Serves as the landing page.
 *
 * @component
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Activity, 
  Zap, 
  Heart, 
  Clock, 
  BookOpen, 
  Sparkles,
  TrendingUp,
  Play,
  Plus,
  Settings,
  Moon
} from 'lucide-react';
import TrendsChart from './TrendsChart';
import { useWebSocketStable as useWebSocket } from '../../hooks/useWebSocketStable';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { useAudioStore } from '../../stores/audioStore';
import { useUIStore } from '../../stores/uiStore';
import { useCrystalStore } from '../../stores/crystalStore';
import { useRateStore } from '../../stores/rateStore';
import SessionTimeline from './SessionTimeline';
import FrequencyWaterfall from '../2D/FrequencyWaterfall';
import { MiniGlobe } from '../3D/RadionicsGlobe';
import JourneyCard from './JourneyCard';
import BuddhaContemplationWidget from './BuddhaContemplationWidget';
import SakaDawaBanner from './SakaDawaBanner';
import RitualPhaseIndicator from './RitualPhaseIndicator';
import BodhicittaBanner from './BodhicittaBanner';
import GeneratedContentGallery from './GeneratedContentGallery';
import RitualMonitor from './RitualMonitor';
import { CardSkeleton, SessionSkeleton } from './LoadingSkeleton';

const colorMap = {
  purple: {
    container: 'hover:border-purple-500/50',
    iconBg: 'bg-purple-900/50 group-hover:bg-purple-800/50',
    icon: 'text-purple-400'
  },
  green: {
    container: 'hover:border-green-500/50',
    iconBg: 'bg-green-900/50 group-hover:bg-green-800/50',
    icon: 'text-green-400'
  },
  blue: {
    container: 'hover:border-blue-500/50',
    iconBg: 'bg-blue-900/50 group-hover:bg-blue-800/50',
    icon: 'text-blue-400'
  },
  gray: {
    container: 'hover:border-gray-500/50',
    iconBg: 'bg-gray-700/50 group-hover:bg-gray-600/50',
    icon: 'text-gray-400'
  }
};

const Dashboard = () => {
  const { sessions, isConnected, crystalStatus, scalarStatus, rngData } = useWebSocket();
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const frequency = useAudioStore((s) => s.frequency);
  const playAudio = useAudioStore((s) => s.playAudio);
  const stopAudio = useAudioStore((s) => s.stopAudio);
  const generateAudio = useAudioStore((s) => s.generateAudio);
  const addToast = useUIStore((s) => s.addToast);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const setSearchOpen = useUIStore((s) => s.setSearchOpen);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [quickAstro, setQuickAstro] = useState(null);
  const [automationStatus, setAutomationStatus] = useState(null);

  const fetchCrystalGrid = useCrystalStore(s => s.fetchCrystalGrid);
  const getRateCategories = useRateStore(s => s.getRateCategories);
  const { isConnected } = useWebSocket();

  // Dashboard data fetcher — extracted so it can be re-invoked on WS reconnect.
  // Without this, a backend restart leaves the dashboard showing stale
  // session history / quickAstro / crystal grid data until a manual refresh.
  const fetchDashboardData = useCallback(() => {
    fetch('/api/v1/sessions/history')
      .then(r => r.json())
      .then(d => setSessionHistory(d.history || []))
      .catch(() => setSessionHistory([]));
    fetchCrystalGrid();
    getRateCategories();
    fetch(`/api/v1/astrology/current?latitude=${DEFAULT_LAT}&longitude=${DEFAULT_LNG}`)
      .then(r => r.json())
      .then(d => setQuickAstro(d.astrology || null))
      .catch(() => {});
  }, [fetchCrystalGrid, getRateCategories]);

  useEffect(() => {
    fetchDashboardData();
    // Poll automation status — this one already self-recovers via its
    // setInterval, so no extra WS-reconnect wiring needed.
    const pollAutomation = async () => {
      try {
        const res = await fetch('/api/v1/automation/status');
        if (res.ok) {
          const data = await res.json();
          setAutomationStatus(data);
        }
      } catch {}
    };
    pollAutomation();
    const interval = setInterval(pollAutomation, 5000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  // Refetch dashboard data when the WebSocket reconnects after a backend
  // restart. Same recovery pattern used in JourneyCard.
  useEffect(() => {
    if (isConnected) {
      fetchDashboardData();
    }
  }, [isConnected, fetchDashboardData]);
  
  const activeSessions = Object.values(sessions);
  const runningSessions = activeSessions.filter(s => s.status === 'running');
  
  const SectionHeading = ({ icon: Icon, label, color, badge }) => (
    <div className="flex items-center gap-3 mb-4">
      <div className={`w-8 h-8 rounded-lg bg-slate-800/80 border border-slate-700/50 flex items-center justify-center`}>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">{label}</h2>
      {badge !== undefined && (
        <span className="px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700/50 text-[10px] font-mono text-slate-400">{badge}</span>
      )}
      <div className="flex-1 h-px bg-gradient-to-r from-slate-800 to-transparent ml-2" />
    </div>
  );

  const QuickStatCard = ({ icon: Icon, label, value, trend, color }) => (
    <div className="group relative overflow-hidden rounded-xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/30 p-5 transition-all duration-300 hover:shadow-[0_0_20px_rgba(168,85,247,0.08)]">
      <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-purple-500/3 to-transparent rounded-bl-3xl" />
      <div className="relative flex items-center justify-between mb-3">
        <div className={`w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
        {trend && (
          <div className="flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
            <TrendingUp className="w-3 h-3" />
            <span>{trend}</span>
          </div>
        )}
      </div>
      <div className="text-3xl font-bold text-white tracking-tight">{value}</div>
      <div className="text-[11px] text-slate-500 mt-1 font-medium uppercase tracking-wider">{label}</div>
    </div>
  );

  const QuickActionButton = ({ icon: Icon, label, onClick, color = 'purple' }) => {
    const colors = colorMap[color] || colorMap.purple;
    return (
      <button
        onClick={onClick}
        className={`group flex flex-col items-center gap-3 p-5 rounded-xl bg-slate-900/60 border border-slate-800 ${colors.container} transition-all duration-300 hover:shadow-[0_0_15px_rgba(168,85,247,0.1)]`}
      >
        <div className={`w-11 h-11 rounded-xl ${colors.iconBg} flex items-center justify-center transition-all group-hover:scale-110`}>
          <Icon className={`w-5 h-5 ${colors.icon}`} />
        </div>
        <span className="text-xs font-medium text-slate-400 group-hover:text-white transition-colors">{label}</span>
      </button>
    );
  };

  const handleNewSession = () => {
    setSidebarOpen(true);
    addToast({ type: 'info', title: 'Create Session', message: 'Use the Session Manager in the sidebar to create a new session', duration: 4000 });
  };

  const handleToggleAudio = async () => {
    if (isPlaying) {
      stopAudio();
      addToast({ type: 'info', title: 'Audio Stopped', message: 'Audio playback stopped', duration: 2000 });
    } else {
      await generateAudio();
      const success = await playAudio();
      if (success) {
        addToast({ type: 'success', title: 'Audio Playing', message: `Playing at ${frequency.toFixed(1)} Hz`, duration: 2000 });
      }
    }
  };

  const handleDharmaTale = () => {
    setSidebarOpen(true);
    addToast({ type: 'info', title: 'Dharma Tales', message: 'Open Dharma Tales in the Sacred Content section', duration: 3000 });
  };

  const handleConfigure = () => {
    setSidebarOpen(true);
    addToast({ type: 'info', title: 'Configuration', message: 'Use the sidebar controls to configure settings', duration: 3000 });
  };

  return (
    <div className="space-y-8">
      {/* Welcome Hero */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-purple-950/40 to-indigo-950/40 border border-white/10 shadow-2xl">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,theme(colors.purple.900/0.3),transparent_60%),radial-gradient(ellipse_at_bottom_left,theme(colors.indigo.900/0.3),transparent_60%)]" />
        <div className="relative flex flex-col md:flex-row items-center gap-6 p-8">
          <div className="flex-shrink-0 rounded-full ring-1 ring-purple-500/20 ring-offset-4 ring-offset-slate-900">
            <MiniGlobe isActive={runningSessions.length > 0} size="small" />
          </div>
          <div className="flex-1 text-center md:text-left">
            <div className="flex items-center gap-2 justify-center md:justify-start mb-1">
              <span className="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-300 rounded-full border border-purple-500/20 font-mono tracking-wide">v2.0 · STABLE</span>
              {isConnected && <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 font-mono">● CONNECTED</span>}
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight mb-1">
              Vajra<span className="text-purple-400">.</span>Stream
            </h1>
            <p className="text-base text-slate-400 max-w-lg">
              Sacred technology for blessing, healing, and transformation — bridging<br/>
              ancient wisdom with modern radionics.
            </p>
            <div className="flex flex-wrap gap-3 mt-4 text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-900/30 rounded-md border border-purple-500/20 text-purple-300">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                {runningSessions.length > 0 ? `${runningSessions.length} sessions active` : 'Ready to begin'}
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-900/30 rounded-md border border-amber-500/20 text-amber-300">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Golden Blessing Rays
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-rose-900/30 rounded-md border border-rose-500/20 text-rose-300">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                Rainbow Chakra Ring
              </span>
            </div>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <QuickStatCard
          icon={Activity}
          label="Active Sessions"
          value={runningSessions.length}
          trend={runningSessions.length > 0 ? `+${runningSessions.length}` : undefined}
          color="text-purple-400"
        />
        <QuickStatCard
          icon={Heart}
          label="Crystal Grid"
          value={crystalStatus.active ? 'Active' : 'Idle'}
          color={crystalStatus.active ? 'text-emerald-400' : 'text-slate-500'}
        />
        <QuickStatCard
          icon={Zap}
          label="Radionic Rate"
          value={scalarStatus.rate || '—'}
          color="text-cyan-400"
        />
        <QuickStatCard
          icon={Clock}
          label="Session History"
          value={sessionHistory.length || activeSessions.length}
          color="text-amber-400"
        />
        {rngData?.coherence !== undefined && (
          <QuickStatCard
            icon={Activity}
            label="RNG Coherence"
            value={rngData.coherence.toFixed(2)}
            trend={rngData.coherence > 0.7 ? 'High' : rngData.coherence > 0.4 ? 'Mid' : undefined}
            color={rngData.coherence > 0.7 ? 'text-emerald-400' : rngData.coherence > 0.4 ? 'text-amber-400' : 'text-red-400'}
          />
        )}
      </div>

      {/* Cosmic Context Banner */}
      {quickAstro && (
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-900/40 border border-indigo-500/15 p-4">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-2xl" />
          <div className="relative flex items-center gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-900/50 border border-indigo-500/20 flex items-center justify-center">
              <Moon className="w-5 h-5 text-indigo-300" />
            </div>
            <div className="flex-1">
              <h3 className="text-xs font-semibold text-indigo-300 uppercase tracking-widest mb-1">Cosmic Context</h3>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                <span className="text-white font-medium">{quickAstro.moon_phase?.phase_name || '—'}</span>
                <span className="w-1 h-1 rounded-full bg-slate-600 hidden sm:block" />
                <span className="text-purple-300">{quickAstro.planetary_hours?.current_planetary_hour || '—'} hour</span>
                <span className="w-1 h-1 rounded-full bg-slate-600 hidden sm:block" />
                <span className="text-slate-400">{quickAstro.moon_phase?.illumination?.toFixed(0) || '—'}% illuminated</span>
              </div>
            </div>
            <div className="hidden sm:block text-right">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">day ruler</div>
              <div className="text-sm text-amber-300 font-medium">{quickAstro.planetary_hours?.current_planetary_hour || '—'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Saka Dawa Banner */}
      <SakaDawaBanner />

      {/* Bodhicitta Banner — The Awakened Heart */}
      <BodhicittaBanner />

      {/* Ritual Phase Indicator */}
      <RitualPhaseIndicator
        sessions={sessions}
        scalarStatus={scalarStatus}
        frequency={frequency}
      />

      {/* Character Journey */}
      <JourneyCard />

      {/* Autonomous Ritual Engine */}
      <RitualMonitor compact />

      {/* Buddha Contemplation */}
      <BuddhaContemplationWidget />

      {/* Automation Status */}
      {automationStatus && automationStatus.active && (
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-emerald-950/40 to-cyan-950/30 border border-emerald-500/20 p-5">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
          <div className="relative space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  <div className="w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-emerald-300">Blessing Rotation Active</h3>
                  <p className="text-[10px] text-slate-500 mt-0.5">Autonomous blessing cycle in progress</p>
                </div>
              </div>
              <span className="text-sm font-mono text-emerald-400 font-bold">
                {Math.round(automationStatus.progress || 0)}%
              </span>
            </div>
            {automationStatus.current_population && (
              <div className="text-xs text-slate-300 pl-8">
                Now blessing <span className="text-emerald-200 font-semibold">{automationStatus.current_population.name}</span>
                <span className="text-slate-600 mx-1.5">·</span>
                <span className="text-slate-500">{automationStatus.current_population.category}</span>
              </div>
            )}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div className="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-1000 ease-out"
                style={{ width: `${Math.round(automationStatus.progress || 0)}%` }} />
            </div>
            <div className="flex justify-between text-[10px] text-slate-600 font-mono pl-8">
              <span>{automationStatus.session_id?.slice(0, 16)}…</span>
              <span>{automationStatus.populations_in_queue || 0} queued · cycle {automationStatus.cycle_count || 0}</span>
            </div>
          </div>
        </div>
      )}

      {/* Trends Chart */}
      <section>
        <SectionHeading icon={TrendingUp} label="Session Trends" color="text-purple-400" />
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-1">
          <TrendsChart sessionHistory={sessionHistory} />
        </div>
      </section>

      {/* Quick Actions */}
      <section>
        <SectionHeading icon={Sparkles} label="Quick Actions" color="text-amber-400" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <QuickActionButton
            icon={Plus}
            label="New Session"
            onClick={handleNewSession}
            color="purple"
          />
          <QuickActionButton
            icon={Play}
            label={isPlaying ? 'Stop Audio' : 'Start Audio'}
            onClick={handleToggleAudio}
            color="green"
          />
          <QuickActionButton
            icon={BookOpen}
            label="Dharma Tale"
            onClick={handleDharmaTale}
            color="blue"
          />
          <QuickActionButton
            icon={Settings}
            label="Configure"
            onClick={handleConfigure}
            color="gray"
          />
        </div>
      </section>

      {/* Active Sessions */}
      <section>
        <SectionHeading icon={Activity} label="Active Sessions" color="text-purple-400" badge={runningSessions.length} />
        <div className="space-y-3">
          {!isConnected ? (
            <div className="rounded-xl bg-red-950/20 border border-red-500/20 p-5">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <p className="text-red-300 text-sm font-medium">Backend connection lost</p>
              </div>
              <p className="text-red-400/60 text-xs mt-1 ml-5">Session management unavailable — check server status</p>
            </div>
          ) : runningSessions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-10 text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
                <Activity className="w-6 h-6 text-slate-600" />
              </div>
              <p className="text-slate-400 text-sm font-medium mb-1">No active sessions</p>
              <p className="text-slate-600 text-xs">Create a session to begin your blessing practice</p>
            </div>
          ) : (
            runningSessions.slice(0, 3).map((session) => (
              <div
                key={session.id}
                className="group rounded-xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/30 p-5 transition-all duration-300"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white text-sm mb-1 truncate">{session.name}</h3>
                    <p className="text-xs text-slate-400 mb-3 truncate">{session.intention}</p>
                    <div className="flex items-center gap-4 text-[11px]">
                      <span className="inline-flex items-center gap-1.5 text-slate-500">
                        <Zap className="w-3 h-3 text-amber-500/70" />
                        {session.audio_frequency?.toFixed(1)} Hz
                      </span>
                      <span className="inline-flex items-center gap-1.5 text-slate-500">
                        <Clock className="w-3 h-3 text-slate-500/70" />
                        {Math.floor(session.duration / 60)} min
                      </span>
                    </div>
                  </div>
                  <span className="flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[10px] font-medium text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Active
                  </span>
                </div>
              </div>
            ))
          )}
          {runningSessions.length > 3 && (
            <button className="w-full py-2.5 text-xs font-medium text-purple-400 hover:text-purple-300 transition-colors">
              View all {runningSessions.length} active sessions →
            </button>
          )}
        </div>
      </section>

      {/* Session Timeline */}
      <section>
        <SectionHeading icon={Clock} label="Session History" color="text-amber-400" />
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-1">
          <SessionTimeline sessions={sessions} />
        </div>
      </section>

      {/* Frequency Waterfall */}
      <section>
        <SectionHeading icon={Activity} label="Live Frequency Monitor" color="text-cyan-400" />
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <FrequencyWaterfall frequency={frequency} isPlaying={isPlaying} />
        </div>
      </section>

      {/* Generated Content Gallery */}
      <section>
        <SectionHeading icon={Sparkles} label="Generated Blessings" color="text-purple-400" />
        <GeneratedContentGallery compact />
      </section>

      {/* System Status */}
      <section>
        <SectionHeading icon={Settings} label="System Status" color="text-slate-400" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Audio Engine', status: isPlaying ? 'Playing' : 'Idle', detail: `${frequency?.toFixed(1)} Hz`, active: isPlaying, color: 'purple' },
            { label: 'WebSocket', status: isConnected ? 'Connected' : 'Offline', detail: 'v2 stable', active: isConnected, color: 'emerald' },
            { label: 'Crystal Grid', status: crystalStatus.active ? 'Active' : 'Inactive', detail: crystalStatus.intention, active: crystalStatus.active, color: 'cyan' },
            { label: 'Scalar Waves', status: scalarStatus.active ? 'Broadcasting' : 'Idle', detail: scalarStatus.rate ? `Rate ${scalarStatus.rate}` : '', active: scalarStatus.active, color: 'amber' },
          ].map((sys) => (
            <div key={sys.label} className="group rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 p-4 transition-all duration-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">{sys.label}</span>
                <div className={`w-2 h-2 rounded-full ${sys.active ? `bg-${sys.color === 'emerald' ? 'emerald' : sys.color === 'purple' ? 'purple' : sys.color === 'cyan' ? 'cyan' : 'amber'}-400 shadow-[0_0_6px_rgba(168,85,247,0.5)] animate-pulse` : 'bg-slate-700'}`} />
              </div>
              <div className="text-sm font-semibold text-white">{sys.status}</div>
              {sys.detail && <div className="text-[10px] text-slate-500 mt-0.5 truncate">{sys.detail}</div>}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
