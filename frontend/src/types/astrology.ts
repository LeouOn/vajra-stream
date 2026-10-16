/**
 * Astrology API response shapes consumed by the Cosmic Clock panel.
 *
 * Modelled on the backend, not on what the UI happens to read:
 *   - `core/astrology.py:AstrologicalCalculator.get_comprehensive_astrology`
 *     → `{datetime, location, western, indian, chinese, planetary_hours}`
 *     (this is also what saved charts cache in `cached_chart_data`).
 *   - `backend/core/services/vajra_service.py:_get_astrology_data` adds the
 *     legacy top-level keys `moon_phase`, `planetary_positions`,
 *     `auspicious_times` and `timestamp` for `GET /astrology/current`.
 *   - `backend/app/api/v1/endpoints/astrology.py:SavedChartResponse` for the
 *     saved-chart rows.
 *
 * Every system block is optional: without the astrology extras installed
 * (`pyswisseph`, `lunar-python`) the backend drops the western/indian/chinese
 * keys, and on calculation failure `_get_astrology_data` returns `{}`.
 */
import type { SavedChart } from '../components/UI/SavedChartsDrawer';

/** One tropical body (or the ascendant / midheaven angle). */
export interface WesternPosition {
  /** Ecliptic longitude, 0–360°. */
  longitude: number;
  sign?: string;
  /** Degree within the sign, 0–30°. */
  degree?: number;
  /** e.g. "Aries 12.34° ℞". */
  formatted?: string;
  retrograde?: boolean;
  speed?: number;
  /** Placidus house; absent on the ascendant / midheaven angles. */
  house?: number;
}

export type WesternPositions = Record<string, WesternPosition>;

/** A natal aspect as emitted by `get_western_astrology`. */
export interface WesternAspect {
  planet1: string;
  planet2: string;
  /** "Conjunction" | "Opposition" | "Trine" | "Square" | "Sextile" | ... */
  aspect: string;
  angle?: number;
  /** 1 = exact, 0 = edge of orb. */
  exactness?: number;
  description?: string;
}

export interface WesternAstrology {
  positions?: WesternPositions;
  /** Weighted element points, e.g. `{Fire: 7, Earth: 3, Air: 2, Water: 4}`. */
  elements?: Record<string, number>;
  modalities?: Record<string, number>;
  dominant_element?: string;
  dominant_modality?: string;
  aspects?: WesternAspect[];
  houses?: Record<string, WesternPosition>;
}

export interface PanchangaLimb {
  number?: number;
  name?: string;
  paksha?: string;
  progress?: number;
  index?: number;
}

export interface Panchanga {
  tithi?: PanchangaLimb;
  nakshatra?: PanchangaLimb;
  yoga?: PanchangaLimb;
  karana?: PanchangaLimb;
  vara?: PanchangaLimb;
}

export interface SiderealPosition {
  longitude?: number;
  rashi?: string;
  rashi_name?: string;
  rashi_number?: number;
  degree?: number;
  formatted?: string;
}

export interface IndianAstrology {
  ayanamsa?: number;
  sidereal_positions?: Record<string, SiderealPosition>;
  panchanga?: Panchanga;
  [key: string]: unknown;
}

export interface ChineseAstrology {
  /** Pillar strings such as "甲子/Jia-Zi-Rat (木水)" keyed year/month/day/hour. */
  bazi?: Record<string, string>;
  lunar_date?: {
    year?: number;
    month?: number;
    day?: number;
    is_leap?: boolean;
    formatted?: string;
    [key: string]: unknown;
  };
  zodiac_animal?: string;
  shichen?: { branch?: string; name?: string; index?: number; [key: string]: unknown };
  /**
   * Translated jieqi. The backend sends `null` on days without a solar term;
   * typed as optional string to match `ChineseBaZi`, which only reads it
   * truthily (`solar_term || '—'`).
   */
  solar_term?: string;
  [key: string]: unknown;
}

export interface PlanetaryHours {
  current_planetary_hour?: string;
  day_planet?: string;
  hour_index?: number;
  is_daytime?: boolean;
  time_remaining_seconds?: number;
  description?: string;
  [key: string]: unknown;
}

export interface MoonPhase {
  phase_name?: string;
  /** Percentage 0–100 (`(1 - cos(phase_angle)) / 2 * 100`), never a 0–1 fraction. */
  illumination?: number;
  phase_angle?: number;
  is_new_moon?: boolean;
  is_full_moon?: boolean;
}

/**
 * One astrology snapshot: the live sky from `GET /astrology/current`
 * (`.astrology`) or a saved chart's parsed `cached_chart_data`.
 */
export interface AstrologySnapshot {
  /** ISO-8601 with offset. */
  datetime?: string;
  location?: { latitude: number; longitude: number };
  western?: WesternAstrology;
  indian?: IndianAstrology;
  chinese?: ChineseAstrology;
  planetary_hours?: PlanetaryHours;
  // Legacy top-level keys — only present on GET /astrology/current.
  moon_phase?: MoonPhase;
  planetary_positions?: WesternPositions;
  auspicious_times?: Record<string, unknown>;
  timestamp?: number;
}

/** `GET /astrology/current` */
export interface CurrentAstrologyResponse {
  status: string;
  astrology: AstrologySnapshot;
  timestamp: number;
}

/** `POST /astrology/charts/{id}/recalculate` */
export interface RecalculateChartResponse {
  status: string;
  cached_chart_data: AstrologySnapshot;
}

/** `POST /astrology/geocode` */
export interface GeocodeResponse {
  latitude: number;
  longitude: number;
  timezone?: string;
  [key: string]: unknown;
}

/**
 * A saved natal chart row (`SavedChartResponse`). Extends the `SavedChart`
 * contract shared with SavedChartsDrawer / SynastryViewer / TransitComparison
 * so the same objects flow to those components unchanged.
 *
 * Note: the backend `id` is an integer, while the shared contract types it as
 * `string`; it is only ever interpolated into URLs or compared against ids
 * from the same list, so both representations behave identically.
 */
export interface SavedNatalChart extends SavedChart {
  latitude?: number;
  longitude?: number;
  timezone?: string;
  notes?: string;
  /** JSON-encoded `AstrologySnapshot` (without the legacy top-level keys). */
  cached_chart_data?: string | null;
  created_at?: string;
  updated_at?: string;
}

/** `POST /astrology/charts/import` */
export interface ImportChartsResponse {
  imported: number;
  [key: string]: unknown;
}
