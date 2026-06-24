/**
 * Dharma Tales — AI-generated Buddhist teaching stories viewer.
 *
 * Displays AI-generated parables, teaching tales, and traditional
 * Buddhist stories. Supports TTS narration, tale saving, theme/
 * tradition selection, and full-screen immersive reading mode.
 *
 * @component
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { BookOpen, Sparkles, RefreshCw, Volume2, VolumeX, Save, ChevronDown, Trash2, Copy, Maximize2, Minimize2 } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { createLogger } from '../../utils/logger';

const TRADITIONS: string[] = ['zen', 'buddhist', 'sufi', 'taoist', 'christian mystical', 'hindu', 'theravada', 'mahayana', 'vajrayana'];
const THEMES: string[] = ['impermanence', 'compassion', 'emptiness', 'interdependence', 'right_action', 'loving_kindness', 'non_self', 'interbeing', 'wisdom', 'equanimity', 'letting_go', 'true_self'];

type TaleLength = 'short' | 'medium' | 'long';

interface SavedTale {
  id: number;
  tale: string;
  theme: string;
  tradition: string;
  length: TaleLength;
  createdAt: string;
}

interface DharmaTalesProps {
  className?: string;
}

const DharmaTales: React.FC<DharmaTalesProps> = ({ className = '' }) => {
  const [tale, setTale] = useState('');
  const [theme, setTheme] = useState('compassion');
  const [tradition, setTradition] = useState('zen');
  const [length, setLength] = useState<TaleLength>('short');
  const [isGenerating, setIsGenerating] = useState(false);
  const [availableThemes, setAvailableThemes] = useState<string[]>([]);
  const [availableTraditions, setAvailableTraditions] = useState<string[]>([]);
  const [savedTales, setSavedTales] = useState<SavedTale[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('dharma-tales') || '[]');
    } catch { return []; }
  });
  const [showSaved, setShowSaved] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [speechRate, setSpeechRate] = useState(1.0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const log = createLogger('DharmaTales');

  const speechRef = useRef<SpeechSynthesisUtterance | null>(null);
  const addToast = useUIStore((s) => s.addToast);
  
  useEffect(() => {
    loadThemes();
    loadTraditions();
  }, []);
  
  const loadThemes = async () => {
    try {
      const response = await fetch(`/api/v1/dharma/tale/themes`);
      if (response.ok) {
        const data = await response.json();
        setAvailableThemes(data.themes || []);
      }
    } catch {
      log.error('Failed to load themes');
    }
  };
  
  const loadTraditions = async () => {
    try {
      const response = await fetch(`/api/v1/dharma/tale/traditions`);
      if (response.ok) {
        const data = await response.json();
        setAvailableTraditions(data.traditions || []);
      }
    } catch {
      log.error('Failed to load traditions');
    }
  };
  
  const generateTale = useCallback(async () => {
    setIsGenerating(true);
    try {
      const response = await fetch(`/api/v1/dharma/tale/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme, tradition, length, use_llm: true })
      });
      if (response.ok) {
        const data = await response.json();
        setTale(data.tale || '');
        addToast({ type: 'success', title: 'Tale Generated', message: `A ${theme} teaching from the ${tradition} tradition`, duration: 3000 });
      }
    } catch (error) {
      addToast({ type: 'error', title: 'Generation Failed', message: 'Could not connect to backend', duration: 4000 });
    }
    setIsGenerating(false);
  }, [theme, tradition, length, addToast]);
  
  const speakTale = useCallback(() => {
    if (!tale) return;
    
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    
    const utterance = new SpeechSynthesisUtterance(tale);
    utterance.rate = speechRate;
    utterance.pitch = 1.0;
    utterance.volume = 0.9;
    
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => 
      v.name.includes('Google') || v.name.includes('Samantha') || v.lang.startsWith('en')
    );
    if (preferredVoice) utterance.voice = preferredVoice;
    
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    speechRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  }, [tale, isSpeaking, speechRate]);

  useEffect(() => {
    if (isSpeaking && speechRef.current) {
      const currentText = speechRef.current.text || tale;
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(currentText);
      utterance.rate = speechRate;
      utterance.pitch = 1.0;
      utterance.volume = 0.9;
      
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => 
        v.name.includes('Google') || v.name.includes('Samantha') || v.lang.startsWith('en')
      );
      if (preferredVoice) utterance.voice = preferredVoice;
      
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      speechRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    }
  }, [speechRate]);
  
  const saveTale = useCallback(() => {
    if (!tale) return;
    const saved: SavedTale[] = [...savedTales, {
      id: Date.now(),
      tale,
      theme,
      tradition,
      length,
      createdAt: new Date().toISOString()
    }];
    setSavedTales(saved);
    localStorage.setItem('dharma-tales', JSON.stringify(saved));
    addToast({ type: 'success', title: 'Tale Saved', message: 'Saved to your collection', duration: 2000 });
  }, [tale, theme, tradition, length, savedTales, addToast]);
  
  const deleteTale = useCallback((id: number) => {
    const saved = savedTales.filter(t => t.id !== id);
    setSavedTales(saved);
    localStorage.setItem('dharma-tales', JSON.stringify(saved));
  }, [savedTales]);
  
  const loadSavedTale = useCallback((savedTale: SavedTale) => {
    setTale(savedTale.tale);
    setTheme(savedTale.theme);
    setTradition(savedTale.tradition);
    setLength(savedTale.length);
    setShowSaved(false);
  }, []);
  
  const copyToClipboard = useCallback(async () => {
    if (!tale) return;
    try {
      await navigator.clipboard.writeText(tale);
      addToast({ type: 'success', title: 'Copied', message: 'Tale copied to clipboard', duration: 2000 });
    } catch {
      addToast({ type: 'error', title: 'Copy Failed', message: 'Could not copy to clipboard', duration: 3000 });
    }
  }, [tale, addToast]);
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-vajra-purple flex items-center gap-2">
          <BookOpen className="w-5 h-5" />
          Dharma Tales
        </h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 rounded-lg hover:bg-purple-900/20 text-purple-300/60 hover:text-white transition-colors"
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
      </div>
      
      {/* Theme Selection */}
      <div>
        <label className="block text-xs text-purple-300/80 mb-1 font-medium">Theme</label>
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          className="w-full bg-black/45 text-white rounded-lg px-3 py-2 text-sm border border-purple-500/20 focus:border-purple-500/60 focus:outline-none transition-all duration-300"
        >
          {(availableThemes.length > 0 ? availableThemes : THEMES).map(t => (
            <option key={t} value={t} className="bg-gray-950">{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>
      
      {/* Tradition Selection */}
      <div>
        <label className="block text-xs text-purple-300/80 mb-1 font-medium">Tradition</label>
        <select
          value={tradition}
          onChange={(e) => setTradition(e.target.value)}
          className="w-full bg-black/45 text-white rounded-lg px-3 py-2 text-sm border border-purple-500/20 focus:border-purple-500/60 focus:outline-none transition-all duration-300"
        >
          {(availableTraditions.length > 0 ? availableTraditions : TRADITIONS).map(t => (
            <option key={t} value={t} className="bg-gray-950">{t}</option>
          ))}
        </select>
      </div>
      
      {/* Length Selection */}
      <div>
        <label className="block text-xs text-purple-300/80 mb-1 font-medium">Length</label>
        <div className="grid grid-cols-3 gap-2">
          {(['short', 'medium', 'long'] as TaleLength[]).map(l => (
            <button
              key={l}
              onClick={() => setLength(l)}
              className={`px-3 py-2 rounded-lg text-sm capitalize transition-all duration-300 border ${
                length === l
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white border-purple-400/20 shadow-md'
                  : 'bg-purple-950/10 text-purple-300/70 border-purple-500/10 hover:text-white hover:bg-purple-900/20'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>
      
      {/* Generate Button */}
      <button
        onClick={generateTale}
        disabled={isGenerating}
        className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg px-4 py-3 text-sm flex items-center justify-center gap-2 font-semibold transition-all duration-300 shadow-lg hover:shadow-purple-500/20"
      >
        {isGenerating ? (
          <RefreshCw className="w-4 h-4 animate-spin" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
        {isGenerating ? 'Generating...' : 'Generate Teaching Tale'}
      </button>
      
      {/* Tale Display */}
      {tale && (
        <div className="bg-black/20 rounded-lg border border-purple-500/15 overflow-hidden shadow-inner">
          {/* Tale content */}
          <div className={`p-4 ${isExpanded ? '' : 'max-h-60'} overflow-y-auto`}>
            <p className="text-sm text-purple-100/90 whitespace-pre-wrap leading-relaxed">{tale}</p>
          </div>
          
          {/* Tale actions */}
          <div className="flex items-center gap-1 px-3 py-2 border-t border-purple-500/15 bg-black/30">
            <button
              onClick={speakTale}
              className={`p-2 rounded-lg hover:bg-purple-900/20 transition-colors ${isSpeaking ? 'text-purple-400' : 'text-purple-300/60 hover:text-white'}`}
              title={isSpeaking ? 'Stop speaking' : 'Read aloud'}
            >
              {isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            <button
              onClick={saveTale}
              className="p-2 rounded-lg hover:bg-purple-900/20 text-purple-300/60 hover:text-yellow-400 transition-colors"
              title="Save tale"
            >
              <Save className="w-4 h-4" />
            </button>
            <button
              onClick={copyToClipboard}
              className="p-2 rounded-lg hover:bg-purple-900/20 text-purple-300/60 hover:text-white transition-colors"
              title="Copy to clipboard"
            >
              <Copy className="w-4 h-4" />
            </button>
            <div className="flex-1" />
            {isSpeaking && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-purple-300/60">Speed:</span>
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={speechRate}
                  onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                  className="w-16 h-1 accent-purple-500"
                />
                <span className="text-xs text-purple-300/80 w-6 font-mono">{speechRate}x</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Saved Tales */}
      <div>
        <button
          onClick={() => setShowSaved(!showSaved)}
          className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <span className="flex items-center gap-2">
            <Save className="w-4 h-4" />
            Saved Tales ({savedTales.length})
          </span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showSaved ? 'rotate-180' : ''}`} />
        </button>
        {showSaved && (
          <div className="space-y-2 mt-2 max-h-48 overflow-y-auto">
            {savedTales.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-4">No saved tales yet</p>
            ) : (
              savedTales.map((savedTale) => (
                <div
                  key={savedTale.id}
                  className="flex items-start gap-2 p-2 bg-gray-700/20 rounded-lg group"
                >
                  <button
                    onClick={() => loadSavedTale(savedTale)}
                    className="flex-1 text-left"
                  >
                    <div className="text-xs font-medium text-gray-300 truncate">
                      {savedTale.tale.slice(0, 60)}...
                    </div>
                    <div className="flex gap-2 mt-1">
                      <span className="text-xs text-gray-500">{savedTale.theme}</span>
                      <span className="text-xs text-gray-600">•</span>
                      <span className="text-xs text-gray-500">{savedTale.tradition}</span>
                    </div>
                  </button>
                  <button
                    onClick={() => deleteTale(savedTale.id)}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-600 text-gray-500 hover:text-red-400 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DharmaTales;
