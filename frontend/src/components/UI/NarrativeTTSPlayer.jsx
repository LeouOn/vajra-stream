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
import React, { useEffect, useRef, useState } from 'react';
import { Volume2, Square, Loader2, AlertTriangle, Settings2 } from 'lucide-react';
import { Button, Slider, Switch, Space, Tooltip, Tag, message } from 'antd';
import { API_BASE } from '../../utils/api';
import { audioFeedback } from '../../utils/audioFeedback';

export default function NarrativeTTSPlayer({
  text,
  role = 'outlook_narrative',
  projectId = null,
  voice = null,
  label = 'Speak blessing',
  size = 'small',
  showAdvanced = true,
}) {
  const audioRef = useRef(null);
  const blobUrlRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [volume, setVolume] = useState(0.85);
  const lastTextRef = useRef(null);

  // Stop + cleanup on unmount
  useEffect(() => {
    return () => stopAndCleanup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-speak when the narrative text changes
  useEffect(() => {
    if (!autoSpeak) return;
    if (!text) return;
    if (text === lastTextRef.current) return;
    lastTextRef.current = text;
    handleSpeak();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, autoSpeak]);

  const stopAndCleanup = () => {
    if (audioRef.current) {
      try { audioRef.current.pause(); } catch {}
      audioRef.current.src = '';
    }
    if (blobUrlRef.current) {
      try { URL.revokeObjectURL(blobUrlRef.current); } catch {}
      blobUrlRef.current = null;
    }
    setPlaying(false);
  };

  const handleSpeak = async () => {
    if (!text) {
      message.warning('No narrative to speak.');
      return;
    }
    stopAndCleanup();
    setLoading(true);
    setError(null);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`${API_BASE}/outlook/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voice: voice || null,
          role,
          project_id: projectId || null,
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: 'TTS failed' }));
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
        if (blobUrlRef.current) {
          URL.revokeObjectURL(blobUrlRef.current);
          blobUrlRef.current = null;
        }
      };
      audio.onerror = () => {
        setError('Audio playback failed');
        setPlaying(false);
      };
      await audio.play();
      setPlaying(true);
      message.success(`Streaming via ${backend}`);
      audioFeedback.playSuccess();
    } catch (e) {
      setError(e.message || String(e));
      audioFeedback.playError();
    } finally {
      setLoading(false);
    }
  };

  const handleStop = () => {
    stopAndCleanup();
    audioFeedback.playClick();
  };

  const isActive = loading || playing;

  return (
    <Space size={6} wrap className="narrative-tts-player">
      {!playing ? (
        <Tooltip title={error ? error : label}>
          <Button
            size={size}
            type="primary"
            icon={loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Volume2 className="w-3.5 h-3.5" />}
            onClick={handleSpeak}
            loading={loading}
            disabled={!text}
          >
            {label}
          </Button>
        </Tooltip>
      ) : (
        <Button
          size={size}
          danger
          icon={<Square className="w-3.5 h-3.5" />}
          onClick={handleStop}
        >
          Stop
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
