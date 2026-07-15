/**
 * useAmbientBowl — tiny hook around a held sine-wave AudioContext
 * oscillator that emulates a singing bowl at a target frequency.
 *
 * Lifecycle:
 *   - Calling `start(freq)` creates an AudioContext, an OscillatorNode
 *     (sine, +3 cents detune for warmth), and a GainNode at ~15 % gain.
 *     The osc is started and the triple is held in a ref.
 *   - Calling `stop()` (or unmounting) tears down osc + ctx cleanly.
 *   - Calling `start(freq)` while already running is a no-op.
 *
 * The hook is fully decoupled from React state — callers drive it from
 * a useEffect watching `enabled && speaking` etc. Returning
 * `isPlaying` lets the UI reflect AudioContext suspension without
 * forcing a re-render on every frame.
 *
 * Safe under SSR / environments without Web Audio (the constructor
 * lookup returns undefined and start() silently no-ops).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAudioActivity } from '../stores/audioActivityStore';

interface AmbientNodes {
  osc: OscillatorNode;
  gain: GainNode;
  ctx: AudioContext;
}

interface UseAmbientBowl {
  start: (freq: number) => void;
  stop: () => void;
  isPlaying: boolean;
}

const GAIN_LEVEL = 0.15;
const DETUNE_CENTS = 3;

export function useAmbientBowl(): UseAmbientBowl {
  const ref = useRef<AmbientNodes | null>(null);
  const unregisterRef = useRef<(() => void) | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const stop = useCallback((): void => {
    const nodes = ref.current;
    if (!nodes) return;
    try {
      nodes.osc.stop();
    } catch {
      // osc may have already been stopped; safe to ignore.
    }
    void nodes.ctx.close().catch(() => undefined);
    ref.current = null;
    if (unregisterRef.current) {
      unregisterRef.current();
      unregisterRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const start = useCallback((freq: number): void => {
    if (ref.current) return;
    try {
      const Ctor = window.AudioContext
        ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return;
      const ctx = new Ctor();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      osc.detune.value = DETUNE_CENTS;
      gain.gain.value = GAIN_LEVEL;
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      ref.current = { osc, gain, ctx };
      setIsPlaying(true);
      unregisterRef.current = useAudioActivity.getState().register({
        id: 'ambient-bowl',
        name: `Ambient Bowl Drone (${freq} Hz)`,
        icon: '🥣',
        stop: () => stop(),
      });
    } catch {
      ref.current = null;
      setIsPlaying(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return { start, stop, isPlaying };
}