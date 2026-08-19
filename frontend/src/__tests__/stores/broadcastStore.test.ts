import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useBroadcastStore } from '../../stores/broadcastStore';

describe('broadcastStore', () => {
  beforeEach(() => {
    useBroadcastStore.getState().clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('pushes a new broadcast and calculates default expiresAt', () => {
    const baseTime = 1700000000000;
    vi.setSystemTime(baseTime);

    useBroadcastStore.getState().push({
      target: 'Japan',
      frequency_hz: 528,
      duration_minutes: 10,
    });

    const list = useBroadcastStore.getState().recentBroadcasts;
    expect(list).toHaveLength(1);
    expect(list[0].target).toBe('Japan');
    expect(list[0].frequency_hz).toBe(528);
    expect(list[0].receivedAt).toBe(baseTime);
    expect(list[0].expiresAt).toBe(baseTime + 10 * 60_000);
  });

  it('stores location, lat, and lon coordinates when provided', () => {
    useBroadcastStore.getState().push({
      target: 'Kathmandu Earthquake Relief',
      location: 'Nepal',
      lat: 27.7172,
      lon: 85.3240,
      frequency_hz: 528,
      duration_minutes: 15,
    });

    const event = useBroadcastStore.getState().recentBroadcasts[0];
    expect(event.target).toBe('Kathmandu Earthquake Relief');
    expect(event.location).toBe('Nepal');
    expect(event.lat).toBe(27.7172);
    expect(event.lon).toBe(85.3240);
  });

  it('caps entries to MAX_BROADCASTS (20)', () => {
    const baseTime = 1700000000000;
    vi.setSystemTime(baseTime);

    for (let i = 0; i < 25; i++) {
      useBroadcastStore.getState().push({
        target: `Target ${i}`,
        duration_minutes: 60,
      });
    }

    const list = useBroadcastStore.getState().recentBroadcasts;
    expect(list).toHaveLength(20);
    expect(list[0].target).toBe('Target 24');
  });

  it('prunes expired broadcasts', () => {
    const baseTime = 1700000000000;
    vi.setSystemTime(baseTime);

    useBroadcastStore.getState().push({
      target: 'Short',
      duration_minutes: 1, // expires in 1 min
    });

    useBroadcastStore.getState().push({
      target: 'Long',
      duration_minutes: 10, // expires in 10 mins
    });

    expect(useBroadcastStore.getState().recentBroadcasts).toHaveLength(2);

    // Advance 2 minutes
    vi.advanceTimersByTime(2 * 60_000);
    useBroadcastStore.getState().prune();

    const remaining = useBroadcastStore.getState().recentBroadcasts;
    expect(remaining).toHaveLength(1);
    expect(remaining[0].target).toBe('Long');
  });

  it('clears all broadcasts', () => {
    useBroadcastStore.getState().push({ target: 'Clear Me' });
    expect(useBroadcastStore.getState().recentBroadcasts).toHaveLength(1);
    useBroadcastStore.getState().clear();
    expect(useBroadcastStore.getState().recentBroadcasts).toHaveLength(0);
  });
});
