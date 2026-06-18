/**
 * Regression test: ensures the 7 orphan UI components + 1 orphan test
 * deleted in Wave 3 Task 17 (remediation-17) are NOT re-introduced.
 *
 * Each file below was confirmed orphan (no imports anywhere in frontend/src)
 * prior to deletion. See .omo/evidence/wave3-task17-orphan-ui-removed.txt.
 *
 * DO NOT recreate these files without first wiring them into the app.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const UI_DIR = path.resolve(__dirname, '..', 'components', 'UI');
const TEST_COMPONENT_DIR = path.resolve(__dirname, 'components');

const ORPHAN_FILES = [
  // [relativeLabel, absolutePath]
  ['UI/ControlPanel.jsx', path.join(UI_DIR, 'ControlPanel.jsx')],
  ['UI/SessionManager.jsx', path.join(UI_DIR, 'SessionManager.jsx')],
  ['UI/RadionicsBroadcastPanel.jsx', path.join(UI_DIR, 'RadionicsBroadcastPanel.jsx')],
  ['UI/SidebarSection.jsx', path.join(UI_DIR, 'SidebarSection.jsx')],
  ['UI/StatusIndicator.jsx', path.join(UI_DIR, 'StatusIndicator.jsx')],
  ['UI/TransitTimeline.jsx', path.join(UI_DIR, 'TransitTimeline.jsx')],
  ['UI/DailyHoroscope.jsx', path.join(UI_DIR, 'DailyHoroscope.jsx')],
  ['__tests__/components/StatusIndicator.test.tsx', path.join(TEST_COMPONENT_DIR, 'StatusIndicator.test.tsx')],
] as const;

describe('remediation-17: orphan UI components stay deleted', () => {
  it.each(ORPHAN_FILES)('file %s must NOT exist', (_label, absPath) => {
    expect(fs.existsSync(absPath)).toBe(false);
  });
});
