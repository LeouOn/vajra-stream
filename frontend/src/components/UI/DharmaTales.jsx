/**
 * Dharma Tales Component
 *
 * Interface for generating teaching stories and parables
 * using LLM integration.
 */

import React, { useState, useEffect } from 'react';
import { BookOpen, Sparkles, RefreshCw, ChevronDown } from 'lucide-react';

const API_BASE = 'http://localhost:8008/api/v1';

const TRADITIONS = ['zen', 'buddhist', 'sufi', 'taoist', 'christian mystical'];
const THEMES = ['impermanence', 'compassion', 'emptiness', 'interdependence', 'right_action', 'loving_kindness', 'impermanence', 'non_self', 'interbeing'];

const DharmaTales = ({ className = '' }) => {
  const [tale, setTale] = useState('');
  const [theme, setTheme] = useState('compassion');
  const [tradition, setTradition] = useState('zen');
  const [length, setLength] = useState('short');
  const [isGenerating, setIsGenerating] = useState(false);
  const [availableThemes, setAvailableThemes] = useState([]);
  const [showDropdown, setShowDropdown] = useState({ theme: false, tradition: false });

  useEffect(() => {
    loadThemes();
  }, []);

  const loadThemes = async () => {
    try {
      const response = await fetch(`${API_BASE}/dharma/tale/themes`);
      if (response.ok) {
        const data = await response.json();
        setAvailableThemes(data.themes || []);
      }
    } catch (error) {
      console.error('Failed to load themes:', error);
    }
  };

  const generateTale = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch(`${API_BASE}/dharma/tale/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme, tradition, length })
      });
      if (response.ok) {
        const data = await response.json();
        setTale(data.tale || '');
      }
    } catch (error) {
      console.error('Failed to generate tale:', error);
    }
    setIsGenerating(false);
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <h3 className="text-lg font-semibold text-vajra-purple flex items-center mb-4">
        <BookOpen className="w-5 h-5 mr-2" />
        Dharma Tales
      </h3>

      {/* Theme Selection */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Theme</label>
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm"
        >
          {availableThemes.length > 0 ? (
            availableThemes.map(t => (
              <option key={t} value={t}>{t.replace('_', ' ')}</option>
            ))
          ) : (
            TRADITIONS.map(t => (
              <option key={t} value={t}>{t}</option>
            ))
          )}
        </select>
      </div>

      {/* Tradition Selection */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Tradition</label>
        <select
          value={tradition}
          onChange={(e) => setTradition(e.target.value)}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm"
        >
          {TRADITIONS.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Length Selection */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Length</label>
        <select
          value={length}
          onChange={(e) => setLength(e.target.value)}
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm"
        >
          <option value="short">Short</option>
          <option value="medium">Medium</option>
          <option value="long">Long</option>
        </select>
      </div>

      {/* Generate Button */}
      <button
        onClick={generateTale}
        disabled={isGenerating}
        className="w-full bg-vajra-purple hover:bg-purple-700 disabled:bg-gray-600 text-white rounded px-4 py-2 text-sm flex items-center justify-center mb-4"
      >
        {isGenerating ? (
          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          <Sparkles className="w-4 h-4 mr-2" />
        )}
        {isGenerating ? 'Generating...' : 'Generate Teaching Tale'}
      </button>

      {/* Tale Display */}
      {tale && (
        <div className="bg-gray-900 rounded p-3 max-h-60 overflow-y-auto">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{tale}</p>
        </div>
      )}
    </div>
  );
};

export default DharmaTales;