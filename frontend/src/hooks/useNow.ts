import { useEffect, useState } from 'react';

/**
 * Current time in ms, re-rendering every `intervalMs` while `enabled`.
 * Used for live elapsed counts derived from a recorded start time.
 */
export function useNow(enabled: boolean, intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!enabled) return undefined;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
  return now;
}
