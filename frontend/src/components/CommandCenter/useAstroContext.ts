/**
 * useAstroContext — the current sky for the chat's astrology context:
 * GET /astrology/current at the home location (Settings → Home location)
 * or else the default coordinates, at local wall-clock time, refreshed every
 * 15s (cleared on unmount). Failures are ignored.
 *
 * The home location is rounded to one decimal place (~11 km) first: this
 * context goes to the chat model, and the sky does not need more.
 */
import { useState, useEffect } from 'react';
import { apiUrl } from '../../utils/api';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import { fetchHomeLocation, roundCoord } from '../../lib/homeLocationApi';

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

    let coords: [number, number] = [DEFAULT_LAT, DEFAULT_LNG];
    let cancelled = false;

    const fetchAstro = async () => {
      doFetch(coords[0], coords[1]);
    };

    fetchHomeLocation()
      .then((res) => {
        if (cancelled || !res.location) return;
        coords = [roundCoord(res.location.latitude), roundCoord(res.location.longitude)];
        void fetchAstro();
      })
      .catch(() => undefined);

    fetchAstro();
    const interval = setInterval(fetchAstro, ASTRO_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return astroData;
}
