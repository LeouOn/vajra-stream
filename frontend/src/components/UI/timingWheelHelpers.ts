/**
 * Auspicious Timing Wheel — Pure Math and Color Mapping Helpers
 *
 * Polar geometry calculations for SVG concentric rings and 24-hour planetary hour wedges.
 */

export interface HourlySlice {
  index: number;
  period: 'day' | 'night';
  hour_number: number;
  ruler: string;
  start_time: string;
  end_time: string;
  is_current: boolean;
  affinities: Record<string, 'favorable' | 'neutral' | 'unfavorable'>;
}

export interface MoonData {
  phase_name: string;
  phase_angle: number;
  glyph: string;
  tithi: string;
  nakshatra: string;
  nakshatra_quality: string;
}

export interface GenreWindow {
  go: boolean;
  planetary_hour: string;
  tithi: string;
  nakshatra: string;
  quality: string;
  message: string;
  transmutation: string;
  transmutation_mantra: string;
  wait_minutes: number;
  next_favorable_hour: string;
  time_shift_available: boolean;
  recommended_approach: string;
}

export interface OptimalWindowSlice {
  period: 'day' | 'night';
  hour_number: number;
  ruler: string;
  start_time: string;
  end_time: string;
  is_current: boolean;
}

export interface TimingWheelResponse {
  status: string;
  datetime: string;
  location: { latitude: number; longitude: number };
  current_planetary_hour: {
    ruler: string;
    day_planet: string;
    is_daytime: boolean;
    hour_number: number;
  };
  moon: MoonData;
  saka_dawa: {
    is_saka_dawa?: boolean;
    is_duchen?: boolean;
    multiplier?: number;
    message?: string;
    [key: string]: unknown;
  };
  hourly_slices: HourlySlice[];
  genre_windows: Record<string, GenreWindow>;
  next_optimal_windows: Record<string, OptimalWindowSlice[]>;
}

export const PLANET_COLORS: Record<string, string> = {
  Sun: '#FFD700',      // Brilliant Gold
  Moon: '#E0E7FF',     // Silver Blue
  Mars: '#EF4444',     // Fiery Red
  Mercury: '#38BDF8',  // Sky Cyan
  Jupiter: '#C084FC',  // Royal Amethyst
  Venus: '#F472B6',    // Rose Pink
  Saturn: '#64748B',   // Deep Slate
};

export const PLANET_SYMBOLS: Record<string, string> = {
  Sun: '☉',
  Moon: '☽',
  Mars: '♂',
  Mercury: '☿',
  Jupiter: '♃',
  Venus: '♀',
  Saturn: '♄',
};

export const GENRE_COLORS: Record<string, string> = {
  healing: '#10B981',       // Emerald
  wisdom: '#3B82F6',        // Azure
  purification: '#8B5CF6',  // Violet
  compassion: '#EC4899',    // Rose
  protection: '#F59E0B',    // Amber
  prosperity: '#EAB308',    // Gold
  victory: '#EF4444',       // Crimson
  creativity: '#06B6D4',    // Cyan
};

/**
 * Convert polar angle (degrees) to Cartesian coordinates (x, y).
 * 0 degrees points straight UP (12 o'clock).
 */
export function polarToCartesian(
  cx: number,
  cy: number,
  radius: number,
  angleInDegrees: number,
): { x: number; y: number } {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: cx + radius * Math.cos(angleInRadians),
    y: cy + radius * Math.sin(angleInRadians),
  };
}

/**
 * Generate an SVG path for an annular sector (wedge between inner and outer radius).
 */
export function describeWedge(
  cx: number,
  cy: number,
  innerRadius: number,
  outerRadius: number,
  startAngle: number,
  endAngle: number,
): string {
  // Ensure strict sweep angle
  const sweep = endAngle - startAngle;
  const largeArcFlag = sweep <= 180 ? '0' : '1';

  const startOuter = polarToCartesian(cx, cy, outerRadius, startAngle);
  const endOuter = polarToCartesian(cx, cy, outerRadius, endAngle);
  const startInner = polarToCartesian(cx, cy, innerRadius, startAngle);
  const endInner = polarToCartesian(cx, cy, innerRadius, endAngle);

  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${endInner.x} ${endInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${startInner.x} ${startInner.y}`,
    'Z',
  ].join(' ');
}

/**
 * Format ISO time to short readable string (e.g., "14:30" or "2:30 PM").
 */
export function formatHourTime(isoString: string): string {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch {
    return isoString;
  }
}
