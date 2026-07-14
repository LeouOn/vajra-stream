/**
 * Outlook Dashboard — narrative generation, universe management, and blessing loop.
 *
 * Ant Design rewrite. Three sections:
 * 1. Generator Tab — configure and generate single/epic blessings
 * 2. Universe Tab — manage realms, characters, populations
 * 3. History — browse past transmissions
 *
 * @component
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Compass, Sparkles, Globe, Clock, Shield, Users, Settings,
  History, RefreshCw, Copy, CheckCircle, Play, Square,
  Plus, Edit2, Trash2, Search, Filter, ArrowUpDown, X,
  BookOpen, Sun, Moon, Layers, Shuffle, Dices, Zap,
  Download, Volume2, Bell,
} from 'lucide-react';
import {
  Card, Tabs, Form, Input, InputNumber, Button, Select, Switch, Tag,
  Segmented, Row, Col, Space, Slider, Collapse, List, Typography,
  Spin, Empty, Divider, Badge, Tooltip, message, Modal, Checkbox,
} from 'antd';
import { useUIStore } from '../../stores/uiStore';
import { audioFeedback } from '../../utils/audioFeedback';
import { useAudioStore } from '../../stores/audioStore';
import EpicStoryViewer from './EpicStoryViewer';
import RothkoGenerator from '../2D/RothkoGenerator';
import NarrativeTTSPlayer from './NarrativeTTSPlayer';
import GuidedRitualFlow from './GuidedRitualFlow';
import JourneyCard from './JourneyCard';
import { createLogger } from '../../utils/logger';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';

const { Text, Paragraph, Title } = Typography;

interface GenreOption {
  value: string;
  label: string;
  desc: string;
}

interface DifficultyOption {
  id: string;
  label: string;
  desc: string;
}

interface GlobalIntention {
  id: string;
  label: string;
  planet: string;
  freq: string;
  icon: string;
}

interface Realm {
  id: string | number;
  name: string;
  description?: string;
  location_type?: string;
  is_metaphysical?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  dimension_frequency?: number;
  priority?: number;
  realm_governor?: string;
  celestial_coordinates?: string;
  total_narratives_featured?: number;
  timezone?: string;
  astrological_anchor?: string;
  elemental_affinity?: string;
  source_type?: string;
  [key: string]: unknown;
}

interface Character {
  id: string | number;
  name: string;
  description?: string;
  role: string;
  tags?: string[];
  mantra_preference?: string;
  elemental_anchor?: string;
  total_narratives_featured?: number;
  dialogue_style?: string;
  priority?: number;
  source_type?: string;
  [key: string]: unknown;
}

interface Population {
  id: string | number;
  name: string;
  description?: string;
  category?: string;
  is_active?: boolean;
  is_urgent?: boolean;
  priority?: number;
  intentions?: string[];
  [key: string]: unknown;
}

interface HistoryItem {
  type?: string;
  date_generated?: string;
  genre?: string;
  content?: string;
  astrology_context?: string;
  divination_context?: string;
  divination_raw?: DivinationRaw;
  entities_invoked?: string;
  [key: string]: unknown;
}

interface DivinationCardPayload {
  svg?: string;
  name?: string;
  [key: string]: unknown;
}

interface SigilData {
  kamea?: string;
  reduced?: string;
  coordinates?: Array<{ x: number; y: number; value?: number; letter?: string }>;
  svg?: string;
}

interface DivinationRaw {
  tarot?: DivinationCardPayload;
  iching?: DivinationCardPayload;
  sigil?: SigilData;
  [key: string]: unknown;
}

interface CurrentNarrative {
  type?: string;
  genre?: string;
  narrative?: string;
  narrative_parts?: string[] | string;
  astrology_used?: string;
  divination_used?: string;
  divination_raw?: DivinationRaw;
  entities_used?: string;
  model_used?: string;
  provider_used?: string;
  [key: string]: unknown;
}

interface OutlookModels {
  lm_studio?: string[];
  local?: string[];
  api?: string[];
}

interface ModelSelectOption {
  value: string;
  label: string;
}

type ResultTab = 'narrative' | 'affirmation';
type UniverseTab = 'realms' | 'characters' | 'populations';
type LoopMode = 'sequential_delay' | 'consecutive';
type GeneratorTab = 'generator' | 'universe' | 'history' | 'journey';

// ─── Constants ────────────────────────────────────────────

const GENRES: GenreOption[] = [
  { value: 'healing', label: '🌿 Healing', desc: 'Sutra of restoration, pacifying sickness & anxiety' },
  { value: 'victory', label: '🛡️ Victory', desc: 'Overcoming limitations, spiritual warfare & triumph' },
  { value: 'alchemist', label: '⚗️ Alchemist', desc: 'Hermetic parables of chemical transmutations' },
  { value: 'fun_parable', label: '☯️ Fun Parable', desc: 'Lighthearted Zen/Sufi teaching jokes' },
  { value: 'dharani', label: '📿 Dharani', desc: 'Dense mantras and direct invocations of power' },
];

const LANGUAGES: string[] = [
  'English', 'Sanskrit', 'Tibetan', 'Chinese', 'Latin', 'Greek', 'Hebrew',
];

// Pre-compute option arrays from module-level constants so they're stable
// across renders (previously each .map() created a new array on every render).
const GENRE_OPTIONS = GENRES.map(g => ({ value: g.value, label: g.label }));
const LANGUAGE_OPTIONS = LANGUAGES.map(l => ({ value: l, label: l }));

/**
 * Genre color theming — soft tinted card backgrounds that visually evoke
 * the genre's energy without overwhelming the typography. Keyed by genre
 * id; unknown genres fall back to transparent.
 */
const GENRE_COLORS: Record<string, string> = {
  healing: 'rgba(0, 168, 107, 0.05)',     // 00A86B green
  victory: 'rgba(220, 20, 60, 0.05)',      // crimson
  alchemist: 'rgba(218, 165, 32, 0.05)',   // goldenrod
  fun_parable: 'rgba(100, 149, 237, 0.05)',// cornflower
  dharani: 'rgba(138, 43, 226, 0.05)',     // violet
  compassion: 'rgba(255, 105, 180, 0.05)', // pink
  wisdom: 'rgba(100, 149, 237, 0.05)',     // cornflower
  protection: 'rgba(34, 139, 34, 0.05)',   // forest green
};

const RITUAL_PHASES: string[] = [
  'Invocatio',
  'Pacificatio',
  'Attunement',
  'Sigillum',
  'Dedicatio',
];

const SAVED_RITUALS_KEY = 'vajra.savedRituals.v1';

interface SavedRitual {
  id: string;
  savedAt: string;
  genre: string;
  narrative: string;
  divinationRaw: DivinationRaw | null;
  entities: string | null;
  model: string | null;
  provider: string | null;
}

const DIFFICULTY_OPTIONS: DifficultyOption[] = [
  { id: 'mild', label: 'Mild', desc: 'Minor obstacles and everyday challenges' },
  { id: 'moderate', label: 'Moderate', desc: 'Persistent patterns and recurring issues' },
  { id: 'deep', label: 'Deep', desc: 'Profound wounds and life-changing difficulties' },
];

const GENRE_BORDER_COLORS: Record<string, string> = {
  healing: '#00A86B',
  victory: '#dc143c',
  alchemist: '#daa520',
  fun_parable: '#6495ed',
  dharani: '#8a2be2',
  compassion: '#ff69b4',
  wisdom: '#6495ed',
  protection: '#228b22',
};

function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^>\s+/gm, '')
    .trim();
}

const GLOBAL_INTENTIONS: GlobalIntention[] = [
  { id: 'world peace', label: 'World Peace', planet: 'Jupiter', freq: '852Hz', icon: '🕊' },  // dove
  { id: 'world prosperity', label: 'World Prosperity', planet: 'Venus', freq: '528Hz', icon: '💎' },  // gem
  { id: 'end to disease and cancer', label: 'End Disease & Cancer', planet: 'Sun', freq: '528Hz', icon: '☀️' },  // sun
  { id: 'happiness', label: 'Happiness', planet: 'Jupiter', freq: '528Hz', icon: '🌟' },  // star
  { id: 'reforestation the world', label: 'Reforestation', planet: 'Earth', freq: '528Hz', icon: '🌲' },  // tree
  { id: 'cleaning up pollution', label: 'Clean Pollution', planet: 'Saturn', freq: '396Hz', icon: '🌊' },  // wave
];

const DEFAULT_CHARACTERS: Character[] = [
  {
    id: 'seed-green-tara',
    name: 'Green Tara',
    role: 'protector',
    description: 'Swift protectress and Mother of Liberation; springs into action at the first cry of fear. Ferries beings across the eight great fears.',
    tags: ['compassion', 'protection', 'swift-action'],
    mantra_preference: 'Oṃ Tāre Tuttāre Ture Svāhā',
    elemental_anchor: 'Air',
    dialogue_style: 'gentle, maternal, swift',
    priority: 9,
    source_type: 'seed',
  },
  {
    id: 'seed-medicine-buddha',
    name: 'Medicine Buddha (Bhaiṣajyaguru)',
    role: 'healer',
    description: 'Lapis Lazuli Radiance of the eastern pure land; embodies the Twelve Great Vows to heal all sickness of body, speech, and mind.',
    tags: ['healing', 'lapis-light', 'medicine'],
    mantra_preference: 'Oṃ Bhaiṣajye Bhaiṣajye Mahābhaiṣajye Rāja Samudgate Svāhā',
    elemental_anchor: 'Water',
    dialogue_style: 'calm, healing, luminous',
    priority: 9,
    source_type: 'seed',
  },
  {
    id: 'seed-vajrasattva',
    name: 'Vajrasattva',
    role: 'purifier',
    description: 'Diamond Being; the embodiment of primordial purity. The hundred-syllable mantra purifies all obscurations and negative karma.',
    tags: ['purification', 'vajra', 'purity'],
    mantra_preference: 'Oṃ Vajrasattva Hūṃ',
    elemental_anchor: 'Aether',
    dialogue_style: 'precise, luminous, diamond-clear',
    priority: 9,
    source_type: 'seed',
  },
];

// ─── Component ─────────────────────────────────────────────

