/**
 * Chakra Healing — targeted chakra healing session UI.
 * Select a chakra, set intention, configure frequencies/duration,
 * and start a prayer-bowl healing broadcast.
 * @component
 */
import React, { useState, useEffect } from 'react';
import { message } from 'antd';
import { Heart, Zap, RefreshCw, ChevronRight, Play, Square } from 'lucide-react';
import { createLogger } from '../../utils/logger';

const log = createLogger('ChakraHealing');

interface ChakraFrequencies {
  root?: number;
  [key: string]: number | undefined;
}

interface ChakraInfo {
  name?: string;
  sanskrit?: string;
  element?: string;
  color?: string;
  frequencies?: ChakraFrequencies;
  [key: string]: unknown;
}

interface ChakraMap {
  [chakraName: string]: ChakraInfo;
}

interface SequenceChakra {
  name?: string;
  frequencies?: ChakraFrequencies;
  [key: string]: unknown;
}

interface HealingSequence {
  total_duration?: number;
  chakras: SequenceChakra[];
  [key: string]: unknown;
}

interface IntentionOption {
  id: string;
  name: string;
  desc: string;
}

interface Props {
  className?: string;
}

const CHAKRA_LIST: string[] = [
  'root', 'sacral', 'solar_plexus', 'heart', 'throat', 'third_eye', 'crown'
];

const INTENTION_OPTIONS: IntentionOption[] = [
  { id: 'balance', name: 'Balance', desc: 'General chakra balance' },
  { id: 'healing', name: 'Healing', desc: 'Healing and restoration' },
  { id: 'activation', name: 'Activate', desc: 'Activate chakra energy' },
  { id: 'ground', name: 'Ground', desc: 'Grounding and stability' },
  { id: 'expand', name: 'Expand', desc: 'Expansion and enlightenment' },
];

