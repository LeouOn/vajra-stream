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
  Settings
} from 'lucide-react';
import TrendsChart from './TrendsChart';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';
import { useUIStore } from '../../stores/uiStore';
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

  useEffect(() => {
    fetch('/api/v1/sessions/history')
      .then(r => r.json())
      .then(d => setSessionHistory(d.history || []))
      .catch(() => setSessionHistory([]));
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
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 rounded-lg p-6 border border-purple-700/50">
        <h1 className="text-2xl font-bold text-white mb-2">
          Welcome to Vajra.Stream
        </h1>
        <p className="text-gray-300">
          Your sacred technology platform for blessing, healing, and transformation
        </p>
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
