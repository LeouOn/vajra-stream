/**
 * Shared practice catalog — single source of truth for the canonical
 * Buddhist practices surfaced by the practice library.
 *
 * Lives outside PracticeSelector / PracticeDetail so both pages can
 * resolve a practice by id without re-fetching or duplicating the seed
 * data. The PracticeSelector prefers backend data when reachable and
 * falls back to this list; PracticeDetail uses this list as the seed
 * and overlays backend status (running/count) when reachable.
 *
 * If/when the backend exposes a full `/practices/:id` endpoint that
 * returns the same shape, swap the in-memory lookup for a fetch — the
 * component contract stays identical.
 */
import {
  BookOpen,
  Leaf,
  Sun,
  Sparkles,
  Heart,
  Shield,
  Flame,
  Compass,
  CircleDot,
  type LucideIcon,
} from 'lucide-react';

export interface Practice {
  id: string;
  name: string;
  /** Optional Sanskrit / Tibetan transliteration shown under the name. */
  transliteration?: string;
  description: string;
  /** Brand-color accent (hex). Used for the top-bar, icon halo, and hover glow. */
  color: string;
  /** RGB triple (no alpha) — lets us compose rgba() per use-site. */
  colorRgb: string;
  /** Lucide icon component. */
  icon: LucideIcon;
  /** Short benefit bullets surfaced on the detail page. */
  benefits: string[];
  /** Sanskrit mantra transliteration (shown on detail page). */
  mantra?: string;
  /** English meaning (shown on detail page). */
  mantraMeaning?: string;
  /** Practice instructions — short prose. */
  instructions?: string;
  /**
   * Resonant bowl frequency in Hz for the ambient drone. Used by the
   * PracticeDetail ambient-bowl oscillator when the toggle is on and
   * TTS is speaking. Falls back to the audio store default when omitted.
   */
  frequencyHz?: number;
}

