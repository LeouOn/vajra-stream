/**
 * useAstroContext — the current sky for the chat's astrology context:
 * GET /astrology/current at the default coordinates and local wall-clock
 * time, refreshed every 15s (cleared on unmount). Failures are ignored.
 */
import { useState, useEffect } from 'react';
import { apiUrl } from '../../utils/api';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';

export const ASTRO_REFRESH_MS = 15000;

export function useAstroContext(): Record<string, unknown> | null {
  const [astroData, setAstroData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const doFetch = async (lat: number | null, lon: number | null) => {
      try {
        const d = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        const localTime = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

        const params = new URLSearchParams();
        params.append('datetime_str', localTime);
        if (lat !== null && lon !== null) {
          params.append('latitude', lat.toString());
          params.append('longitude', lon.toString());
        }

        const res = await fetch(apiUrl(`/astrology/current?${params.toString()}`));
        if (res.ok) {
          const data = await res.json();
          setAstroData(data.astrology);
        }
      } catch (e) {
        // Ignore
      }
    };

    const fetchAstro = async () => {
      doFetch(DEFAULT_LAT, DEFAULT_LNG);
    };

    fetchAstro();
    const interval = setInterval(fetchAstro, ASTRO_REFRESH_MS);
    return () => clearInterval(interval);
  }, []);

  return astroData;
}
