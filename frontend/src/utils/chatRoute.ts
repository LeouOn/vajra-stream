/** Registered LLM providers in ``core/llm/bootstrap.py``. */
const REGISTRY_PROVIDERS = new Set([
  'openrouter',
  'lm_studio',
  'local',
  'deepseek',
  'anthropic',
  'openai',
  'minimax',
  'z_ai',
]);

export interface ChatModelMeta {
  id: string;
  provider: string;
  source?: string;
}

/** Map the model dropdown value onto a registered provider + bare model id. */
export function resolveChatRoute(
  model: string,
  catalog: ChatModelMeta[],
): { provider: string; model: string | null } {
  if (!model || model === 'auto') {
    return { provider: 'auto', model: null };
  }
  if (model.startsWith('lm_studio:')) {
    return { provider: 'lm_studio', model: model.slice('lm_studio:'.length) };
  }
  if (model.startsWith('local:')) {
    return { provider: 'local', model: model.slice('local:'.length) };
  }
  const meta = catalog.find((m) => m.id === model);
  if (meta?.source === 'openrouter' || model.includes('/')) {
    return { provider: 'openrouter', model };
  }
  if (meta && REGISTRY_PROVIDERS.has(meta.provider)) {
    return { provider: meta.provider, model };
  }
  return { provider: 'auto', model };
}