export const PRACTICES: Practice[] = [
  {
    id: '88_buddhas',
    name: '88 Buddhas',
    transliteration: 'Bāshíbā Fó',
    description:
      'The Great Confession of the 88 Buddhas — purification through recitation.',
    color: '#fbbf24',
    colorRgb: '251 191 36',
    icon: BookOpen,
    benefits: [
      'Purifies negative karma accumulated across lifetimes',
      'Opens the path of the 53 Past Buddhas and 35 Confession Buddhas',
      'Cultivates the bodhisattva vow of sincere repentance',
    ],
    mantra: 'Namo Bāshíbā Fó',
    mantraMeaning: 'Homage to the 88 Buddhas',
    instructions:
      'Recite the names of the 88 Buddhas in sequence, visualizing each Buddha at the crown of your head emitting purifying light that cleanses negative karma.',
    frequencyHz: 136.1,
  },
  {
    id: 'green_tara',
    name: 'Green Tara',
    transliteration: 'Shye Tara',
    description:
      'Swift protectoress — overcomes fear, danger, and obstacles.',
    color: '#10b981',
    colorRgb: '16 185 129',
    icon: Leaf,
    benefits: [
      'Overcomes fear, anxiety, and eight classes of obstacles',
      'Swift compassionate action in response to danger',
      'Heals sickness and stabilizes relationships',
    ],
    mantra: 'Om Tāre Tuttāre Ture Svāhā',
    mantraMeaning: 'May Tara liberate us from suffering',
    instructions:
      'Visualize Green Tara at your heart, emerald-green, seated on a lotus. With each recitation, send her compassionate activity out into the world to liberate all beings from the eight fears.',
    frequencyHz: 261.63,
  },
  {
    id: 'white_tara',
    name: 'White Tara',
    transliteration: 'Karma Tara',
    description:
      'Mother of long life, healing, and compassionate merit.',
    color: '#e0e7ff',
    colorRgb: '224 231 255',
    icon: Sparkles,
    benefits: [
      'Bestows long life and removes obstacles to longevity',
      'Heals illness and stabilizes vital energy',
      'Cultivates compassionate serenity like the full moon',
    ],
    mantra: 'Om Tāre Tuttāre Ture Mama Āyu Punya Jñāna Pustim Kuru Svāhā',
    mantraMeaning: 'May Tara bestow long life, merit, and wisdom',
    instructions:
      'Visualize White Tara seated on a moon disc, peaceful and smiling, with seven eyes (palms, soles, forehead) seeing all suffering. Recite to extend your lifespan and that of all beings.',
    frequencyHz: 293.66,
  },
  {
    id: 'zhunti',
    name: 'Zhunti',
    transliteration: 'Cundi',
    description:
      'The bodhisattva of pure awareness — clears obscurations.',
    color: '#fbbf24',
    colorRgb: '251 191 36',
    icon: Sun,
    benefits: [
      'Cuts through delusion at its root',
      'Purifies the three poisons (greed, aversion, ignorance)',
      "Empowers prajñā — the wisdom of emptiness",
    ],
    mantra: 'Namo Cundi Bodhisattva',
    mantraMeaning: 'Homage to the Bodhisattva of Pure Awareness',
    instructions:
      'Visualize Cundi Bodhisattva, pure and serene, atop a lotus. Each recitation purifies obscurations and sharpens discriminating-awareness wisdom.',
    frequencyHz: 329.63,
  },
  {
    id: 'medicine_buddha',
    name: 'Medicine Buddha',
    transliteration: 'Yao Shi Fo',
    description:
      'Heals physical and mental illness, purifies karma of body.',
    color: '#3b82f6',
    colorRgb: '59 130 246',
    icon: Heart,
    benefits: [
      'Alleviates physical and mental illness',
      'Purifies the karma of body, speech, and mind',
      'Confers the healing radiance of lapis lazuli light',
    ],
    mantra: 'Tadyathā Om Bhekaṇḍze Bhekaṇḍze Mahābhekaṇḍze Raḍza Samudgate Svāhā',
    mantraMeaning: 'May all beings be healed of sickness',
    instructions:
      'Visualize Medicine Buddha, deep blue as lapis lazuli, holding a medicine bowl and the stem of a myrobalan plant. Rays of blue light emanate from his heart, healing all illness.',
    frequencyHz: 528.0,
  },
  {
    id: 'vajrasattva',
    name: 'Vajrasattva',
    transliteration: 'Dorje Sempa',
    description:
      'Indestructible purity — the 100-syllable mantra of confession.',
    color: '#f8fafc',
    colorRgb: '248 250 252',
    icon: Shield,
    benefits: [
      'Cleanses negative karma and broken vows',
      'Restores the purity of body, speech, and mind',
      'Strengthens samaya commitments and bodhicitta',
    ],
    mantra: 'Om Vajrasattva Samaya Manu Pālaya Vajrasattva Tveno Paṭiṣṭha Dṛḍho Me Bhava Sutoṣyo Me Bhava Supoṣyo Me Bhava Anurakto Me Bhava Sarva Siddhiṃ Me Prayaccha Sarva Karma Su Cā Me Cittam Śreyaḥ Kuru Hūṃ Ha Ha Ha Ha Hoḥ Bhagavān Sarva Tathāgata Vajra Mā Me Muñca Vajra Bhāva Mahā Samaya Sattva Āḥ',
    mantraMeaning: 'May Vajrasattva purify all obscurations',
    instructions:
      'Visualize Vajrasattva, white as the full moon, holding a vajra and bell at your crown. With each recitation, nectar streams down from his heart, purifying all broken vows and negative karma.',
    frequencyHz: 396.0,
  },
  {
    id: 'amitabha',
    name: 'Amitabha',
    transliteration: 'Āmítuó Fó',
    description:
      'Boundless light — recitation calls forth Sukhāvatī, the Pure Land.',
    color: '#f43f5e',
    colorRgb: '244 63 94',
    icon: Flame,
    benefits: [
      'Builds karmic connection with Amitabha and the Pure Land',
      'Brings peace at the moment of death and beyond',
      'Cultivates the boundless light of discriminating wisdom',
    ],
    mantra: 'Namo Āmítuó Fó',
    mantraMeaning: 'Homage to Amitābha Buddha of Infinite Light',
    instructions:
      'Visualize Amitābha, ruby-red and radiant, seated in Sukhāvatī. Recitations build the karmic cause to be reborn in his Western Pure Land at the moment of death.',
    frequencyHz: 174.61,
  },
  {
    id: 'avalokiteshvara',
    name: 'Avalokiteshvara',
    transliteration: 'Chenrezig',
    description:
      "The bodhisattva of compassion — embodiment of all Buddhas' kindness.",
    color: '#06b6d4',
    colorRgb: '6 182 212',
    icon: Compass,
    benefits: [
      'Develops universal compassion for all beings',
      'Liberates from fear, hatred, and attachment',
      'Embodies the four immeasurables — love, joy, equanimity, compassion',
    ],
    mantra: 'Om Maṇi Padme Hūṃ',
    mantraMeaning: 'The jewel is in the lotus — may compassion arise',
    instructions:
      "Visualize Chenrezig, white and four-armed, at your crown. Each recitation of the six syllables opens the lotus of your heart and liberates all beings from the six realms of samsāra.",
    frequencyHz: 220.0,
  },
  {
    id: 'heart_sutra',
    name: 'Heart Sutra',
    transliteration: 'Prajñāpāramitā Hṛdaya',
    description: 'The condensed essence of the Perfection of Wisdom.',
    color: '#8b5cf6',
    colorRgb: '139 92 246',
    icon: CircleDot,
    benefits: [
      'Cuts through conceptual grasping at the root',
      'Realizes the union of form and emptiness',
      'The shortest path to the heart of Mahāyāna view',
    ],
    mantra: 'Gate Gate Pāragate Pārasaṃgate Bodhi Svāhā',
    mantraMeaning:
      'Gone, gone, gone beyond, gone utterly beyond — awakening, so be it',
    instructions:
      'Recite the Heart Sutra, contemplating form as emptiness and emptiness as form. The closing mantra seals the realization of prajñāpāramitā.',
    frequencyHz: 432.0,
  },
];

/** Resolve a practice by id. Returns undefined if no match. */
export function getPracticeById(id: string | undefined): Practice | undefined {
  if (!id) return undefined;
  return PRACTICES.find((p) => p.id === id);
}