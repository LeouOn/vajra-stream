import React from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

const CHAKRAS = [
  { id: 'root', name: 'Root', color: '#ff4444', frequency: 396 },
  { id: 'sacral', name: 'Sacral', color: '#ff8c00', frequency: 417 },
  { id: 'solar', name: 'Solar', color: '#ffdd00', frequency: 528 },
  { id: 'heart', name: 'Heart', color: '#00ff88', frequency: 639 },
  { id: 'throat', name: 'Throat', color: '#00ccff', frequency: 741 },
  { id: 'third_eye', name: 'Third Eye', color: '#9966ff', frequency: 852 },
  { id: 'crown', name: 'Crown', color: '#cc66ff', frequency: 963 },
];

const ChakraAlignmentStrip = () => {
  const { sessions } = useWebSocket();
  const activeSessions = Object.values(sessions).filter(s => s.status === 'running');

  if (activeSessions.length === 0) {
    return (
      <div className="h-12 bg-gray-900/50 border-t border-gray-700 flex items-center justify-center">
        <span className="text-xs text-gray-500">No active session — chakra strip inactive</span>
      </div>
    );
  }

  const activeSession = activeSessions[0];
  const enabledChakras = activeSession.config?.chakras_enabled || CHAKRAS.map(c => c.id);

  return (
    <div className="h-12 bg-gray-900/80 border-t border-gray-700 flex items-center justify-center gap-6 px-4">
      {CHAKRAS.map((chakra) => {
        const isActive = enabledChakras.includes(chakra.id);
        return (
          <div key={chakra.id} className="flex flex-col items-center gap-0.5">
            <div
              className={`w-6 h-6 rounded-full transition-all duration-500 ${
                isActive ? 'animate-pulse-glow' : 'opacity-30'
              }`}
              style={{
                backgroundColor: isActive ? chakra.color : '#333',
                boxShadow: isActive ? `0 0 8px ${chakra.color}` : 'none',
              }}
            />
            <span className="text-[9px] text-gray-400">{chakra.frequency}</span>
          </div>
        );
      })}
    </div>
  );
};

export default ChakraAlignmentStrip;