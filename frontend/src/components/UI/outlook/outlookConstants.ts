/**
 * outlookConstants.ts — static option lists and seed data for the Outlook
 * Generator. Option arrays are computed once at module load so they are
 * stable across renders.
 */
import type { Character } from './outlookShared';

export interface GenreOption {
  value: string;
  label: string;
  desc: string;
}

export interface DifficultyOption {
  id: string;
  label: string;
  desc: string;
}

export interface GlobalIntention {
  id: string;
  label: string;
  planet: string;
  freq: string;
  icon: string;
}

export const GENRES: GenreOption[] = [
  { value: 'healing', label: '🌿 Healing', desc: 'Sutra of restoration, pacifying sickness & anxiety' },
  { value: 'victory', label: '🛡️ Victory', desc: 'Overcoming limitations, spiritual warfare & triumph' },
  { value: 'alchemist', label: '⚗️ Alchemist', desc: 'Hermetic parables of chemical transmutations' },
  { value: 'fun_parable', label: '☯️ Fun Parable', desc: 'Lighthearted Zen/Sufi teaching jokes' },
  { value: 'dharani', label: '📿 Dharani', desc: 'Dense mantras and direct invocations of power' },
];

export const LANGUAGES: string[] = [
  'English', 'Sanskrit', 'Tibetan', 'Chinese', 'Latin', 'Greek', 'Hebrew',
];

// Pre-compute option arrays from module-level constants so they're stable
// across renders (previously each .map() created a new array on every render).
export const GENRE_OPTIONS = GENRES.map(g => ({ value: g.value, label: g.label }));
export const LANGUAGE_OPTIONS = LANGUAGES.map(l => ({ value: l, label: l }));

export const RITUAL_PHASES: string[] = [
  'Invocatio',
  'Pacificatio',
  'Attunement',
  'Sigillum',
  'Dedicatio',
];

export const DIFFICULTY_OPTIONS: DifficultyOption[] = [
  { id: 'mild', label: 'Mild', desc: 'Minor obstacles and everyday challenges' },
  { id: 'moderate', label: 'Moderate', desc: 'Persistent patterns and recurring issues' },
  { id: 'deep', label: 'Deep', desc: 'Profound wounds and life-changing difficulties' },
];

export const GLOBAL_INTENTIONS: GlobalIntention[] = [
  { id: 'world peace', label: 'World Peace', planet: 'Jupiter', freq: '852Hz', icon: '🕊' },  // dove
  { id: 'world prosperity', label: 'World Prosperity', planet: 'Venus', freq: '528Hz', icon: '💎' },  // gem
  { id: 'end to disease and cancer', label: 'End Disease & Cancer', planet: 'Sun', freq: '528Hz', icon: '☀️' },  // sun
  { id: 'happiness', label: 'Happiness', planet: 'Jupiter', freq: '528Hz', icon: '🌟' },  // star
  { id: 'reforestation the world', label: 'Reforestation', planet: 'Earth', freq: '528Hz', icon: '🌲' },  // tree
  { id: 'cleaning up pollution', label: 'Clean Pollution', planet: 'Saturn', freq: '396Hz', icon: '🌊' },  // wave
];

export const BG_INTERVAL_OPTIONS = [
  { value: 5, label: 'Every 5 min (testing)' },
  { value: 15, label: 'Every 15 min' },
  { value: 30, label: 'Every 30 min' },
  { value: 60, label: 'Every hour' },
  { value: 180, label: 'Every 3 hours' },
  { value: 360, label: 'Every 6 hours' },
];

export const DEFAULT_CHARACTERS: Character[] = [
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
