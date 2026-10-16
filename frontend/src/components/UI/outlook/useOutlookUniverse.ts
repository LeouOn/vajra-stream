/**
 * useOutlookUniverse — realms, characters, populations and the role /
 * location-type lists, loaded from the outlook + populations endpoints.
 */
import { useState, useCallback } from 'react';
import { apiUrl } from '../../../utils/api';
import type { AddToast, Character, Population, Realm } from './outlookShared';

const isItemsEnvelope = <T,>(v: unknown): v is { items: T[] } =>
  typeof v === 'object' && v !== null && Array.isArray((v as { items?: unknown }).items);
const isDataEnvelope = <T,>(v: unknown): v is { data: T[] } =>
  typeof v === 'object' && v !== null && Array.isArray((v as { data?: unknown }).data);

/**
 * Defensive unwrap — same crash class as AstrologyExtractionPanel's
 * ``runs.some is not a function`` bug. Backend today returns bare arrays
 * for these 5 endpoints, but a future envelope wrap (e.g. ``{items: [...]}``
 * or ``{data: [...]}``) would silently store the envelope object in state
 * and crash every downstream ``.map()`` / ``.filter()`` call with
 * "object is not iterable". Accept either shape; fall back to ``[]``.
 */
export function unwrapList<T>(v: unknown): T[] {
  if (Array.isArray(v)) return v as T[];
  if (isItemsEnvelope<T>(v)) return v.items;
  if (isDataEnvelope<T>(v)) return v.data;
  return [];
}

export function useOutlookUniverse(addToast: AddToast) {
  const [realms, setRealms] = useState<Realm[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [populations, setPopulations] = useState<Population[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [locationTypes, setLocationTypes] = useState<string[]>([]);

  const fetchUniverseData = useCallback(async (): Promise<void> => {
    try {
      const [realmsRes, charsRes, popsRes, rolesRes, typesRes] = await Promise.all([
        fetch(apiUrl(`/outlook/locations`)),
        fetch(apiUrl(`/outlook/characters`)),
        fetch(apiUrl(`/populations/`)),
        fetch(apiUrl(`/outlook/characters/roles/list`)),
        fetch(apiUrl(`/outlook/locations/types/list`)),
      ]);
      if (realmsRes.ok) setRealms(unwrapList<Realm>(await realmsRes.json()));
      if (charsRes.ok) setCharacters(unwrapList<Character>(await charsRes.json()));
      if (popsRes.ok) setPopulations(unwrapList<Population>(await popsRes.json()));
      if (rolesRes.ok) setRoles(unwrapList<string>(await rolesRes.json()));
      if (typesRes.ok) setLocationTypes(unwrapList<string>(await typesRes.json()));
    } catch (e) {
      addToast({ type: 'error', title: 'Could not load realms', message: 'Backend unreachable. Some data may be stale.', duration: 3000 });
    }
  }, [addToast]);

  return {
    realms,
    characters,
    setCharacters,
    populations,
    roles,
    locationTypes,
    fetchUniverseData,
  };
}
