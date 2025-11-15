import React from 'react';
import { Wifi, WifiOff, Activity, Volume2, Clock } from 'lucide-react';

const StatusIndicator = ({ isConnected, isPlaying, frequency, lastUpdate }) => {
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
      <div className="flex items-center space-x-2">
        {isConnected ? (
          <Wifi className={`w-4 h-4 ${getConnectionColor()}`} />
        ) : (
          <WifiOff className={`w-4 h-4 ${getConnectionColor()}`} />
        )}
        <span className={getConnectionColor()}>
          {getConnectionText()}
        </span>
      </div>

      {/* Play Status */}
      <div className="flex items-center space-x-2">
        <Activity className={`w-4 h-4 ${getPlayStatusColor()}`} />
        <span className={getPlayStatusColor()}>
          {getPlayStatusText()}
        </span>
      </div>

      {/* Frequency Display */}
      {frequency && (
        <div className="flex items-center space-x-2">
          <Volume2 className="w-4 h-4 text-vajra-cyan" />
          <span className="frequency-display">
            {frequency.toFixed(1)} Hz
          </span>
        </div>
      )}

      {/* Last Update */}
      {lastUpdate && (
        <div className="flex items-center space-x-2 text-gray-400">
          <Clock className="w-4 h-4" />
          <span className="text-xs">
            {formatLastUpdate(lastUpdate)}
          </span>
        </div>
      )}

      {/* Status Indicator Light */}
      <div className="flex items-center">
        <div className={`w-2 h-2 rounded-full mr-2 ${
          isConnected 
            ? 'bg-green-500 animate-pulse' 
            : 'bg-red-500'
        }`} />
        <span className="text-xs text-gray-400">
          {isConnected ? 'Live' : 'Offline'}
        </span>
      </div>
    </div>
  );
};

export default StatusIndicator;