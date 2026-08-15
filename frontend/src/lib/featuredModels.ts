/**
 * Featured OpenRouter slugs shown at the top of Command Center / Outlook
 * pickers when the live catalog is empty. Keep in sync with
 * ``KNOWN_FEATURED_MODEL_IDS`` in ``core/llm/defaults.py``.
 */
export const FEATURED_MODEL_IDS: readonly string[] = [
  'nvidia/nemotron-3-ultra-550b-a55b:free',
  'nvidia/nemotron-3.5-lightning:free',
  'poolside/laguna-s-2.1:free',
  'poolside/laguna-xs-2.1:free',
  'deepseek/deepseek-v4-flash',
  'minimax/minimax-m3',
  'inclusionai/ling-3.0-flash',
  'openai/gpt-4o-mini',
];

export const FEATURED_MODEL_LABELS: Record<string, string> = {
  'nvidia/nemotron-3-ultra-550b-a55b:free': 'Nemotron 3 Ultra 550B (Free)',
  'nvidia/nemotron-3.5-lightning:free': 'Nemotron 3.5 Lightning (Free)',
  'poolside/laguna-s-2.1:free': 'Laguna S 2.1 (Free)',
  'poolside/laguna-xs-2.1:free': 'Laguna XS 2.1 (Free)',
  'deepseek/deepseek-v4-flash': 'DeepSeek V4 Flash',
  'minimax/minimax-m3': 'MiniMax M3',
  'inclusionai/ling-3.0-flash': 'Ling 3.0 Flash',
  'openai/gpt-4o-mini': 'GPT-4o mini',
};

export interface FeaturedModelChoice {
  id: string;
  name: string;
  is_free: boolean;
}

export function featuredFallbackChoices(): FeaturedModelChoice[] {
  return FEATURED_MODEL_IDS.map((id) => ({
    id,
    name: FEATURED_MODEL_LABELS[id] || id,
    is_free: id.endsWith(':free'),
  }));
}
