import { describe, it, expect } from 'vitest';
import {
  nudgeCarrierFrequency,
  STICK_PLATE_MAX_HZ,
  STICK_PLATE_MIN_HZ,
} from '../lib/stickPlate';

// The stick-plate carrier nudge used to pick a random direction on every rub
// event. It now follows the hand and is deterministic.
describe('nudgeCarrierFrequency', () => {
  it('raises the carrier when rubbing right and lowers it when rubbing left', () => {
    expect(nudgeCarrierFrequency(528, 40, 80, 5)).toBe(538);
    expect(nudgeCarrierFrequency(528, 40, 80, -5)).toBe(518);
  });

  it('leaves the carrier alone without horizontal movement', () => {
    expect(nudgeCarrierFrequency(528, 10, 80, 0)).toBe(528);
  });

  it('shifts more near the node and not at all at the edge of range', () => {
    expect(nudgeCarrierFrequency(528, 0, 80, 1)).toBe(548);
    expect(nudgeCarrierFrequency(528, 80, 80, 1)).toBe(528);
    expect(nudgeCarrierFrequency(528, 200, 80, 1)).toBe(528);
  });

  it('is deterministic for the same inputs', () => {
    const first = nudgeCarrierFrequency(432, 25, 80, 3);
    for (let i = 0; i < 50; i++) expect(nudgeCarrierFrequency(432, 25, 80, 3)).toBe(first);
  });

  it('stays inside the audible range', () => {
    expect(nudgeCarrierFrequency(STICK_PLATE_MIN_HZ, 0, 80, -1)).toBe(STICK_PLATE_MIN_HZ);
    expect(nudgeCarrierFrequency(STICK_PLATE_MAX_HZ, 0, 80, 1)).toBe(STICK_PLATE_MAX_HZ);
  });
});
