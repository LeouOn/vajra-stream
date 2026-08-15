import { describe, it, expect } from 'vitest';
import { resolveChatRoute } from '../../utils/chatRoute';

const catalog = [
  {
    id: 'nvidia/nemotron-3-ultra-550b-a55b:free',
    name: 'Nemotron',
    provider: 'nvidia',
    context_length: 1,
    input_per_m: 0,
    output_per_m: 0,
    is_free: true,
    featured: true,
    description: '',
    source: 'openrouter',
  },
];

describe('resolveChatRoute', () => {
  it('keeps Auto as registry pick_best', () => {
    expect(resolveChatRoute('auto', catalog)).toEqual({ provider: 'auto', model: null });
  });

  it('sends OpenRouter catalog ids to the openrouter provider', () => {
    expect(resolveChatRoute('nvidia/nemotron-3-ultra-550b-a55b:free', catalog)).toEqual({
      provider: 'openrouter',
      model: 'nvidia/nemotron-3-ultra-550b-a55b:free',
    });
  });

  it('strips the lm_studio launcher prefix', () => {
    expect(resolveChatRoute('lm_studio:qwen2.5', [])).toEqual({
      provider: 'lm_studio',
      model: 'qwen2.5',
    });
  });

  it('routes Laguna and DeepSeek slash-ids to OpenRouter', () => {
    expect(resolveChatRoute('poolside/laguna-s-2.1:free', [])).toEqual({
      provider: 'openrouter',
      model: 'poolside/laguna-s-2.1:free',
    });
    expect(resolveChatRoute('poolside/laguna-xs-2.1:free', [])).toEqual({
      provider: 'openrouter',
      model: 'poolside/laguna-xs-2.1:free',
    });
    expect(resolveChatRoute('deepseek/deepseek-v4-flash', [])).toEqual({
      provider: 'openrouter',
      model: 'deepseek/deepseek-v4-flash',
    });
  });
});
