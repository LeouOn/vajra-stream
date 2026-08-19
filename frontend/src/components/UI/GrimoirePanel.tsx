/**
 * Grimoire Panel — multi-corpus esoteric knowledge and learning reference hub.
 * Displays planetary correspondences, Tarot codex, I Ching book of changes,
 * mantras, dharanis, sutras, and healing frequencies from the Grimoire service.
 * @component
 */
import React, { useState, useEffect, useMemo } from 'react';
import { apiUrl } from '../../utils/api';
import {
  BookOpen,
  Search,
  Sparkles,
  RefreshCw,
  Clock,
  ArrowRight,
  Layers,
  GraduationCap,
  Volume2,
  Copy,
  Check,
  Zap,
} from 'lucide-react';
import { message, Tabs, Tag } from 'antd';
import DharmaTales from './DharmaTales';
import EsotericTutor from './EsotericTutor';
import { audioFeedback } from '../../utils/audioFeedback';
import { createLogger } from '../../utils/logger';

export interface GrimoireItem {
  id: string;
  category: 'planets' | 'tarot' | 'iching' | 'mantras' | 'sutras' | 'frequencies' | string;
  title: string;
  subtitle: string;
  description: string;
  keywords?: string[];
  chakra?: string;
  element?: string;
  planet?: string;
  metal?: string;
  minerals?: string[];
  herbs?: string[];
  rates?: (number | string)[];
  frequencies?: number[];
  archetypes?: string[];
  day?: string;
  moon_phase?: string;
  details?: Record<string, unknown>;
}

interface CategoryInfo {
  key: string;
  name: string;
  icon: string;
  count: number;
  description: string;
}

const CATEGORY_PILLS = [
  { key: 'all', label: 'All Knowledge', icon: '🌟' },
  { key: 'planets', label: 'Planets', icon: '🪐' },
  { key: 'tarot', label: 'Tarot Codex', icon: '🃏' },
  { key: 'iching', label: 'I Ching', icon: '☯️' },
  { key: 'mantras', label: 'Mantras', icon: '📿' },
  { key: 'sutras', label: 'Sutras', icon: '📜' },
  { key: 'frequencies', label: 'Frequencies', icon: '💎' },
];

