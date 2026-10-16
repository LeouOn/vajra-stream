/**
 * buildModelOptions — grouped Select options for the Command Center's model
 * picker (and per-message "regenerate with" picker): Auto, Recommended
 * (catalog-featured, else the built-in featured list), LM Studio, local
 * GGUF, other catalog models by provider, and — only when the catalog is
 * empty — the basic API provider list.
 */
import React from 'react';
import { Tag } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { FEATURED_MODEL_IDS, FEATURED_MODEL_LABELS } from '../../lib/featuredModels';
import type { AvailableModelMeta, BasicModelLists } from './commandCenterTypes';

function ModelOptionLabel({ model, perM }: { model: AvailableModelMeta; perM: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="truncate">{model.name}</span>
      {model.is_free
        ? <Tag color="green" style={{ fontSize: '8px', lineHeight: '14px', margin: 0, padding: '0 4px' }}>FREE</Tag>
        : <span className="text-gray-500 text-[9px] ml-auto font-mono">
            ${model.input_per_m.toFixed(2)}/${model.output_per_m.toFixed(2)}{perM ? ' per M' : ''}
          </span>}
    </span>
  );
}

export function buildModelOptions(
  availableModelList: AvailableModelMeta[],
  availableModels: BasicModelLists,
): DefaultOptionType[] {
  const stripPrefix = (m: string, prefix: string) =>
    m.startsWith(`${prefix}:`) ? m.slice(prefix.length + 1) : m;

  const featuredIds = new Set<string>(FEATURED_MODEL_IDS);
  const groups: DefaultOptionType[] = [{
    label: '⚡ Auto',
    title: 'Auto-select',
    options: [
      { value: 'auto', label: '⚡ Auto (DeepSeek V4 Flash / pick_best)' },
    ],
  }];

  let recommendedModels = availableModelList.filter(m => m.featured || featuredIds.has(m.id));
  const otherApiModels = availableModelList.filter(m => !(m.featured || featuredIds.has(m.id)));
  if (recommendedModels.length === 0) {
    recommendedModels = FEATURED_MODEL_IDS.map((id) => ({
      id,
      name: FEATURED_MODEL_LABELS[id] || id,
      provider: 'openrouter',
      context_length: null,
      input_per_m: 0,
      output_per_m: 0,
      is_free: id.endsWith(':free'),
      featured: true,
      description: '',
      source: 'builtin',
    }));
  }

  if (recommendedModels.length > 0) {
    groups.push({
      label: '⭐ Recommended (Free + Fast)',
      title: 'Recommended',
      options: recommendedModels.map(m => ({
        value: m.id,
        label: <ModelOptionLabel model={m} perM={false} />,
      })),
    });
  }

  if (availableModels.lm_studio && availableModels.lm_studio.length > 0) {
    groups.push({
      label: '🖥 LM Studio',
      title: 'LM Studio (Active)',
      options: availableModels.lm_studio.map(m => ({
        value: `lm_studio:${m}`,
        label: m,
      })),
    });
  }

  if (availableModels.local && availableModels.local.length > 0) {
    groups.push({
      label: '💾 Local GGUF',
      title: 'Local GGUF',
      options: availableModels.local.map(m => {
        const bare = stripPrefix(m, 'local');
        return { value: `local:${bare}`, label: bare };
      }),
    });
  }

  const otherByProvider = new Map<string, AvailableModelMeta[]>();
  for (const m of otherApiModels) {
    const arr = otherByProvider.get(m.provider) || [];
    arr.push(m);
    otherByProvider.set(m.provider, arr);
  }
  const sortedProviders = Array.from(otherByProvider.keys()).sort();
  for (const provider of sortedProviders) {
    const models = otherByProvider.get(provider)!;
    groups.push({
      label: provider.charAt(0).toUpperCase() + provider.slice(1),
      title: provider,
      options: models.map(m => ({
        value: m.id,
        label: <ModelOptionLabel model={m} perM />,
      })),
    });
  }

  if (availableModels.api && availableModels.api.length > 0 && availableModelList.length === 0) {
    groups.push({
      label: '🌐 API Providers',
      title: 'API Providers',
      options: availableModels.api
        .map((m): { value: string; label: string } | null => {
          const match = m.match(/^([a-zA-Z0-9_-]+)\s*\(([^)]+)\)\s*$/);
          if (!match) return null;
          return { value: `${match[1]}:${match[2]}`, label: m };
        })
        .filter((opt): opt is { value: string; label: string } => opt !== null),
    });
  }

  return groups;
}
