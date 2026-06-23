/**
 * Centralized logger for the frontend.
 *
 * Wraps console.* with:
 * - A `[vajra]` prefix so logs are searchable in browser DevTools
 * - ISO timestamps for ordering / debugging timing issues
 * - A single chokepoint to add monitoring (Sentry, Datadog) later
 * - Per-component context via `logger.with('ComponentName')`
 *
 * Usage:
 *   import { logger } from '../utils/logger';
 *   logger.error('Failed to load X:', err);          // [vajra] 2026-... Failed to load X: ...
 *
 *   const log = logger.with('ScalarTab');
 *   log.info('connecting');                          // [vajra:ScalarTab] 2026-... connecting
 *
 *   const scoped = createLogger('ScalarTab').with('useEffect');
 *   scoped.warn('retry');                            // [vajra:ScalarTab:useEffect] 2026-... retry
 *
 * Currently delegates to console.* — replace this file when adding a
 * monitoring backend (Sentry, Datadog, etc). No dependencies.
 */

const PREFIX = '[vajra';
const isoNow = (): string => new Date().toISOString();

export interface Logger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
  with: (context: string) => Logger;
}

function makeLogger(parentContext?: string): Logger {
  // tag is the full bracket: [vajra] for root, [vajra:A] for one with, [vajra:A:B] for chained.
  const tag = parentContext ? `${PREFIX}:${parentContext}]` : `${PREFIX}]`;
  return {
    debug: (...args: unknown[]) => console.debug(isoNow(), tag, ...args),
    info: (...args: unknown[]) => console.info(isoNow(), tag, ...args),
    warn: (...args: unknown[]) => console.warn(isoNow(), tag, ...args),
    error: (...args: unknown[]) => console.error(isoNow(), tag, ...args),
    with: (child: string): Logger =>
      makeLogger(parentContext ? `${parentContext}:${child}` : child),
  };
}

export const logger: Logger = makeLogger();
export const createLogger = (context: string): Logger => makeLogger(context);