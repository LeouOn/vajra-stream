/**
 * ws-contract.test.ts — Wave 4 Task 24 ( Remediation-24 )
 *
 * Bidirectional WebSocket message-type contract test.
 *
 * Source of truth: .omo/evidence/wave0-task3-ws-whitelist.json (Wave 0 Task 3).
 * The canonical set of backend-emitted WS message types is the union of the
 * whitelist's `matched` (14) and `backend_only` (4) entries = 18 types total.
 *
 * This test enforces BOTH drift directions against the single canonical set:
 *
 *   1. Every backend-emitted type MUST have a corresponding `case` in the
 *      `useWebSocketStable` switch (no silent `default:` drops).
 *   2. Every `case` in the switch MUST correspond to a backend-emitted type
 *      (no dead branches handling messages the backend will never send).
 *
 * Reconnect-survival guarantee: because the hook's `onmessage` handler wraps
 * the switch in a try/catch and every backend type has an explicit case,
 * receiving ANY backend-emitted message type cannot break the connection —
 * the new types (SESSION_STARTED, settings_updated, system_error) are now
 * handled rather than falling through to `default:` console.log noise, and
 * there are no dead branches to mislead future maintainers.
 *
 * When this test fails, it prints the exact drift:
 *   - `missingCases`   — backend emits, frontend silent (RED before Task 24)
 *   - `deadCases`      — frontend handles, backend never emits (RED before Task 24)
 *
 * The companion CI guard is scripts/audit_ws_contract.py which performs the
 * same comparison dynamically against the live backend source files.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Canonical backend-emitted WS message types.
 * Originally 18 (wave0-task3 whitelist union); 10 more restored after
 * remediation Task 24 regressively deleted their case branches; 3 more
 * (SessionCreated/Started/Stopped) added when the camelCase DomainEvent
 * forwarders from orchestrator_bridge._forward_event_to_websocket were
 * wired into the sessions map; 3 more (CURRENT_ASTROLOGY/MOPS_AVERAGES/
 * JOURNEY_STATUS) added when the slow-data broadcast loop replaced
 * frontend HTTP polling. Total = 34.
 * DO NOT edit this set without first updating the whitelist evidence file.
 */
const BACKEND_EMITTED_TYPES: ReadonlySet<string> = new Set([
  // --- matched (backend emits + frontend handles) ---
  'realtime_data',
  'session_update',
  'connection_status',
  'heartbeat',
  'pong',
  'ping',
  'RNG_READING',
  'BUDDHA_RECITATION_UPDATE',
  'SAKA_DAWA_CHECK',
  'PROVIDER_HEALTH',
  'CRYSTAL_BROADCAST_STARTED',
  'RADIONICS_RATE_BROADCAST',
  'SCALAR_WAVE_ACTIVE',
  'error', // lowercase — distinct from uppercase ERROR
  // --- backend_only (backend emits, frontend must handle) ---
  'ERROR', // uppercase — added in Wave 1 Task 10
  'SESSION_STARTED',
  'settings_updated',
  'system_error',
  // --- restored after remediation Task 24 regression (core/ emitters) ---
  // 88-Buddhas recitation lifecycle (core/buddha_recitation_loop.py).
  'BUDDHA_RECITATION_STARTED',
  'BUDDHA_NAME_RECITED',
  'BUDDHA_RECITATION_STOPPED',
  // Ritual engine lifecycle + planetary-hour shift (core/ritual_engine.py).
  'RITUAL_ENGINE_STATUS',
  'RITUAL_PHASE',
  'RITUAL_COMPLETED',
  'PLANETARY_HOUR_SHIFT',
  // Character journey lifecycle (core/character_journey.py).
  'JOURNEY_STAGE_STARTED',
  'JOURNEY_STAGE_COMPLETED',
  'JOURNEY_COMPLETED',
  // DomainEvent forwarders from orchestrator_bridge._forward_event_to_websocket.
  // Class names become WS message `type` strings; payload wrapped in {type, timestamp, data:{...}}.
  'SessionCreated',
  'SessionStarted',
  'SessionStopped',
  // Slow-data broadcasts from main.py _slow_data_broadcast_loop (10s interval).
  // Replace frontend HTTP polling with WebSocket push.
  'CURRENT_ASTROLOGY',
  'MOPS_AVERAGES',
  'JOURNEY_STATUS',
]);

