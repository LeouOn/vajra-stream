/**
 * ritualAudio.ts — the Outlook ritual's audio cues (section chime and
 * dedication bell), synthesized on the shared audioFeedback context.
 * Both are silent when UI sounds are disabled or the context is suspended.
 */
import { audioFeedback } from '../../../utils/audioFeedback';

function runningContext(): AudioContext | null {
  if (!audioFeedback.enabled) return null;
  audioFeedback.init();
  const ctx = (audioFeedback as unknown as { ctx: AudioContext | null }).ctx;
  if (!ctx || ctx.state !== 'running') return null;
  return ctx;
}

/** A single 528 Hz sine chime, played as each ritual section is revealed. */
export function playSectionChime(): void {
  const ctx = runningContext();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(528, ctx.currentTime);
  gain.gain.setValueAtTime(0.1, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.5);
  osc.connect(gain).connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 1.5);
}

/** Bell = fundamental + two overtones with quick decay; closes the dedication. */
export function playDedicationBell(): void {
  const ctx = runningContext();
  if (!ctx) return;
  const now = ctx.currentTime;
  const partials = [528, 1056, 1584];
  partials.forEach((freq, i) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, now + i * 0.01);
    gain.gain.setValueAtTime(0.08, now + i * 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.01 + 2.0);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now + i * 0.01);
    osc.stop(now + i * 0.01 + 2.0);
  });
}
