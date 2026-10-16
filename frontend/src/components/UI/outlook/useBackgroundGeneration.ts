/**
 * useBackgroundGeneration — the server-side blessing loop: its config,
 * status/stats (GET /outlook/background/status), start/stop, and a 30s
 * status + history poll while the loop is active (cleared on stop/unmount).
 */
import { useState, useEffect, useCallback } from 'react';
import { message } from 'antd';
import { apiUrl } from '../../../utils/api';
import { audioFeedback } from '../../../utils/audioFeedback';
import type { LoopMode } from './outlookNarrative';

export interface BackgroundStats {
  total_generated?: number;
  total_saved?: number;
  total_errors?: number;
  last_generated_at?: string | null;
  last_genre?: string | null;
}

interface BackgroundStatusResponse {
  active?: boolean;
  config?: {
    interval_minutes?: number;
    loop_mode?: LoopMode;
    cycle_genres?: boolean;
    include_astrology?: boolean;
    include_tarot?: boolean;
    include_iching?: boolean;
  };
  stats?: BackgroundStats;
}

interface BackgroundGenerationDeps {
  lat: number | null;
  lon: number | null;
  selectedLangs: string[];
  /** Refreshed alongside the status on every poll tick. */
  fetchHistory: () => Promise<void>;
}

export function useBackgroundGeneration({ lat, lon, selectedLangs, fetchHistory }: BackgroundGenerationDeps) {
  const [bgActive, setBgActive] = useState<boolean>(false);
  const [bgInterval, setBgInterval] = useState<number>(60);
  const [bgMode, setBgMode] = useState<LoopMode>('sequential_delay');
  const [bgAstrology, setBgAstrology] = useState<boolean>(true);
  const [bgTarot, setBgTarot] = useState<boolean>(true);
  const [bgIching, setBgIching] = useState<boolean>(true);
  const [bgCycleGenres, setBgCycleGenres] = useState<boolean>(true);
  const [bgStats, setBgStats] = useState<BackgroundStats>({});

  const fetchBgStatus = useCallback(async (): Promise<void> => {
    try {
      const res = await fetch(apiUrl(`/outlook/background/status`));
      if (res.ok) {
        const data = await res.json() as BackgroundStatusResponse;
        setBgActive(Boolean(data.active));
        if (data.config?.interval_minutes) setBgInterval(data.config.interval_minutes);
        if (data.config?.loop_mode) setBgMode(data.config.loop_mode);
        if (data.config?.cycle_genres !== undefined) setBgCycleGenres(data.config.cycle_genres);
        if (data.config?.include_astrology !== undefined) setBgAstrology(data.config.include_astrology);
        if (data.config?.include_tarot !== undefined) setBgTarot(data.config.include_tarot);
        if (data.config?.include_iching !== undefined) setBgIching(data.config.include_iching);
        if (data.stats) setBgStats(data.stats);
      }
    } catch {
    }
  }, []);

  const toggleBackgroundGeneration = useCallback(async (): Promise<void> => {
    if (bgActive) {
      try {
        await fetch(apiUrl(`/outlook/background/stop`), { method: 'POST' });
        setBgActive(false);
        message.success('Background generation stopped.');
      } catch {
        message.error('Could not stop background generation.');
      }
    } else {
      try {
        const res = await fetch(apiUrl(`/outlook/background/start`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            interval_minutes: bgInterval,
            loop_mode: bgMode,
            cycle_genres: bgCycleGenres,
            cycle_intentions: true,
            include_astrology: bgAstrology,
            include_tarot: bgTarot,
            include_iching: bgIching,
            include_geomancy: true,
            lat: parseFloat(String(lat)),
            lon: parseFloat(String(lon)),
            languages: selectedLangs,
          }),
        });
        if (res.ok) {
          setBgActive(true);
          message.success(`Background generation every ${bgInterval} min.`);
          audioFeedback.playSuccess();
          fetchBgStatus();
        } else {
          message.error('Could not start background generation.');
          audioFeedback.playError();
        }
      } catch {
        message.error('Backend unreachable.');
        audioFeedback.playError();
      }
    }
  }, [bgActive, bgInterval, bgMode, bgCycleGenres, bgAstrology, bgTarot, bgIching, lat, lon, selectedLangs, fetchBgStatus]);

  useEffect(() => {
    if (!bgActive) return;
    const id = window.setInterval(() => {
      fetchBgStatus();
      fetchHistory();
    }, 30000);
    return () => window.clearInterval(id);
  }, [bgActive, fetchBgStatus, fetchHistory]);

  return {
    bgActive,
    bgInterval, setBgInterval,
    bgMode, setBgMode,
    bgAstrology, setBgAstrology,
    bgTarot, setBgTarot,
    bgIching, setBgIching,
    bgCycleGenres, setBgCycleGenres,
    bgStats,
    fetchBgStatus,
    toggleBackgroundGeneration,
  };
}

export type BackgroundGeneration = ReturnType<typeof useBackgroundGeneration>;
