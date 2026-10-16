/**
 * Home location — where workings are sealed unless they name their own place,
 * so each witness shows the true sky from there (core/home_location.py).
 *
 *   GET    /settings/location  → { location | null, default, display }
 *   PUT    /settings/location  ← { latitude, longitude, label?, source: 'browser' | 'typed' }
 *                              ← { place }   (geocoded on the server; source 'geocoded')
 *   DELETE /settings/location
 *
 * Location is personal data: anything shown goes through `formatCoords`,
 * which rounds to one decimal place (~11 km), never full precision.
 */
import { apiUrl } from '../utils/api';
import { errorMessage } from './apiError';

export type HomeLocationSource = 'browser' | 'typed' | 'geocoded';

export interface HomeLocation {
  latitude: number;
  longitude: number;
  label: string | null;
  source: HomeLocationSource;
  updated_at?: string;
}

export interface HomeLocationResponse {
  location: HomeLocation | null;
  default: { latitude: number; longitude: number };
  display: string | null;
}

export type HomeLocationInput =
  | { latitude: number; longitude: number; label?: string | null; source: 'browser' | 'typed' }
  | { place: string };

/** Decimal places shown anywhere a person can see or share a location. */
export const PUBLIC_DECIMALS = 1;

/** Round a coordinate for display or for leaving the browser (e.g. the chat's astrology context). */
export function roundCoord(value: number): number {
  const f = 10 ** PUBLIC_DECIMALS;
  return Math.round(value * f) / f;
}

/** `"27.7°, 85.3°"` — rounded, never full precision. */
export function formatCoords(latitude: number, longitude: number): string {
  return `${roundCoord(latitude).toFixed(PUBLIC_DECIMALS)}°, ${roundCoord(longitude).toFixed(PUBLIC_DECIMALS)}°`;
}

/** `"Kathmandu (27.7°, 85.3°)"`, or the rounded coordinates alone. */
export function describeLocation(location: HomeLocation): string {
  const coords = formatCoords(location.latitude, location.longitude);
  return location.label ? `${location.label} (${coords})` : coords;
}

/** `"27.7, 85.3"` / `"-33.87 151.21"` typed as coordinates, else null (a place name). */
export function parseTypedCoords(text: string): { latitude: number; longitude: number } | null {
  const m = text.trim().match(/^(-?\d+(?:\.\d+)?)\s*[,\s]\s*(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const latitude = Number(m[1]);
  const longitude = Number(m[2]);
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return null;
  return { latitude, longitude };
}

function isResponse(value: unknown): value is HomeLocationResponse {
  return !!value && typeof value === 'object' && 'location' in value;
}

async function read(res: Response, fallback: string): Promise<HomeLocationResponse> {
  if (!res.ok) throw new Error(await errorMessage(res, fallback));
  const body: unknown = await res.json();
  if (!isResponse(body)) throw new Error(`${fallback}: unexpected response`);
  return body;
}

export async function fetchHomeLocation(): Promise<HomeLocationResponse> {
  return read(await fetch(apiUrl('/settings/location')), 'Could not load the home location');
}

export async function saveHomeLocation(input: HomeLocationInput): Promise<HomeLocationResponse> {
  const res = await fetch(apiUrl('/settings/location'), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  return read(res, 'Could not save the home location');
}

export async function clearHomeLocation(): Promise<HomeLocationResponse> {
  return read(await fetch(apiUrl('/settings/location'), { method: 'DELETE' }), 'Could not clear the home location');
}