const HOOK_PATH = resolve(process.cwd(), 'src/hooks/useWebSocketStable.ts');

/**
 * Extract every `case '<TYPE>':` literal from the `switch (data.type)` block
 * of useWebSocketStable.ts. Returns the set of case labels (string literals only).
 *
 * The regex captures string-literal case labels (`case 'foo':` / `case "foo":`).
 * It is scoped to the onmessage switch block to avoid stray matches elsewhere.
 */
function extractFrontendCases(): Set<string> {
  const source = readFileSync(HOOK_PATH, 'utf8');

  // Locate the message-handling switch block.
  const switchStart = source.indexOf('switch (data.type)');
  if (switchStart === -1) {
    throw new Error('Could not locate `switch (data.type)` in useWebSocketStable.ts');
  }
  // Find the matching closing brace of the switch by brace counting.
  const braceStart = source.indexOf('{', switchStart);
  if (braceStart === -1) {
    throw new Error('Malformed switch statement — no opening brace');
  }
  let depth = 0;
  let switchEnd = -1;
  for (let i = braceStart; i < source.length; i++) {
    const ch = source[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) { switchEnd = i; break; }
    }
  }
  if (switchEnd === -1) {
    throw new Error('Could not find closing brace of `switch (data.type)` block');
  }
  const switchBlock = source.slice(braceStart, switchEnd);

  const cases = new Set<string>();
  // Match: case '<label>':  or  case "<label>":
  const casePattern = /case\s+(['"])([A-Za-z_][A-Za-z0-9_]*)\1\s*:/g;
  let m: RegExpExecArray | null;
  while ((m = casePattern.exec(switchBlock)) !== null) {
    cases.add(m[2]);
  }
  return cases;
}

describe('WebSocket message-type contract (wave4-task24)', () => {
  const frontendCases = extractFrontendCases();

  it('frontend switch has exactly the same number of cases as the canonical backend set', () => {
    // Sanity guard: if either side changes count without the other following,
    // fail loudly with counts rather than a confusing subset diff.
    expect(
      frontendCases.size,
      `frontend has ${frontendCases.size} case labels but canonical backend set has ${BACKEND_EMITTED_TYPES.size}. ` +
      `Run scripts/audit_ws_contract.py for details.`,
    ).toBe(BACKEND_EMITTED_TYPES.size);
  });

  it('every backend-emitted type has a frontend handler case (no silent drops)', () => {
    const missingCases = [...BACKEND_EMITTED_TYPES].filter(
      (t) => !frontendCases.has(t),
    );
    expect(
      missingCases,
      `Backend emits these types but frontend switch has no case: [${missingCases.join(', ')}]. ` +
      `Add a case branch for each in useWebSocketStable.ts.`,
    ).toEqual([]);
  });

  it('every frontend case has a backend emitter (no dead branches)', () => {
    const deadCases = [...frontendCases].filter(
      (t) => !BACKEND_EMITTED_TYPES.has(t),
    );
    expect(
      deadCases,
      `Frontend switch handles these types but backend never emits them: [${deadCases.join(', ')}]. ` +
      `Delete the dead case branch from useWebSocketStable.ts.`,
    ).toEqual([]);
  });

  it('frontend case set exactly equals canonical backend set (no drift in either direction)', () => {
    // Bidirectional equality — the single strongest assertion.
    expect([...frontendCases].sort()).toEqual([...BACKEND_EMITTED_TYPES].sort());
  });
});
