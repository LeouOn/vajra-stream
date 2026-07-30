/**
 * Lightweight chat progress store.
 *
 * Components subscribe to receive real-time updates as the backend processes
 * async chat jobs. The WebSocket hook writes to this store; CommandCenter reads
 * from it to render progress indicators.
 */

type ProgressData = Record<string, unknown>;
type ProgressListener = (jobId: string, data: ProgressData) => void;

const _progress: Map<string, ProgressData> = new Map();
const _listeners: ProgressListener[] = [];

export function update(jobId: string, data: ProgressData): void {
  const merged = { ...(_progress.get(jobId) ?? {}), ...data, job_id: jobId };
  _progress.set(jobId, merged);
  for (const fn of _listeners) {
    try {
      fn(jobId, merged);
    } catch (err) {
      console.error('chat progress listener failed', err);
    }
  }
}

export function get(jobId: string): ProgressData | undefined {
  return _progress.get(jobId);
}

export function subscribe(fn: ProgressListener): () => void {
  _listeners.push(fn);
  return () => {
    const idx = _listeners.indexOf(fn);
    if (idx >= 0) _listeners.splice(idx, 1);
  };
}

export function clear(jobId: string): void {
  _progress.delete(jobId);
}
