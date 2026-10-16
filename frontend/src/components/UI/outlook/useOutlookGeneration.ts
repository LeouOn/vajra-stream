/**
 * useOutlookGeneration — the Generator's result: generating a single or epic
 * narrative from the form, the affirmation forged from it, copy feedback,
 * loading a history item, and saving the ritual to the local archive.
 *
 * Handlers are plain functions recreated each render (as they were inline),
 * so they always read the current form and model selection.
 */
import { useState } from 'react';
import { message } from 'antd';
import { apiUrl } from '../../../utils/api';
import { audioFeedback } from '../../../utils/audioFeedback';
import type { HistoryItem } from './outlookShared';
import { historyItemToNarrative, type CurrentNarrative, type ResultTab } from './outlookNarrative';
import { appendSavedRitual, buildSavedRitual } from './savedRituals';
import type { GeneratorForm } from './useGeneratorForm';

interface GenerationDeps {
  form: GeneratorForm;
  /** Model choice at generation time. */
  model: { randomModel: boolean; selectedModel: string; outlookDefaultModel: string };
  fetchHistory: () => Promise<void>;
  fetchUniverseData: () => Promise<void>;
}

export function useOutlookGeneration({ form, model, fetchHistory, fetchUniverseData }: GenerationDeps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [currentNarrative, setCurrentNarrative] = useState<CurrentNarrative | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [resultTab, setResultTab] = useState<ResultTab>('narrative');
  const [affirmation, setAffirmation] = useState<string | null>(null);
  const [affirmationLoading, setAffirmationLoading] = useState<boolean>(false);
  const [affirmationCopied, setAffirmationCopied] = useState<boolean>(false);

  const handleGenerate = async (): Promise<void> => {
    setLoading(true);
    setCurrentNarrative(null);
    setAffirmation(null);
    setResultTab('narrative');
    audioFeedback.playClick();

    try {
      const endpoint = form.isEpic ? '/outlook/generate_epic' : '/outlook/generate_single';
      const body: Record<string, unknown> = {
        lat: parseFloat(String(form.lat)), lon: parseFloat(String(form.lon)),
        languages: form.selectedLangs, genre: form.genre,
        date: new Date(form.date).toISOString(),
        custom_context: form.customContext || null,
        difficulty: form.difficulty,
        realm_id: form.selectedRealmId || null,
        population_ids: form.selectedPopIds.length > 0 ? form.selectedPopIds : null,
        character_ids: form.selectedCharIds.length > 0 ? form.selectedCharIds : null,
        excluded_forces: form.excludedForcesText ? form.excludedForcesText.split(',').map(s => s.trim()) : null,
        include_dialogue: form.includeDialogue,
        model: model.randomModel ? null : (model.selectedModel || model.outlookDefaultModel || null),
        random: model.randomModel || null,
        include_astrology: form.includeAstrology,
        include_tarot: form.includeTarot,
        include_iching: form.includeIching,
        randomize_realm: form.randomizeRealm,
        randomize_characters: form.randomizeCharacters,
      };
      if (form.isEpic) body.stages = parseInt(String(form.stages));

      const res = await fetch(apiUrl(endpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = await res.json() as CurrentNarrative;
        setCurrentNarrative(data);
        message.success(form.isEpic ? `Epic journey of ${form.stages} stages received.` : 'Narrative generated.');
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
      const intention = form.customContext
        || currentNarrative.genre
        || 'spiritual practice';
      const res = await fetch(apiUrl(`/radionics/affirmation/generate`), {
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

  const copyNarrative = (): void => {
    const text = currentNarrative?.narrative || JSON.stringify(currentNarrative?.narrative_parts || '', null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const loadHistoryItem = (item: HistoryItem): void => {
    setCurrentNarrative(historyItemToNarrative(item));
  };

  const saveCurrentRitual = (): void => {
    if (!currentNarrative?.narrative) return;
    const entry = buildSavedRitual({ ...currentNarrative, narrative: currentNarrative.narrative }, form.genre);
    try {
      appendSavedRitual(entry);
      message.success('Ritual saved to local archive.');
      audioFeedback.playSuccess();
    } catch {
      message.error('Could not save ritual — localStorage may be full or disabled.');
    }
  };

  return {
    loading,
    currentNarrative,
    setCurrentNarrative,
    copied,
    resultTab,
    setResultTab,
    affirmation,
    affirmationLoading,
    affirmationCopied,
    handleGenerate,
    generateAffirmation,
    copyAffirmation,
    copyNarrative,
    loadHistoryItem,
    saveCurrentRitual,
  };
}

export type OutlookGeneration = ReturnType<typeof useOutlookGeneration>;
