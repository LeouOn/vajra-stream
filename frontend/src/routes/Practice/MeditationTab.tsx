/**
 * MeditationTab — fullscreen Rothko art generator with audio spectrum.
 *
 * Extracted verbatim from the legacy `/meditation` route in App.tsx as
 * part of the 12 → 7 nav consolidation (UI rework 2026-06-20). Renders
 * the RothkoGenerator filling the available tab area with the calm
 * "compassion" palette, plus an "Exit Meditation" control that returns
 * to the default Practice sub-tab (Sanctuary) instead of triggering a
 * browser-back, per the spec.
 *
 * Uses the shared hooks directly (no prop drilling) so the tab stays
 * self-contained inside the Practice tabbed layout.
 *
 * @component
 * @route /practice/meditation
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import RothkoGenerator from '../../components/2D/RothkoGenerator';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { useAudioStore } from '../../stores/audioStore';

export default function MeditationTab(): React.ReactElement {
  const navigate = useNavigate();
  const { audioSpectrum } = useWebSocketStable();
  const { isPlaying } = useAudioStore();

  return (
    <div className="relative w-full h-full bg-black overflow-hidden">
      <RothkoGenerator
        audioSpectrum={audioSpectrum}
        isPlaying={isPlaying}
        palette="compassion"
        transitionSpeed={30}
        fullscreen
      />
      <button
        onClick={() => navigate('/practice/sanctuary')}
        className="absolute top-4 right-4 z-50 bg-white/10 hover:bg-white/20 text-white/70 hover:text-white px-4 py-2 rounded-lg text-sm backdrop-blur-sm transition-colors"
      >
        Exit Meditation
      </button>
    </div>
  );
}
