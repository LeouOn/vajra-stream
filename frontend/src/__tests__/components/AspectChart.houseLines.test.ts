/**
 * The astrologer prompt's house summary survives planets without a house.
 *
 * AspectChart grouped planets under `p.house || '?'` and then read each group
 * back with `byHouse[Number(h)]`; for the '?' group that is `byHouse[NaN]`
 * (undefined), so `.join` threw and "Ask the astrologer" failed outright.
 */
import { describe, it, expect } from 'vitest';
import { formatHouseLines } from '../../components/2D/AspectChart';

describe('formatHouseLines', () => {
  it('orders numeric houses and keeps house-less planets last', () => {
    const lines = formatHouseLines({
      '10': ['☉ sun in Leo 12.0°'],
      '?': ['♇ pluto in Scorpio 3.0°'],
      '2': ['☽ moon in Cancer 4.5°', '♀ venus in Cancer 20.1°'],
    });
    expect(lines.split('\n')).toEqual([
      '  House 2: ☽ moon in Cancer 4.5°, ♀ venus in Cancer 20.1°',
      '  House 10: ☉ sun in Leo 12.0°',
      '  House ?: ♇ pluto in Scorpio 3.0°',
    ]);
  });

  it('returns an empty string for no planets', () => {
    expect(formatHouseLines({})).toBe('');
  });
});
