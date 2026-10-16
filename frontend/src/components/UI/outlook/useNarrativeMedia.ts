/**
 * useNarrativeMedia — media generated from the current narrative:
 * the sacred illustration (POST /outlook/illustration, captioned with the
 * server's caption_facts) and the manifestation video (POST
 * /videos/from-narrative, then a status poll).
 *
 * The video poll's stop() lives in a ref: it is replaced when a new task is
 * submitted, cleared when the poll finishes, and called on unmount so a poll
 * never outlives the page.
 */
import { useState, useEffect, useRef } from 'react';
import { message } from 'antd';
import { apiUrl } from '../../../utils/api';
import { audioFeedback } from '../../../utils/audioFeedback';
import { pollVideoTask, type VideoTaskStatus } from '../../../lib/videoTaskPoll';
import { narrativePlainText, type CurrentNarrative, type IllustrationResult } from './outlookNarrative';

export function useNarrativeMedia(currentNarrative: CurrentNarrative | null) {
  const [illustrationLoading, setIllustrationLoading] = useState<boolean>(false);
  const [illustration, setIllustration] = useState<IllustrationResult | null>(null);
  const [videoGenLoading, setVideoGenLoading] = useState<boolean>(false);
  const [videoGenState, setVideoGenState] = useState<VideoTaskStatus | null>(null);
  // stop() for the active video-status poll (cleared on finish and unmount).
  const stopVideoPollRef = useRef<(() => void) | null>(null);
  useEffect(() => () => stopVideoPollRef.current?.(), []);

  const generateIllustration = async (): Promise<void> => {
    if (!currentNarrative) return;
    setIllustrationLoading(true);
    audioFeedback.playTelemetry();
    try {
      // The server builds an imagery-only prompt (chart numbers, headings and
      // glyphs stripped) and returns the real values as caption_facts.
      const storedId = Number(currentNarrative.id);
      const chartTime = currentNarrative.date_generated;
      const payload: Record<string, unknown> = Number.isInteger(storedId) && storedId > 0
        ? { narrative_id: storedId }
        : {
            narrative: narrativePlainText(currentNarrative),
            genre: currentNarrative.genre || 'healing',
            date: typeof chartTime === 'string' ? chartTime : undefined,
          };
      const res = await fetch(apiUrl('/outlook/illustration'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        setIllustration(data);
        message.success('Illustration generated.');
      } else {
        const err = await res.json().catch(() => ({})) as { detail?: string };
        message.error(err.detail || 'Image generation failed (is it enabled in Settings?).');
        audioFeedback.playError();
      }
    } catch {
      message.error('Network error — could not reach backend.');
      audioFeedback.playError();
    } finally {
      setIllustrationLoading(false);
    }
  };

  const generateVideoFromNarrative = async (): Promise<void> => {
    if (!currentNarrative) return;
    setVideoGenLoading(true);
    setVideoGenState(null);
    audioFeedback.playTelemetry();
    try {
      const narrativeText = narrativePlainText(currentNarrative);
      const payload: Record<string, unknown> = {
        narrative: narrativeText.slice(0, 3000),
        genre: currentNarrative.genre || 'healing',
        entities: currentNarrative.entities_used || '',
        divination: currentNarrative.divination_used || '',
      };
      if (currentNarrative.id != null) payload.narrative_id = currentNarrative.id;

      const res = await fetch(apiUrl('/videos/from-narrative'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        setVideoGenState(data);
        message.success('Video task submitted. Polling for completion...');
        stopVideoPollRef.current?.();
        stopVideoPollRef.current = pollVideoTask({
          taskId: data.task_id,
          model: data.model || 'MiniMax-H3',
          onStatus: setVideoGenState,
          onFinish: (sdata) => {
            stopVideoPollRef.current = null;
            if (sdata.status === 'failed') message.error(sdata.error || 'Video generation failed');
            else message.success('Video generated!');
          },
        });
      } else {
        const err = await res.json().catch(() => ({})) as { detail?: string };
        message.error(err.detail || 'Video generation failed (is it enabled in Settings?).');
        audioFeedback.playError();
      }
    } catch {
      message.error('Network error — could not reach backend.');
      audioFeedback.playError();
    } finally {
      setVideoGenLoading(false);
    }
  };

  return {
    illustration,
    illustrationLoading,
    generateIllustration,
    videoGenState,
    videoGenLoading,
    generateVideoFromNarrative,
  };
}

export type NarrativeMedia = ReturnType<typeof useNarrativeMedia>;
