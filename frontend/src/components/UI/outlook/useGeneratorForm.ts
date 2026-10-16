/**
 * useGeneratorForm — the Quick Generate form's state (location, epoch,
 * genre, languages, oracles, cast, difficulty, epic stages).
 *
 * Kept as component state (not a store) so the form resets when the Outlook
 * route unmounts, exactly as it did inline. The parent hands the returned
 * object to the settings card and reads it when generating.
 */
import { useState } from 'react';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../../lib/geo';
import type { RealmSelection } from './outlookShared';

export function useGeneratorForm() {
  const [lat, setLat] = useState<number | null>(DEFAULT_LAT);
  const [lon, setLon] = useState<number | null>(DEFAULT_LNG);
  const [genre, setGenre] = useState<string>('healing');
  const [selectedLangs, setSelectedLangs] = useState<string[]>(['English']);
  const [isEpic, setIsEpic] = useState<boolean>(false);
  const [stages, setStages] = useState<number>(9);
  const [date, setDate] = useState<string>(() => new Date().toISOString().slice(0, 16));
  const [selectedRealmId, setSelectedRealmId] = useState<RealmSelection>('');
  const [selectedCharIds, setSelectedCharIds] = useState<Array<string | number>>([]);
  const [selectedPopIds, setSelectedPopIds] = useState<Array<string | number>>([]);
  const [includeDialogue, setIncludeDialogue] = useState<boolean>(false);
  const [customContext, setCustomContext] = useState<string>('');
  const [difficulty, setDifficulty] = useState<string>('moderate');
  const [excludedForcesText, setExcludedForcesText] = useState<string>('');
  const [includeAstrology, setIncludeAstrology] = useState<boolean>(true);
  const [includeTarot, setIncludeTarot] = useState<boolean>(true);
  const [includeIching, setIncludeIching] = useState<boolean>(true);
  const [randomizeRealm, setRandomizeRealm] = useState<boolean>(false);
  const [randomizeCharacters, setRandomizeCharacters] = useState<boolean>(false);

  return {
    lat, setLat,
    lon, setLon,
    genre, setGenre,
    selectedLangs, setSelectedLangs,
    isEpic, setIsEpic,
    stages, setStages,
    date, setDate,
    selectedRealmId, setSelectedRealmId,
    selectedCharIds, setSelectedCharIds,
    selectedPopIds, setSelectedPopIds,
    includeDialogue, setIncludeDialogue,
    customContext, setCustomContext,
    difficulty, setDifficulty,
    excludedForcesText, setExcludedForcesText,
    includeAstrology, setIncludeAstrology,
    includeTarot, setIncludeTarot,
    includeIching, setIncludeIching,
    randomizeRealm, setRandomizeRealm,
    randomizeCharacters, setRandomizeCharacters,
  };
}

export type GeneratorForm = ReturnType<typeof useGeneratorForm>;