export default function OutlookDashboard() {
  const { isPlaying } = useAudioStore();
  const addToast = useUIStore((s) => s.addToast);
  const { isConnected, idleReflectionCount } = useWebSocketStable();
  const [activeTab, setActiveTab] = useState<GeneratorTab>('generator');

  // ─── Generator State ─────────────────────────────────────
  const [lat, setLat] = useState<number | null>(34.0522);
  const [lon, setLon] = useState<number | null>(-118.2437);
  const [genre, setGenre] = useState<string>('healing');
  const [selectedLangs, setSelectedLangs] = useState<string[]>(['English']);
  const [isEpic, setIsEpic] = useState<boolean>(false);
  const [stages, setStages] = useState<number>(9);
  const [date, setDate] = useState<string>(() => new Date().toISOString().slice(0, 16));
  const [selectedRealmId, setSelectedRealmId] = useState<string>('');
  const [selectedCharIds, setSelectedCharIds] = useState<Array<string | number>>([]);
  const [selectedPopIds, setSelectedPopIds] = useState<Array<string | number>>([]);
  const [includeDialogue, setIncludeDialogue] = useState<boolean>(false);
  const [customContext, setCustomContext] = useState<string>('');
  const [difficulty, setDifficulty] = useState<string>('moderate');
  const [excludedForcesText, setExcludedForcesText] = useState<string>('');
  const [includeAstrology, setIncludeAstrology] = useState<boolean>(true);
  const [includeTarot, setIncludeTarot] = useState<boolean>(true);
  const [includeIching, setIncludeIching] = useState<boolean>(true);
  const [randomizeRealm, setRandomizeRealm] = useState<boolean>(false);
  const [randomizeCharacters, setRandomizeCharacters] = useState<boolean>(false);

  const [bgActive, setBgActive] = useState<boolean>(false);
  const [bgInterval, setBgInterval] = useState<number>(60);
  const [bgMode, setBgMode] = useState<LoopMode>('sequential_delay');
  const [bgAstrology, setBgAstrology] = useState<boolean>(true);
  const [bgTarot, setBgTarot] = useState<boolean>(true);
  const [bgIching, setBgIching] = useState<boolean>(true);
  const [bgCycleGenres, setBgCycleGenres] = useState<boolean>(true);
  const [bgStats, setBgStats] = useState<{
    total_generated?: number;
    total_saved?: number;
    total_errors?: number;
    last_generated_at?: string | null;
    last_genre?: string | null;
  }>({});

  // ─── Generation Mode ─────────────────────────────────────
  const [generationMode, setGenerationMode] = useState<'guided' | 'quick'>('guided');

  // ─── Result State ────────────────────────────────────────
  const [loading, setLoading] = useState<boolean>(false);
  const [currentNarrative, setCurrentNarrative] = useState<CurrentNarrative | null>(null);
  const [historyList, setHistoryList] = useState<HistoryItem[]>([]);
  const [historyGenreFilter, setHistoryGenreFilter] = useState<string>('all');
  const [copied, setCopied] = useState<boolean>(false);
  const [resultTab, setResultTab] = useState<ResultTab>('narrative');
  const [affirmation, setAffirmation] = useState<string | null>(null);
  const [affirmationLoading, setAffirmationLoading] = useState<boolean>(false);
  const [affirmationCopied, setAffirmationCopied] = useState<boolean>(false);

  // ─── Ritual Reveal State ─────────────────────────────────
  // Progressive section reveal — sections (I. Invocatio … V. Dedicatio)
  // fade in one at a time. `revealedSections` counts how many have
  // appeared so far; the underlying text is split on Roman-numeral
  // headers and only the revealed slice is rendered.
  const [revealedSections, setRevealedSections] = useState<number>(0);
  const revealTimersRef = useRef<number[]>([]);

  // ─── Universe Data ───────────────────────────────────────
  const [realms, setRealms] = useState<Realm[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [populations, setPopulations] = useState<Population[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [locationTypes, setLocationTypes] = useState<string[]>([]);

  // ─── Universe Sub-tab ────────────────────────────────────
  const [universeTab, setUniverseTab] = useState<UniverseTab>('realms');

  // ─── CRUD Modals ─────────────────────────────────────────
  const [realmModalOpen, setRealmModalOpen] = useState<boolean>(false);
  const [editingRealm, setEditingRealm] = useState<Realm | null>(null);
  const [realmForm] = Form.useForm();

  const [charModalOpen, setCharModalOpen] = useState<boolean>(false);
  const [editingChar, setEditingChar] = useState<Character | null>(null);
  const [charForm] = Form.useForm();

  // ─── Filter State ────────────────────────────────────────
  const [realmSearch, setRealmSearch] = useState<string>('');
  const [realmTypeFilter, setRealmTypeFilter] = useState<string>('all');
  const [charSearch, setCharSearch] = useState<string>('');
  const [charRoleFilter, setCharRoleFilter] = useState<string>('all');

  // ─── Model Selection ─────────────────────────────────────
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [randomModel, setRandomModel] = useState<boolean>(false);
  const [outlookModels, setOutlookModels] = useState<OutlookModels>({ lm_studio: [], local: [], api: [] });
  const [healthyProviders, setHealthyProviders] = useState<Record<string, boolean>>({});
  const log = createLogger('OutlookDashboard');

  // ─── Data Fetching ───────────────────────────────────────

  const fetchUniverseData = useCallback(async (): Promise<void> => {
    try {
      const [realmsRes, charsRes, popsRes, rolesRes, typesRes] = await Promise.all([
        fetch(`/api/v1/outlook/locations`),
        fetch(`/api/v1/outlook/characters`),
        fetch(`/api/v1/populations/`),
        fetch(`/api/v1/outlook/characters/roles/list`),
        fetch(`/api/v1/outlook/locations/types/list`),
      ]);
      // Defensive unwrap — same crash class as AstrologyExtractionPanel's
      // ``runs.some is not a function`` bug. Backend today returns bare arrays
      // for these 5 endpoints, but a future envelope wrap (e.g. ``{items: [...]}``
      // or ``{data: [...]}``) would silently store the envelope object in state
      // and crash every downstream ``.map()`` / ``.filter()`` call with
      // "object is not iterable". Accept either shape; fall back to ``[]``.
      const unwrap = <T,>(v: unknown): T[] =>
        Array.isArray(v) ? v as T[] : Array.isArray((v as any)?.items) ? (v as any).items : Array.isArray((v as any)?.data) ? (v as any).data : [];
      if (realmsRes.ok) setRealms(unwrap<Realm>(await realmsRes.json()));
      if (charsRes.ok) setCharacters(unwrap<Character>(await charsRes.json()));
      if (popsRes.ok) setPopulations(unwrap<Population>(await popsRes.json()));
      if (rolesRes.ok) setRoles(unwrap<string>(await rolesRes.json()));
      if (typesRes.ok) setLocationTypes(unwrap<string>(await typesRes.json()));
    } catch (e) {
      addToast({ type: 'error', title: 'Could not load realms', message: 'Backend unreachable. Some data may be stale.', duration: 3000 });
    }
  }, [addToast]);

  const fetchHistory = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/outlook/history?limit=15`);
      if (res.ok) setHistoryList(((await res.json()) as { history?: HistoryItem[] }).history || []);
    } catch (e) {
      addToast({ type: 'error', title: 'Could not load history', message: 'Backend unreachable.', duration: 3000 });
    }
  }, [addToast]);

  const fetchModels = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/llm/models`);
      if (res.ok) {
        const data = await res.json() as {
          status?: string;
          available?: OutlookModels;
          default_model?: string;
        };
        if (data.status === 'success') {
          setOutlookModels(data.available || { lm_studio: [], local: [], api: [] });
          if (!selectedModel && data.default_model) setSelectedModel(data.default_model);
        }
      }
    } catch (e) {
      addToast({ type: 'error', title: 'Could not load LLM models', message: 'Backend unreachable.', duration: 3000 });
    }
  }, [selectedModel, addToast]);

  const fetchProvidersHealth = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/llm/providers/health`);
      if (!res.ok) return;
      const data = await res.json() as {
        providers?: Array<{ provider: string; healthy: boolean }>;
      };
      const map: Record<string, boolean> = {};
      (data.providers || []).forEach(p => { map[p.provider] = p.healthy; });
      setHealthyProviders(map);
    } catch (e) {
      log.error('Providers health fetch failed:', e);
    }
  }, []);

  const fetchBgStatus = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(`/api/v1/outlook/background/status`);
      if (res.ok) {
        const data = await res.json() as {
          active?: boolean;
          config?: {
            interval_minutes?: number;
            loop_mode?: LoopMode;
            cycle_genres?: boolean;
            include_astrology?: boolean;
            include_tarot?: boolean;
            include_iching?: boolean;
          };
          stats?: typeof bgStats;
        };
        setBgActive(Boolean(data.active));
        if (data.config?.interval_minutes) setBgInterval(data.config.interval_minutes);
        if (data.config?.loop_mode) setBgMode(data.config.loop_mode);
        if (data.config?.cycle_genres !== undefined) setBgCycleGenres(data.config.cycle_genres);
        if (data.config?.include_astrology !== undefined) setBgAstrology(data.config.include_astrology);
        if (data.config?.include_tarot !== undefined) setBgTarot(data.config.include_tarot);
        if (data.config?.include_iching !== undefined) setBgIching(data.config.include_iching);
        if (data.stats) setBgStats(data.stats);
      }
    } catch {
    }
  }, []);

  const toggleBackgroundGeneration = useCallback(async (): Promise<void> => {
    if (bgActive) {
      try {
        await fetch(`/api/v1/outlook/background/stop`, { method: 'POST' });
        setBgActive(false);
        message.success('Background generation stopped.');
      } catch {
        message.error('Could not stop background generation.');
      }
    } else {
      try {
        const res = await fetch(`/api/v1/outlook/background/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            interval_minutes: bgInterval,
            loop_mode: bgMode,
            cycle_genres: bgCycleGenres,
            cycle_intentions: true,
            include_astrology: bgAstrology,
            include_tarot: bgTarot,
            include_iching: bgIching,
            include_geomancy: true,
            lat: parseFloat(String(lat)),
            lon: parseFloat(String(lon)),
            languages: selectedLangs,
          }),
        });
        if (res.ok) {
          setBgActive(true);
          message.success(`Background generation every ${bgInterval} min.`);
          audioFeedback.playSuccess();
          fetchBgStatus();
        } else {
          message.error('Could not start background generation.');
          audioFeedback.playError();
        }
      } catch {
        message.error('Backend unreachable.');
        audioFeedback.playError();
      }
    }
  }, [bgActive, bgInterval, bgMode, bgCycleGenres, bgAstrology, bgTarot, bgIching, lat, lon, selectedLangs, fetchBgStatus]);

  useEffect(() => {
    fetchUniverseData();
    fetchHistory();
    fetchModels();
    fetchProvidersHealth();
    fetchBgStatus();
  }, []);

  useEffect(() => {
    if (isConnected) {
      fetchUniverseData();
      fetchHistory();
      fetchModels();
      fetchProvidersHealth();
      fetchBgStatus();
    }
    // Intentionally NOT listing the fetch callbacks in deps — they capture
    // addToast and may change identity on each render, which would cause
    // an infinite refetch loop. This matches the JourneyCard pattern.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]);

  useEffect(() => {
    if (!bgActive) return;
    const id = window.setInterval(() => {
      fetchBgStatus();
      fetchHistory();
    }, 30000);
    return () => window.clearInterval(id);
  }, [bgActive, fetchBgStatus, fetchHistory]);

  // Auto-set coordinates from selected realm
  useEffect(() => {
    if (selectedRealmId) {
      const realm = realms.find(r => r.id === selectedRealmId);
      if (realm && !realm.is_metaphysical && realm.latitude != null && realm.longitude != null) {
        setLat(realm.latitude);
        setLon(realm.longitude);
      }
    }
  }, [selectedRealmId, realms]);

  // Seed defaults so first-time users don't see "Characters (0) /
  // Populations (0)". Seed characters are local-only (not persisted);
  // populations are auto-selected from the backend's first 3.
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    if (characters.length === 0) {
      setCharacters(DEFAULT_CHARACTERS);
    }
    if (selectedPopIds.length === 0 && populations.length > 0) {
      setSelectedPopIds(populations.slice(0, 3).map(p => p.id));
    }
    if (characters.length > 0 || populations.length > 0) {
      seededRef.current = true;
    }
  }, [characters.length, populations, selectedPopIds.length]);

  // ─── Filtered Lists ──────────────────────────────────────

  const filteredRealms = useMemo<Realm[]>(() => {
    let result = realms;
    if (realmSearch) {
      const q = realmSearch.toLowerCase();
      result = result.filter(r =>
        r.name.toLowerCase().includes(q) ||
        (r.description || '').toLowerCase().includes(q) ||
        (r.realm_governor || '').toLowerCase().includes(q)
      );
    }
    if (realmTypeFilter !== 'all') result = result.filter(r => r.location_type === realmTypeFilter);
    return result;
  }, [realms, realmSearch, realmTypeFilter]);

  const filteredCharacters = useMemo<Character[]>(() => {
    let result = characters;
    if (charSearch) {
      const q = charSearch.toLowerCase();
      result = result.filter(c =>
        c.name.toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q) ||
        (c.tags || []).some(t => t.toLowerCase().includes(q))
      );
    }
    if (charRoleFilter !== 'all') result = result.filter(c => c.role === charRoleFilter);
    return result;
  }, [characters, charSearch, charRoleFilter]);

  // ─── Generate Narrative ──────────────────────────────────

  const handleGenerate = async (): Promise<void> => {
    setLoading(true);
    setCurrentNarrative(null);
    setAffirmation(null);
    setResultTab('narrative');
    audioFeedback.playClick();

    try {
      const endpoint = isEpic ? '/outlook/generate_epic' : '/outlook/generate_single';
      const body: Record<string, unknown> = {
        lat: parseFloat(String(lat)), lon: parseFloat(String(lon)),
        languages: selectedLangs, genre,
        date: new Date(date).toISOString(),
        custom_context: customContext || null,
        difficulty,
        realm_id: selectedRealmId || null,
        population_ids: selectedPopIds.length > 0 ? selectedPopIds : null,
        character_ids: selectedCharIds.length > 0 ? selectedCharIds : null,
        excluded_forces: excludedForcesText ? excludedForcesText.split(',').map(s => s.trim()) : null,
        include_dialogue: includeDialogue,
        model: randomModel ? null : (selectedModel || null),
        random: randomModel || null,
        include_astrology: includeAstrology,
        include_tarot: includeTarot,
        include_iching: includeIching,
        randomize_realm: randomizeRealm,
        randomize_characters: randomizeCharacters,
      };
      if (isEpic) body.stages = parseInt(String(stages));

      const res = await fetch(`/api/v1${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = await res.json() as CurrentNarrative;
        setCurrentNarrative(data);
        message.success(isEpic ? `Epic journey of ${stages} stages received.` : 'Narrative generated.');
        audioFeedback.playSuccess();
        fetchHistory();
        fetchUniverseData();
      } else {
        const err = await res.json().catch(() => ({})) as { detail?: string };
        message.error(err.detail || 'Generation failed.');
        audioFeedback.playError();
      }
    } catch {
      message.error('Network error — could not reach backend.');
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  const generateAffirmation = async (): Promise<void> => {
    if (!currentNarrative) return;
    setAffirmationLoading(true);
    audioFeedback.playTelemetry();
    try {
      const intention = customContext
        || currentNarrative.genre
        || 'spiritual practice';
      const res = await fetch(`/api/v1/radionics/affirmation/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention, style: 'empowering' }),
      });
      if (res.ok) {
        const data = await res.json() as { affirmation?: string; text?: string };
        setAffirmation(data.affirmation || data.text || '');
        setResultTab('affirmation');
        audioFeedback.playSuccess();
      } else {
        message.error('Affirmation service unavailable.');
        audioFeedback.playError();
      }
    } catch {
      message.error('Could not reach affirmation endpoint.');
      audioFeedback.playError();
    }
    setAffirmationLoading(false);
  };

  const copyAffirmation = (): void => {
    if (!affirmation) return;
    navigator.clipboard.writeText(affirmation);
    setAffirmationCopied(true);
    setTimeout(() => setAffirmationCopied(false), 2000);
  };

  const handleStartBroadcast = async (): Promise<void> => {
    if (!bgActive) {
      await toggleBackgroundGeneration();
    }
  };

  // ─── Realm CRUD ──────────────────────────────────────────

  const openRealmModal = (realm: Realm | null = null): void => {
    setEditingRealm(realm);
    if (realm) {
      realmForm.setFieldsValue({
        ...realm,
        is_metaphysical: realm.is_metaphysical ?? true,
        latitude: realm.latitude ?? 0,
        longitude: realm.longitude ?? 0,
        dimension_frequency: realm.dimension_frequency ?? 528,
        priority: realm.priority ?? 5,
      });
    } else {
      realmForm.resetFields();
    }
    setRealmModalOpen(true);
  };

  const saveRealm = async (): Promise<void> => {
    try {
      const values = await realmForm.validateFields() as Record<string, unknown>;
      const payload: Record<string, unknown> = { ...values };
      if (payload.is_metaphysical) { payload.latitude = null; payload.longitude = null; }
      else { payload.latitude = parseFloat(String(payload.latitude)); payload.longitude = parseFloat(String(payload.longitude)); }

      const url = editingRealm
        ? `/api/v1/outlook/locations/${editingRealm.id}`
        : `/api/v1/outlook/locations`;
      const method = editingRealm ? 'PUT' : 'POST';

      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (res.ok) {
        message.success(editingRealm ? 'Realm updated.' : 'Realm created.');
        setRealmModalOpen(false);
        fetchUniverseData();
      } else {
        const err = await res.json().catch(() => ({} as { detail?: string }));
        message.error(err.detail || `Failed to save realm: HTTP ${res.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      if ((e as { errorFields?: unknown }).errorFields) return;
      message.error('Failed to save realm.');
    }
  };

  const deleteRealm = async (id: string | number): Promise<void> => {
    Modal.confirm({
      title: 'Exile this realm?',
      content: 'This action cannot be undone.',
      okText: 'Delete', okType: 'danger', cancelText: 'Cancel',
      onOk: async () => {
        try {
          const res = await fetch(`/api/v1/outlook/locations/${id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
          message.success('Realm deleted.');
          fetchUniverseData();
        } catch (e) {
          addToast({ type: 'error', title: 'Could not delete realm', message: 'Backend unreachable or refused the request.', duration: 3000 });
        }
      },
    });
  };

  // ─── Character CRUD ──────────────────────────────────────

  const openCharModal = (char: Character | null = null): void => {
    setEditingChar(char);
    if (char) {
      charForm.setFieldsValue({ ...char, priority: char.priority ?? 5 });
    } else {
      charForm.resetFields();
    }
    setCharModalOpen(true);
  };

  const saveCharacter = async (): Promise<void> => {
    try {
      const values = await charForm.validateFields() as Record<string, unknown>;
      const url = editingChar
        ? `/api/v1/outlook/characters/${editingChar.id}`
        : `/api/v1/outlook/characters`;
      const method = editingChar ? 'PUT' : 'POST';

      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
      if (res.ok) {
        message.success(editingChar ? 'Character updated.' : 'Character created.');
        setCharModalOpen(false);
        fetchUniverseData();
      } else {
        const err = await res.json().catch(() => ({} as { detail?: string }));
        message.error(err.detail || `Failed to save character: HTTP ${res.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      if ((e as { errorFields?: unknown }).errorFields) return;
      message.error('Failed to save character.');
    }
  };

  const deleteCharacter = async (id: string | number): Promise<void> => {
    Modal.confirm({
      title: 'Exile this character?',
      content: 'They will be removed from all future narratives.',
      okText: 'Exile', okType: 'danger', cancelText: 'Cancel',
      onOk: async () => {
        try {
          const res = await fetch(`/api/v1/outlook/characters/${id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
          message.success('Character exiled.');
          fetchUniverseData();
        } catch (e) {
          addToast({ type: 'error', title: 'Could not delete character', message: 'Backend unreachable or refused the request.', duration: 3000 });
        }
      },
    });
  };

  // ─── History ─────────────────────────────────────────────

  const loadHistoryItem = (item: HistoryItem): void => {
    const normalized: CurrentNarrative = {
      ...item,
      astrology_used: item.astrology_context,
      divination_used: item.divination_context,
      divination_raw: item.divination_raw,
      entities_used: item.entities_invoked,
      narrative: item.type === 'epic' ? undefined : item.content,
      narrative_parts: item.type === 'epic' ? item.content : undefined,
    };
    setCurrentNarrative(normalized);
  };

  const copyNarrative = (): void => {
    const text = currentNarrative?.narrative || JSON.stringify(currentNarrative?.narrative_parts || '', null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ─── Ritual Reveal Logic ─────────────────────────────────

  const parseSections = (text: string): string[] => {
    // Splitting on the captured group means odd-indexed parts are the
    // roman numerals (I, II, III…) and even-indexed parts are the bodies.
    // We re-prepend the header marker so the rendered text keeps its
    // bold section titles.
    const parts = text.split(/\*\*([IVX]+)\.\s/);
    const sections: string[] = [];
    for (let i = 1; i < parts.length; i += 2) {
      const combined = `**${parts[i]}. ${parts[i + 1] || ''}`;
      if (combined.trim().length > 50) sections.push(combined);
    }
    const preamble = parts[0]?.trim();
    if (preamble && sections.length > 0) {
      sections[0] = `${preamble}\n\n${sections[0]}`;
    } else if (preamble && sections.length === 0) {
      sections.push(preamble);
    }
    return sections;
  };

  const sections = useMemo<string[]>(() => {
    if (!currentNarrative?.narrative) return [];
    return parseSections(currentNarrative.narrative);
  }, [currentNarrative]);

  // Schedule progressive section reveal whenever a new narrative arrives.
  // Each section appears ~1.5s after the previous; the dedication section
  // (last) also triggers a bell tone.
  useEffect(() => {
    revealTimersRef.current.forEach(t => window.clearTimeout(t));
    revealTimersRef.current = [];
    setRevealedSections(0);
    if (sections.length === 0) return;
    sections.forEach((_, i) => {
      const idx = i;
      const timer = window.setTimeout(() => {
        setRevealedSections(idx + 1);
        if (idx === sections.length - 1) {
          playDedicationBell();
        } else {
          playSectionChime();
        }
      }, (idx + 1) * 1500);
      revealTimersRef.current.push(timer);
    });
    return () => {
      revealTimersRef.current.forEach(t => window.clearTimeout(t));
      revealTimersRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sections]);

  // ─── Audio Cues ──────────────────────────────────────────

  const playSectionChime = (): void => {
    if (!audioFeedback.enabled) return;
    audioFeedback.init();
    const ctx = (audioFeedback as unknown as { ctx: AudioContext | null }).ctx;
    if (!ctx || ctx.state !== 'running') return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(528, ctx.currentTime);
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.5);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 1.5);
  };

  const playDedicationBell = (): void => {
    if (!audioFeedback.enabled) return;
    audioFeedback.init();
    const ctx = (audioFeedback as unknown as { ctx: AudioContext | null }).ctx;
    if (!ctx || ctx.state !== 'running') return;
    const now = ctx.currentTime;
    // Bell = fundamental + two overtones with quick decay.
    const partials = [528, 1056, 1584];
    partials.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + i * 0.01);
      gain.gain.setValueAtTime(0.08, now + i * 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.01 + 2.0);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now + i * 0.01);
      osc.stop(now + i * 0.01 + 2.0);
    });
  };

  const replayTTS = (): void => {
    // Trigger the existing TTS player if it's mounted. Falls back to
    // a fresh chime so the user gets audible confirmation even without
    // TTS support.
    playSectionChime();
  };

  // ─── Save / Load Saved Rituals ───────────────────────────

  const loadSavedRituals = (): SavedRitual[] => {
    try {
      const raw = window.localStorage.getItem(SAVED_RITUALS_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw) as unknown;
      return Array.isArray(parsed) ? parsed as SavedRitual[] : [];
    } catch {
      return [];
    }
  };

  const saveCurrentRitual = (): void => {
    if (!currentNarrative?.narrative) return;
    const entry: SavedRitual = {
      id: `ritual_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      savedAt: new Date().toISOString(),
      genre: currentNarrative.genre || genre,
      narrative: currentNarrative.narrative,
      divinationRaw: currentNarrative.divination_raw || null,
      entities: currentNarrative.entities_used || null,
      model: currentNarrative.model_used || null,
      provider: currentNarrative.provider_used || null,
    };
    try {
      const existing = loadSavedRituals();
      const next = [entry, ...existing].slice(0, 50);
      window.localStorage.setItem(SAVED_RITUALS_KEY, JSON.stringify(next));
      message.success('Ritual saved to local archive.');
      audioFeedback.playSuccess();
    } catch {
      message.error('Could not save ritual — localStorage may be full or disabled.');
    }
  };

  // ─── Memoized option arrays (prevent new-array-every-render) ────────────

  const realmOptions = useMemo(() =>
    realms.map(r => ({ value: r.id, label: `${r.name} (${r.is_metaphysical ? 'Meta' : 'Earth'})` }))
  , [realms]);

  // ─── Model Options ───────────────────────────────────────

  const modelOptions = useMemo<ModelSelectOption[]>(() => {
    // Sentinel: '' → backend auto-detect (registry.pick_best()).
    const opts: ModelSelectOption[] = [
      { value: '', label: '✨ Auto-detect (default)' },
    ];

    // API providers: built from the ACTUAL healthy providers reported by
    // /llm/providers/health, cross-referenced with /llm/models so each
    // option carries the provider's real default_model. No static list —
    // unhealthy or unregistered providers simply do not appear.
    const PROVIDER_LABEL: Record<string, { icon: string; name: string }> = {
      openrouter: { icon: '🧭', name: 'OpenRouter' },
      lm_studio: { icon: '🧪', name: 'LM Studio' },
      deepseek: { icon: '🐉', name: 'DeepSeek' },
      z_ai: { icon: '🔮', name: 'Z.AI' },
      anthropic: { icon: '🤖', name: 'Anthropic' },
      openai: { icon: '🧠', name: 'OpenAI' },
      minimax: { icon: '🚀', name: 'MiniMax' },
      local: { icon: '💻', name: 'Local' },
    };
    (outlookModels.api || []).forEach(entry => {
      const m = entry.match(/^([a-zA-Z0-9_-]+)\s*\(([^)]+)\)\s*$/);
      if (!m) return;
      const providerKey = m[1];
      const defaultModel = m[2];
      if (healthyProviders[providerKey] === false) return;
      const meta = PROVIDER_LABEL[providerKey] || { icon: '✨', name: providerKey };
      opts.push({
        value: `${providerKey}:${defaultModel}`,
        label: `${meta.icon} ${meta.name} (${defaultModel})`,
      });
    });

    (outlookModels.lm_studio || []).forEach(m =>
      opts.push({ value: `lm_studio:${m}`, label: `🧪 LM Studio: ${m}` }),
    );
    (outlookModels.local || []).forEach(m =>
      opts.push({ value: `local:${m}`, label: `💻 Local: ${m}` }),
    );
    const seen = new Set<string>();
    return opts.filter(o => { const k = o.value; if (seen.has(k)) return false; seen.add(k); return true; });
  }, [outlookModels, healthyProviders]);

  // ─── Render ──────────────────────────────────────────────

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6">
      <Space orientation="vertical" size="large" className="w-full">

        {/* ── Header ── */}
        <Card size="small">
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <Compass className="w-6 h-6" style={{ color: '#06b6d4' }} />
                <div>
                  <Title level={5} style={{ margin: 0, color: '#67e8f9' }}>Narrative Generation & Outlook</Title>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Construct localized, sutra-style blessing cycles based on high-entropy oracles, planetary lines, and active entity grids.
                  </Text>
                </div>
              </Space>
            </Col>
            <Col>
              <Segmented
                value={activeTab}
                onChange={v => { setActiveTab(v); audioFeedback.playClick(); }}
                options={[
                  { label: <span><Sparkles className="w-3 h-3 inline mr-1" />Generator</span>, value: 'generator' },
                  { label: <span><Layers className="w-3 h-3 inline mr-1" />Universe</span>, value: 'universe' },
                  { label: <span><History className="w-3 h-3 inline mr-1" />History</span>, value: 'history' },
                  { label: <span><Compass className="w-3 h-3 inline mr-1" />Journey</span>, value: 'journey' },
                ]}
              />
            </Col>
          </Row>
        </Card>

        {/* ── Ambient Rothko ── */}
        <Card styles={{ body: { padding: 0, height: 100, overflow: 'hidden' } }}>
          <RothkoGenerator isPlaying={isPlaying} palette="compassion" transitionSpeed={60} />
        </Card>

        {/* ═══════════════════════════════════════════════════════
            GENERATOR TAB
        ═══════════════════════════════════════════════════════ */}
        {activeTab === 'generator' && (
          <>
            {/* Mode Toggle */}
            <div style={{ marginBottom: 16 }}>
              <Segmented
                value={generationMode}
                onChange={(v) => { setGenerationMode(v as 'guided' | 'quick'); audioFeedback.playTabChange(); }}
                options={[
                  { label: <span><Sparkles className="w-3 h-3 inline mr-1" />🔮 Guided Flow</span>, value: 'guided' },
                  { label: <span><Zap className="w-3 h-3 inline mr-1" />⚡ Quick Generate</span>, value: 'quick' },
                ]}
                className="bg-black/40 border border-white/5"
              />
            </div>
            <Row gutter={[24, 24]}>
              {/* ── Left: Settings or Guided Flow ── */}
              <Col xs={24} xl={8}>
                {generationMode === 'guided' ? (
                  <GuidedRitualFlow
                    cosmicData={undefined}
                    activeChart={null}
                    result={currentNarrative}
                    broadcastActive={bgActive}
                    onResult={(data) => setCurrentNarrative(data as CurrentNarrative)}
                    onStartBroadcast={() => { void handleStartBroadcast(); }}
                    onComplete={() => setGenerationMode('quick')}
                    onBackToQuick={() => setGenerationMode('quick')}
                  />
                ) : (
                  <>
                  <Card
                    title={<Text strong className="font-mono text-xs uppercase">Transmission Settings</Text>}
                    extra={bgActive && <Badge status="processing" color="cyan" text="BG Active" />}
                    size="small"
                  >
                    <Space orientation="vertical" className="w-full" size="middle">

                  {/* Active selections summary */}
                  {(selectedRealmId || selectedCharIds.length > 0 || selectedPopIds.length > 0) && (
                    <Space wrap size={[4, 4]}>
                      {selectedRealmId && (() => {
                        const r = realms.find(x => x.id === selectedRealmId);
                        return <Tag closable color="cyan" onClose={() => setSelectedRealmId('')}>📍 {r?.name || 'Realm'}</Tag>;
                      })()}
                      {selectedCharIds.length > 0 && (
                        <Tag closable color="purple" onClose={() => setSelectedCharIds([])}>👤 {selectedCharIds.length} characters</Tag>
                      )}
                      {selectedPopIds.length > 0 && (
                        <Tag closable color="blue" onClose={() => setSelectedPopIds([])}>🫂 {selectedPopIds.length} populations</Tag>
                      )}
                    </Space>
                  )}

                  {/* Realm */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}><Globe className="w-3 h-3 inline mr-1" /> Realm / Setting</Text>
                    <Row gutter={8} align="middle" style={{ marginTop: 4 }}>
                      <Col flex="auto">
                        <Select
                          value={selectedRealmId || undefined}
                          onChange={setSelectedRealmId}
                          disabled={randomizeRealm}
                          placeholder="Dynamic Map Coordinates"
                          allowClear
                          size="small"
                          className="w-full"
                          options={realmOptions}
                        />
                      </Col>
                      <Col>
                        <Tooltip title="Randomize realm"><Switch size="small" checked={randomizeRealm} onChange={setRandomizeRealm} /></Tooltip>
                      </Col>
                    </Row>
                  </div>

                  {/* Coordinates */}
                  <Row gutter={8}>
                    <Col span={12}>
                      <Text style={{ fontSize: 11 }}>Latitude</Text>
                      <InputNumber size="small" className="w-full" value={lat} onChange={setLat} step={0.0001}
                        disabled={randomizeRealm || (!!selectedRealmId && !(realms.find(r => r.id === selectedRealmId)?.is_metaphysical))} />
                    </Col>
                    <Col span={12}>
                      <Text style={{ fontSize: 11 }}>Longitude</Text>
                      <InputNumber size="small" className="w-full" value={lon} onChange={setLon} step={0.0001}
                        disabled={randomizeRealm || (!!selectedRealmId && !(realms.find(r => r.id === selectedRealmId)?.is_metaphysical))} />
                    </Col>
                  </Row>

                  {/* Date */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}><Clock className="w-3 h-3 inline mr-1" /> Cosmic Epoch</Text>
                    <Input size="small" type="datetime-local" value={date} onChange={e => setDate(e.target.value)} style={{ marginTop: 4 }} />
                  </div>

                  {/* Global Intentions Presets (saved from deleted RadionicsNarrative) */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}><Globe className="w-3 h-3 inline mr-1" /> Global Intentions</Text>
                    <div className="grid grid-cols-2 gap-1.5" style={{ marginTop: 4 }}>
                      {GLOBAL_INTENTIONS.map((preset) => {
                        const isActive = customContext.toLowerCase().includes(preset.id);
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            onClick={() => setCustomContext(preset.id)}
                            className={`p-1.5 rounded text-left text-[10px] transition-colors border ${
                              isActive
                                ? 'bg-cyan-950/60 border-cyan-500/40 text-cyan-200'
                                : 'bg-gray-800/50 border-white/5 text-gray-400 hover:border-white/15 hover:text-gray-200'
                            }`}
                          >
                            <div className="flex items-center gap-1">
                              <span>{preset.icon}</span>
                              <span className="font-medium truncate">{preset.label}</span>
                            </div>
                            <div className="text-[8px] opacity-70 mt-0.5 font-mono">
                              {preset.planet} · {preset.freq}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Genre */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}>Blessing Genre</Text>
                    <Select
                      value={genre}
                      onChange={setGenre}
                      size="small"
                      className="w-full"
                      style={{ marginTop: 4 }}
                      options={GENRE_OPTIONS}
                    />
                  </div>

                  <Divider style={{ margin: '4px 0' }} />

                  {/* Oracle Sources */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}>Oracle Sources</Text>
                    <Space orientation="vertical" size={4} style={{ marginTop: 4 }}>
                      <Space><Switch size="small" checked={includeAstrology} onChange={setIncludeAstrology} /><Text style={{ fontSize: 11 }}>🌟 Astrology</Text></Space>
                      <Space><Switch size="small" checked={includeTarot} onChange={setIncludeTarot} /><Text style={{ fontSize: 11 }}>🃏 Tarot</Text></Space>
                      <Space><Switch size="small" checked={includeIching} onChange={setIncludeIching} /><Text style={{ fontSize: 11 }}>☯️ I Ching</Text></Space>
                    </Space>
                  </div>

                  {/* Languages */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}>Weave Languages</Text>
                    <Select
                      mode="multiple"
                      size="small"
                      value={selectedLangs}
                      onChange={setSelectedLangs}
                      className="w-full"
                      style={{ marginTop: 4 }}
                      options={LANGUAGE_OPTIONS}
                    />
                  </div>

                  {/* Model */}
                  <div>
                    <Row justify="space-between" align="middle">
                      <Col><Text strong style={{ fontSize: 12 }}>LLM Model</Text></Col>
                      <Col>
                        <Tooltip title="Let the backend pick a random provider each run">
                          <Space size={4}>
                            <Switch size="small" checked={randomModel} onChange={setRandomModel} />
                            <Text style={{ fontSize: 11 }}><Dices className="w-3 h-3 inline mr-1" />🎲 Random</Text>
                          </Space>
                        </Tooltip>
                      </Col>
                    </Row>
                    <Select
                      size="small"
                      value={selectedModel || undefined}
                      onChange={setSelectedModel}
                      className="w-full"
                      style={{ marginTop: 4 }}
                      options={modelOptions}
                      placeholder="Auto-detect"
                      disabled={randomModel}
                      showSearch
                      optionFilterProp="label"
                      filterSort={(a: ModelSelectOption, b: ModelSelectOption) => a.label.localeCompare(b.label)}
                    />
                    {randomModel && (
                      <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 2 }}>
                        <Shuffle className="w-3 h-3 inline mr-1" />Provider rolled at generation time — selection disabled.
                      </Text>
                    )}
                  </div>

                  <Divider style={{ margin: '4px 0' }} />

                  {/* Characters — Collapsible */}
                  <Collapse ghost size="small" expandIconPlacement="end"
                    items={[{
                      key: 'chars', label: <Text strong style={{ fontSize: 12 }}><Shield className="w-3 h-3 inline mr-1" />Characters ({selectedCharIds.length})</Text>,
                      extra: <Tooltip title="Random 2-3"><Switch size="small" checked={randomizeCharacters} onChange={setRandomizeCharacters} /></Tooltip>,
                      children: (
                        <div className="max-h-40 overflow-y-auto">
                          <Space orientation="vertical" size={2} className="w-full">
                            {characters.map(c => (
                              <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
                                <Switch size="small" checked={selectedCharIds.includes(c.id)}
                                  onChange={checked => setSelectedCharIds(prev => checked ? [...prev, c.id] : prev.filter(id => id !== c.id))}
                                  disabled={randomizeCharacters} />
                                <Text style={{ fontSize: 11, flex: 1 }}>{c.name}</Text>
                                <Tag style={{ fontSize: 9 }}>{c.role}</Tag>
                              </div>
                            ))}
                          </Space>
                        </div>
                      ),
                    }]}
                  />

                  {/* Populations — Collapsible */}
                  <Collapse ghost size="small" expandIconPlacement="end"
                    items={[{
                      key: 'pops', label: <Text strong style={{ fontSize: 12 }}><Users className="w-3 h-3 inline mr-1" />Populations ({selectedPopIds.length})</Text>,
                      children: (
                        <div className="max-h-32 overflow-y-auto">
                          <Space orientation="vertical" size={2} className="w-full">
                            {populations.map(p => (
                              <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
                                <Switch size="small" checked={selectedPopIds.includes(p.id)}
                                  onChange={checked => setSelectedPopIds(prev => checked ? [...prev, p.id] : prev.filter(id => id !== p.id))} />
                                <Text style={{ fontSize: 11 }}>{p.name}</Text>
                              </div>
                            ))}
                          </Space>
                        </div>
                      ),
                    }]}
                  />

                  <Divider style={{ margin: '4px 0' }} />

                  {/* Dialogue */}
                  <Row justify="space-between" align="middle">
                    <Col><Text strong style={{ fontSize: 12 }}>Weave Dialogue</Text></Col>
                    <Col><Switch size="small" checked={includeDialogue} onChange={setIncludeDialogue} disabled={selectedCharIds.length === 0} /></Col>
                  </Row>

                  {/* Excluded Forces */}
                  <div>
                    <Text style={{ fontSize: 11 }}>Exclude Forces</Text>
                    <Input size="small" value={excludedForcesText} onChange={e => setExcludedForcesText(e.target.value)}
                      placeholder="sickness, doubt, obstacles" style={{ marginTop: 4 }} />
                  </div>

                  {/* Custom Context */}
                  <div>
                    <Text style={{ fontSize: 11 }}>Custom Aspiration</Text>
                    <Input.TextArea size="small" rows={2} value={customContext} onChange={e => setCustomContext(e.target.value)}
                      placeholder="Weave in intentions of peaceful passing for all beings..." style={{ marginTop: 4 }} />
                  </div>

                  <Divider style={{ margin: '4px 0' }} />

                  {/* Difficulty Level */}
                  <div>
                    <Text strong style={{ fontSize: 12 }}>Difficulty Level</Text>
                    <div className="grid grid-cols-3 gap-1.5" style={{ marginTop: 4 }}>
                      {DIFFICULTY_OPTIONS.map((opt) => (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => setDifficulty(opt.id)}
                          className={`p-1.5 rounded text-[10px] transition-colors border ${
                            difficulty === opt.id
                              ? 'bg-purple-950/60 border-purple-500/40 text-purple-200'
                              : 'bg-gray-800/50 border-white/5 text-gray-400 hover:border-white/15 hover:text-gray-200'
                          }`}
                          title={opt.desc}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Epic Toggle */}
                  <Row justify="space-between" align="middle">
                    <Col>
                      <Text strong style={{ fontSize: 12 }}>Epic Multi-Stage Journey</Text>
                      <br /><Text type="secondary" style={{ fontSize: 10 }}>Generate {stages} sequential narrative stages.</Text>
                    </Col>
                    <Col><Switch checked={isEpic} onChange={setIsEpic} /></Col>
                  </Row>
                  {isEpic && (
                    <Row align="middle" style={{ marginTop: 8 }}>
                      <Text style={{ fontSize: 12, marginRight: 8 }}>Stages:</Text>
                      <InputNumber size="small" min={3} max={15} value={stages} onChange={setStages} />
                    </Row>
                  )}

                  {/* Generate Button */}
                  <Button
                    type="primary"
                    block
                    size="large"
                    icon={loading ? <RefreshCw className="animate-spin w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                    onClick={handleGenerate}
                    loading={loading}
                    disabled={selectedLangs.length === 0}
                    style={{ background: 'linear-gradient(135deg, #0891b2, #0d9488)', border: 'none' }}
                  >
                    {loading ? 'Decrypting Transmission...' : 'Initiate Narrative Stream'}
                  </Button>
                 </Space>
               </Card>
                   </>
                 )}

                {/* ── Background Generation (unified) ── */}
               <Card
                 title={
                   <Text strong className="font-mono text-xs uppercase">
                     <Moon className="w-3 h-3 inline mr-1" />Background Generation
                     {bgActive && <Badge status="processing" color="purple" style={{ marginLeft: 8 }} />}
                   </Text>
                 }
                 size="small"
                 style={{ marginTop: 16 }}
               >
                 <Space orientation="vertical" className="w-full" size="middle">
                   <Row justify="space-between" align="middle">
                     <Col>
                       <Text style={{ fontSize: 12 }}>
                         Auto-generate blessings with full oracles. Saves to history.
                       </Text>
                     </Col>
                     <Col>
                       <Switch
                         checked={bgActive}
                         onChange={toggleBackgroundGeneration}
                         checkedChildren="🌙 On"
                         unCheckedChildren="Off"
                       />
                     </Col>
                   </Row>

                   <div>
                     <Text style={{ fontSize: 11 }}>Interval</Text>
                     <Select
                       value={bgInterval}
                       onChange={setBgInterval}
                       size="small"
                       disabled={bgActive}
                       className="w-full"
                       style={{ marginTop: 4 }}
                       options={[
                         { value: 5, label: 'Every 5 min (testing)' },
                         { value: 15, label: 'Every 15 min' },
                         { value: 30, label: 'Every 30 min' },
                         { value: 60, label: 'Every hour' },
                         { value: 180, label: 'Every 3 hours' },
                         { value: 360, label: 'Every 6 hours' },
                       ]}
                     />
                   </div>

                   <Segmented
                     block
                     size="small"
                     value={bgMode}
                     onChange={setBgMode}
                     disabled={bgActive}
                     options={[
                       { label: 'Sequential', value: 'sequential_delay' },
                       { label: 'Consecutive', value: 'consecutive' },
                     ]}
                   />

                   <div>
                     <Text style={{ fontSize: 11 }}>Oracle Sources</Text>
                     <Space orientation="vertical" size={4} style={{ marginTop: 4 }}>
                       <Space>
                         <Switch size="small" checked={bgAstrology} onChange={setBgAstrology} disabled={bgActive} />
                         <Text style={{ fontSize: 11 }}>🌟 Astrology</Text>
                       </Space>
                       <Space>
                         <Switch size="small" checked={bgTarot} onChange={setBgTarot} disabled={bgActive} />
                         <Text style={{ fontSize: 11 }}>🃏 Tarot</Text>
                       </Space>
                       <Space>
                         <Switch size="small" checked={bgIching} onChange={setBgIching} disabled={bgActive} />
                         <Text style={{ fontSize: 11 }}>☯️ I Ching</Text>
                       </Space>
                     </Space>
                   </div>

                   <Row justify="space-between" align="middle">
                     <Col>
                       <Checkbox
                         checked={bgCycleGenres}
                         onChange={e => setBgCycleGenres(e.target.checked)}
                         disabled={bgActive}
                         style={{ fontSize: 12 }}
                       >
                         🔄 Cycle all genres
                       </Checkbox>
                     </Col>
                   </Row>

                   {bgStats.total_generated > 0 && (
                     <div style={{ background: 'rgba(139,92,246,0.05)', padding: 8, borderRadius: 6 }}>
                       <Text style={{ fontSize: 10 }} className="font-mono">
                         <Bell className="w-3 h-3 inline mr-1" />
                         Generated: {bgStats.total_generated} · Saved: {bgStats.total_saved}
                         {bgStats.total_errors > 0 && ` · Errors: ${bgStats.total_errors}`}
                       </Text>
                       {bgStats.last_generated_at && (
                         <div>
                           <Text type="secondary" style={{ fontSize: 9 }}>
                             Last: {new Date(bgStats.last_generated_at).toLocaleString()}
                             {bgStats.last_genre && ` · ${bgStats.last_genre}`}
                           </Text>
                         </div>
                       )}
                     </div>
                   )}

                   {bgActive && (
                     <Text type="secondary" style={{ fontSize: 10 }}>
                       Running every {bgInterval} min — {bgMode === 'consecutive' ? 'consecutive (5s apart)' : 'sequential delay'}.
                       Genres {bgCycleGenres ? 'cycling' : 'fixed'}.
                     </Text>
                   )}
                 </Space>
               </Card>
              </Col>

            {/* ── Right: Narrative Display ── */}
            <Col xs={24} xl={16}>
              {loading ? (
                <Card>
                  <div className="flex flex-col items-center justify-center py-20">
                    <Spin size="large" />
                    <Text type="secondary" style={{ marginTop: 16 }}>Generating your narrative transmission...</Text>
                  </div>
                </Card>
              ) : currentNarrative ? (
                currentNarrative.type === 'epic' || currentNarrative.narrative_parts ? (
                  <>
                    {currentNarrative.model_used && (
                      <div style={{ marginBottom: 8 }}>
                        <Tag color="blue" style={{ fontSize: 10 }}>
                          🤖 {currentNarrative.provider_used || 'unknown'}/{currentNarrative.model_used}
                        </Tag>
                      </div>
                    )}
                    <EpicStoryViewer
                      narrativeParts={currentNarrative.narrative_parts}
                      astrologyContext={currentNarrative.astrology_used}
                      divinationContext={currentNarrative.divination_used}
                      divinationRaw={currentNarrative.divination_raw}
                      entitiesInvoked={currentNarrative.entities_used}
                    />
                  </>
                ) : (
                  <Row gutter={[24, 24]}>
                    <Col xs={24} lg={16}>
                      <Card
                        title={<Text strong className="font-mono text-xs uppercase">Transmission</Text>}
                        style={{ background: GENRE_COLORS[currentNarrative.genre || genre] || 'transparent', transition: 'background 0.8s ease' }}
                        extra={
                          <Space size={4}>
                            <NarrativeTTSPlayer
                              text={currentNarrative.narrative}
                              role="outlook_narrative"
                            />
                            <Button size="small" icon={copied ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                              onClick={copyNarrative}>{copied ? 'Copied' : 'Copy'}</Button>
                          </Space>
                        }
                      >
                        <Tabs
                          size="small"
                          activeKey={resultTab}
                          onChange={setResultTab}
                          items={[
                            {
                              key: 'narrative',
                              label: <span><BookOpen className="w-3 h-3 inline mr-1" />Narrative</span>,
                              children: (
                                <>
                                  <Title level={4} style={{ color: '#e2e8f0', textTransform: 'capitalize' }}>{currentNarrative.genre} Revelation</Title>
                                  {currentNarrative.model_used && (
                                    <div style={{ marginBottom: 8 }}>
                                      <Tag color="blue" style={{ fontSize: 10 }}>
                                        🤖 {currentNarrative.provider_used || 'unknown'}/{currentNarrative.model_used}
                                      </Tag>
                                    </div>
                                  )}
                                  <Divider />
                                  {sections.length > 1 ? (
                                    <>
                                      <div
                                        className="ritual-phase-dots"
                                        aria-label="Ritual phases"
                                        style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 12 }}
                                      >
                                        {RITUAL_PHASES.map((phase, i) => (
                                          <Tooltip key={phase} title={`${i + 1}. ${phase}`}>
                                            <div
                                              style={{
                                                width: 10,
                                                height: 10,
                                                borderRadius: '50%',
                                                background: i < revealedSections ? '#06b6d4' : 'rgba(148, 163, 184, 0.25)',
                                                boxShadow: i < revealedSections ? '0 0 8px rgba(6, 182, 212, 0.6)' : 'none',
                                                transition: 'background 0.6s ease, box-shadow 0.6s ease',
                                              }}
                                            />
                                          </Tooltip>
                                        ))}
                                      </div>
                                      {sections.slice(0, revealedSections).map((section, i) => (
                                        <Paragraph
                                          key={`section-${i}-${section.slice(0, 24)}`}
                                          className="ritual-section-fade"
                                          style={{
                                            whiteSpace: 'pre-wrap',
                                            fontSize: 14,
                                            lineHeight: 1.8,
                                            fontFamily: 'Georgia, serif',
                                            color: '#e5e7eb',
                                            marginBottom: 12,
                                          }}
                                        >
                                          {section}
                                        </Paragraph>
                                      ))}
                                      {revealedSections < sections.length && (
                                        <div style={{ textAlign: 'center', padding: '8px 0' }}>
                                          <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
                                            <RefreshCw className="w-3 h-3 inline mr-1 animate-spin" />
                                            Unveiling phase {revealedSections + 1} of {sections.length}…
                                          </Text>
                                        </div>
                                      )}
                                    </>
                                  ) : (
                                    <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.8, fontFamily: 'Georgia, serif', color: '#e5e7eb' }}>
                                      {currentNarrative.narrative}
                                    </Paragraph>
                                  )}
                                  {revealedSections >= sections.length && sections.length > 0 && currentNarrative.divination_raw?.sigil?.svg && (
                                    <div style={{ marginTop: 16, textAlign: 'center' }}>
                                      <div
                                        dangerouslySetInnerHTML={{ __html: currentNarrative.divination_raw.sigil.svg }}
                                        className="svg-container"
                                        style={{ maxWidth: 280, margin: '0 auto' }}
                                      />
                                      <Text type="secondary" style={{ fontSize: 11 }}>
                                        Sigil: {currentNarrative.divination_raw.sigil.reduced} on {currentNarrative.divination_raw.sigil.kamea} grid
                                      </Text>
                                    </div>
                                  )}
                                  {sections.length > 0 && revealedSections >= sections.length && (
                                    <Card
                                      title={<Text strong style={{ fontSize: 12 }}>📋 Ritual Summary</Text>}
                                      size="small"
                                      style={{ marginTop: 16, background: GENRE_COLORS[currentNarrative.genre || genre] || 'transparent' }}
                                    >
                                      <Row gutter={[8, 8]}>
                                        <Col xs={24} sm={12} md={8}>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Deity</Text>
                                          <div><Text strong style={{ fontSize: 12 }}>{currentNarrative.entities_used || currentNarrative.divination_used || '—'}</Text></div>
                                        </Col>
                                        <Col xs={24} sm={12} md={8}>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Genre</Text>
                                          <div><Text strong style={{ fontSize: 12, textTransform: 'capitalize' }}>{currentNarrative.genre || genre}</Text></div>
                                        </Col>
                                        <Col xs={24} sm={12} md={8}>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Model</Text>
                                          <div><Text strong style={{ fontSize: 12 }}>{currentNarrative.model_used ? `${currentNarrative.provider_used || 'unknown'}/${currentNarrative.model_used}` : '—'}</Text></div>
                                        </Col>
                                        <Col xs={24} sm={12} md={8}>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Tarot</Text>
                                          <div><Text strong style={{ fontSize: 12 }}>{currentNarrative.divination_raw?.tarot?.name || '—'}</Text></div>
                                        </Col>
                                        <Col xs={24} sm={12} md={8}>
                                          <Text type="secondary" style={{ fontSize: 10 }}>I Ching</Text>
                                          <div><Text strong style={{ fontSize: 12 }}>{currentNarrative.divination_raw?.iching?.name || '—'}</Text></div>
                                        </Col>
                                        <Col xs={24} sm={12} md={8}>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Kamea</Text>
                                          <div><Text strong style={{ fontSize: 12 }}>{currentNarrative.divination_raw?.sigil?.kamea || '—'}</Text></div>
                                        </Col>
                                      </Row>
                                      {currentNarrative.divination_raw?.sigil?.svg && (
                                        <div
                                          dangerouslySetInnerHTML={{ __html: currentNarrative.divination_raw.sigil.svg }}
                                          style={{ marginTop: 12, maxWidth: 160, marginLeft: 'auto', marginRight: 'auto' }}
                                        />
                                      )}
                                      <Space style={{ marginTop: 12 }} wrap>
                                        <Button size="small" icon={<Download className="w-3 h-3" />} onClick={saveCurrentRitual}>
                                          Save Ritual
                                        </Button>
                                        <Button size="small" icon={<Volume2 className="w-3 h-3" />} onClick={replayTTS}>
                                          Replay
                                        </Button>
                                        <Button
                                          size="small"
                                          icon={<Bell className="w-3 h-3" />}
                                          onClick={playDedicationBell}
                                        >
                                          Bell
                                        </Button>
                                      </Space>
                                    </Card>
                                  )}
                                </>
                              ),
                            },
                            {
                              key: 'affirmation',
                              label: <span><Sparkles className="w-3 h-3 inline mr-1" />Affirmation</span>,
                              children: (
                                <div className="py-4">
                                  {!affirmation ? (
                                    <div className="text-center space-y-3 py-6">
                                      <Text type="secondary" style={{ fontSize: 13 }}>
                                        Forge a personal affirmation from this transmission's intention.
                                      </Text>
                                      <Button
                                        type="primary"
                                        onClick={generateAffirmation}
                                        loading={affirmationLoading}
                                        icon={<Sparkles className="w-3.5 h-3.5" />}
                                        style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', border: 'none' }}
                                      >
                                        Generate Affirmation
                                      </Button>
                                    </div>
                                  ) : (
                                    <div>
                                      <div className="flex justify-between items-center mb-3">
                                        <Text strong style={{ fontSize: 12, color: '#fbbf24' }}>Empowering Affirmation</Text>
                                        <Button
                                          size="small"
                                          icon={affirmationCopied ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                                          onClick={copyAffirmation}
                                        >
                                          {affirmationCopied ? 'Copied' : 'Copy'}
                                        </Button>
                                      </div>
                                      <blockquote className="border-l-4 border-amber-500/50 pl-4 pr-2 italic text-amber-100 text-base leading-relaxed whitespace-pre-wrap">
                                        "{affirmation}"
                                      </blockquote>
                                      <div className="mt-4 text-center">
                                        <Button
                                          size="small"
                                          type="default"
                                          onClick={generateAffirmation}
                                          loading={affirmationLoading}
                                          icon={<RefreshCw className="w-3 h-3" />}
                                        >
                                          Regenerate
                                        </Button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ),
                            },
                          ]}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Space orientation="vertical" className="w-full" size="middle">
                        {/* Divination */}
                        {currentNarrative.divination_raw && (
                          <Card size="small" title={<Text strong className="font-mono text-xs uppercase">🔮 Esoteric Reading</Text>}>
                            {/* SVGs suppressed — they were taking up all available space.
                                The text descriptions below carry the same information. */}
                            {currentNarrative.divination_raw.tarot?.name && (
                              <div className="mb-2">
                                <Tag color="purple" style={{ fontSize: 10 }}>
                                  🃏 {currentNarrative.divination_raw.tarot.name}
                                  {currentNarrative.divination_raw.tarot.orientation ? ` (${currentNarrative.divination_raw.tarot.orientation})` : ''}
                                </Tag>
                              </div>
                            )}
                            {currentNarrative.divination_raw.iching?.name && (
                              <div className="mb-2">
                                <Tag color="cyan" style={{ fontSize: 10 }}>
                                  ☯️ {currentNarrative.divination_raw.iching.name}
                                  {currentNarrative.divination_raw.iching.changing_lines ? ` → ${currentNarrative.divination_raw.iching.relating_name || ''}` : ''}
                                </Tag>
                              </div>
                            )}
                            {currentNarrative.divination_used && (
                              <Paragraph style={{ fontSize: 11, fontStyle: 'italic' }} ellipsis={{ rows: 4 }}>
                                "{currentNarrative.divination_used}"
                              </Paragraph>
                            )}
                          </Card>
                        )}
                        {/* Astrology */}
                        {currentNarrative.astrology_used && (
                          <Card size="small" title={<Text strong className="font-mono text-xs uppercase"><Sun className="w-3 h-3 inline mr-1" />Astrology</Text>}>
                            <Paragraph style={{ fontSize: 11 }}>{currentNarrative.astrology_used}</Paragraph>
                          </Card>
                        )}
                        {/* Entities */}
                        {currentNarrative.entities_used && (
                          <Card size="small" title={<Text strong className="font-mono text-xs uppercase"><BookOpen className="w-3 h-3 inline mr-1" />Entities Invoked</Text>}>
                            <Paragraph style={{ fontSize: 11 }}>{currentNarrative.entities_used}</Paragraph>
                          </Card>
                        )}
                      </Space>
                    </Col>
                  </Row>
                )
              ) : (
                <Card>
                  <Empty
                    image={<Compass className="w-16 h-16" style={{ color: '#06b6d4', opacity: 0.4 }} />}
                    description={
                      <div>
                        <Title level={4} style={{ color: '#94a3b8' }}>Awaiting Narrative Beacon</Title>
                        <Text type="secondary">Configure settings on the left and initiate the stream to invoke a blessing sutra.</Text>
                      </div>
                    }
                  />
                </Card>
              )}
            </Col>
          </Row>
          </>
        )}

        {/* ═══════════════════════════════════════════════════════
            UNIVERSE TAB
        ═══════════════════════════════════════════════════════ */}
        {activeTab === 'universe' && (
          <Card size="small" styles={{ body: { padding: 0 } }}>
            <Tabs
              activeKey={universeTab}
              onChange={k => { setUniverseTab(k); audioFeedback.playClick(); }}
              style={{ padding: '0 16px' }}
              tabBarExtraContent={
                universeTab !== 'populations' && (
                  <Button type="primary" size="small" icon={<Plus className="w-3 h-3" />}
                    onClick={() => universeTab === 'realms' ? openRealmModal() : openCharModal()}>
                    New {universeTab === 'realms' ? 'Realm' : 'Character'}
                  </Button>
                )
              }
              items={[
                // ── Realms ──
                {
                  key: 'realms',
                  label: `Realms (${realms.length})`,
                  children: (
                    <div className="space-y-4">
                      {/* Filters */}
                      <Space wrap>
                        <Input
                          size="small"
                          placeholder="Search realms..."
                          prefix={<Search className="w-3 h-3" />}
                          value={realmSearch}
                          onChange={e => setRealmSearch(e.target.value)}
                          style={{ width: 200 }}
                          allowClear
                        />
                        <Select
                          size="small"
                          value={realmTypeFilter}
                          onChange={setRealmTypeFilter}
                          style={{ width: 150 }}
                          options={[
                            { value: 'all', label: 'All Types' },
                            ...(locationTypes.map(t => ({ value: t, label: t.replace(/_/g, ' ') }))),
                          ]}
                        />
                        <Text type="secondary" style={{ fontSize: 11 }}>{filteredRealms.length} of {realms.length} realms</Text>
                      </Space>

                      {/* Realm Grid */}
                      <Row gutter={[16, 16]}>
                        {filteredRealms.map(r => (
                          <Col xs={24} md={12} key={r.id}>
                            <Card
                              size="small"
                              hoverable
                              className={r.id === selectedRealmId ? 'border-cyan-500' : ''}
                              actions={[
                                <Tooltip title="Set as setting" key="set"><Button type="text" size="small"
                                  onClick={() => { setSelectedRealmId(r.id === selectedRealmId ? '' : r.id); audioFeedback.playClick(); }}>
                                  {r.id === selectedRealmId ? '📍 Active' : '📍 Set'}</Button></Tooltip>,
                                <Tooltip title="Edit" key="edit"><Button type="text" size="small" icon={<Edit2 className="w-3 h-3" />}
                                  onClick={() => openRealmModal(r)} /></Tooltip>,
                                <Tooltip title="Delete" key="del"><Button type="text" size="small" danger icon={<Trash2 className="w-3 h-3" />}
                                  onClick={() => deleteRealm(r.id)} /></Tooltip>,
                              ]}
                            >
                              <Card.Meta
                                title={<span>{r.name} <Tag style={{ fontSize: 9 }}>{r.location_type?.replace(/_/g, ' ')}</Tag></span>}
                                description={
                                  <div>
                                    <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, marginBottom: 8 }}>{r.description}</Paragraph>
                                    <Space size={[4, 4]} wrap>
                                      {r.is_metaphysical ? (
                                        <>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Freq: {r.dimension_frequency} Hz</Text>
                                          <Text type="secondary" style={{ fontSize: 10 }}>Coord: {r.celestial_coordinates || 'Uncharted'}</Text>
                                        </>
                                      ) : (
                                        <>
                                          <Text type="secondary" style={{ fontSize: 10 }}>LAT/LON: {r.latitude}/{r.longitude}</Text>
                                        </>
                                      )}
                                      <Text type="secondary" style={{ fontSize: 10 }}>Gov: {r.realm_governor || '—'}</Text>
                                      <Text type="secondary" style={{ fontSize: 10 }}>Featured: {r.total_narratives_featured || 0}×</Text>
                                    </Space>
                                  </div>
                                }
                              />
                            </Card>
                          </Col>
                        ))}
                        {filteredRealms.length === 0 && (
                          <Col span={24}><Empty description="No realms match your filters" /></Col>
                        )}
                      </Row>
                    </div>
                  ),
                },
                // ── Characters ──
                {
                  key: 'characters',
                  label: `Characters (${characters.length})`,
                  children: (
                    <div className="space-y-4">
                      <Space wrap>
                        <Input size="small" placeholder="Search characters..." prefix={<Search className="w-3 h-3" />}
                          value={charSearch} onChange={e => setCharSearch(e.target.value)} style={{ width: 200 }} allowClear />
                        <Select size="small" value={charRoleFilter} onChange={setCharRoleFilter} style={{ width: 130 }}
                          options={[{ value: 'all', label: 'All Roles' }, ...roles.map(r => ({ value: r, label: r.toUpperCase() }))]} />
                        <Text type="secondary" style={{ fontSize: 11 }}>{filteredCharacters.length} of {characters.length}</Text>
                      </Space>

                      <Row gutter={[16, 16]}>
                        {filteredCharacters.map(c => (
                          <Col xs={24} md={12} key={c.id}>
                            <Card
                              size="small"
                              hoverable
                              className={selectedCharIds.includes(c.id) ? 'border-purple-500' : ''}
                              actions={[
                                <Tooltip title={selectedCharIds.includes(c.id) ? 'Remove' : 'Add to narrative'} key="add">
                                  <Button type="text" size="small"
                                    onClick={() => setSelectedCharIds(prev => prev.includes(c.id) ? prev.filter(id => id !== c.id) : [...prev, c.id])}>
                                    {selectedCharIds.includes(c.id) ? '✓ Added' : '👤 Add'}</Button></Tooltip>,
                                <Tooltip title="Edit" key="edit"><Button type="text" size="small" icon={<Edit2 className="w-3 h-3" />}
                                  onClick={() => openCharModal(c)} /></Tooltip>,
                                <Tooltip title="Exile" key="del"><Button type="text" size="small" danger icon={<Trash2 className="w-3 h-3" />}
                                  onClick={() => deleteCharacter(c.id)} /></Tooltip>,
                              ]}
                            >
                              <Card.Meta
                                title={<span>{c.name} <Tag style={{ fontSize: 9 }}>{c.role}</Tag></span>}
                                description={
                                  <div>
                                    <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, marginBottom: 8 }}>{c.description}</Paragraph>
                                    <Space size={[4, 4]} wrap>
                                      {(c.tags || []).map(t => <Tag key={t} style={{ fontSize: 9 }}>{t}</Tag>)}
                                    </Space>
                                    <div style={{ marginTop: 8 }}>
                                      <Text type="secondary" style={{ fontSize: 10 }}>Mantra: {c.mantra_preference || '—'} · Element: {c.elemental_anchor} · Featured: {c.total_narratives_featured || 0}×</Text>
                                    </div>
                                  </div>
                                }
                              />
                            </Card>
                          </Col>
                        ))}
                        {filteredCharacters.length === 0 && (
                          <Col span={24}><Empty description="No characters match your filters" /></Col>
                        )}
                      </Row>
                    </div>
                  ),
                },
                // ── Populations ──
                {
                  key: 'populations',
                  label: `Populations (${populations.length})`,
                  children: (
                    <Row gutter={[16, 16]}>
                      {populations.map(p => (
                        <Col xs={24} md={12} key={p.id}>
                          <Card size="small" hoverable>
                            <Card.Meta
                              title={<span>{p.name} {p.is_urgent && '🔥'}</span>}
                              description={
                                <div>
                                  <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12 }}>{p.description}</Paragraph>
                                  <Space size={[4, 4]} wrap style={{ marginTop: 8 }}>
                                    <Tag color={p.is_active ? 'green' : 'default'}>{p.is_active ? 'ACTIVE' : 'INACTIVE'}</Tag>
                                    <Text type="secondary" style={{ fontSize: 10 }}>Intentions: {p.intentions?.join(', ')}</Text>
                                    <Text type="secondary" style={{ fontSize: 10 }}>Category: {p.category}</Text>
                                    <Text type="secondary" style={{ fontSize: 10 }}>Priority: {p.priority}/10</Text>
                                  </Space>
                                </div>
                              }
                            />
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  ),
                },
              ]}
            />
          </Card>
        )}

        {/* ═══════════════════════════════════════════════════════
            HISTORY TAB
        ═══════════════════════════════════════════════════════ */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <Card size="small">
              <Row justify="space-between" align="middle">
                <Col>
                  <Space>
                    <History className="w-4 h-4 text-cyan-400" />
                    <Text strong className="font-mono text-xs uppercase">Past Transmissions</Text>
                    <Tag color="cyan">{historyList.length}</Tag>
                  </Space>
                </Col>
                <Col>
                  <Space>
                    <Select
                      size="small"
                      value={historyGenreFilter}
                      onChange={setHistoryGenreFilter}
                      style={{ width: 150 }}
                      options={[
                        { value: 'all', label: 'All Genres' },
                        ...Array.from(new Set(historyList.map(h => h.genre).filter(Boolean))).map(g => ({ value: g!, label: g!.charAt(0).toUpperCase() + g!.slice(1) })),
                      ]}
                    />
                    <Button size="small" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchHistory}>Refresh</Button>
                  </Space>
                </Col>
              </Row>
            </Card>

            {historyList.length === 0 ? (
              <Card>
                <Empty
                  image={<Compass className="w-16 h-16" style={{ color: '#06b6d4', opacity: 0.4 }} />}
                  description={
                    <div>
                      <Title level={4} style={{ color: '#94a3b8' }}>No Transmissions Yet</Title>
                      <Text type="secondary">Create one in the Generator tab.</Text>
                    </div>
                  }
                />
              </Card>
            ) : (
              <Row gutter={[16, 16]}>
                {historyList
                  .filter(item => historyGenreFilter === 'all' || item.genre === historyGenreFilter)
                  .map((item, idx) => {
                    const genre = item.genre || 'unknown';
                    const genreColor = GENRE_COLORS[genre] || 'transparent';
                    const borderColor = GENRE_BORDER_COLORS[genre] || '#334155';
                    const rawContent = item.type === 'epic' ? 'Multi-stage epic narrative' : (item.content || '');
                    const preview = stripMarkdown(rawContent);
                    const date = item.date_generated ? new Date(item.date_generated) : null;
                    return (
                      <Col xs={24} md={12} lg={8} key={`hist-${idx}`}>
                        <Card
                          size="small"
                          hoverable
                          style={{
                            background: genreColor,
                            borderLeft: `3px solid ${borderColor}`,
                            transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
                          }}
                          actions={[
                            <Tooltip title="Load in Generator" key="load">
                              <Button
                                type="text"
                                size="small"
                                icon={<Play className="w-3 h-3" />}
                                onClick={() => { loadHistoryItem(item); setActiveTab('generator'); audioFeedback.playClick(); }}
                              />
                            </Tooltip>,
                            <Tooltip title="Copy text" key="copy">
                              <Button
                                type="text"
                                size="small"
                                icon={<Copy className="w-3 h-3" />}
                                onClick={() => {
                                  navigator.clipboard.writeText(item.content || '');
                                  message.success('Copied narrative text.');
                                  audioFeedback.playSuccess();
                                }}
                              />
                            </Tooltip>,
                            <Tooltip title="Save to archive" key="save">
                              <Button
                                type="text"
                                size="small"
                                icon={<Download className="w-3 h-3" />}
                                onClick={() => {
                                  const entry: SavedRitual = {
                                    id: `ritual_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
                                    savedAt: new Date().toISOString(),
                                    genre: item.genre || 'unknown',
                                    narrative: item.content || '',
                                    divinationRaw: item.divination_raw || null,
                                    entities: item.entities_invoked || null,
                                    model: null,
                                    provider: null,
                                  };
                                  try {
                                    const existing = JSON.parse(window.localStorage.getItem(SAVED_RITUALS_KEY) || '[]') as SavedRitual[];
                                    window.localStorage.setItem(SAVED_RITUALS_KEY, JSON.stringify([entry, ...existing].slice(0, 50)));
                                    message.success('Saved to local archive.');
                                  } catch {
                                    message.error('Could not save — storage full or disabled.');
                                  }
                                }}
                              />
                            </Tooltip>,
                          ]}
                        >
                          <Card.Meta
                            title={
                              <Space size={4}>
                                <Text strong className="capitalize" style={{ fontSize: 13 }}>{genre}</Text>
                                <Tag color={item.type === 'epic' ? 'purple' : 'cyan'} style={{ fontSize: 9 }}>
                                  {item.type === 'epic' ? 'EPIC' : 'SINGLE'}
                                </Tag>
                              </Space>
                            }
                            description={
                              <div>
                                <Paragraph
                                  ellipsis={{ rows: 3 }}
                                  style={{ fontSize: 11, color: '#94a3b8', marginBottom: 8, lineHeight: 1.5 }}
                                >
                                  {preview || '(empty)'}
                                </Paragraph>
                                <Space size={[8, 4]} wrap>
                                  {date && (
                                    <Text type="secondary" style={{ fontSize: 10 }}>
                                      <Clock className="w-2.5 h-2.5 inline mr-1" />
                                      {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </Text>
                                  )}
                                  {item.entities_invoked && (
                                    <Tag style={{ fontSize: 9, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                      👤 {item.entities_invoked}
                                    </Tag>
                                  )}
                                  {item.divination_context && (
                                    <Tag style={{ fontSize: 9, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                      🔮 {item.divination_context}
                                    </Tag>
                                  )}
                                </Space>
                              </div>
                            }
                          />
                        </Card>
                      </Col>
                    );
                  })}
              </Row>
            )}
          </div>
        )}

        {activeTab === 'journey' && (
          <div className="max-w-2xl mx-auto">
            <JourneyCard />
          </div>
        )}
      </Space>

      {/* ═══════════════════════════════════════════════════════
          REALM MODAL
      ═══════════════════════════════════════════════════════ */}
      <Modal
        title={editingRealm ? 'Edit Realm' : 'Create New Realm'}
        open={realmModalOpen}
        onCancel={() => setRealmModalOpen(false)}
        onOk={saveRealm}
        okText="Save"
        width={640}
        destroyOnHidden
      >
        <Form form={realmForm} layout="vertical" size="small" initialValues={{ is_metaphysical: true, priority: 5, source_type: 'manual' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Mount Kailash" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="location_type" label="Type">
                <Select options={(locationTypes || ['metaphysical_realm', 'earthly_sacred', 'cosmic_anchor', 'historical_academy']).map(t => ({ value: t, label: t.replace(/_/g, ' ') }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="is_metaphysical" label="Metaphysical Realm?" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.is_metaphysical !== cur.is_metaphysical}>
            {({ getFieldValue }) => {
              const isMeta = getFieldValue('is_metaphysical') !== false;
              return isMeta ? (
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="celestial_coordinates" label="Celestial Coordinates">
                      <Input placeholder="e.g. Northern Axis" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="dimension_frequency" label="Dimension Frequency (Hz)">
                      <InputNumber className="w-full" step={0.1} />
                    </Form.Item>
                  </Col>
                </Row>
              ) : (
                <Row gutter={16}>
                  <Col span={8}><Form.Item name="latitude" label="Latitude"><InputNumber className="w-full" step={0.0001} /></Form.Item></Col>
                  <Col span={8}><Form.Item name="longitude" label="Longitude"><InputNumber className="w-full" step={0.0001} /></Form.Item></Col>
                  <Col span={8}><Form.Item name="timezone" label="Timezone"><Input placeholder="UTC" /></Form.Item></Col>
                </Row>
              );
            }}
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="realm_governor" label="Governor"><Input placeholder="Ruler/Deity" /></Form.Item></Col>
            <Col span={8}><Form.Item name="astrological_anchor" label="Astro Anchor"><Input placeholder="e.g. Saturn MC" /></Form.Item></Col>
            <Col span={8}><Form.Item name="elemental_affinity" label="Element"><Input placeholder="e.g. Aether" /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="priority" label="Priority"><InputNumber className="w-full" min={1} max={10} /></Form.Item></Col>
            <Col span={12}><Form.Item name="source_type" label="Source"><Select options={['manual', 'generated', 'mythology', 'geographic'].map(s => ({ value: s, label: s }))} /></Form.Item></Col>
          </Row>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ═══════════════════════════════════════════════════════
          CHARACTER MODAL
      ═══════════════════════════════════════════════════════ */}
      <Modal
        title={editingChar ? 'Edit Character' : 'Create Character'}
        open={charModalOpen}
        onCancel={() => setCharModalOpen(false)}
        onOk={saveCharacter}
        okText="Save"
        width={560}
        destroyOnHidden
      >
        <Form form={charForm} layout="vertical" size="small" initialValues={{ role: 'master', source_type: 'manual', elemental_anchor: 'space', priority: 5 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Zen Master Zhao" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role" label="Role">
                <Select options={(roles || ['master', 'student', 'alchemist', 'hero', 'deity', 'guardian', 'custom']).map(r => ({ value: r, label: r.toUpperCase() }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="dialogue_style" label="Dialogue Style">
            <Input placeholder="e.g. riddle-like, Zen Koans" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="mantra_preference" label="Mantra">
                <Input placeholder="om_mani_padme_hum" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="elemental_anchor" label="Elemental Anchor">
                <Select options={['space', 'earth', 'water', 'fire', 'air', 'aether'].map(e => ({ value: e, label: e }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="priority" label="Priority"><InputNumber className="w-full" min={1} max={10} /></Form.Item></Col>
            <Col span={12}><Form.Item name="source_type" label="Source"><Select options={['manual', 'generated', 'mythology', 'historical'].map(s => ({ value: s, label: s }))} /></Form.Item></Col>
          </Row>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
