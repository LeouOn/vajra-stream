import { describe, expect, it } from 'vitest';
import { describePresence } from '../../components/CommandCenter/SystemMonitorsCard';

// Field Presence must reflect real state only — never a synthesized reading.
describe('describePresence', () => {
  it('rests when nothing is playing and no sessions are active', () => {
    expect(describePresence(false, {})).toEqual({ holding: false, label: 'Resting' });
    expect(describePresence(false, undefined)).toEqual({ holding: false, label: 'Resting' });
  });

  it('names exactly what is holding the field', () => {
    expect(describePresence(true, {})).toEqual({ holding: true, label: 'Holding · audio' });
    expect(describePresence(false, { a: {} })).toEqual({ holding: true, label: 'Holding · 1 session' });
    expect(describePresence(true, { a: {}, b: {} })).toEqual({ holding: true, label: 'Holding · audio + 2 sessions' });
  });

  it('is deterministic for the same state', () => {
    const first = describePresence(true, { a: {} });
    for (let i = 0; i < 20; i++) expect(describePresence(true, { a: {} })).toEqual(first);
  });
});
