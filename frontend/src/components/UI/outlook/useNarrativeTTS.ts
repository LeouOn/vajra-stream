/**
 * useNarrativeTTS — bridge between the Transmission card's NarrativeTTSPlayer
 * and the Ritual Summary's Replay button. The player registers its speak()
 * in `narrativeSpeakRef`; Replay calls it, or falls back to the section
 * chime when no player is mounted.
 */
import { useRef } from 'react';
import { playSectionChime } from './ritualAudio';

export function useNarrativeTTS() {
  const narrativeSpeakRef = useRef<(() => void) | null>(null);

  const replayTTS = (): void => {
    if (narrativeSpeakRef.current) {
      narrativeSpeakRef.current();
    } else {
      playSectionChime();
    }
  };

  return { narrativeSpeakRef, replayTTS };
}