const GrimoirePanel: React.FC = () => {
  const log = createLogger('GrimoirePanel');
  const [activeTab, setActiveTab] = useState<'explorer' | 'tutor' | 'parables'>('explorer');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [items, setItems] = useState<GrimoireItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeItem, setActiveItem] = useState<GrimoireItem | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchGrimoire(searchQuery, selectedCategory);
  }, [selectedCategory]);

  const fetchGrimoire = async (query: string, category: string) => {
    setLoading(true);
    try {
      const catParam = category && category !== 'all' ? `&category=${encodeURIComponent(category)}` : '';
      const res = await fetch(apiUrl(`/divination/grimoire/search?query=${encodeURIComponent(query)}${catParam}`));
      if (res.ok) {
        const data = await res.json();
        const results: GrimoireItem[] = data.results || [];
        setItems(results);
        if (results.length > 0) {
          // If current selection is still in list keep it, otherwise pick first
          setActiveItem((prev) => {
            if (prev) {
              const existing = results.find((r) => r.id === prev.id);
              if (existing) return existing;
            }
            return results[0];
          });
        } else {
          setActiveItem(null);
        }
      }
    } catch (e) {
      log.error('Grimoire search failed:', e);
      message.error('Could not search grimoire: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    audioFeedback.playTelemetry();
    fetchGrimoire(searchQuery, selectedCategory);
  };

  const selectItem = (item: GrimoireItem) => {
    audioFeedback.playClick();
    setActiveItem(item);
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    audioFeedback.playTelemetry();
    setCopiedKey(key);
    message.success(`Copied: ${text}`);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Helper for rendering item details
  const renderItemDetails = () => {
    if (!activeItem) {
      return (
        <div className="text-center py-28 text-gray-500 italic text-xs flex flex-col items-center justify-center gap-2">
          <BookOpen className="w-8 h-8 text-gray-600 animate-pulse" />
          <span>Select an item from the library or type in the search bar above.</span>
        </div>
      );
    }

    const { category, details = {} } = activeItem;

    return (
      <div className="space-y-6">
        {/* Header summary */}
        <div className="border-b border-white/10 pb-4">
          <div className="flex flex-wrap justify-between items-start gap-2">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                {activeItem.title}
              </h3>
              <p className="text-xs text-purple-300 mt-1 font-mono">{activeItem.subtitle}</p>
            </div>
            <div className="flex gap-2">
              <span className="text-[10px] px-2.5 py-1 font-mono bg-purple-950 text-purple-300 border border-purple-500/20 rounded-full font-semibold uppercase">
                {category}
              </span>
              {activeItem.chakra && (
                <span className="text-[10px] px-2.5 py-1 font-mono bg-cyan-950 text-cyan-300 border border-cyan-500/20 rounded-full font-semibold uppercase">
                  {activeItem.chakra}
                </span>
              )}
            </div>
          </div>
          {activeItem.description && (
            <p className="text-xs text-gray-300 italic mt-3 leading-relaxed bg-white/5 p-3 rounded-lg border border-white/5">
              "{activeItem.description}"
            </p>
          )}
        </div>

        {/* ================= PLANET VIEW ================= */}
        {category === 'planets' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            {/* Minerals */}
            <div className="space-y-2 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-purple-500/20 transition-colors">
              <span className="text-[10px] font-mono text-purple-300 uppercase flex items-center gap-1.5 font-bold">
                💎 Sacred Minerals & Crystals
              </span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {activeItem.minerals?.map((m) => (
                  <span key={m} className="px-2 py-0.5 bg-purple-950/60 text-purple-200 border border-purple-500/30 rounded text-[11px]">
                    {m}
                  </span>
                ))}
              </div>
            </div>

            {/* Herbs */}
            <div className="space-y-2 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-emerald-500/20 transition-colors">
              <span className="text-[10px] font-mono text-emerald-300 uppercase flex items-center gap-1.5 font-bold">
                🌿 Aligned Herbs & Resins
              </span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {activeItem.herbs?.map((h) => (
                  <span key={h} className="px-2 py-0.5 bg-emerald-950/60 text-emerald-200 border border-emerald-500/30 rounded text-[11px]">
                    {h}
                  </span>
                ))}
              </div>
            </div>

            {/* Radionics Rates */}
            <div className="space-y-2 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-cyan-500/20 transition-colors">
              <span className="text-[10px] font-mono text-cyan-300 uppercase flex items-center justify-between font-bold">
                <span className="flex items-center gap-1.5">⚡ Radionics Tuning Rates</span>
                <span className="text-[9px] text-gray-400 font-normal">Click to copy</span>
              </span>
              <div className="flex gap-2 flex-wrap mt-1">
                {activeItem.rates?.map((r) => (
                  <button
                    key={String(r)}
                    type="button"
                    onClick={() => copyToClipboard(String(r), `rate-${r}`)}
                    className="px-2.5 py-1 bg-cyan-950 text-cyan-300 border border-cyan-500/30 hover:border-cyan-400 hover:bg-cyan-900 rounded font-mono text-xs font-bold transition-all flex items-center gap-1.5"
                  >
                    <span>{r}</span>
                    {copiedKey === `rate-${r}` ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-2.5 h-2.5 opacity-50" />}
                  </button>
                ))}
              </div>
            </div>

            {/* Frequencies & Metal */}
            <div className="space-y-2 bg-white/5 p-3.5 rounded-lg border border-white/5 hover:border-amber-500/20 transition-colors">
              <span className="text-[10px] font-mono text-amber-300 uppercase flex items-center gap-1.5 font-bold">
                ⚗️ Alchemical Correspondences
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-[9px] text-gray-500 block">Metal:</span>
                  <span className="text-white font-semibold">{activeItem.metal || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-[9px] text-gray-500 block">Element:</span>
                  <span className="text-amber-300 font-semibold">{activeItem.element || 'N/A'}</span>
                </div>
                {activeItem.frequencies && activeItem.frequencies.length > 0 && (
                  <div className="col-span-2 mt-1">
                    <span className="text-[9px] text-gray-500 block">Harmonic Frequencies:</span>
                    <span className="text-cyan-400 font-mono font-bold">{activeItem.frequencies.map((f) => `${f} Hz`).join(' · ')}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Ritual Timing */}
            <div className="sm:col-span-2 bg-gradient-to-r from-purple-950/30 to-indigo-950/30 rounded-lg border border-purple-500/20 p-3.5">
              <div className="flex items-center gap-2 mb-1.5">
                <Clock className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-[10px] font-mono text-purple-300 uppercase tracking-wider font-bold">Ritual Timing Recommendation</span>
              </div>
              <p className="text-[11px] text-gray-300 leading-relaxed">
                For optimal {activeItem.planet} operations, conduct broadcasts or meditations during the {activeItem.planet} planetary hour
                {activeItem.day ? ` on ${activeItem.day}` : ''}.
                {activeItem.moon_phase ? ` The ${activeItem.moon_phase} amplifies alignment.` : ''}
              </p>
            </div>
          </div>
        )}

        {/* ================= TAROT VIEW ================= */}
        {category === 'tarot' && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white/5 p-3.5 rounded-lg border border-white/5">
                <span className="text-[10px] font-mono text-yellow-300 uppercase block font-bold mb-1">
                  ☀️ Upright Interpretation
                </span>
                <p className="text-gray-200 text-[11px] leading-relaxed">
                  {String(details.upright || activeItem.description)}
                </p>
              </div>
              <div className="bg-white/5 p-3.5 rounded-lg border border-white/5">
                <span className="text-[10px] font-mono text-red-300 uppercase block font-bold mb-1">
                  🌑 Reversed Interpretation
                </span>
                <p className="text-gray-200 text-[11px] leading-relaxed">
                  {String(details.reversed || 'Internalized energy, resistance, or transformation of card themes.')}
                </p>
              </div>
            </div>

            {details.desc && (
              <div className="bg-purple-950/20 p-3.5 rounded-lg border border-purple-500/20">
                <span className="text-[10px] font-mono text-purple-300 uppercase block font-bold mb-1">
                  👁️ Symbolism & Archetypal Imagery
                </span>
                <p className="text-gray-300 text-[11px] leading-relaxed">
                  {String(details.desc)}
                </p>
              </div>
            )}

            {activeItem.keywords && activeItem.keywords.length > 0 && (
              <div>
                <span className="text-[10px] font-mono text-gray-400 uppercase block mb-1.5 font-bold">Key Aspects</span>
                <div className="flex flex-wrap gap-1.5">
                  {activeItem.keywords.map((kw) => (
                    <span key={kw} className="px-2.5 py-0.5 bg-white/5 text-gray-300 border border-white/10 rounded-full text-[10px]">
                      #{kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= I CHING VIEW ================= */}
        {category === 'iching' && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white/5 p-3.5 rounded-lg border border-white/5">
                <span className="text-[10px] font-mono text-cyan-300 uppercase block font-bold mb-1">
                  彖 The Judgment
                </span>
                <p className="text-gray-200 text-[11px] leading-relaxed">
                  {String(details.judgment || activeItem.description)}
                </p>
              </div>
              <div className="bg-white/5 p-3.5 rounded-lg border border-white/5">
                <span className="text-[10px] font-mono text-emerald-300 uppercase block font-bold mb-1">
                  象 The Image
                </span>
                <p className="text-gray-200 text-[11px] leading-relaxed">
                  {String(details.image || details.images || 'The movement of the trigrams guides right action.')}
                </p>
              </div>
            </div>

            {Array.isArray(details.lines) && details.lines.length > 0 && (
              <div className="bg-gray-950/60 p-4 rounded-lg border border-white/10 space-y-2">
                <span className="text-[10px] font-mono text-purple-300 uppercase block font-bold">
                  ☯️ Six Moving Line Dynamics
                </span>
                <div className="space-y-1.5 text-[11px]">
                  {details.lines.map((line: string, idx: number) => (
                    <div key={idx} className="flex gap-2 text-gray-300">
                      <span className="text-purple-400 font-mono font-bold">Line {idx + 1}:</span>
                      <span>{line}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= MANTRAS & SUTRAS VIEW ================= */}
        {(category === 'mantras' || category === 'sutras') && (
          <div className="space-y-4 text-xs">
            {details.sanskrit && (
              <div className="bg-white/5 p-3.5 rounded-lg border border-white/5">
                <span className="text-[10px] font-mono text-amber-300 uppercase block font-bold mb-1">
                  Sanskrit / Devanagari Script
                </span>
                <p className="text-white text-sm font-serif">{String(details.sanskrit)}</p>
              </div>
            )}
            {details.passage && (
              <div className="bg-purple-950/20 p-4 rounded-lg border border-purple-500/20 space-y-2">
                <span className="text-[10px] font-mono text-purple-300 uppercase block font-bold">
                  📜 Sacred Passage Excerpt
                </span>
                <p className="text-gray-200 text-[11px] leading-relaxed whitespace-pre-line font-serif">
                  {String(details.passage)}
                </p>
              </div>
            )}
            {details.context && (
              <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                <span className="text-[10px] font-mono text-gray-400 uppercase block font-bold mb-1">Context & Commentary</span>
                <p className="text-gray-300 text-[11px] leading-relaxed">{String(details.context)}</p>
              </div>
            )}
          </div>
        )}

        {/* ================= FREQUENCIES VIEW ================= */}
        {category === 'frequencies' && (
          <div className="space-y-4 text-xs">
            <div className="bg-cyan-950/30 p-4 rounded-lg border border-cyan-500/20 flex justify-between items-center">
              <div>
                <span className="text-[10px] font-mono text-cyan-300 uppercase block font-bold">Resonant Frequency</span>
                <span className="text-2xl font-mono font-bold text-white mt-1 block">
                  {activeItem.frequencies?.[0] || '528.0'} Hz
                </span>
              </div>
              <button
                type="button"
                onClick={() => copyToClipboard(String(activeItem.frequencies?.[0] || 528), 'freq-copy')}
                className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
              >
                <Copy className="w-3.5 h-3.5" />
                Copy Frequency
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
      {/* Title Header */}
      <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 border border-white/10 rounded-xl p-5 shadow-xl">
        <div className="flex flex-wrap justify-between items-center gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
              <BookOpen className="w-7 h-7 text-purple-400 animate-pulse" />
              The Esoteric Grimoire & Learning Library
            </h2>
            <p className="text-xs text-purple-200 mt-1">
              Explore 7 wisdom corpora: 10 Planetary Correspondences, 78 Tarot Cards, 64 I Ching Hexagrams, Mantras, Sutras, and Healing Frequencies.
            </p>
          </div>

          {/* Navigation Mode Tabs */}
          <div className="flex bg-gray-950/70 p-1 rounded-lg border border-white/10">
            <button
              type="button"
              onClick={() => setActiveTab('explorer')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'explorer'
                  ? 'bg-purple-600 text-white shadow'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              Grimoire Explorer
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('tutor')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'tutor'
                  ? 'bg-cyan-600 text-white shadow'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5" />
              Esoteric Tutor
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('parables')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'parables'
                  ? 'bg-amber-600 text-white shadow'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Dharma Parables
            </button>
          </div>
        </div>
      </div>

      {/* ================= TAB 1: GRIMOIRE EXPLORER ================= */}
      {activeTab === 'explorer' && (
        <div className="space-y-6">
          {/* Category Filter Pills & Search */}
          <div className="bg-gray-900/60 p-4 rounded-xl border border-white/10 space-y-3">
            <div className="flex flex-wrap gap-2">
              {CATEGORY_PILLS.map((cat) => {
                const isSelected = selectedCategory === cat.key;
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => setSelectedCategory(cat.key)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                      isSelected
                        ? 'bg-purple-600/30 border-purple-500 text-white shadow-[0_0_10px_rgba(168,85,247,0.25)]'
                        : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>

            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    audioFeedback.playType();
                  }}
                  placeholder="Search by name, mineral, herb, chakra, keyword, hexagram, or mantra (e.g. Lavender, Magician, 528 Hz, Tara)..."
                  className="w-full bg-gray-950 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-all font-sans"
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
          </div>

          {/* Explorer Layout: Item List + Detail View */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Items Sidebar */}
            <div className="bg-gray-900/60 p-4 rounded-xl border border-white/10 space-y-3 max-h-[580px] overflow-y-auto">
              <div className="flex justify-between items-center text-xs font-mono text-gray-400 border-b border-white/5 pb-2">
                <span className="font-bold uppercase tracking-wider">
                  {selectedCategory === 'all' ? 'Knowledge Items' : selectedCategory.toUpperCase()}
                </span>
                <span>{items.length} records</span>
              </div>

              <div className="flex flex-col gap-1.5">
                {items.map((item) => {
                  const isSelected = activeItem?.id === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => selectItem(item)}
                      className={`w-full flex items-center justify-between p-2.5 rounded-lg border text-left text-xs transition-all duration-200 ${
                        isSelected
                          ? 'bg-purple-950/70 border-purple-500 text-white shadow-[0_0_10px_rgba(168,85,247,0.3)]'
                          : 'bg-white/5 border-transparent text-gray-400 hover:text-white hover:bg-white/10'
                      }`}
                    >
                      <div className="truncate pr-2">
                        <span className="font-semibold block truncate">{item.title}</span>
                        <span className="text-[10px] text-gray-500 font-mono block truncate">{item.subtitle}</span>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 opacity-50 shrink-0" />
                    </button>
                  );
                })}
                {items.length === 0 && !loading && (
                  <div className="text-center py-12 text-gray-500 text-xs italic">
                    No entries found matching "{searchQuery}".
                  </div>
                )}
              </div>
            </div>

            {/* Main Detail Card */}
            <div className="lg:col-span-2 bg-gray-900/60 p-5 md:p-6 rounded-xl border border-white/10 flex flex-col justify-between shadow-2xl min-h-[480px]">
              {renderItemDetails()}
            </div>
          </div>
        </div>
      )}

      {/* ================= TAB 2: ESOTERIC TUTOR (LEARNING LIBRARY) ================= */}
      {activeTab === 'tutor' && (
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 md:p-6 shadow-2xl">
          <EsotericTutor />
        </div>
      )}

      {/* ================= TAB 3: DHARMA PARABLES ================= */}
      {activeTab === 'parables' && (
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 md:p-6 shadow-2xl">
          <DharmaTales />
        </div>
      )}
    </div>
  );
};

export default GrimoirePanel;
