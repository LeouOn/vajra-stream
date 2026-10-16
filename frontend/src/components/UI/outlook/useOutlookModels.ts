/**
 * useOutlookModels — the Generator's LLM model picker: available models,
 * the server's Outlook default, the featured catalog, provider health, and
 * the derived Select options.
 */
import { useState, useCallback, useMemo } from 'react';
import { apiUrl } from '../../../utils/api';
import { createLogger } from '../../../utils/logger';
import { featuredFallbackChoices, type FeaturedModelChoice } from '../../../lib/featuredModels';
import type { AddToast } from './outlookShared';

export interface OutlookModels {
  lm_studio?: string[];
  local?: string[];
  api?: string[];
}

export interface ModelSelectOption {
  value: string;
  label: string;
}

const log = createLogger('OutlookDashboard');

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

/**
 * Build the model Select options: auto-detect sentinel, featured models,
 * the Outlook default, healthy API providers, LM Studio and local models,
 * de-duplicated by value (first wins).
 */
export function buildOutlookModelOptions(
  outlookModels: OutlookModels,
  healthyProviders: Record<string, boolean>,
  outlookDefaultModel: string,
  featuredModels: FeaturedModelChoice[],
): ModelSelectOption[] {
  // Sentinel: '' → backend auto-detect (registry.pick_best()).
  const opts: ModelSelectOption[] = [
    { value: '', label: '✨ Auto-detect (Nemotron Ultra)' },
  ];
  featuredModels.forEach((m) => {
    const tag = m.is_free ? 'FREE' : 'paid';
    opts.push({
      value: m.id,
      label: `${m.is_free ? '🆓' : '💳'} ${m.name} (${tag})`,
    });
  });
  if (outlookDefaultModel && !featuredModels.some((m) => m.id === outlookDefaultModel)) {
    opts.push({
      value: outlookDefaultModel,
      label: '🧭 Nemotron 3 Ultra 550B (Free)',
    });
  }

  // API providers: built from the ACTUAL healthy providers reported by
  // /llm/providers/health, cross-referenced with /llm/models so each
  // option carries the provider's real default_model. No static list —
  // unhealthy or unregistered providers simply do not appear.
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
}

export function useOutlookModels(addToast: AddToast) {
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [outlookDefaultModel, setOutlookDefaultModel] = useState<string>(
    'nvidia/nemotron-3-ultra-550b-a55b:free',
  );
  const [featuredModels, setFeaturedModels] = useState<FeaturedModelChoice[]>(featuredFallbackChoices);
  const [randomModel, setRandomModel] = useState<boolean>(false);
  const [outlookModels, setOutlookModels] = useState<OutlookModels>({ lm_studio: [], local: [], api: [] });
  const [healthyProviders, setHealthyProviders] = useState<Record<string, boolean>>({});

  const fetchModels = useCallback(async (): Promise<void> => {
    try {
      const [modelsRes, defaultsRes, catalogRes] = await Promise.all([
        fetch(apiUrl('/llm/models')),
        fetch(apiUrl('/llm/models/defaults')),
        fetch(apiUrl('/llm/models/available')),
      ]);
      if (modelsRes.ok) {
        const data = await modelsRes.json() as {
          status?: string;
          available?: OutlookModels;
        };
        if (data.status === 'success') {
          setOutlookModels(data.available || { lm_studio: [], local: [], api: [] });
        }
      }
      if (catalogRes.ok) {
        const catalog = await catalogRes.json() as {
          status?: string;
          models?: Array<{ id?: string; name?: string; is_free?: boolean; featured?: boolean }>;
        };
        if (catalog.status === 'success' && Array.isArray(catalog.models)) {
          const featured = catalog.models
            .filter((m) => m.featured && typeof m.id === 'string' && m.id)
            .map((m) => ({
              id: m.id as string,
              name: m.name || (m.id as string),
              is_free: Boolean(m.is_free),
            }));
          if (featured.length > 0) setFeaturedModels(featured);
        }
      }
      if (defaultsRes.ok) {
        const defaultsPayload = await defaultsRes.json() as {
          defaults?: { outlook_narrative?: { model_id?: string } };
        };
        const outlookDefault = defaultsPayload.defaults?.outlook_narrative?.model_id;
        if (outlookDefault) {
          setOutlookDefaultModel(outlookDefault);
          if (!selectedModel) setSelectedModel(outlookDefault);
        }
      }
    } catch (e) {
      addToast({ type: 'error', title: 'Could not load LLM models', message: 'Backend unreachable.', duration: 3000 });
    }
  }, [selectedModel, addToast]);

  const fetchProvidersHealth = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(apiUrl(`/llm/providers/health`));
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

  const modelOptions = useMemo<ModelSelectOption[]>(
    () => buildOutlookModelOptions(outlookModels, healthyProviders, outlookDefaultModel, featuredModels),
    [outlookModels, healthyProviders, outlookDefaultModel, featuredModels],
  );

  return {
    selectedModel,
    setSelectedModel,
    outlookDefaultModel,
    randomModel,
    setRandomModel,
    modelOptions,
    fetchModels,
    fetchProvidersHealth,
  };
}

export type OutlookModelPicker = ReturnType<typeof useOutlookModels>;
