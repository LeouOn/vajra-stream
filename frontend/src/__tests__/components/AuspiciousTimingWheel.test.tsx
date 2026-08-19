import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import AuspiciousTimingWheel from '../../components/UI/AuspiciousTimingWheel';

const mockTimingWheelResponse = {
  status: 'success',
  datetime: '2026-08-18T14:30:00Z',
  location: { latitude: 37.7749, longitude: -122.4194 },
  current_planetary_hour: {
    ruler: 'Mars',
    day_planet: 'Mars',
    is_daytime: true,
    hour_number: 9,
  },
  moon: {
    phase_name: 'Waxing Gibbous',
    phase_angle: 120.0,
    glyph: '🌔',
    tithi: 'Shukla Ekadashi',
    nakshatra: 'Pushya',
    nakshatra_quality: 'nourishment, wisdom, auspicious for all',
  },
  saka_dawa: {
    is_saka_dawa: true,
    is_duchen: false,
    multiplier: 10000,
    message: 'Saka Dawa month is active',
  },
  hourly_slices: Array.from({ length: 24 }, (_, i) => ({
    index: i,
    period: i < 12 ? 'day' as const : 'night' as const,
    hour_number: (i % 12) + 1,
    ruler: ['Sun', 'Venus', 'Mercury', 'Moon', 'Saturn', 'Jupiter', 'Mars'][i % 7],
    start_time: `2026-08-18T${String(i).padStart(2, '0')}:00:00Z`,
    end_time: `2026-08-18T${String(i + 1).padStart(2, '0')}:00:00Z`,
    is_current: i === 8,
    affinities: {
      healing: i % 2 === 0 ? 'favorable' as const : 'unfavorable' as const,
      wisdom: 'neutral' as const,
    },
  })),
  genre_windows: {
    healing: {
      go: true,
      planetary_hour: 'Mars',
      tithi: 'Shukla Ekadashi',
      nakshatra: 'Pushya',
      quality: 'good',
      message: 'FAVORABLE — Good window for healing practice.',
      transmutation: '',
      transmutation_mantra: '',
      wait_minutes: 0,
      next_favorable_hour: 'Sun',
      time_shift_available: false,
      recommended_approach: 'direct',
    },
  },
  next_optimal_windows: {
    healing: [
      {
        period: 'day' as const,
        hour_number: 1,
        ruler: 'Sun',
        start_time: '2026-08-18T06:00:00Z',
        end_time: '2026-08-18T07:00:00Z',
        is_current: false,
      },
    ],
  },
};

const originalFetch = globalThis.fetch;

describe('AuspiciousTimingWheel', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: async () => mockTimingWheelResponse,
      } as Response),
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  });

  it('renders timing wheel title and moon details', async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<AuspiciousTimingWheel initialData={mockTimingWheelResponse} />);
    });

    expect(container.textContent || '').toContain('Auspicious Timing Wheel');
    expect(container.textContent || '').toContain('Saka Dawa ×10,000');
    expect(container.textContent || '').toContain('Pushya');
  });

  it('renders polar clock SVG with planetary symbols', async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<AuspiciousTimingWheel initialData={mockTimingWheelResponse} />);
    });

    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(container.textContent || '').toContain('Planetary Hour');
  });
});
