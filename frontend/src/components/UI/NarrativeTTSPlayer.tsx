/**
 * NarrativeTTSPlayer — speaks a generated outlook narrative through the
 * unified TTSProvider (Qwen3-TTS or Edge) via the /api/v1/outlook/speak
 * streaming endpoint.
 *
 * Supports:
 *  - Play / stop a single string
 *  - Auto-speak on narrative change
 *  - Per-project speaker overrides
 *  - Volume slider
 *
 * @component
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Volume2, Square, Loader2, AlertTriangle, Settings2 } from 'lucide-react';
import { Button, Slider, Switch, Space, Tooltip, Tag } from 'antd';
import { audioFeedback } from '../../utils/audioFeedback';
import { useUIStore } from '../../stores/uiStore';
import { useAudioActivity } from '../../stores/audioActivityStore';

interface NarrativeTTSPlayerProps {
  text?: string;
  role?: string;
  projectId?: string | null;
  voice?: string | null;
  label?: string;
  size?: 'small' | 'middle' | 'large';
  showAdvanced?: boolean;
  onSpeakRef?: React.MutableRefObject<(() => void) | null>;
}

export default function NarrativeTTSPlayer({
  text,
  role = 'outlook_narrative',
  projectId = null,
  voice = null,
  label = 'Speak blessing',
  size = 'small',
  showAdvanced = true,
  onSpeakRef,
}: NarrativeTTSPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const ttsUnregisterRef = useRef<(() => void) | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const addToast = useUIStore((s) => s.addToast);
  const [loading, setLoading] = useState<boolean>(false);
  const [playing, setPlaying] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [autoSpeak, setAutoSpeak] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(0.85);
  const lastTextRef = useRef<string | null>(null);

  // IMPORTANT: declare callbacks BEFORE the useEffects that reference them.
  // The previous order had these two ``useCallback`` blocks AFTER the
  // ``useEffect`` blocks — a TDZ violation that crashed the Outlook
  // dashboard with "Cannot access 'stopAndCleanup' before initialization"
  // every time a narrative result was rendered.
  const stopAndCleanup = useCallback(() => {
    if (audioRef.current) {
      try { audioRef.current.pause(); } catch { /* noop */ }
      audioRef.current.src = '';
    }
    if (blobUrlRef.current) {
      try { URL.revokeObjectURL(blobUrlRef.current); } catch { /* noop */ }
      blobUrlRef.current = null;
    }
    ttsUnregisterRef.current?.();
    ttsUnregisterRef.current = null;
    setPlaying(false);
  }, []);

  const handleSpeak = useCallback(async (): Promise<void> => {
    if (!text) {
      addToast({ type: 'warning', title: 'No narrative to speak.', duration: 4 });
      return;
    }
    stopAndCleanup();
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setLoading(true);
    setError(null);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`/api/v1/outlook/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voice: voice || null,
          role,
          project_id: projectId || null,
        }),
        signal: abortRef.current.signal,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: 'TTS failed' })) as { detail?: string };
        throw new Error(detail.detail || 'TTS generation failed');
      }
      const mimeType = res.headers.get('Content-Type') || 'audio/mpeg';
      const backend = res.headers.get('X-TTS-Backend') || 'unknown';
      const blob = await res.blob();
      const url = URL.createObjectURL(new Blob([blob], { type: mimeType }));
      blobUrlRef.current = url;
      const audio = new Audio(url);
      audio.volume = volume;
      audioRef.current = audio;
      audio.onended = () => {
        setPlaying(false);
        ttsUnregisterRef.current?.();
        ttsUnregisterRef.current = null;
        if (blobUrlRef.current) {
          URL.revokeObjectURL(blobUrlRef.current);
          blobUrlRef.current = null;
        }
      };
      audio.onerror = () => {
        setError('Audio playback failed');
        setPlaying(false);
        ttsUnregisterRef.current?.();
        ttsUnregisterRef.current = null;
      };
      await audio.play();
      setPlaying(true);
      const activityId = `tts-${role}-${text?.slice(0, 16) || 'narrative'}`;
      ttsUnregisterRef.current = useAudioActivity.getState().register({
        id: activityId,
        name: role === 'outlook_epic' ? 'Narrative TTS (Epic)' : 'Narrative TTS Playback',
        icon: '🔊',
        stop: () => { try { audio.pause(); } catch { /* noop */ } },
      });
      addToast({ type: 'success', title: `Streaming via ${backend}`, duration: 3 });
      audioFeedback.playSuccess();
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        setError(null);
        return;
      }
      setError(e instanceof Error ? (e.message || String(e)) : String(e));
      audioFeedback.playError();
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [text, voice, role, projectId, volume, stopAndCleanup]);

  useEffect(() => {
    if (onSpeakRef) onSpeakRef.current = () => { handleSpeak(); };
  }, [handleSpeak, onSpeakRef]);

  // Stop + cleanup on unmount — now safely AFTER ``stopAndCleanup`` is declared.
  useEffect(() => {
    return () => stopAndCleanup();
  }, [stopAndCleanup]);

  // Auto-speak when the narrative text changes — now safely AFTER ``handleSpeak``.
  useEffect(() => {
    if (!autoSpeak) return;
    if (!text) return;
    if (text === lastTextRef.current) return;
    lastTextRef.current = text;
    handleSpeak();
  }, [text, autoSpeak, handleSpeak]);

  const handleStop = (): void => {
    abortRef.current?.abort();
    abortRef.current = null;
    stopAndCleanup();
    setLoading(false);
    audioFeedback.playClick();
  };

  const isActive = loading || playing;

  return (
    <Space size={6} wrap className="narrative-tts-player">
      {!isActive ? (
        <Tooltip title={error || label}>
          <Button
            size={size}
            type="primary"
            icon={<Volume2 className="w-3.5 h-3.5" />}
            onClick={handleSpeak}
            disabled={!text}
          >
            {label}
          </Button>
        </Tooltip>
      ) : (
        <Button
          size={size}
          danger
          icon={loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Square className="w-3.5 h-3.5" />}
          onClick={handleStop}
          title="Stop TTS"
        >
          {loading ? 'Stop' : 'Stop'}
        </Button>
      )}

      {showAdvanced && (
        <>
          <Tooltip title="Auto-speak when a new narrative is generated">
            <Space size={4}>
              <Switch
                size="small"
                checked={autoSpeak}
                onChange={setAutoSpeak}
              />
              <span className="text-[10px] text-slate-400">Auto</span>
            </Space>
          </Tooltip>
          <Tooltip title="Playback volume">
            <Slider
              size="small"
              min={0}
              max={1}
              step={0.05}
              value={volume}
              onChange={setVolume}
              style={{ width: 70 }}
            />
          </Tooltip>
          <Tag color="cyan" style={{ fontSize: 9 }}>{role}</Tag>
        </>
      )}

      {error && (
        <Tooltip title={error}>
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        </Tooltip>
      )}
    </Space>
  );
}
