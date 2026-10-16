/**
 * Poll POST /videos/status for one video task until it reaches a terminal
 * status, then stop.
 *
 * Extracted from OutlookDashboard, whose inline poller read `.current` off a
 * `useState` value (a Timeout id or null, not a ref): the throw was swallowed
 * by the poll's own try/catch, so the interval was never cleared and the
 * done/failed toast never fired — it polled every 5s for the life of the tab.
 */
import { apiUrl } from '../utils/api';

/** Response of POST /api/v1/videos/status (video_generation.py). */
export interface VideoTaskStatus {
  task_id?: string;
  status?: string;
  video_url?: string;
  local_path?: string;
  video_prompt?: string;
  error?: string;
  model?: string;
}

const TERMINAL_STATUSES = new Set(['succeeded', 'done', 'failed']);

export function isVideoTaskTerminal(status: string | undefined): boolean {
  return status !== undefined && TERMINAL_STATUSES.has(status);
}

export interface VideoTaskPollOptions {
  taskId: string;
  model: string;
  intervalMs?: number;
  /** Every status response, including the terminal one. */
  onStatus: (status: VideoTaskStatus) => void;
  /** Once, with the terminal status, after polling has stopped. */
  onFinish: (status: VideoTaskStatus) => void;
}

/** Start polling; returns a `stop()` that is safe to call more than once. */
export function pollVideoTask({ taskId, model, intervalMs = 5000, onStatus, onFinish }: VideoTaskPollOptions): () => void {
  let stopped = false;
  const stop = (): void => {
    stopped = true;
    window.clearInterval(id);
  };
  const id = window.setInterval(async () => {
    try {
      const res = await fetch(apiUrl('/videos/status'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, model }),
      });
      if (stopped || !res.ok) return;
      const status = (await res.json()) as VideoTaskStatus;
      if (stopped) return;
      onStatus(status);
      if (isVideoTaskTerminal(status.status)) {
        stop();
        onFinish(status);
      }
    } catch {
      // Transient network error — keep polling.
    }
  }, intervalMs);
  return stop;
}
