import React from 'react';
import { Wifi, WifiOff, Activity, Volume2, Clock, Zap, Gem } from 'lucide-react';

const StatusIndicator = ({ isConnected, isPlaying, frequency, lastUpdate, crystalStatus, scalarStatus }) => {
  const getConnectionColor = () => {
    if (isConnected) return 'text-green-400';
    return 'text-red-400';
  };

  const getConnectionText = () => {
    if (isConnected) return 'Connected';
    return 'Disconnected';
  };

  const getPlayStatusColor = () => {
    if (isPlaying) return 'text-green-400';
    return 'text-gray-400';
  };

  const getPlayStatusText = () => {
    if (isPlaying) return 'Playing';
    return 'Stopped';
  };

  const getCrystalStatusColor = () => {
    if (crystalStatus?.active) return 'text-purple-400';
    return 'text-gray-600';
  };

  const getScalarStatusColor = () => {
    if (scalarStatus?.active) return 'text-blue-400';
    return 'text-gray-600';
  };

  const formatLastUpdate = (date) => {
    if (!date) return 'Never';
    
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  return (
    <div className="flex items-center space-x-6 text-sm">
      {/* Connection Status */}
      <div className={`flex items-center space-x-2 px-3 py-2 rounded-full glassmorphism ${
        isConnected ? 'border-green-500/50' : 'border-red-500/50'
      }`}>
        {isConnected ? (
          <Wifi className={`w-5 h-5 ${getConnectionColor()} ${isConnected ? 'pulse-glow' : ''}`} />
        ) : (
          <WifiOff className={`w-5 h-5 ${getConnectionColor()}`} />
        )}
        <span className={`font-medium ${getConnectionColor()}`}>
          {getConnectionText()}
        </span>
      </div>

      {/* Play Status */}
      <div className={`flex items-center space-x-2 px-3 py-2 rounded-full glassmorphism ${
        isPlaying ? 'border-green-500/50' : 'border-gray-500/50'
      }`}>
        <Activity className={`w-5 h-5 ${getPlayStatusColor()} ${isPlaying ? 'pulse-glow' : ''}`} />
        <span className={`font-medium ${getPlayStatusColor()}`}>
          {getPlayStatusText()}
        </span>
      </div>

      {/* Crystal Status */}
      <div className={`flex items-center space-x-2 px-3 py-2 rounded-full glassmorphism ${
        crystalStatus?.active ? 'border-purple-500/50' : 'border-gray-500/50'
      }`} title={crystalStatus?.intention || 'Crystal Inactive'}>
        <Gem className={`w-5 h-5 ${getCrystalStatusColor()} ${crystalStatus?.active ? 'pulse-glow float-animation' : ''}`} />
        <span className={`text-xs font-medium ${getCrystalStatusColor()}`}>
          {crystalStatus?.active ? 'Crystal Active' : 'Crystal Idle'}
        </span>
      </div>

      {/* Scalar Status */}
      <div className={`flex items-center space-x-2 px-3 py-2 rounded-full glassmorphism ${
        scalarStatus?.active ? 'border-blue-500/50' : 'border-gray-500/50'
      }`} title={`Rate: ${scalarStatus?.rate || 0}`}>
        <Zap className={`w-5 h-5 ${getScalarStatusColor()} ${scalarStatus?.active ? 'pulse-glow rotate-glow' : ''}`} />
        <span className={`text-xs font-medium ${getScalarStatusColor()}`}>
          {scalarStatus?.active ? 'Scalar Active' : 'Scalar Idle'}
        </span>
      </div>

      {/* Frequency Display */}
      {frequency && (
        <div className="flex items-center space-x-2 px-3 py-2 rounded-full glassmorphism border-cyan-500/50">
          <Volume2 className="w-5 h-5 text-vajra-cyan glow-cyan" />
          <span className="frequency-display font-medium">
            {frequency.toFixed(1)} Hz
          </span>
        </div>
      )}

      {/* Last Update */}
      {lastUpdate && (
        <div className="flex items-center space-x-2 px-3 py-2 rounded-full glassmorphism border-gray-500/50">
          <Clock className="w-5 h-5 text-gray-400" />
          <span className="text-xs font-medium text-gray-400">
            {formatLastUpdate(lastUpdate)}
          </span>
        </div>
      )}

      {/* Status Indicator Light */}
      <div className="flex items-center px-3 py-2 rounded-full glassmorphism">
        <div className={`w-3 h-3 rounded-full mr-2 ${
          isConnected
            ? 'bg-green-500 animate-pulse shadow-green-500/50 shadow-lg'
            : 'bg-red-500'
        }`} />
        <span className="text-xs font-medium text-gray-400">
          {isConnected ? 'Live' : 'Offline'}
        </span>
      </div>
    </div>
  );
};

export default StatusIndicator;