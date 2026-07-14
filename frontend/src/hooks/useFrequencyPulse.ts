import { useEffect, useRef } from 'react';

export type PracticePhase = 'idle' | 'invoking' | 'reciting' | 'dedicating' | 'completed';

const PHASE_MULTIPLIERS: Record<PracticePhase, number> = {
  idle: 0.5,
  invoking: 0.8,
  reciting: 1.5,
  dedicating: 1.2,
  completed: 0.3,
};

const PHASE_OPACITIES: Record<PracticePhase, number> = {
  idle: 0.6,
  invoking: 0.8,
  reciting: 1.0,
  dedicating: 0.9,
  completed: 0.7,
};

export function useFrequencyPulse(freqHz: number, phase: PracticePhase, isActive: boolean) {
  const frameRef = useRef(0);
  const rafRef = useRef(0);
  const callbackRef = useRef<(pulse: number, opacity: number) => void>(() => {});

  const speedMultiplier = PHASE_MULTIPLIERS[phase] || 0.5;
  const baseOpacity = PHASE_OPACITIES[phase] || 0.6;
  const freqDelta = (freqHz / 8000) * speedMultiplier;

  useEffect(() => {
    if (!isActive) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    const animate = () => {
      frameRef.current += freqDelta;
      const pulse = 0.5 + 0.3 * Math.sin(frameRef.current);
      const opacity = baseOpacity + pulse * 0.3;
      callbackRef.current(pulse, opacity);
      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [freqDelta, baseOpacity, isActive]);

  return {
    frame: frameRef,
    setCallback: (cb: (pulse: number, opacity: number) => void) => { callbackRef.current = cb; },
    speedMultiplier,
    baseOpacity,
  };
}
