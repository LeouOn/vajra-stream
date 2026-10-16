/**
 * useRitualReveal — progressive section reveal for a ritual narrative.
 *
 * Sections (I. Invocatio … V. Dedicatio) fade in one at a time, ~1.5s
 * apart. `revealedSections` counts how many have appeared so far; each
 * reveal plays a chime and the last one (the dedication) a bell. Pending
 * timers are cleared whenever a new narrative arrives and on unmount.
 */
import { useState, useEffect, useMemo, useRef } from 'react';
import { parseSections, type CurrentNarrative } from './outlookNarrative';
import { playDedicationBell, playSectionChime } from './ritualAudio';

export const REVEAL_STEP_MS = 1500;

export function useRitualReveal(currentNarrative: CurrentNarrative | null) {
  const [revealedSections, setRevealedSections] = useState<number>(0);
  const revealTimersRef = useRef<number[]>([]);

  const sections = useMemo<string[]>(() => {
    if (!currentNarrative?.narrative) return [];
    return parseSections(currentNarrative.narrative);
  }, [currentNarrative]);

  useEffect(() => {
    revealTimersRef.current.forEach(t => window.clearTimeout(t));
    revealTimersRef.current = [];
    setRevealedSections(0);
    if (sections.length === 0) return;
    sections.forEach((_, i) => {
      const idx = i;
      const timer = window.setTimeout(() => {
        setRevealedSections(idx + 1);
        if (idx === sections.length - 1) {
          playDedicationBell();
        } else {
          playSectionChime();
        }
      }, (idx + 1) * REVEAL_STEP_MS);
      revealTimersRef.current.push(timer);
    });
    return () => {
      revealTimersRef.current.forEach(t => window.clearTimeout(t));
      revealTimersRef.current = [];
    };
  }, [sections]);

  return { sections, revealedSections };
}
