import React, { useState, useEffect } from 'react';
import { Sparkles, BookOpen, Heart, RefreshCw, Copy, CheckCircle, Lightbulb, Globe, Orbit } from 'lucide-react';

const API_BASE = 'http://localhost:8008/api/v1';

const THEME_OPTIONS = [
  { id: 'overcoming', name: 'Overcoming', desc: 'Stories of triumph over difficulties', icon: '🏔️' },
  { id: 'transformation', name: 'Transformation', desc: 'Journeys of profound change', icon: '🦋' },
  { id: 'healing', name: 'Healing', desc: 'Gentle recovery and restoration', icon: '🌿' },
  { id: 'liberation', name: 'Liberation', desc: 'Freedom from what binds us', icon: '🔓' },
  { id: 'manifestation', name: 'Manifestation', desc: 'Bringing intentions to life', icon: '✨' },
];

const GLOBAL_INTENTION_PRESETS = [
  { id: 'world peace', label: 'World Peace', planet: 'Jupiter', freq: '852Hz', icon: '🕊️' },
  { id: 'world prosperity', label: 'World Prosperity', planet: 'Venus', freq: '528Hz', icon: '💎' },
  { id: 'end to disease and cancer', label: 'End Disease & Cancer', planet: 'Sun', freq: '528Hz', icon: '☀️' },
  { id: 'happiness', label: 'Happiness', planet: 'Jupiter', freq: '528Hz', icon: '🌟' },
  { id: 'reforestation the world', label: 'Reforestation', planet: 'Earth', freq: '528Hz', icon: '🌲' },
  { id: 'cleaning up pollution', label: 'Clean Pollution', planet: 'Saturn', freq: '396Hz', icon: '🌊' },
];

const DIFFICULTY_OPTIONS = [
  { id: 'mild', name: 'Mild', desc: 'Minor obstacles and everyday challenges' },
  { id: 'moderate', name: 'Moderate', desc: 'Persistent patterns and recurring issues' },
  { id: 'deep', name: 'Deep', desc: 'Profound wounds and life-changing difficulties' },
];

