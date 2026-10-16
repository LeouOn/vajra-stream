/**
 * useLlmModels — the Command Center's model picker data: the basic model
 * lists (GET /llm/models), the priced catalog (GET /llm/models/available),
 * and provider health (GET /llm/providers/health, refreshed every 30s and
 * cleared on unmount). Each source is best-effort.
 */
import { useState, useEffect } from 'react';
import { apiUrl } from '../../utils/api';
import type {
  AvailableModelMeta, AvailableModelsResponse, BasicModelLists, BasicModelsResponse,
  ModelPricing, ProviderHealthEntry, ProviderHealthResponse,
} from './commandCenterTypes';

export const PROVIDER_HEALTH_REFRESH_MS = 30000;

export function useLlmModels() {
  const [availableModels, setAvailableModels] = useState<BasicModelLists>({ local: [], api: [], lm_studio: [] });
  const [selectedModel, setSelectedModel] = useState('auto');
  const [availableModelList, setAvailableModelList] = useState<AvailableModelMeta[]>([]);
  const [modelPricing, setModelPricing] = useState<Record<string, ModelPricing>>({});
  const [providerHealth, setProviderHealth] = useState<ProviderHealthEntry[]>([]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch(apiUrl('/llm/models'));
        if (res.ok) {
          const data: BasicModelsResponse = await res.json();
          if (data.status === 'success') {
            setAvailableModels(data.available || { local: [], api: [], lm_studio: [] });
            if (!selectedModel || selectedModel === 'auto') {
              setSelectedModel('auto');
            }
          }
        }
      } catch (e) {
        console.error("Failed to fetch available models", e);
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    const fetchModelCatalog = async () => {
      try {
        const res = await fetch(apiUrl('/llm/models/available'));
        if (res.ok) {
          const data: AvailableModelsResponse = await res.json();
          if (data.status === 'success' && Array.isArray(data.models)) {
            setAvailableModelList(data.models);
            const pricing: Record<string, ModelPricing> = {};
            for (const m of data.models) {
              pricing[m.id] = {
                input_per_m: m.input_per_m,
                output_per_m: m.output_per_m,
                is_free: m.is_free,
              };
            }
            setModelPricing(pricing);
          }
        }
      } catch {
        /* catalog is best-effort; basic /models still provides the selector */
      }
    };
    fetchModelCatalog();
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(apiUrl('/llm/providers/health'));
        if (res.ok) {
          const data: ProviderHealthResponse = await res.json();
          setProviderHealth(data.providers || []);
        }
      } catch {
        /* health checks are best-effort */
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, PROVIDER_HEALTH_REFRESH_MS);
    return () => clearInterval(interval);
  }, []);

  return {
    availableModels,
    availableModelList,
    modelPricing,
    providerHealth,
    selectedModel,
    setSelectedModel,
  };
}
