/**
 * Grimoire Panel — esoteric correspondence reference browser.
 * Displays planetary, elemental, colour, herbal, and crystal
 * correspondences from the Grimoire service.
 * @component
 */
import React, { useState, useEffect } from 'react';
import { BookOpen, Search, Sparkles, RefreshCw, Compass, Moon, Sun, Layers, HelpCircle, ArrowRight, Clock } from 'lucide-react';
import DharmaTales from './DharmaTales';
import { audioFeedback } from '../../utils/audioFeedback';

import { API_BASE } from '../../utils/api';

export default function GrimoirePanel() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activePlanetDetails, setActivePlanetDetails] = useState(null);

  // Default planetary records
  const defaultPlanets = [
    { key: 'sun', name: 'Sun', color: 'border-yellow-500/30 text-yellow-400 text-shadow-yellow' },
    { key: 'moon', name: 'Moon', color: 'border-cyan-500/30 text-cyan-400 text-shadow-cyan' },
    { key: 'mercury', name: 'Mercury', color: 'border-teal-500/30 text-teal-400 text-shadow-teal' },
    { key: 'venus', name: 'Venus', color: 'border-pink-500/30 text-pink-400 text-shadow-pink' },
    { key: 'mars', name: 'Mars', color: 'border-red-500/30 text-red-400 text-shadow-red' },
    { key: 'jupiter', name: 'Jupiter', color: 'border-purple-500/30 text-purple-400 text-shadow-purple' },
    { key: 'saturn', name: 'Saturn', color: 'border-indigo-500/30 text-indigo-400 text-shadow-indigo' }
  ];

  useEffect(() => {
    // Run empty search to fetch all initial results
    handleSearch('');
  }, []);

  const handleSearch = async (query) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/divination/grimoire/search?query=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
        if (data.results && data.results.length > 0) {
          // Default selection to first result
          setActivePlanetDetails(data.results[0]);
        }
      }
    } catch (e) {
      console.error("Grimoire search failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    audioFeedback.playTelemetry();
    handleSearch(searchQuery);
  };

  const selectPlanet = (planetData) => {
    audioFeedback.playClick();
    setActivePlanetDetails(planetData);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
      
      {/* Title Header */}
      <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 border border-white/10 rounded-xl p-5">
        <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
          <BookOpen className="w-7 h-7 text-purple-400 animate-pulse" />
          The Esoteric Grimoire & Correspondences Library
        </h2>
        <p className="text-xs text-purple-200 mt-1">
          Explore cosmological rate connections, planetary hour alignments, sacred minerals, and contemplate teaching parables.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* ================= COLUMN 1 & 2: DATABASE SEARCH ================= */}
        <div className="xl:col-span-2 space-y-6 flex flex-col">
          
          {/* Search Bar Form */}
          <form onSubmit={handleSearchSubmit} className="bg-gray-900/60 p-4 rounded-xl border border-white/10 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  audioFeedback.playType();
                }}
                placeholder="Search correspondences (e.g. Lavender, Lapis Lazuli, Copper, Heart)..."
                className="w-full bg-gray-950 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-all font-sans"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center gap-2 select-none"
            >
              {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Search Grimoire'}
            </button>
          </form>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1">
            
            {/* Planetary Quick Links sidebar */}
            <div className="bg-gray-900/60 p-4 rounded-xl border border-white/10 space-y-4 max-h-[480px] overflow-y-auto">
              <h3 className="text-xs font-bold font-mono text-gray-400 tracking-wider">COSMOLOGICAL PLANETS</h3>
              <div className="flex flex-col gap-2">
                {defaultPlanets.map(p => {
                  const isActive = activePlanetDetails?.planet.toLowerCase() === p.key;
                  return (
                    <button
                      key={p.key}
                      onClick={() => {
                        const match = results.find(r => r.planet.toLowerCase() === p.key);
                        if (match) selectPlanet(match);
                        else selectPlanet({ planet: p.name, minerals: [], herbs: [], rates: [], influence: 'Custom Node' });
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-left text-xs font-semibold uppercase tracking-wider transition-all duration-300 ${
                        isActive
                          ? 'bg-purple-950/60 border-purple-500 text-white shadow-[0_0_8px_rgba(168,85,247,0.3)]'
                          : 'bg-white/5 border-transparent text-gray-400 hover:text-white hover:bg-white/10'
                      }`}
                    >
                      <span>{p.name}</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-50" />
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Correspondence details main card */}
            <div className="md:col-span-2 bg-gray-900/60 p-5 rounded-xl border border-white/10 flex flex-col justify-between shadow-2xl min-h-[380px]">
              {activePlanetDetails ? (
                <div className="space-y-6">
                  <div className="border-b border-white/5 pb-3">
                    <div className="flex justify-between items-center">
                      <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        🪐 {activePlanetDetails.planet} Correspondences
                      </h3>
                      <span className="text-xs px-2.5 py-0.5 font-mono bg-purple-950 text-purple-300 border border-purple-500/20 rounded-full font-semibold uppercase">
                        {activePlanetDetails.chakra} Chakra
                      </span>
                    </div>
                    <p className="text-xs text-purple-300 italic mt-1 leading-relaxed">
                      "{activePlanetDetails.influence}"
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    
                    {/* Minerals & Crystals */}
                    <div className="space-y-3 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-purple-500/20 transition-colors">
                      <span className="text-[10px] font-mono text-gray-400 block uppercase flex items-center gap-1.5">
                        💎 Sacred Minerals & Crystals
                      </span>
                      <ul className="list-disc pl-4 space-y-1.5 text-gray-200">
                        {activePlanetDetails.minerals?.map(m => <li key={m}>{m}</li>)}
                        {(!activePlanetDetails.minerals || activePlanetDetails.minerals.length === 0) && <li className="text-gray-500 italic">None catalogued</li>}
                      </ul>
                      {/* Crystal grid recommendation */}
                      {activePlanetDetails.minerals?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-white/5">
                          <span className="text-[8px] text-purple-400/70 uppercase tracking-wider">Grid Layout</span>
                          <p className="text-[9px] text-gray-400 mt-0.5">
                            Arrange in a {activePlanetDetails.planet?.toLowerCase() === 'moon' ? 'crescent' : 'hexagonal'} pattern during {activePlanetDetails.planet} hour for maximum resonance.
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Herbs & Resins */}
                    <div className="space-y-3 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-emerald-500/20 transition-colors">
                      <span className="text-[10px] font-mono text-gray-400 block uppercase flex items-center gap-1.5">
                        🌿 Aligned Herbs & Resins
                      </span>
                      <ul className="list-disc pl-4 space-y-1.5 text-gray-200">
                        {activePlanetDetails.herbs?.map(h => <li key={h}>{h}</li>)}
                        {(!activePlanetDetails.herbs || activePlanetDetails.herbs.length === 0) && <li className="text-gray-500 italic">None catalogued</li>}
                      </ul>
                      {/* Ritual use hint */}
                      {activePlanetDetails.herbs?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-white/5">
                          <span className="text-[8px] text-emerald-400/70 uppercase tracking-wider">Ritual Use</span>
                          <p className="text-[9px] text-gray-400 mt-0.5">
                            Burn as offering or infuse in anointing oil before {activePlanetDetails.planet} hour operations.
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Radionics Rates */}
                    <div className="space-y-3 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-cyan-500/20 transition-colors">
                      <span className="text-[10px] font-mono text-gray-400 block uppercase flex items-center gap-1.5">
                        ⚡ Radionics Tuning Rates
                      </span>
                      <div className="flex gap-2 flex-wrap mt-1">
                        {activePlanetDetails.rates?.map(r => (
                          <span key={r} className="px-2 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-500/20 rounded font-mono text-xs font-bold hover:bg-cyan-900 hover:border-cyan-400/40 transition-colors cursor-default">
                            {r}
                          </span>
                        ))}
                        {(!activePlanetDetails.rates || activePlanetDetails.rates.length === 0) && <span className="text-gray-500 italic">None calibrated</span>}
                      </div>
                      {/* Rate usage guidance */}
                      {activePlanetDetails.rates?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-white/5">
                          <span className="text-[8px] text-cyan-400/70 uppercase tracking-wider">Broadcast Guidance</span>
                          <p className="text-[9px] text-gray-400 mt-0.5">
                            Set dials to these rates during {activePlanetDetails.planet} planetary hours for amplified resonance.
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Alchemical Metal + Element */}
                    <div className="space-y-3 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-amber-500/20 transition-colors">
                      <span className="text-[10px] font-mono text-gray-400 block uppercase flex items-center gap-1.5">
                        ⚗️ Alchemical Correspondences
                      </span>
                      <div className="space-y-2">
                        <div>
                          <span className="text-[8px] text-gray-500 uppercase">Linked Metal</span>
                          <span className="text-sm font-bold text-white block mt-0.5">{activePlanetDetails.metal || 'N/A'}</span>
                        </div>
                        {activePlanetDetails.element && (
                          <div>
                            <span className="text-[8px] text-gray-500 uppercase">Element</span>
                            <span className="text-sm font-bold text-amber-300 block mt-0.5">{activePlanetDetails.element}</span>
                          </div>
                        )}
                        {activePlanetDetails.chakra && (
                          <div>
                            <span className="text-[8px] text-gray-500 uppercase">Chakra Resonance</span>
                            <span className="text-sm font-bold text-purple-300 block mt-0.5">{activePlanetDetails.chakra}</span>
                          </div>
                        )}
                      </div>
                    </div>

                  </div>

                  {/* Ritual Timing Recommendation */}
                  <div className="bg-gradient-to-r from-purple-950/20 to-indigo-950/20 rounded-lg border border-purple-500/15 p-3.5">
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-3.5 h-3.5 text-purple-400" />
                      <span className="text-[10px] font-mono text-purple-300 uppercase tracking-wider">Ritual Timing</span>
                    </div>
                    <p className="text-[10px] text-gray-400 leading-relaxed">
                      For optimal {activePlanetDetails.planet} operations, work during the {activePlanetDetails.planet} planetary hour
                      {activePlanetDetails.day ? ` on ${activePlanetDetails.day}` : ''}.
                      {activePlanetDetails.moon_phase ? ` The ${activePlanetDetails.moon_phase} Moon phase amplifies results.` : ''}
                      {!activePlanetDetails.day && !activePlanetDetails.moon_phase && ' Use the planetary hours calculator in the Cosmic Clock tab to find the next auspicious window.'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-24 text-gray-500 italic text-xs flex-1 flex items-center justify-center">
                  Select a planetary node or type in the search bar above to query correspondences.
                </div>
              )}
            </div>

          </div>

        </div>

        {/* ================= COLUMN 3: DHARMA WISDOM PARABLES ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 shadow-2xl">
          <DharmaTales />
        </div>

      </div>

    </div>
  );
}
