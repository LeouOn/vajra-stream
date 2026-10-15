import { describe, it, expect } from 'vitest';
import { formatMoonIllumination } from '../lib/moonIllumination';

describe('formatMoonIllumination', () => {
  it('prints the backend percentage as-is', () => {
    expect(formatMoonIllumination(73.456)).toBe('73.5%');
    expect(formatMoonIllumination(100)).toBe('100.0%');
  });

  it('does not inflate sub-1% values near the new moon', () => {
    // Regression: the card treated <= 1 as a 0–1 fraction and showed 45.0%.
    expect(formatMoonIllumination(0.45)).toBe('0.5%');
    expect(formatMoonIllumination(1)).toBe('1.0%');
    expect(formatMoonIllumination(0)).toBe('0.0%');
  });

  it('renders a dash when illumination is missing', () => {
    expect(formatMoonIllumination(undefined)).toBe('—');
    expect(formatMoonIllumination(null)).toBe('—');
    expect(formatMoonIllumination(Number.NaN)).toBe('—');
  });
});
