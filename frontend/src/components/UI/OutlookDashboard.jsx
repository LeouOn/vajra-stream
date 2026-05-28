import React, { useState, useEffect, useCallback } from 'react';
import { 
  Sparkles, BookOpen, Compass, Moon, Sun, RefreshCw, Copy, CheckCircle, 
  MapPin, Clock, Globe, HelpCircle, Layers, ArrowRight, History, Users, 
  Plus, Edit2, Trash2, Shield, Settings, Play, Square, Check, X,
  Search, Filter, ArrowUpDown
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { audioFeedback } from '../../utils/audioFeedback';
import { API_BASE } from '../../utils/api';
import EpicStoryViewer from './EpicStoryViewer';

const GENRES = [
  { id: 'healing', name: 'Healing', desc: 'Sutra of restoration, pacifying sickness & anxiety', icon: '🌿' },
  { id: 'victory', name: 'Victory', desc: 'Overcoming limitations, spiritual warfare & triumph', icon: '🛡️' },
  { id: 'alchemist', name: 'Alchemist', desc: 'Hermetic parables of chemical transmutations', icon: '⚗️' },
  { id: 'fun_parable', name: 'Fun Parable', desc: 'Lighthearted Zen/Sufi teaching jokes', icon: '☯️' },
  { id: 'dharani', name: 'Dharani', desc: 'Dense mantras and direct invocations of power', icon: '📿' },
];

const LANGUAGES = [
  { id: 'English', label: 'English (Bridge)' },
  { id: 'Sanskrit', label: 'Sanskrit (Sacred)' },
  { id: 'Tibetan', label: 'Tibetan (Esoteric)' },
  { id: 'Chinese', label: 'Chinese (Canonical)' },
  { id: 'Latin', label: 'Latin (Hermetic)' },
  { id: 'Greek', label: 'Greek (Theurgic)' },
  { id: 'Hebrew', label: 'Hebrew (Kabbalistic)' }
];

export default function OutlookDashboard() {
  const [dashboardTab, setDashboardTab] = useState('generator'); // generator, universe
  const [universeSubTab, setUniverseSubTab] = useState('realms'); // realms, characters, populations

  // --- Generation Settings Form ---
  const [lat, setLat] = useState(34.0522);
  const [lon, setLon] = useState(-118.2437);
  const [genre, setGenre] = useState('healing');
  const [selectedLangs, setSelectedLangs] = useState(['English']);
  const [isEpic, setIsEpic] = useState(false);
  const [stages, setStages] = useState(9);
  const [date, setDate] = useState(() => {
    const now = new Date();
    const tzOffset = now.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(now - tzOffset)).toISOString().slice(0, 16);
    return localISOTime;
  });

  // Narrative Universe selection states
  const [selectedRealmId, setSelectedRealmId] = useState('');
  const [selectedCharIds, setSelectedCharIds] = useState([]);
  const [selectedPopIds, setSelectedPopIds] = useState([]);
  const [includeDialogue, setIncludeDialogue] = useState(false);
  const [customContext, setCustomContext] = useState('');
  const [excludedForcesText, setExcludedForcesText] = useState('');

  // Loaded universe entities
  const [realms, setRealms] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [populations, setPopulations] = useState([]);
  const [roles, setRoles] = useState([]);
  const [locationTypes, setLocationTypes] = useState([]);

  // Loop control states
  const [loopActive, setLoopActive] = useState(false);
  const [loopInterval, setLoopInterval] = useState(5);
  const [loopMode, setLoopMode] = useState('sequential_delay');
  const [loopStatusData, setLoopStatusData] = useState(null);

  // Result and Loading states
  const [loading, setLoading] = useState(false);
  const [currentNarrative, setCurrentNarrative] = useState(null);
  const [history, setHistory] = useState([]);
  const [copied, setCopied] = useState(false);

  // Model selection states
  const [outlookModels, setOutlookModels] = useState({ lm_studio: [], local: [], api: [] });
  const [selectedModel, setSelectedModel] = useState('');
  const [randomizeRealm, setRandomizeRealm] = useState(false);
  const [randomizeCharacters, setRandomizeCharacters] = useState(false);

  // Divination source toggles (all ON by default)
  const [includeAstrology, setIncludeAstrology] = useState(true);
  const [includeTarot, setIncludeTarot] = useState(true);
  const [includeIching, setIncludeIching] = useState(true);

  // Collapse states for generator sections
  const [showCharsSection, setShowCharsSection] = useState(false);
  const [showPopsSection, setShowPopsSection] = useState(false);

  // --- Universe Manager Form States ---
  const [showCreateRealm, setShowCreateRealm] = useState(false);
  const [editingRealmId, setEditingRealmId] = useState(null);
  const [realmForm, setRealmForm] = useState({
    name: '', description: '', location_type: 'metaphysical_realm', source_type: 'manual',
    is_metaphysical: true, latitude: 0.0, longitude: 0.0, celestial_coordinates: '',
    dimension_frequency: 528.0, realm_governor: '', astrological_anchor: '', elemental_affinity: '',
    priority: 5, notes: ''
  });

  const [showCreateCharacter, setShowCreateCharacter] = useState(false);
  const [editingCharId, setEditingCharId] = useState(null);
  const [charForm, setCharForm] = useState({
    name: '', role: 'master', description: '', source_type: 'manual', dialogue_style: '',
    mantra_preference: '', elemental_anchor: 'space', priority: 5, notes: ''
  });

  const { addToast } = useUIStore();

  // --- Universe Manager Filter/Search/Sort States ---
  const [realmSearch, setRealmSearch] = useState('');
  const [realmTypeFilter, setRealmTypeFilter] = useState('all'); // all, earthly_sacred, metaphysical_realm, cosmic_anchor
  const [realmSort, setRealmSort] = useState('name'); // name, priority, featured

  const [charSearch, setCharSearch] = useState('');
  const [charTraditionFilter, setCharTraditionFilter] = useState('all'); // all, taoist, buddhist, legendary, folk, creation
  const [charRoleFilter, setCharRoleFilter] = useState('all');
  const [charSort, setCharSort] = useState('name'); // name, role, priority, featured

  // Computed filtered + sorted lists
  const filteredRealms = React.useMemo(() => {
    let result = realms;
    if (realmSearch) {
      const q = realmSearch.toLowerCase();
      result = result.filter(r =>
        r.name.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q) ||
        (r.realm_governor || '').toLowerCase().includes(q)
      );
    }
    if (realmTypeFilter !== 'all') {
      result = result.filter(r => r.location_type === realmTypeFilter);
    }
    result = [...result].sort((a, b) => {
      if (realmSort === 'name') return a.name.localeCompare(b.name);
      if (realmSort === 'priority') return (b.priority || 0) - (a.priority || 0);
      if (realmSort === 'featured') return (b.total_narratives_featured || 0) - (a.total_narratives_featured || 0);
      return 0;
    });
    return result;
  }, [realms, realmSearch, realmTypeFilter, realmSort]);

  const filteredCharacters = React.useMemo(() => {
    let result = characters;
    if (charSearch) {
      const q = charSearch.toLowerCase();
      result = result.filter(c =>
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        (c.dialogue_style || '').toLowerCase().includes(q) ||
        (c.tags || []).some(t => t.toLowerCase().includes(q))
      );
    }
    if (charTraditionFilter !== 'all') {
      result = result.filter(c => (c.tags || []).includes(charTraditionFilter));
    }
    if (charRoleFilter !== 'all') {
      result = result.filter(c => c.role === charRoleFilter);
    }
    result = [...result].sort((a, b) => {
      if (charSort === 'name') return a.name.localeCompare(b.name);
      if (charSort === 'role') return a.role.localeCompare(b.role);
      if (charSort === 'priority') return (b.priority || 0) - (a.priority || 0);
      if (charSort === 'featured') return (b.total_narratives_featured || 0) - (a.total_narratives_featured || 0);
      return 0;
    });
    return result;
  }, [characters, charSearch, charTraditionFilter, charRoleFilter, charSort]);

  // Character tags helper — extract unique tradition tags for filter pills
  const charTraditionTags = React.useMemo(() => {
    const tagSet = new Set();
    characters.forEach(c => (c.tags || []).forEach(t => {
      if (['taoist', 'buddhist', 'folk', 'creation', 'legendary'].includes(t)) tagSet.add(t);
    }));
    return ['all', ...Array.from(tagSet)];
  }, [characters]);

  // --- API CALLS ---
  const fetchUniverseData = useCallback(async () => {
    try {
      // Realms
      const realmsRes = await fetch(`${API_BASE}/outlook/locations`);
      if (realmsRes.ok) {
        const data = await realmsRes.json();
        setRealms(data);
      }
      // Characters
      const charRes = await fetch(`${API_BASE}/outlook/characters`);
      if (charRes.ok) {
        const data = await charRes.json();
        setCharacters(data);
      }
      // Populations
      const popRes = await fetch(`${API_BASE}/populations/`);
      if (popRes.ok) {
        const data = await popRes.json();
        setPopulations(data);
      }
      // Metadata lists
      const rolesRes = await fetch(`${API_BASE}/outlook/characters/roles/list`);
      if (rolesRes.ok) setRoles(await rolesRes.json());

      const typesRes = await fetch(`${API_BASE}/outlook/locations/types/list`);
      if (typesRes.ok) setLocationTypes(await typesRes.json());
    } catch (e) {
      console.error('Failed to fetch Universe Data:', e);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/outlook/history?limit=15`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (e) {
      console.error('Failed to load history:', e);
    }
  }, []);

  const fetchLoopStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/outlook/loop/status`);
      if (res.ok) {
        const data = await res.json();
        setLoopStatusData(data);
        setLoopActive(data.active);
        if (data.active) {
          setLoopInterval(data.interval_minutes);
          if (data.config && data.config.loop_mode) {
            setLoopMode(data.config.loop_mode);
          }
        }
      }
    } catch (e) {
      console.error('Failed to fetch loop status:', e);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
    fetchUniverseData();
    fetchLoopStatus();
    fetchOutlookModels();
  }, [fetchHistory, fetchUniverseData, fetchLoopStatus]);

  const fetchOutlookModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/llm/models`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setOutlookModels(data.available || { lm_studio: [], local: [], api: [] });
          if (!selectedModel && data.default_model) {
            setSelectedModel(data.default_model);
          }
        }
      }
    } catch (e) {
      console.error('Failed to fetch outlook models:', e);
    }
  }, [selectedModel]);

  // Handle active location coordinate overrides
  useEffect(() => {
    if (selectedRealmId) {
      const activeLoc = realms.find(r => r.id === selectedRealmId);
      if (activeLoc && !activeLoc.is_metaphysical && activeLoc.latitude !== null && activeLoc.longitude !== null) {
        setLat(activeLoc.latitude);
        setLon(activeLoc.longitude);
      }
    }
  }, [selectedRealmId, realms]);

  const toggleLanguage = (langId) => {
    audioFeedback.playClick();
    setSelectedLangs(prev => {
      if (prev.includes(langId)) {
        if (prev.length === 1) return prev;
        return prev.filter(l => l !== langId);
      } else {
        return [...prev, langId];
      }
    });
  };

  const handleGenerate = async () => {
    setLoading(true);
    setCurrentNarrative(null);
    audioFeedback.playTelemetry();

    try {
      const endpoint = isEpic ? '/outlook/generate_epic' : '/outlook/generate_single';
      const body = {
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        languages: selectedLangs,
        genre: genre,
        date: new Date(date).toISOString(),
        custom_context: customContext || null,
        realm_id: selectedRealmId || null,
        population_ids: selectedPopIds.length > 0 ? selectedPopIds : null,
        character_ids: selectedCharIds.length > 0 ? selectedCharIds : null,
        excluded_forces: excludedForcesText ? excludedForcesText.split(',').map(s => s.trim()) : null,
        include_dialogue: includeDialogue,
        model: selectedModel || null,
        include_astrology: includeAstrology,
        include_tarot: includeTarot,
        include_iching: includeIching,
        randomize_realm: randomizeRealm,
        randomize_characters: randomizeCharacters,
      };

      if (isEpic) {
        body.stages = parseInt(stages);
      }

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (res.ok) {
        const data = await res.json();
        setCurrentNarrative(data);
        addToast({
          type: 'success',
          title: 'Transmission Secured',
          message: isEpic ? `Epic Journey received over ${stages} stages.` : 'Single narrative generated.',
          duration: 3000
        });
        audioFeedback.playSuccess();
        fetchHistory();
        fetchUniverseData(); // Refresh features count
      } else {
        const errData = await res.json();
        addToast({
          type: 'error',
          title: 'Transmission Failed',
          message: errData.detail || 'Could not contact generator.',
          duration: 4000
        });
        audioFeedback.playError();
      }
    } catch (error) {
      console.error(error);
      addToast({
        type: 'error',
        title: 'Network Error',
        message: 'Could not connect to backend server.',
        duration: 4000
      });
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  // --- LOOP CONTROLS ---
  const handleStartLoop = async () => {
    audioFeedback.playClick();
    try {
      const body = {
        interval_minutes: parseInt(loopInterval),
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        languages: selectedLangs,
        genre: genre,
        custom_context: customContext || null,
        realm_id: selectedRealmId || null,
        population_ids: selectedPopIds.length > 0 ? selectedPopIds : null,
        character_ids: selectedCharIds.length > 0 ? selectedCharIds : null,
        excluded_forces: excludedForcesText ? excludedForcesText.split(',').map(s => s.trim()) : null,
        include_dialogue: includeDialogue,
        loop_mode: loopMode,
        model: selectedModel || null,
        include_astrology: includeAstrology,
        include_tarot: includeTarot,
        include_iching: includeIching,
        randomize_realm: randomizeRealm,
        randomize_characters: randomizeCharacters,
      };

      const res = await fetch(`${API_BASE}/outlook/loop/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (res.ok) {
        setLoopActive(true);
        addToast({
          type: 'success',
          title: 'Loop Activated',
          message: `Broadcast generation cycling every ${loopInterval} minutes.`,
          duration: 3000
        });
        fetchLoopStatus();
      }
    } catch (e) {
      console.error('Failed to start loop:', e);
    }
  };

  const handleStopLoop = async () => {
    audioFeedback.playClick();
    try {
      const res = await fetch(`${API_BASE}/outlook/loop/stop`, {
        method: 'POST'
      });
      if (res.ok) {
        setLoopActive(false);
        setLoopStatusData(null);
        addToast({
          type: 'success',
          title: 'Loop Stopped',
          message: 'Continuous broadcast loop paused.',
          duration: 3000
        });
      }
    } catch (e) {
      console.error('Failed to stop loop:', e);
    }
  };

  // --- CRUD REALMS ---
  const saveRealm = async () => {
    try {
      const url = editingRealmId ? `${API_BASE}/outlook/locations/${editingRealmId}` : `${API_BASE}/outlook/locations`;
      const method = editingRealmId ? 'PUT' : 'POST';
      const payload = { ...realmForm };
      
      // format coordinates
      if (!payload.is_metaphysical) {
        payload.latitude = parseFloat(payload.latitude);
        payload.longitude = parseFloat(payload.longitude);
      } else {
        payload.latitude = null;
        payload.longitude = null;
      }
      payload.dimension_frequency = payload.dimension_frequency ? parseFloat(payload.dimension_frequency) : null;
      payload.priority = parseInt(payload.priority);

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingRealmId ? payload : payload)
      });

      if (res.ok) {
        addToast({
          type: 'success',
          title: editingRealmId ? 'Realm Updated' : 'Realm Created',
          message: `${payload.name} has been synchronized.`,
          duration: 3000
        });
        fetchUniverseData();
        setShowCreateRealm(false);
        setEditingRealmId(null);
        setRealmForm({
          name: '', description: '', location_type: 'metaphysical_realm', source_type: 'manual',
          is_metaphysical: true, latitude: 0.0, longitude: 0.0, celestial_coordinates: '',
          dimension_frequency: 528.0, realm_governor: '', astrological_anchor: '', elemental_affinity: '',
          priority: 5, notes: ''
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteRealm = async (id) => {
    if (!confirm('Exile this realm?')) return;
    try {
      const res = await fetch(`${API_BASE}/outlook/locations/${id}`, { method: 'DELETE' });
      if (res.ok) {
        addToast({ type: 'success', title: 'Realm Deleted', message: 'Setting removed from grimoire.', duration: 3000 });
        fetchUniverseData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // --- CRUD CHARACTERS ---
  const saveCharacter = async () => {
    try {
      const url = editingCharId ? `${API_BASE}/outlook/characters/${editingCharId}` : `${API_BASE}/outlook/characters`;
      const method = editingCharId ? 'PUT' : 'POST';
      const payload = { ...charForm };
      payload.priority = parseInt(payload.priority);

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        addToast({
          type: 'success',
          title: editingCharId ? 'Character Updated' : 'Character Created',
          message: `${payload.name} has been materialized.`,
          duration: 3000
        });
        fetchUniverseData();
        setShowCreateCharacter(false);
        setEditingCharId(null);
        setCharForm({
          name: '', role: 'master', description: '', source_type: 'manual', dialogue_style: '',
          mantra_preference: '', elemental_anchor: 'space', priority: 5, notes: ''
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteCharacter = async (id) => {
    if (!confirm('Exile this character from the universe?')) return;
    try {
      const res = await fetch(`${API_BASE}/outlook/characters/${id}`, { method: 'DELETE' });
      if (res.ok) {
        addToast({ type: 'success', title: 'Character Exiled', message: 'Character removed from grimoire.', duration: 3000 });
        fetchUniverseData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // --- Load history item ---
  const handleLoadHistory = (item) => {
    audioFeedback.playClick();
    const normalized = {
      ...item,
      astrology_used: item.astrology_context,
      divination_used: item.divination_context,
      divination_raw: item.divination_raw,
      entities_used: item.entities_invoked
    };

    if (item.type === 'epic') {
      normalized.narrative_parts = item.content;
    } else {
      normalized.narrative = item.content;
    }
    
    setCurrentNarrative(normalized);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    audioFeedback.playClick();
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
      {/* Header Tabs */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between border-b border-white/10 pb-4 gap-4">
        <div>
          <h2 className="text-xl font-bold text-vajra-cyan glow-cyan tracking-wider flex items-center gap-2">
            <Compass className="w-6 h-6 animate-pulse text-vajra-cyan" />
            Narrative Generation & Outlook
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Construct localized, sutra-style blessing cycles based on high-entropy oracles, planetary lines, and active entity grids.
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex bg-gray-900/60 p-1 rounded-lg border border-white/5 self-end md:self-auto">
          <button
            onClick={() => { setDashboardTab('generator'); audioFeedback.playClick(); }}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              dashboardTab === 'generator'
                ? 'bg-gradient-to-r from-cyan-600/90 to-blue-600/90 text-white shadow'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 inline mr-1" />
            Generator
          </button>
          <button
            onClick={() => { setDashboardTab('universe'); audioFeedback.playClick(); }}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              dashboardTab === 'universe'
                ? 'bg-gradient-to-r from-cyan-600/90 to-blue-600/90 text-white shadow'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5 inline mr-1" />
            Universe Manager
          </button>
        </div>
      </div>

      {dashboardTab === 'generator' ? (
        // ==========================================
        //         GENERATOR SCREEN
        // ==========================================
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
          {/* Left Controls column */}
          <div className="space-y-6">
            <div className="bg-gray-950/40 p-5 rounded-xl border border-white/5 space-y-5">
              <div className="flex justify-between items-center border-b border-white/10 pb-2">
                <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
                  Transmission Settings
                </h3>
                {loopActive && (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                  </span>
                )}
              </div>

              {/* Selected Summary Bar */}
              {(selectedRealmId || selectedCharIds.length > 0 || selectedPopIds.length > 0) && (
                <div className="flex flex-wrap gap-1.5 bg-cyan-950/20 border border-cyan-800/20 rounded-lg p-2">
                  {selectedRealmId && (() => {
                    const realm = realms.find(r => r.id === selectedRealmId);
                    return (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-900/40 border border-cyan-700/30 text-[10px] text-cyan-300">
                        📍 {realm?.name || 'Unknown Realm'}
                        <button onClick={() => { setSelectedRealmId(''); audioFeedback.playClick(); }} className="ml-0.5 hover:text-white">&times;</button>
                      </span>
                    );
                  })()}
                  {selectedCharIds.length > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-900/40 border border-purple-700/30 text-[10px] text-purple-300">
                      👤 {selectedCharIds.length} character{selectedCharIds.length > 1 ? 's' : ''}
                      <button onClick={() => { setSelectedCharIds([]); audioFeedback.playClick(); }} className="ml-0.5 hover:text-white">&times;</button>
                    </span>
                  )}
                  {selectedPopIds.length > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-900/40 border border-blue-700/30 text-[10px] text-blue-300">
                      🫂 {selectedPopIds.length} population{selectedPopIds.length > 1 ? 's' : ''}
                      <button onClick={() => { setSelectedPopIds([]); audioFeedback.playClick(); }} className="ml-0.5 hover:text-white">&times;</button>
                    </span>
                  )}
                </div>
              )}

              {/* Active Location/Realm Selection */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="block text-xs font-semibold text-gray-400 flex items-center gap-1">
                    <Globe className="w-3.5 h-3.5 text-vajra-cyan" />
                    Realm / Setting
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer select-none text-[10px] text-gray-400 hover:text-white">
                    <input
                      type="checkbox"
                      checked={randomizeRealm}
                      onChange={(e) => { setRandomizeRealm(e.target.checked); audioFeedback.playClick(); }}
                      className="w-3 h-3 rounded border-white/10 bg-black/40 text-vajra-cyan focus:ring-0"
                    />
                    Randomize
                  </label>
                </div>
                <select
                  value={selectedRealmId}
                  onChange={(e) => { setSelectedRealmId(e.target.value); audioFeedback.playClick(); }}
                  disabled={randomizeRealm}
                  className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 focus:border-vajra-cyan outline-none font-mono disabled:opacity-40"
                >
                  <option value="">{randomizeRealm ? "-- Selected at Random --" : "-- Dynamic Map Coordinates --"}</option>
                  {realms.map(r => (
                    <option key={r.id} value={r.id}>{r.name} ({r.is_metaphysical ? 'Metaphysical' : 'Earthly'})</option>
                  ))}
                </select>
              </div>

              {/* Coordinates Grid */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-gray-400">Target Coordinates</label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="relative">
                    <span className="absolute left-2.5 top-2.5 text-xs text-gray-500 font-mono">LAT</span>
                    <input
                      type="number"
                      step="0.0001"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                      disabled={randomizeRealm || (!!selectedRealmId && !(realms.find(r => r.id === selectedRealmId)?.is_metaphysical))}
                      className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 pl-10 text-xs border border-white/10 focus:border-vajra-cyan outline-none font-mono disabled:opacity-40"
                    />
                  </div>
                  <div className="relative">
                    <span className="absolute left-2.5 top-2.5 text-xs text-gray-500 font-mono">LON</span>
                    <input
                      type="number"
                      step="0.0001"
                      value={lon}
                      onChange={(e) => setLon(e.target.value)}
                      disabled={randomizeRealm || (!!selectedRealmId && !(realms.find(r => r.id === selectedRealmId)?.is_metaphysical))}
                      className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 pl-10 text-xs border border-white/10 focus:border-vajra-cyan outline-none font-mono disabled:opacity-40"
                    />
                  </div>
                </div>
              </div>

              {/* Target Date */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-yellow-500" />
                  Cosmic Epoch (Timing)
                </label>
                <input
                  type="datetime-local"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 focus:border-vajra-cyan outline-none font-mono"
                />
              </div>

              {/* Genre Selection */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-400">Blessing Genre</label>
                <div className="space-y-2">
                  {GENRES.map((g) => (
                    <button
                      key={g.id}
                      onClick={() => { setGenre(g.id); audioFeedback.playClick(); }}
                      className={`w-full flex items-center p-2 rounded-lg text-left transition-all border ${
                        genre === g.id
                          ? 'bg-purple-950/20 border-vajra-purple text-white shadow-[0_0_8px_rgba(168,85,247,0.15)]'
                          : 'bg-black/30 border-transparent text-gray-400 hover:text-white hover:bg-black/50'
                      }`}
                    >
                      <span className="text-base mr-2">{g.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold">{g.name}</div>
                        <div className="text-[10px] text-gray-500 truncate">{g.desc}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Divination Source Toggles */}
              <div className="border-t border-white/5 pt-3 space-y-2">
                <label className="block text-xs font-semibold text-gray-400">Oracle Sources</label>
                <div className="flex flex-col gap-1.5">
                  <label className="flex items-center justify-between cursor-pointer select-none">
                    <span className="text-[11px] text-gray-300 flex items-center gap-1.5">
                      <span className="text-xs">🌟</span> Astrology Chart
                    </span>
                    <button
                      onClick={() => { setIncludeAstrology(!includeAstrology); audioFeedback.playClick(); }}
                      className={`w-9 h-5 rounded-full transition-all relative ${includeAstrology ? 'bg-amber-600' : 'bg-gray-700'}`}
                    >
                      <div className={`w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-all ${includeAstrology ? 'left-5' : 'left-0.5'}`} />
                    </button>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer select-none">
                    <span className="text-[11px] text-gray-300 flex items-center gap-1.5">
                      <span className="text-xs">🃏</span> Tarot Oracle
                    </span>
                    <button
                      onClick={() => { setIncludeTarot(!includeTarot); audioFeedback.playClick(); }}
                      className={`w-9 h-5 rounded-full transition-all relative ${includeTarot ? 'bg-purple-600' : 'bg-gray-700'}`}
                    >
                      <div className={`w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-all ${includeTarot ? 'left-5' : 'left-0.5'}`} />
                    </button>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer select-none">
                    <span className="text-[11px] text-gray-300 flex items-center gap-1.5">
                      <span className="text-xs">☯️</span> I Ching Hexagram
                    </span>
                    <button
                      onClick={() => { setIncludeIching(!includeIching); audioFeedback.playClick(); }}
                      className={`w-9 h-5 rounded-full transition-all relative ${includeIching ? 'bg-cyan-600' : 'bg-gray-700'}`}
                    >
                      <div className={`w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-all ${includeIching ? 'left-5' : 'left-0.5'}`} />
                    </button>
                  </label>
                </div>
              </div>

              {/* Weave Languages */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-gray-400">
                  Weave Languages ({selectedLangs.length} active)
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {LANGUAGES.map((lang) => {
                    const selected = selectedLangs.includes(lang.id);
                    return (
                      <button
                        key={lang.id}
                        onClick={() => toggleLanguage(lang.id)}
                        className={`px-2.5 py-1 rounded text-[10px] font-semibold border transition-all duration-300 ${
                          selected
                            ? 'bg-gradient-to-r from-cyan-600/80 to-indigo-600/80 text-white border-cyan-400/30'
                            : 'bg-white/5 border-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                        }`}
                      >
                        {lang.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Model Selection */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-400 flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  LLM Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => { setSelectedModel(e.target.value); audioFeedback.playClick(); }}
                  className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 focus:border-amber-500/50 outline-none"
                >
                  <option value="">Auto-detect (default)</option>
                  {outlookModels.lm_studio && outlookModels.lm_studio.length > 0 && (
                    <optgroup label="LM Studio (Loaded)">
                      {outlookModels.lm_studio.map(m => (
                        <option key={`outlook-lm-${m}`} value={m}>{m}</option>
                      ))}
                    </optgroup>
                  )}
                  {outlookModels.local && outlookModels.local.length > 0 && (
                    <optgroup label="Local GGUF">
                      {outlookModels.local.map(m => (
                        <option key={`outlook-local-${m}`} value={m}>{m}</option>
                      ))}
                    </optgroup>
                  )}
                </select>
                <span className="text-[9px] text-gray-500">
                  {selectedModel ? `Using: ${selectedModel}` : 'Auto-detected from LM Studio'}
                </span>
              </div>

              {/* Characters — collapsible */}
              <div className="border-t border-white/5 pt-3">
                <div className="flex justify-between items-center">
                  <button
                    onClick={() => { setShowCharsSection(!showCharsSection); audioFeedback.playClick(); }}
                    className="flex-1 flex items-center gap-1 text-xs font-semibold text-gray-400 hover:text-white transition-colors text-left"
                  >
                    <Shield className="w-3.5 h-3.5 text-purple-400" />
                    Characters & Heroes
                    {!randomizeCharacters && selectedCharIds.length > 0 && (
                      <span className="text-[10px] text-purple-400 font-mono">({selectedCharIds.length})</span>
                    )}
                    {randomizeCharacters && (
                      <span className="text-[10px] text-purple-400 font-mono font-bold">(Random 2-3)</span>
                    )}
                  </button>
                  <label className="flex items-center gap-1 cursor-pointer select-none text-[10px] text-gray-400 hover:text-white">
                    <input
                      type="checkbox"
                      checked={randomizeCharacters}
                      onChange={(e) => { setRandomizeCharacters(e.target.checked); audioFeedback.playClick(); }}
                      className="w-3 h-3 rounded border-white/10 bg-black/40 text-vajra-cyan focus:ring-0"
                    />
                    Randomize
                  </label>
                </div>
                {showCharsSection && (
                  <div className={`space-y-1.5 mt-2 transition-opacity duration-300 ${randomizeCharacters ? 'opacity-30 pointer-events-none' : ''}`}>
                    {/* Quick action buttons per tradition */}
                    <div className="flex gap-1 flex-wrap">
                      {[['All', null], ['☯️', 'taoist'], ['📿', 'buddhist'], ['🏮', 'folk'], ['🪐', 'creation']].map(([label, tag]) => {
                        const subset = tag ? characters.filter(c => (c.tags || []).includes(tag)) : characters;
                        const allSelected = subset.length > 0 && subset.every(c => selectedCharIds.includes(c.id));
                        return (
                          <button
                            key={tag || 'all'}
                            onClick={() => {
                              audioFeedback.playClick();
                              if (allSelected) {
                                setSelectedCharIds(prev => prev.filter(id => !subset.find(c => c.id === id)));
                              } else {
                                setSelectedCharIds(prev => [...new Set([...prev, ...subset.map(c => c.id)])]);
                              }
                            }}
                            className={`px-1.5 py-0.5 rounded text-[9px] font-semibold transition-all ${
                              allSelected && subset.length > 0
                                ? 'bg-purple-600/40 text-purple-300'
                                : 'bg-white/5 text-gray-500 hover:text-white hover:bg-white/10'
                            }`}
                          >
                            {label} {tag ? subset.length : ''}
                          </button>
                        );
                      })}
                    </div>
                    <div className="bg-black/30 border border-white/10 rounded-lg p-1.5 max-h-40 overflow-y-auto space-y-0.5">
                      {characters.map(c => {
                        const isSelected = selectedCharIds.includes(c.id);
                        const traditionTag = (c.tags || []).find(t => ['taoist','buddhist','folk','creation'].includes(t));
                        const dotColor = traditionTag === 'taoist' ? 'bg-amber-400' : traditionTag === 'buddhist' ? 'bg-orange-400' : traditionTag === 'folk' ? 'bg-red-400' : traditionTag === 'creation' ? 'bg-indigo-400' : 'bg-gray-500';
                        return (
                          <label key={c.id} className={`flex items-center gap-1.5 text-[11px] cursor-pointer select-none rounded px-1.5 py-0.5 transition-colors ${isSelected ? 'bg-purple-900/30 text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                audioFeedback.playClick();
                                setSelectedCharIds(prev => 
                                  e.target.checked ? [...prev, c.id] : prev.filter(id => id !== c.id)
                                );
                              }}
                              className="w-3 h-3 rounded border-white/10 bg-black/40 text-vajra-cyan"
                            />
                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
                            <span className="flex-1 truncate">{c.name}</span>
                            <span className="text-[8px] bg-white/10 px-1 py-0.5 rounded font-mono uppercase flex-shrink-0">{c.role}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Populations — collapsible */}
              <div className="border-t border-white/5 pt-3">
                <button
                  onClick={() => { setShowPopsSection(!showPopsSection); audioFeedback.playClick(); }}
                  className="w-full flex items-center justify-between text-xs font-semibold text-gray-400 hover:text-white transition-colors"
                >
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5 text-blue-400" />
                    Beneficiary Populations
                    {selectedPopIds.length > 0 && (
                      <span className="text-[10px] text-blue-400 font-mono ml-1">({selectedPopIds.length})</span>
                    )}
                  </span>
                  <span className={`transform transition-transform ${showPopsSection ? 'rotate-90' : ''}`}>▶</span>
                </button>
                {showPopsSection && (
                  <div className="bg-black/30 border border-white/10 rounded-lg p-2 mt-2 max-h-32 overflow-y-auto space-y-1">
                    {populations.map(p => {
                      const isSelected = selectedPopIds.includes(p.id);
                      return (
                        <label key={p.id} className="flex items-center gap-2 text-xs text-gray-300 hover:text-white cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              audioFeedback.playClick();
                              setSelectedPopIds(prev => 
                                e.target.checked ? [...prev, p.id] : prev.filter(id => id !== p.id)
                              );
                            }}
                            className="w-3.5 h-3.5 rounded border-white/10 bg-black/40 text-vajra-cyan"
                          />
                          <span>{p.name}</span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Dialogue & Custom Settings */}
              <div className="border-t border-white/5 pt-4 space-y-3">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-xs font-bold text-white block">Weave Dialogue</span>
                    <span className="text-[10px] text-gray-500">Characters engage in speaking parables.</span>
                  </div>
                  <button
                    onClick={() => { setIncludeDialogue(!includeDialogue); audioFeedback.playClick(); }}
                    disabled={selectedCharIds.length === 0}
                    className={`w-11 h-6 rounded-full transition-all relative disabled:opacity-30 ${
                      includeDialogue ? 'bg-vajra-cyan' : 'bg-gray-800'
                    }`}
                  >
                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${
                      includeDialogue ? 'left-6' : 'left-1'
                    }`} />
                  </button>
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-gray-400">Exclude Forces</label>
                  <input
                    type="text"
                    value={excludedForcesText}
                    onChange={(e) => setExcludedForcesText(e.target.value)}
                    placeholder="sickness, doubt, obstacles"
                    className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 focus:border-vajra-cyan outline-none font-serif"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-gray-400">Custom Aspiration / Intentions</label>
                  <textarea
                    value={customContext}
                    onChange={(e) => setCustomContext(e.target.value)}
                    rows="2"
                    placeholder="Weave in intentions of peaceful passing for all being in hospitals..."
                    className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 focus:border-vajra-cyan outline-none font-serif resize-none"
                  />
                </div>
              </div>

              {/* Epic Toggle */}
              <div className="border-t border-white/5 pt-3 space-y-3">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-xs font-bold text-white block">Epic Multi-Stage Journey</span>
                    <span className="text-[10px] text-gray-500">Generate multi-stage narrative sequence.</span>
                  </div>
                  <button
                    onClick={() => { setIsEpic(!isEpic); audioFeedback.playClick(); }}
                    className={`w-11 h-6 rounded-full transition-all relative ${
                      isEpic ? 'bg-vajra-cyan' : 'bg-gray-800'
                    }`}
                  >
                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${
                      isEpic ? 'left-6' : 'left-1'
                    }`} />
                  </button>
                </div>

                {isEpic && (
                  <div className="flex items-center justify-between bg-black/30 p-2.5 rounded border border-white/5">
                    <label className="text-xs text-gray-400 font-mono">STAGES:</label>
                    <input
                      type="number"
                      min="3"
                      max="15"
                      value={stages}
                      onChange={(e) => setStages(e.target.value)}
                      className="w-16 bg-gray-950 text-white rounded border border-white/10 px-2 py-0.5 text-xs text-center font-mono outline-none"
                    />
                  </div>
                )}
              </div>

              {/* Initiate Trigger */}
              <button
                onClick={handleGenerate}
                disabled={loading || selectedLangs.length === 0}
                className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 disabled:opacity-50 text-white rounded-lg py-2.5 text-xs font-bold flex items-center justify-center gap-2 transition-all duration-300 shadow-lg hover:shadow-cyan-500/20"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 animate-pulse" />}
                {loading ? 'Decrypting Transmissions...' : 'Initiate Narrative Stream'}
              </button>
            </div>

            {/* Loop settings panel */}
            <div className="bg-gray-950/40 p-5 rounded-xl border border-white/5 space-y-4">
              <h4 className="text-xs font-bold font-mono text-gray-400 flex items-center gap-1.5 uppercase tracking-wider border-b border-white/10 pb-2">
                <Settings className="w-3.5 h-3.5 text-vajra-cyan" />
                Continuous Broadcast Loop
              </h4>
              
              <div className="space-y-3">
                <div className="flex justify-between text-xs text-gray-300">
                  <span>Cycle Interval: {loopInterval} minutes</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="60"
                  step="1"
                  value={loopInterval}
                  onChange={(e) => setLoopInterval(parseInt(e.target.value))}
                  disabled={loopActive}
                  className="w-full disabled:opacity-50"
                />

                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] text-gray-400 font-mono block">Loop Mode:</span>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      disabled={loopActive}
                      onClick={() => { setLoopMode('sequential_delay'); audioFeedback.playClick(); }}
                      className={`px-2 py-1 rounded text-[10px] font-bold border transition-all ${
                        loopMode === 'sequential_delay'
                          ? 'bg-purple-900/60 border-purple-500 text-purple-200'
                          : 'bg-black/40 border-white/10 text-gray-400 hover:text-gray-200'
                      }`}
                    >
                      Sequential Delay
                    </button>
                    <button
                      type="button"
                      disabled={loopActive}
                      onClick={() => { setLoopMode('consecutive'); audioFeedback.playClick(); }}
                      className={`px-2 py-1 rounded text-[10px] font-bold border transition-all ${
                        loopMode === 'consecutive'
                          ? 'bg-purple-900/60 border-purple-500 text-purple-200'
                          : 'bg-black/40 border-white/10 text-gray-400 hover:text-gray-200'
                      }`}
                    >
                      Consecutive
                    </button>
                  </div>
                  <span className="text-[9px] text-gray-500 block leading-tight">
                    {loopMode === 'sequential_delay' 
                      ? 'Wait for the previous run to finish before starting interval.' 
                      : 'Loop immediately after previous run is finished (5s gap).'}
                  </span>
                </div>

                <div className="flex gap-2 pt-1">
                  {loopActive ? (
                    <button
                      onClick={handleStopLoop}
                      className="flex-1 bg-red-900/60 border border-red-500/30 hover:bg-red-900 text-white py-1.5 rounded text-xs font-bold flex items-center justify-center gap-1.5 transition-all"
                    >
                      <Square className="w-3.5 h-3.5" />
                      Deactivate Loop
                    </button>
                  ) : (
                    <button
                      onClick={handleStartLoop}
                      className="flex-1 bg-cyan-900/60 border border-cyan-500/30 hover:bg-cyan-900 text-white py-1.5 rounded text-xs font-bold flex items-center justify-center gap-1.5 transition-all"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Activate Loop
                    </button>
                  )}
                </div>
              </div>

              {loopActive && loopStatusData && (
                <div className="text-[10px] text-gray-500 font-mono leading-relaxed pt-1 space-y-1">
                  <div>Status: <span className="text-green-400 font-bold uppercase">Broadcasting</span></div>
                  <div>Mode: <span className="text-purple-400 font-bold uppercase">{loopStatusData.config?.loop_mode === 'consecutive' ? 'Consecutive' : 'Sequential Delay'}</span></div>
                  <div>Frequency: {loopStatusData.config?.loop_mode === 'consecutive' ? 'Immediate consecutive (5s gap)' : `1 cycle / ${loopInterval}m`}</div>
                  {loopStatusData.last_generated && (
                    <div className="truncate">Last blessing: "{loopStatusData.last_generated.genre} revelation"</div>
                  )}
                </div>
              )}
            </div>

            {/* History Panel */}
            <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-3">
              <h4 className="text-xs font-bold font-mono text-gray-400 flex items-center gap-1.5 uppercase tracking-wider">
                <History className="w-3.5 h-3.5 text-vajra-cyan" />
                Past Transmissions
              </h4>
              <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                {history.length === 0 ? (
                  <div className="text-[10px] text-gray-500 italic py-4 text-center">
                    No records stored in local database.
                  </div>
                ) : (
                  history.map((h) => (
                    <button
                      key={h.id}
                      onClick={() => handleLoadHistory(h)}
                      className="w-full text-left p-2 rounded bg-black/30 hover:bg-black/60 border border-white/5 hover:border-vajra-cyan/30 transition-all flex justify-between items-center gap-2 group"
                    >
                      <div className="min-w-0">
                        <div className="text-[10px] text-gray-300 font-bold flex items-center gap-1">
                          <span className="capitalize">{h.genre}</span>
                          <span className="text-[8px] bg-purple-950 text-purple-400 px-1 rounded uppercase scale-90">
                            {h.type}
                          </span>
                        </div>
                        <div className="text-[9px] text-gray-500 mt-0.5 truncate font-serif">
                          {h.type === 'epic' ? 'Multi-stage story' : (h.content || '').slice(0, 45) + '...'}
                        </div>
                      </div>
                      <span className="text-[8px] text-gray-600 font-mono group-hover:text-vajra-cyan">
                        {h.date_generated ? h.date_generated.slice(5, 16).replace('T', ' ') : ''}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Main Display Area Column Span 2 */}
          <div className="xl:col-span-2">
            {currentNarrative ? (
              currentNarrative.type === 'epic' ? (
                <EpicStoryViewer
                  narrativeParts={currentNarrative.narrative_parts}
                  astrologyContext={currentNarrative.astrology_used}
                  divinationContext={currentNarrative.divination_used}
                  divinationRaw={currentNarrative.divination_raw}
                  entitiesInvoked={currentNarrative.entities_used}
                />
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                  <div className="lg:col-span-2 bg-gray-950/40 p-5 rounded-xl border border-white/5 flex flex-col justify-between min-h-[400px]">
                    <div className="space-y-4">
                      <div className="flex justify-between items-center border-b border-white/10 pb-3">
                        <div>
                          <span className="text-[10px] text-vajra-purple font-mono font-bold tracking-widest uppercase">
                            SINGLE TRANSMISSION BLESSING
                          </span>
                          <h3 className="text-xl font-bold text-white mt-1 capitalize">
                            {currentNarrative.genre} Revelation
                          </h3>
                        </div>
                        <button
                          onClick={() => copyToClipboard(currentNarrative.narrative)}
                          className="text-xs text-gray-400 hover:text-white flex items-center gap-1 font-mono"
                        >
                          {copied ? <CheckCircle className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copied ? 'Copied' : 'Copy'}
                        </button>
                      </div>

                      <div className="text-sm md:text-base text-gray-200 whitespace-pre-wrap leading-relaxed space-y-4 py-2 font-serif">
                        {currentNarrative.narrative}
                      </div>
                    </div>
                  </div>

                  {/* Sidebar details */}
                  <div className="space-y-6">
                    {/* Divination card drawn */}
                    {currentNarrative.divination_raw && (
                      <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-4">
                        <h4 className="text-xs font-bold font-mono text-vajra-cyan tracking-wider flex items-center gap-2 uppercase">
                          <Sparkles className="w-4 h-4" />
                          Esoteric Reading
                        </h4>

                        <div className="grid grid-cols-2 gap-3">
                          {currentNarrative.divination_raw.tarot && currentNarrative.divination_raw.tarot.svg && (
                            <div className="flex flex-col items-center bg-black/45 p-2 rounded border border-white/5 text-center">
                              <span className="text-[9px] text-gray-500 font-mono block">TAROT</span>
                              <div className="w-20 h-28 my-1 flex items-center justify-center relative overflow-hidden rounded">
                                <div 
                                  dangerouslySetInnerHTML={{ __html: currentNarrative.divination_raw.tarot.svg }} 
                                  className="divination-card-container w-full h-full flex justify-center" 
                                />
                              </div>
                              <span className="text-[9px] font-bold text-white truncate max-w-full block">
                                {currentNarrative.divination_raw.tarot.name}
                              </span>
                            </div>
                          )}

                          {currentNarrative.divination_raw.iching && currentNarrative.divination_raw.iching.svg && (
                            <div className="flex flex-col items-center bg-black/45 p-2 rounded border border-white/5 text-center">
                              <span className="text-[9px] text-gray-500 font-mono block">I CHING</span>
                              <div className="w-20 h-28 my-1 flex items-center justify-center relative overflow-hidden rounded">
                                <div 
                                  dangerouslySetInnerHTML={{ __html: currentNarrative.divination_raw.iching.svg }} 
                                  className="divination-card-container w-full h-full flex justify-center" 
                                />
                              </div>
                              <span className="text-[9px] font-bold text-white truncate max-w-full block">
                                {currentNarrative.divination_raw.iching.name.split(' / ')[0]}
                              </span>
                            </div>
                          )}
                        </div>

                        {currentNarrative.divination_used && (
                          <p className="text-[10px] text-gray-400 italic font-serif leading-relaxed border-t border-white/5 pt-2">
                            "{currentNarrative.divination_used}"
                          </p>
                        )}
                      </div>
                    )}

                    {/* Astrology snap */}
                    {currentNarrative.astrology_used && (
                      <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-2">
                        <h4 className="text-xs font-bold font-mono text-yellow-500 tracking-wider flex items-center gap-2 uppercase">
                          <Sun className="w-4 h-4" />
                          Astrology Used
                        </h4>
                        <p className="text-xs text-gray-300 leading-relaxed font-serif">
                          {currentNarrative.astrology_used}
                        </p>
                      </div>
                    )}

                    {/* Entities */}
                    {currentNarrative.entities_used && (
                      <div className="bg-gray-950/40 p-4 rounded-xl border border-white/5 space-y-2">
                        <h4 className="text-xs font-bold font-mono text-vajra-purple tracking-wider flex items-center gap-2 uppercase">
                          <BookOpen className="w-4 h-4" />
                          Entities Invoked
                        </h4>
                        <p className="text-xs text-gray-300 leading-relaxed font-serif">
                          {currentNarrative.entities_used}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )
            ) : (
              <div className="bg-gray-950/20 border border-dashed border-white/10 rounded-xl p-12 flex flex-col items-center justify-center min-h-[450px] text-center space-y-4">
                <div className="relative">
                  <div className="absolute inset-0 bg-cyan-500/10 blur-xl rounded-full scale-150 animate-pulse" />
                  <Compass className="w-16 h-16 text-vajra-cyan/40 animate-spin" style={{ animationDuration: '20s' }} />
                </div>
                <div className="max-w-md space-y-2">
                  <h3 className="text-lg font-bold text-white font-mono">AWAITING NARRATIVE BEACON</h3>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Select coordinates, active settings, and translation languages on the left, then trigger the stream to invoke the blessing sutra.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        // ==========================================
        //         UNIVERSE MANAGER SCREEN
        // ==========================================
        <div className="space-y-6">
          {/* Sub tabs */}
          <div className="flex border-b border-white/10 gap-4">
            <button
              onClick={() => { setUniverseSubTab('realms'); audioFeedback.playClick(); }}
              className={`pb-2 text-sm font-semibold border-b-2 transition-all ${
                universeSubTab === 'realms' ? 'border-vajra-cyan text-white' : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              Realms & Places ({realms.length})
            </button>
            <button
              onClick={() => { setUniverseSubTab('characters'); audioFeedback.playClick(); }}
              className={`pb-2 text-sm font-semibold border-b-2 transition-all ${
                universeSubTab === 'characters' ? 'border-vajra-cyan text-white' : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              Esoteric Characters ({characters.length})
            </button>
            <button
              onClick={() => { setUniverseSubTab('populations'); audioFeedback.playClick(); }}
              className={`pb-2 text-sm font-semibold border-b-2 transition-all ${
                universeSubTab === 'populations' ? 'border-vajra-cyan text-white' : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              Target Populations ({populations.length})
            </button>
          </div>

          {/* REALMS SECTION */}
          {universeSubTab === 'realms' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-base font-bold text-white">Esoteric Realms and Sacred Sites</h3>
                <button
                  onClick={() => {
                    setEditingRealmId(null);
                    setRealmForm({
                      name: '', description: '', location_type: 'metaphysical_realm', source_type: 'manual',
                      is_metaphysical: true, latitude: 0.0, longitude: 0.0, celestial_coordinates: '',
                      dimension_frequency: 528.0, realm_governor: '', astrological_anchor: '', elemental_affinity: '',
                      priority: 5, notes: ''
                    });
                    setShowCreateRealm(!showCreateRealm);
                    audioFeedback.playClick();
                  }}
                  className="bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-1"
                >
                  {showCreateRealm ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                  {showCreateRealm ? 'Close Form' : 'New Realm'}
                </button>
              </div>

              {/* Realm Form */}
              {showCreateRealm && (
                <div className="bg-gray-950/60 p-5 rounded-xl border border-white/10 space-y-4">
                  <h4 className="text-xs font-bold text-white font-mono uppercase">{editingRealmId ? 'Edit Location' : 'Define New Location'}</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Name</label>
                      <input type="text" value={realmForm.name} onChange={(e) => setRealmForm({...realmForm, name: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="e.g. Mount Kailash" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Type</label>
                      <select value={realmForm.location_type} onChange={(e) => setRealmForm({...realmForm, location_type: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10">
                        {locationTypes.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                      </select>
                    </div>
                    <div className="flex items-center pt-5">
                      <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-gray-300">
                        <input type="checkbox" checked={realmForm.is_metaphysical} onChange={(e) => setRealmForm({...realmForm, is_metaphysical: e.target.checked})} className="w-3.5 h-3.5 rounded" />
                        Is Metaphysical Realm? (No Earth coordinates)
                      </label>
                    </div>

                    {!realmForm.is_metaphysical ? (
                      <>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Latitude</label>
                          <input type="number" step="0.0001" value={realmForm.latitude} onChange={(e) => setRealmForm({...realmForm, latitude: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Longitude</label>
                          <input type="number" step="0.0001" value={realmForm.longitude} onChange={(e) => setRealmForm({...realmForm, longitude: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Timezone</label>
                          <input type="text" value={realmForm.timezone} onChange={(e) => setRealmForm({...realmForm, timezone: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" />
                        </div>
                      </>
                    ) : (
                      <>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Celestial Coordinates</label>
                          <input type="text" value={realmForm.celestial_coordinates} onChange={(e) => setRealmForm({...realmForm, celestial_coordinates: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="e.g. Northern Axis" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Dimension Frequency (Hz)</label>
                          <input type="number" step="0.1" value={realmForm.dimension_frequency} onChange={(e) => setRealmForm({...realmForm, dimension_frequency: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" />
                        </div>
                        <div />
                      </>
                    )}

                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Realm Governor</label>
                      <input type="text" value={realmForm.realm_governor} onChange={(e) => setRealmForm({...realmForm, realm_governor: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="Ruler/Deity name" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Astrological Anchor</label>
                      <input type="text" value={realmForm.astrological_anchor} onChange={(e) => setRealmForm({...realmForm, astrological_anchor: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="e.g. Saturn Conjunct Midheaven" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Elemental Affinity</label>
                      <input type="text" value={realmForm.elemental_affinity} onChange={(e) => setRealmForm({...realmForm, elemental_affinity: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="e.g. Aether" />
                    </div>

                    <div className="md:col-span-3">
                      <label className="block text-xs text-gray-400 mb-1">Description</label>
                      <textarea value={realmForm.description} onChange={(e) => setRealmForm({...realmForm, description: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 resize-none" rows="2" />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={saveRealm} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-xs font-bold">Save Setting</button>
                    <button onClick={() => setShowCreateRealm(false)} className="bg-gray-800 text-gray-300 px-4 py-2 rounded text-xs font-bold">Cancel</button>
                  </div>
                </div>
              )}

              {/* Realms Filters */}
              <div className="flex flex-wrap items-center gap-3 bg-gray-950/40 p-3 rounded-lg border border-white/5">
                <div className="relative flex-1 min-w-[180px] max-w-sm">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                  <input
                    type="text"
                    value={realmSearch}
                    onChange={(e) => setRealmSearch(e.target.value)}
                    placeholder="Search realms..."
                    className="w-full bg-black/40 text-white rounded pl-8 pr-3 py-1.5 text-xs border border-white/10 focus:border-cyan-500/50 outline-none transition-colors"
                  />
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {['all', 'earthly_sacred', 'metaphysical_realm', 'cosmic_anchor', 'historical_academy'].map(t => (
                    <button
                      key={t}
                      onClick={() => { setRealmTypeFilter(t); audioFeedback.playClick(); }}
                      className={`px-2 py-1 rounded text-[10px] font-semibold transition-all ${
                        realmTypeFilter === t
                          ? 'bg-cyan-600 text-white'
                          : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                      }`}
                    >
                      {t === 'all' ? 'All Types' : t.replace(/_/g, ' ')}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-1.5 ml-auto">
                  <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  <select
                    value={realmSort}
                    onChange={(e) => setRealmSort(e.target.value)}
                    className="bg-black/40 text-white rounded px-2 py-1 text-[10px] border border-white/10 outline-none"
                  >
                    <option value="name">Name</option>
                    <option value="priority">Priority</option>
                    <option value="featured">Most Featured</option>
                  </select>
                </div>
                <span className="text-[10px] text-gray-500 ml-1">
                  {filteredRealms.length} of {realms.length} realms
                </span>
              </div>

              {/* Realms List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredRealms.map(r => {
                  const isActiveRealm = r.id === selectedRealmId;
                  return (
                  <div key={r.id} className={`bg-gray-900/60 p-4 rounded-xl border space-y-3 relative group transition-colors ${isActiveRealm ? 'border-cyan-500/50 ring-1 ring-cyan-500/20' : 'border-white/5'}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="text-sm font-bold text-white">{r.name}</h4>
                        <span className="text-[9px] bg-cyan-950 text-cyan-400 px-1.5 py-0.5 rounded font-mono uppercase mt-1 inline-block">
                          {r.location_type.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => {
                            setSelectedRealmId(isActiveRealm ? '' : r.id);
                            audioFeedback.playClick();
                          }}
                          className={`px-2 py-1 rounded text-[10px] font-semibold transition-all ${
                            isActiveRealm
                              ? 'bg-cyan-600 text-white'
                              : 'bg-cyan-950/30 text-cyan-400 hover:bg-cyan-600 hover:text-white opacity-0 group-hover:opacity-100'
                          }`}
                        >
                          {isActiveRealm ? '📍 Active Setting' : '📍 Set as Setting'}
                        </button>
                        <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all">
                        <button
                          onClick={() => {
                            setEditingRealmId(r.id);
                            setRealmForm({ ...r });
                            setShowCreateRealm(true);
                            audioFeedback.playClick();
                          }}
                          className="bg-blue-600/30 hover:bg-blue-600 text-white p-1.5 rounded"
                          title="Edit"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteRealm(r.id)}
                          className="bg-red-600/30 hover:bg-red-600 text-white p-1.5 rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      </div>
                    </div>
                    <p className="text-xs text-gray-400 leading-relaxed font-serif">{r.description}</p>
                    {/* Realm Tags */}
                    {(r.tags || []).length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {(r.tags || []).map(t => (
                          <span key={t} className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-cyan-950/40 text-cyan-400">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-500 font-mono border-t border-white/5 pt-2">
                      <div>Governor: <span className="text-gray-300">{r.realm_governor || 'None'}</span></div>
                      <div>Astro Anchor: <span className="text-gray-300">{r.astrological_anchor || 'Dynamic'}</span></div>
                      {r.is_metaphysical ? (
                        <>
                          <div>Frequency: <span className="text-gray-300">{r.dimension_frequency} Hz</span></div>
                          <div>Sky Coord: <span className="text-gray-300">{r.celestial_coordinates || 'Uncharted'}</span></div>
                        </>
                      ) : (
                        <>
                          <div>LAT/LON: <span className="text-gray-300">{r.latitude}/{r.longitude}</span></div>
                          <div>TZ: <span className="text-gray-300">{r.timezone}</span></div>
                        </>
                      )}
                      <div>Featured: <span className="text-gray-300">{r.total_narratives_featured} times</span></div>
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* CHARACTERS SECTION */}
          {universeSubTab === 'characters' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-base font-bold text-white">
                  Esoteric Characters & Archetypes
                  <span className="ml-2 text-xs text-gray-500 font-normal font-mono">({filteredCharacters.length}/{characters.length})</span>
                </h3>
                <button
                  onClick={() => {
                    setEditingCharId(null);
                    setCharForm({
                      name: '', role: 'master', description: '', source_type: 'manual', dialogue_style: '',
                      mantra_preference: '', elemental_anchor: 'space', priority: 5, notes: ''
                    });
                    setShowCreateCharacter(!showCreateCharacter);
                    audioFeedback.playClick();
                  }}
                  className="bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-1"
                >
                  {showCreateCharacter ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                  {showCreateCharacter ? 'Close Form' : 'New Character'}
                </button>
              </div>

              {/* Character Form */}
              {showCreateCharacter && (
                <div className="bg-gray-950/60 p-5 rounded-xl border border-white/10 space-y-4">
                  <h4 className="text-xs font-bold text-white font-mono uppercase">{editingCharId ? 'Modify Character' : 'Create Character Archetype'}</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Name</label>
                      <input type="text" value={charForm.name} onChange={(e) => setCharForm({...charForm, name: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="e.g. Zen Master Zhao" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Role</label>
                      <select value={charForm.role} onChange={(e) => setCharForm({...charForm, role: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10">
                        {roles.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Dialogue Style</label>
                      <input type="text" value={charForm.dialogue_style} onChange={(e) => setCharForm({...charForm, dialogue_style: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="e.g. riddle-like, Zen Koans" />
                    </div>

                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Mantra Preference</label>
                      <input type="text" value={charForm.mantra_preference} onChange={(e) => setCharForm({...charForm, mantra_preference: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="om_mani_padme_hum" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Elemental Anchor</label>
                      <input type="text" value={charForm.elemental_anchor} onChange={(e) => setCharForm({...charForm, elemental_anchor: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10" placeholder="space" />
                    </div>
                    <div />

                    <div className="md:col-span-3">
                      <label className="block text-xs text-gray-400 mb-1">Description</label>
                      <textarea value={charForm.description} onChange={(e) => setCharForm({...charForm, description: e.target.value})} className="w-full bg-black/40 text-white rounded px-2.5 py-1.5 text-xs border border-white/10 resize-none" rows="2" />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={saveCharacter} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-xs font-bold">Summon Character</button>
                    <button onClick={() => setShowCreateCharacter(false)} className="bg-gray-800 text-gray-300 px-4 py-2 rounded text-xs font-bold">Cancel</button>
                  </div>
                </div>
              )}

              {/* Characters Filters */}
              <div className="flex flex-wrap items-center gap-3 bg-gray-950/40 p-3 rounded-lg border border-white/5">
                <div className="relative flex-1 min-w-[180px] max-w-sm">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                  <input
                    type="text"
                    value={charSearch}
                    onChange={(e) => setCharSearch(e.target.value)}
                    placeholder="Search by name, description, tags..."
                    className="w-full bg-black/40 text-white rounded pl-8 pr-3 py-1.5 text-xs border border-white/10 focus:border-purple-500/50 outline-none transition-colors"
                  />
                </div>
                <div className="flex gap-1.5 flex-wrap items-center">
                  <Filter className="w-3 h-3 text-gray-500" />
                  {charTraditionTags.map(t => (
                    <button
                      key={t}
                      onClick={() => { setCharTraditionFilter(t); audioFeedback.playClick(); }}
                      className={`px-2 py-1 rounded text-[10px] font-semibold transition-all capitalize ${
                        charTraditionFilter === t
                          ? 'bg-purple-600 text-white'
                          : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                      }`}
                    >
                      {t === 'all' ? '🌐 All' : t === 'taoist' ? '☯️ Taoist' : t === 'buddhist' ? '📿 Buddhist' : t === 'folk' ? '🏮 Folk' : t === 'creation' ? '🪐 Creation' : t === 'legendary' ? '⚔️ Legendary' : t}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-1.5">
                  <select
                    value={charRoleFilter}
                    onChange={(e) => setCharRoleFilter(e.target.value)}
                    className="bg-black/40 text-white rounded px-2 py-1 text-[10px] border border-white/10 outline-none"
                  >
                    <option value="all">All Roles</option>
                    {roles.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                  </select>
                  <select
                    value={charSort}
                    onChange={(e) => setCharSort(e.target.value)}
                    className="bg-black/40 text-white rounded px-2 py-1 text-[10px] border border-white/10 outline-none"
                  >
                    <option value="name">Name</option>
                    <option value="role">Role</option>
                    <option value="priority">Priority</option>
                    <option value="featured">Most Featured</option>
                  </select>
                </div>
                <span className="text-[10px] text-gray-500 ml-1">
                  {filteredCharacters.length} of {characters.length} characters
                </span>
              </div>

              {/* Characters List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredCharacters.map(c => {
                  const isSelected = selectedCharIds.includes(c.id);
                  return (
                  <div key={c.id} className={`bg-gray-900/60 p-4 rounded-xl border space-y-3 relative group transition-colors ${isSelected ? 'border-purple-500/50 ring-1 ring-purple-500/20' : 'border-white/5'}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="text-sm font-bold text-white">{c.name}</h4>
                        <span className="text-[9px] bg-purple-950 text-purple-400 px-1.5 py-0.5 rounded font-mono uppercase mt-1 inline-block">
                          {c.role}
                        </span>
                      </div>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => {
                            setSelectedCharIds(prev =>
                              isSelected ? prev.filter(id => id !== c.id) : [...prev, c.id]
                            );
                            audioFeedback.playClick();
                          }}
                          className={`px-2 py-1 rounded text-[10px] font-semibold transition-all ${
                            isSelected
                              ? 'bg-purple-600 text-white'
                              : 'bg-purple-950/30 text-purple-400 hover:bg-purple-600 hover:text-white opacity-0 group-hover:opacity-100'
                          }`}
                        >
                          {isSelected ? '✓ Added' : '👤 Add to Narrative'}
                        </button>
                        <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all">
                        <button
                          onClick={() => {
                            setEditingCharId(c.id);
                            setCharForm({ ...c });
                            setShowCreateCharacter(true);
                            audioFeedback.playClick();
                          }}
                          className="bg-blue-600/30 hover:bg-blue-600 text-white p-1.5 rounded"
                          title="Edit"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteCharacter(c.id)}
                          className="bg-red-600/30 hover:bg-red-600 text-white p-1.5 rounded"
                          title="Exile"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      </div>
                    </div>
                    <p className="text-xs text-gray-400 leading-relaxed font-serif">{c.description}</p>
                    {/* Tags */}
                    {(c.tags || []).length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {(c.tags || []).map(t => (
                          <span
                            key={t}
                            onClick={() => { setCharTraditionFilter(t); setCharSearch(''); audioFeedback.playClick(); }}
                            className={`px-1.5 py-0.5 rounded text-[9px] font-semibold cursor-pointer transition-colors ${
                              t === 'taoist' ? 'bg-amber-950/60 text-amber-400 hover:bg-amber-900/60' :
                              t === 'buddhist' ? 'bg-orange-950/60 text-orange-400 hover:bg-orange-900/60' :
                              t === 'folk' ? 'bg-red-950/60 text-red-400 hover:bg-red-900/60' :
                              t === 'creation' ? 'bg-indigo-950/60 text-indigo-400 hover:bg-indigo-900/60' :
                              t === 'hero' ? 'bg-emerald-950/60 text-emerald-400 hover:bg-emerald-900/60' :
                              t === 'deity' ? 'bg-violet-950/60 text-violet-400 hover:bg-violet-900/60' :
                              t === 'guardian' ? 'bg-cyan-950/60 text-cyan-400 hover:bg-cyan-900/60' :
                              t === 'feminine-divine' ? 'bg-pink-950/60 text-pink-400 hover:bg-pink-900/60' :
                              'bg-gray-800 text-gray-400 hover:bg-gray-700'
                            }`}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-500 font-mono border-t border-white/5 pt-2">
                      <div>Dialogue: <span className="text-gray-300">{c.dialogue_style?.slice(0, 28)}{(c.dialogue_style || '').length > 28 ? '…' : ''}</span></div>
                      <div>Mantra: <span className="text-gray-300 font-mono text-[9px]">{c.mantra_preference || '—'}</span></div>
                      <div>Element: <span className="text-gray-300">{c.elemental_anchor}</span></div>
                      <div>Featured: <span className="text-gray-300">{c.total_narratives_featured || 0}×</span></div>
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* POPULATIONS LIST (READ ONLY REDIRECT VIEW) */}
          {universeSubTab === 'populations' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-base font-bold text-white">Active Beneficiary Populations</h3>
                <span className="text-xs text-gray-500">To edit populations, navigate to the main Broadcast tab.</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {populations.map(p => (
                  <div key={p.id} className="bg-gray-900/60 p-4 rounded-xl border border-white/5 space-y-2">
                    <div className="flex justify-between items-center">
                      <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                        {p.name}
                        {p.is_urgent && <span className="text-red-400">🔥</span>}
                      </h4>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${p.is_active ? 'bg-green-950 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                        {p.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 font-serif leading-relaxed">{p.description}</p>
                    <div className="grid grid-cols-2 gap-1 text-[10px] text-gray-500 font-mono pt-1">
                      <div>Intentions: <span className="text-gray-300">{p.intentions.join(', ')}</span></div>
                      <div>Category: <span className="text-gray-300">{p.category}</span></div>
                      <div>Priority: <span className="text-gray-300">{p.priority}/10</span></div>
                      <div>Mantra: <span className="text-gray-300 font-mono">{p.mantra_preference}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