const RadionicsNarrative = ({ className = '' }) => {
  const [intention, setIntention] = useState('');
  const [difficulty, setDifficulty] = useState('moderate');
  const [theme, setTheme] = useState('manifestation');
  const [narrative, setNarrative] = useState(null);
  const [affirmation, setAffirmation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('narrative');
  const [copied, setCopied] = useState(false);
  const [radionicsData, setRadionicsData] = useState(null);
  const [globalIntentions, setGlobalIntentions] = useState([]);

  useEffect(() => {
    loadGlobalIntentions();
  }, []);

  const loadGlobalIntentions = async () => {
    try {
      const resp = await fetch(`${API_BASE}/radionics/radionics/global-intentions`);
      if (resp.ok) {
        const data = await resp.json();
        setGlobalIntentions(data.intentions || []);
      }
    } catch (error) {
      console.error('Failed to load global intentions:', error);
      setGlobalIntentions(GLOBAL_INTENTION_PRESETS);
    }
  };

  const isGlobalIntention = (text) => {
    const lower = text.toLowerCase();
    return GLOBAL_INTENTION_PRESETS.some(gi => lower.includes(gi.id));
  };

  const generateNarrative = async () => {
    if (!intention.trim()) return;

    setIsLoading(true);
    setNarrative(null);
    setAffirmation(null);
    setRadionicsData(null);

    try {
      let response;
      let data;

      if (isGlobalIntention(intention)) {
        response = await fetch(`${API_BASE}/radionics/narrative/global-intention`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            intention,
            theme
          })
        });

        if (response.ok) {
          data = await response.json();
          setRadionicsData(data.radionics_data || {});
          setNarrative(data.narrative);
          if (data.affirmation) setAffirmation(data.affirmation);
        }
      } else {
        response = await fetch(`${API_BASE}/radionics/narrative/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            intention,
            difficulty,
            theme,
            include_affirmation: true
          })
        });

        if (response.ok) {
          data = await response.json();
          setNarrative(data.narrative);
          if (data.affirmation) setAffirmation(data.affirmation);
          if (data.radionics) setRadionicsData(data.radionics);
        }
      }

      if (!response.ok) {
        console.error('Failed to generate narrative:', response.status);
      }
    } catch (error) {
      console.error('Error generating narrative:', error);
    }

    setIsLoading(false);
  };

  const generateAffirmationOnly = async () => {
    if (!intention.trim()) return;
    
    setIsLoading(true);
    setAffirmation(null);
    
    try {
      const response = await fetch(`${API_BASE}/radionics/affirmation/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intention,
          style: 'empowering'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setAffirmation(data.affirmation);
      }
    } catch (error) {
      console.error('Error generating affirmation:', error);
    }
    
    setIsLoading(false);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <h3 className="text-lg font-semibold text-vajra-cyan flex items-center mb-4">
        <Sparkles className="w-5 h-5 mr-2" />
        Radionics Narratives
      </h3>

      {/* Global Intentions Section */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1 flex items-center">
          <Globe className="w-4 h-4 mr-1" />
          Global Healing Intentions
        </label>
        <div className="grid grid-cols-2 gap-2">
          {GLOBAL_INTENTION_PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => {
                setIntention(preset.id);
                setTheme('manifestation');
              }}
              className={`p-2 rounded text-left transition-colors ${
                intention.toLowerCase().includes(preset.id.toLowerCase())
                  ? 'bg-vajra-cyan text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
            >
              <div className="flex items-center">
                <span className="mr-2 text-lg">{preset.icon}</span>
                <span className="text-xs font-medium">{preset.label}</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {preset.planet} | {preset.freq}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Intention Input */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Or Enter Custom Intention</label>
        <input
          type="text"
          value={intention}
          onChange={(e) => setIntention(e.target.value)}
          placeholder="e.g., healing from grief, finding courage..."
          className="w-full bg-gray-700 text-white rounded px-3 py-2 text-sm"
        />
      </div>

      {/* Difficulty Selection */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Difficulty Level</label>
        <div className="grid grid-cols-3 gap-2">
          {DIFFICULTY_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setDifficulty(opt.id)}
              className={`p-2 rounded text-xs transition-colors ${
                difficulty === opt.id
                  ? 'bg-vajra-purple text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
            >
              {opt.name}
            </button>
          ))}
        </div>
      </div>

      {/* Theme Selection */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">Narrative Theme</label>
        <div className="grid grid-cols-1 gap-2">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setTheme(opt.id)}
              className={`flex items-center p-2 rounded text-left transition-colors ${
                theme === opt.id
                  ? 'bg-vajra-cyan text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
            >
              <span className="mr-2 text-lg">{opt.icon}</span>
              <div>
                <div className="text-sm font-medium">{opt.name}</div>
                <div className={`text-xs ${theme === opt.id ? 'text-cyan-100' : 'text-gray-500'}`}>
                  {opt.desc}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={generateNarrative}
          disabled={isLoading || !intention.trim()}
          className="flex-1 bg-vajra-cyan hover:bg-cyan-700 disabled:bg-gray-600 text-white rounded px-4 py-2 text-sm flex items-center justify-center"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 mr-2" />
          )}
          Generate Narrative
        </button>
        <button
          onClick={generateAffirmationOnly}
          disabled={isLoading || !intention.trim()}
          className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 text-white rounded px-4 py-2 text-sm flex items-center justify-center"
          title="Generate just an affirmation"
        >
          <Lightbulb className="w-4 h-4" />
        </button>
      </div>

      {/* Radionics Data Display */}
      {radionicsData && (
        <div className="mb-4 p-3 bg-gray-900 rounded-lg border border-vajra-purple/30">
          <div className="text-xs text-vajra-purple mb-2 flex items-center">
            <Orbit className="w-4 h-4 mr-1" />
            Radionics Configuration
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {radionicsData.solfeggio_frequency && (
              <div className="bg-gray-800 p-2 rounded">
                <span className="text-gray-500">Solfeggio:</span>
                <span className="ml-1 text-vajra-cyan">{radionicsData.solfeggio_frequency}Hz</span>
              </div>
            )}
            {radionicsData.planetary_planets && (
              <div className="bg-gray-800 p-2 rounded">
                <span className="text-gray-500">Planet:</span>
                <span className="ml-1 text-vajra-purple">{radionicsData.planetary_planets}</span>
                {radionicsData.planetary_frequency && (
                  <span className="text-gray-400 ml-1">({radionicsData.planetary_frequency}Hz)</span>
                )}
              </div>
            )}
            {radionicsData.location && (
              <div className="bg-gray-800 p-2 rounded col-span-2">
                <span className="text-gray-500">Sacred Location:</span>
                <span className="ml-1 text-white">{radionicsData.location}</span>
              </div>
            )}
            {radionicsData.chakra && (
              <div className="bg-gray-800 p-2 rounded">
                <span className="text-gray-500">Chakra:</span>
                <span className="ml-1 text-green-400 capitalize">{radionicsData.chakra}</span>
              </div>
            )}
            {radionicsData.intention_type && (
              <div className="bg-gray-800 p-2 rounded">
                <span className="text-gray-500">Type:</span>
                <span className="ml-1 text-amber-400 capitalize">{radionicsData.intention_type}</span>
              </div>
            )}
            {radionicsData.broadcast_recommendation && (
              <div className="bg-gray-800 p-2 rounded col-span-2">
                <span className="text-gray-500">Broadcast:</span>
                <span className="ml-1 text-gray-300 text-xs">{radionicsData.broadcast_recommendation}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {(narrative || affirmation) && (
        <div className="bg-gray-900 rounded-lg p-4">
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-700 mb-4">
            <button
              onClick={() => setActiveTab('narrative')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'narrative'
                  ? 'text-vajra-cyan border-b-2 border-vajra-cyan'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <BookOpen className="w-4 h-4 inline mr-1" />
              Narrative
            </button>
            {affirmation && (
              <button
                onClick={() => setActiveTab('affirmation')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'affirmation'
                    ? 'text-vajra-cyan border-b-2 border-vajra-cyan'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Heart className="w-4 h-4 inline mr-1" />
                Affirmation
              </button>
            )}
          </div>

          {/* Narrative Content */}
          {activeTab === 'narrative' && narrative && (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-vajra-purple">Healing Narrative</span>
                <button
                  onClick={() => copyToClipboard(narrative)}
                  className="text-xs text-gray-400 hover:text-white flex items-center"
                >
                  {copied ? <CheckCircle className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <div className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                {narrative}
              </div>
            </div>
          )}

          {/* Affirmation Content */}
          {activeTab === 'affirmation' && affirmation && (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-vajra-purple">Empowering Affirmation</span>
                <button
                  onClick={() => copyToClipboard(affirmation)}
                  className="text-xs text-gray-400 hover:text-white flex items-center"
                >
                  {copied ? <CheckCircle className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <div className="text-lg text-vajra-cyan font-medium whitespace-pre-wrap leading-relaxed">
                "{affirmation}"
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tips */}
      <div className="mt-4 p-3 bg-gray-900/50 rounded border border-gray-700">
        <div className="text-xs text-gray-500">
          <strong className="text-gray-400">Tip:</strong> Use these narratives during your radionics 
          sessions. Read them aloud while the crystal grid is active to amplify the healing intention.
        </div>
      </div>
    </div>
  );
};

export default RadionicsNarrative;