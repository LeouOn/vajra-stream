/**
 * Dashboard — system overview and real-time metrics display.
 *
 * Shows high-level Vajra.Stream status: active sessions, MOPS throughput,
 * WebSocket connection state, RNG coherence, current astrological
 * conditions, and recent blessing activity. Serves as the landing page.
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
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
import { useAudioStore } from '../../stores/audioStore';
import { useUIStore } from '../../stores/uiStore';
import { useCrystalStore } from '../../stores/crystalStore';
import { useRateStore } from '../../stores/rateStore';
import SessionTimeline from './SessionTimeline';
import FrequencyWaterfall from '../2D/FrequencyWaterfall';
import { MiniGlobe } from '../3D/RadionicsGlobe';
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
  const { sessions, isConnected, crystalStatus, scalarStatus } = useWebSocket();
  const { isPlaying, frequency, playAudio, stopAudio, generateAudio } = useAudioStore();
  const { addToast, setSidebarOpen, setSearchOpen } = useUIStore();
  const [sessionHistory, setSessionHistory] = useState([]);
  const [quickAstro, setQuickAstro] = useState(null);
  const [automationStatus, setAutomationStatus] = useState(null);

  const fetchCrystalGrid = useCrystalStore(s => s.fetchCrystalGrid);
  const getRateCategories = useRateStore(s => s.getRateCategories);

  useEffect(() => {
    fetch('/api/v1/sessions/history')
      .then(r => r.json())
      .then(d => setSessionHistory(d.history || []))
      .catch(() => setSessionHistory([]));
    fetchCrystalGrid();
    getRateCategories();
    fetch('/api/v1/astrology/current?latitude=37.7749&longitude=-122.4194')
      .then(r => r.json())
      .then(d => setQuickAstro(d.astrology || null))
      .catch(() => {});

    // Poll automation status
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
  }, []);
  
  const activeSessions = Object.values(sessions);
  const runningSessions = activeSessions.filter(s => s.status === 'running');
  
  const QuickStatCard = ({ icon: Icon, label, value, trend, color }) => (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-purple-500/50 transition-all duration-300">
      <div className="flex items-center justify-between mb-2">
        <Icon className={`w-5 h-5 ${color}`} />
        {trend && (
          <div className="flex items-center gap-1 text-xs text-green-400">
            <TrendingUp className="w-3 h-3" />
            <span>{trend}</span>
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-gray-400 mt-1">{label}</div>
    </div>
  );

  const QuickActionButton = ({ icon: Icon, label, onClick, color = 'purple' }) => {
    const colors = colorMap[color] || colorMap.purple;
    return (
      <button
        onClick={onClick}
        className={`flex flex-col items-center gap-2 p-4 bg-gray-800 rounded-lg border border-gray-700 ${colors.container} hover:bg-gray-700 transition-all duration-300 group`}
      >
        <div className={`p-3 rounded-full ${colors.iconBg} transition-colors`}>
          <Icon className={`w-5 h-5 ${colors.icon}`} />
        </div>
        <span className="text-sm text-gray-300">{label}</span>
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
    <div className="space-y-6">
      {/* Welcome Section with Mini Globe */}
      <div className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 rounded-lg border border-purple-700/50 overflow-hidden">
        <div className="flex flex-col md:flex-row items-center gap-4 p-6">
          <div className="flex-shrink-0">
            <MiniGlobe isActive={runningSessions.length > 0} size="small" />
          </div>
          <div className="flex-1 text-center md:text-left">
            <h1 className="text-2xl font-bold text-white mb-2">
              Welcome to Vajra.Stream
            </h1>
            <p className="text-gray-300">
              Your sacred technology platform for blessing, healing, and transformation
            </p>
            <div className="flex gap-3 mt-3 text-xs">
              <span className="text-purple-300">🌍 {runningSessions.length > 0 ? 'Blessings Active' : 'Ready'}</span>
              <span className="text-cyan-300">✨ Golden Light</span>
              <span className="text-amber-300">🌈 Rainbow Ring</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <QuickStatCard
          icon={Activity}
          label="Active Sessions"
          value={runningSessions.length}
          trend={runningSessions.length > 0 ? '+1' : undefined}
          color="text-purple-400"
        />
        <QuickStatCard
          icon={Heart}
          label="Crystal Status"
          value={crystalStatus.active ? 'Active' : 'Idle'}
          color={crystalStatus.active ? 'text-green-400' : 'text-gray-400'}
        />
        <QuickStatCard
          icon={Zap}
          label="Current Rate"
          value={scalarStatus.rate || 'N/A'}
          color="text-cyan-400"
        />
        <QuickStatCard
          icon={Clock}
          label="Total Sessions"
          value={activeSessions.length}
          color="text-amber-400"
        />
      </div>

      <div className="mt-6">
        <h2 className="text-lg font-semibold text-gray-200 mb-4">Trends</h2>
        <TrendsChart sessionHistory={sessionHistory} />
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          Quick Actions
        </h2>
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
      </div>

      {/* Active Sessions */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-purple-400" />
          Active Sessions
        </h2>
        <div className="space-y-3">
          {!isConnected ? (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
              <p className="text-red-300 text-sm">
                ⚠️ Disconnected from backend. Session management unavailable.
              </p>
            </div>
          ) : runningSessions.length === 0 ? (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 text-center">
              <Activity className="w-12 h-12 mx-auto mb-3 text-gray-600" />
              <p className="text-gray-400 mb-2">No active sessions</p>
              <p className="text-sm text-gray-500">Create a session to begin your blessing practice</p>
            </div>
          ) : (
            runningSessions.slice(0, 3).map((session) => (
              <div
                key={session.id}
                className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-purple-500/50 transition-all duration-300"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-white mb-1">{session.name}</h3>
                    <p className="text-sm text-gray-400 mb-2">{session.intention}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {session.audio_frequency?.toFixed(1)} Hz
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {Math.floor(session.duration / 60)} min
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="px-3 py-1 bg-green-600 text-white text-xs rounded-full font-medium">
                      Active
                    </div>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  </div>
                </div>
              </div>
            ))
          )}
          {runningSessions.length > 3 && (
            <button className="w-full py-2 text-sm text-purple-400 hover:text-purple-300 transition-colors">
              View all {runningSessions.length} active sessions →
            </button>
          )}
        </div>
      </div>

      {/* Automation Status */}
      {automationStatus && automationStatus.active && (
        <div className="bg-gradient-to-r from-emerald-900/20 to-cyan-900/20 rounded-lg p-4 border border-emerald-500/20 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-bold text-emerald-300">Blessing Rotation Active</span>
            </div>
            <span className="text-xs text-emerald-400 font-mono">
              {Math.round(automationStatus.progress || 0)}%
            </span>
          </div>
          {automationStatus.current_population && (
            <div className="text-xs text-gray-300">
              Now blessing: <span className="text-emerald-200 font-semibold">{automationStatus.current_population.name}</span>
              <span className="text-gray-500 mx-1">·</span>
              <span className="text-gray-500">{automationStatus.current_population.category}</span>
            </div>
          )}
          <div className="w-full bg-gray-700 rounded-full h-1.5">
            <div className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-1.5 rounded-full transition-all duration-1000"
              style={{ width: `${Math.round(automationStatus.progress || 0)}%` }} />
          </div>
          <div className="flex justify-between text-[10px] text-gray-500">
            <span>Session: {automationStatus.session_id?.slice(0, 20)}…</span>
            <span>{automationStatus.populations_in_queue || 0} in queue · Cycle {automationStatus.cycle_count || 0}</span>
          </div>
        </div>
      )}

      {/* Quick Astrology */}
      {quickAstro && (
        <div className="bg-gradient-to-r from-indigo-900/20 to-purple-900/20 rounded-lg p-4 border border-indigo-500/20">
          <div className="flex items-center gap-3 text-xs">
            <Moon className="w-5 h-5 text-cyan-400" />
            <div>
              <span className="text-gray-400">Cosmic Context · </span>
              <span className="text-indigo-300 font-semibold">{quickAstro.moon_phase?.phase_name || '—'}</span>
              <span className="text-gray-500 mx-1">·</span>
              <span className="text-purple-300">{quickAstro.planetary_hour || '—'} hour</span>
              <span className="text-gray-500 mx-1">·</span>
              <span className="text-gray-400">{quickAstro.day_ruler || '—'} day</span>
            </div>
          </div>
        </div>
      )}

      {/* Session Timeline */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-amber-400" />
          Session History
        </h2>
        <SessionTimeline sessions={sessions} />
      </div>

      {/* Frequency Waterfall */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          Live Frequency Monitor
        </h2>
        <FrequencyWaterfall frequency={frequency} isPlaying={isPlaying} />
      </div>

      {/* System Status */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5 text-purple-400" />
          System Status
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-400">Audio System</span>
              <div className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
            </div>
            <div className="text-white font-medium">
              {isPlaying ? 'Playing' : 'Idle'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {frequency?.toFixed(1)} Hz
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-400">Connection</span>
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            </div>
            <div className="text-white font-medium">
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              WebSocket
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-400">Crystal Grid</span>
              <div className={`w-2 h-2 rounded-full ${crystalStatus.active ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
            </div>
            <div className="text-white font-medium">
              {crystalStatus.active ? 'Active' : 'Inactive'}
            </div>
            {crystalStatus.intention && (
              <div className="text-xs text-gray-500 mt-1 truncate">
                {crystalStatus.intention}
              </div>
            )}
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-400">Radionics</span>
              <div className={`w-2 h-2 rounded-full ${scalarStatus.active ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
            </div>
            <div className="text-white font-medium">
              {scalarStatus.active ? 'Broadcasting' : 'Idle'}
            </div>
            {scalarStatus.rate && (
              <div className="text-xs text-gray-500 mt-1">
                Rate: {scalarStatus.rate}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
