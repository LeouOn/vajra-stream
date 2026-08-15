import { describe, it, expect } from 'vitest';
import { FEATURED_MODEL_IDS, featuredFallbackChoices } from '../lib/featuredModels';

describe('featuredModels', () => {
  it('includes Laguna, DeepSeek, and Nemotron', () => {
    expect(FEATURED_MODEL_IDS).toContain('poolside/laguna-s-2.1:free');
    expect(FEATURED_MODEL_IDS).toContain('poolside/laguna-xs-2.1:free');
    expect(FEATURED_MODEL_IDS).toContain('deepseek/deepseek-v4-flash');
    expect(FEATURED_MODEL_IDS).toContain('nvidia/nemotron-3-ultra-550b-a55b:free');
  });

  it('does not advertise withdrawn free slugs', () => {
    expect(FEATURED_MODEL_IDS).not.toContain('inclusionai/ling-3.0-flash:free');
  });

  it('fallback choices keep ids selectable offline', () => {
    const ids = featuredFallbackChoices().map((m) => m.id);
    expect(ids).toEqual([...FEATURED_MODEL_IDS]);
  });
});