const ChakraHealing: React.FC<Props> = ({ className = '' }) => {
  const [chakras, setChakras] = useState<ChakraMap>({});
  const [selectedChakra, setSelectedChakra] = useState<string | null>(null);
  const [intention, setIntention] = useState<string>('balance');
  const [sequence, setSequence] = useState<HealingSequence | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [chakraInfo, setChakraInfo] = useState<ChakraInfo | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playingChakra, setPlayingChakra] = useState<string | null>(null);

  useEffect(() => {
    loadChakras();
  }, []);

  const loadChakras = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/healing/chakra/all`);
      if (response.ok) {
        const data = await response.json();
        setChakras(data.chakras || {});
      }
    } catch (error) {
      log.error('Failed to load chakras:', error);
      message.error('Could not load chakras: ' + (error instanceof Error ? error.message : String(error)));
    }
    setIsLoading(false);
  };

  const getChakraInfo = async (chakraName: string) => {
    try {
      const response = await fetch(`/api/v1/healing/chakra/info/${chakraName}`);
      if (response.ok) {
        const data = await response.json();
        setChakraInfo(data.chakra);
        setSelectedChakra(chakraName);
      }
    } catch (error) {
      log.error('Failed to get chakra info:', error);
      message.error('Could not load chakra info: ' + (error instanceof Error ? error.message : String(error)));
    }
  };

  const createSequence = async (type: string = 'full') => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/healing/chakra/balance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention, sequence_type: type })
      });
      if (response.ok) {
        const data = await response.json();
        setSequence(data.sequence);
      }
    } catch (error) {
      log.error('Failed to create sequence:', error);
      message.error('Could not create healing sequence: ' + (error instanceof Error ? error.message : String(error)));
    }
    setIsLoading(false);
  };

  const playChakraAudio = async (chakraName: string | null) => {
    if (!chakraName) return;
    setIsPlaying(true);
    setPlayingChakra(chakraName);
    try {
      // 1. Generate the tone in the backend
      const genResponse = await fetch(`/api/v1/audio/generate_chakra`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chakra_name: chakraName, duration: 30.0 })
      });
      if (genResponse.ok) {
        // 2. Play it on the hardware
        await fetch(`/api/v1/audio/play`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hardware_level: 2 })
        });
      }
    } catch (error) {
      log.error('Failed to play chakra audio:', error);
      message.error('Could not play chakra audio: ' + (error instanceof Error ? error.message : String(error)));
      setIsPlaying(false);
      setPlayingChakra(null);
    }
  };

  const stopAudio = async () => {
    try {
      await fetch(`/api/v1/audio/stop`, { method: 'POST' });
    } catch (e) {
      log.error('Failed to stop audio', e);
      message.error('Could not stop audio: ' + (e instanceof Error ? e.message : String(e)));
    }
    setIsPlaying(false);
    setPlayingChakra(null);
  };

  const getChakraColor = (chakraName: string | null | undefined): string => {
    if (!chakraName) return 'bg-gray-600';
    const colors: Record<string, string> = {
      root: 'bg-red-600',
      sacral: 'bg-orange-600',
      solar_plexus: 'bg-yellow-600',
      heart: 'bg-green-600',
      throat: 'bg-blue-600',
      third_eye: 'bg-indigo-600',
      crown: 'bg-violet-600'
    };
    return colors[chakraName] || 'bg-gray-600';
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <h3 className="text-lg font-semibold text-vajra-cyan flex items-center mb-4">
        <Heart className="w-5 h-5 mr-2" />
        Chakra Healing
      </h3>

      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Intention</label>
        <select
          value={intention}
          onChange={(e) => setIntention(e.target.value)}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm"
        >
          {INTENTION_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.name} - {opt.desc}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Chakras</label>
        <div className="grid grid-cols-1 gap-2">
          {CHAKRA_LIST.map((name) => (
            <button
              key={name}
              onClick={() => getChakraInfo(name)}
              className={`flex items-center justify-between p-2 rounded transition-colors ${
                selectedChakra === name ? 'bg-vajra-cyan text-white' : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
            >
              <span className="flex items-center">
                <span className={`w-3 h-3 rounded-full ${getChakraColor(name)} mr-2`}></span>
                <span className="text-sm capitalize">{name.replace('_', ' ')}</span>
              </span>
              <ChevronRight className="w-4 h-4" />
            </button>
          ))}
        </div>
      </div>

      {chakraInfo && (
        <div className="mb-4 bg-gray-900 rounded p-3">
          <h4 className="font-semibold text-vajra-cyan mb-2">{chakraInfo.name}</h4>
          <p className="text-xs text-gray-400 mb-2">{chakraInfo.sanskrit}</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-500">Element:</span>
              <span className="ml-1 text-white">{chakraInfo.element}</span>
            </div>
            <div>
              <span className="text-gray-500">Color:</span>
              <span className="ml-1 text-white">{chakraInfo.color}</span>
            </div>
            <div>
              <span className="text-gray-500">Frequency:</span>
              <span className="ml-1 text-white">{chakraInfo.frequencies?.root} Hz</span>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            {!isPlaying ? (
              <button 
                onClick={() => playChakraAudio(selectedChakra)}
                className="flex items-center gap-1 bg-green-600/30 hover:bg-green-600/50 text-green-400 px-3 py-1.5 rounded text-xs transition-colors"
              >
                <Play className="w-3 h-3" /> Play Tone
              </button>
            ) : (
              <button 
                onClick={stopAudio}
                className="flex items-center gap-1 bg-red-600/30 hover:bg-red-600/50 text-red-400 px-3 py-1.5 rounded text-xs transition-colors"
              >
                <Square className="w-3 h-3" /> Stop
              </button>
            )}
          </div>
        </div>
      )}

      <button
        onClick={() => createSequence('full')}
        disabled={isLoading}
        className="w-full bg-vajra-cyan hover:bg-cyan-700 disabled:bg-gray-600 text-white rounded px-4 py-2 text-sm flex items-center justify-center mb-4"
      >
        {isLoading ? (
          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          <Zap className="w-4 h-4 mr-2" />
        )}
        {isLoading ? 'Creating...' : 'Create Full Healing Sequence'}
      </button>

      {sequence && (
        <div className="bg-gray-900 rounded p-3 max-h-60 overflow-y-auto">
          <h4 className="text-sm font-semibold text-vajra-purple mb-2">
            Healing Sequence ({sequence.total_duration}s)
          </h4>
          <div className="space-y-2">
            {sequence.chakras.map((c, i) => (
              <div key={i} className="flex items-center text-xs">
                <span className={`w-2 h-2 rounded-full ${getChakraColor(c.name?.toLowerCase().split(' ')[0])} mr-2`}></span>
                <span className="text-gray-300">{c.name}</span>
                <span className="ml-auto text-gray-500">{c.frequencies?.root} Hz</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChakraHealing;