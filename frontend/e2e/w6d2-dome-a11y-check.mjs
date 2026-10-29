// W6-D3 real-browser check — run manually:
//   node frontend/e2e/w6d2-dome-a11y-check.mjs http://127.0.0.1:3024
// Asserts: Planets text / 24 px padding / Space / Enter each toggle exactly
// once; a real touch tap on the DISPLAYED Mars ring opens the tooltip and the
// polite live region; Escape and an outside tap close it; compatibility mouse
// events do not undo the tap; a two-finger press (release the first) opens
// nothing.
// Optional: set PLAYWRIGHT_CHROME to a Chromium binary; otherwise Playwright's
// own installed browser is used (`npx playwright install chromium`).
import { createRequire } from 'node:module';
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Resolve playwright from frontend/node_modules, relative to this script.
const require = createRequire(
  realpathSync(
    fileURLToPath(new URL('../node_modules/@playwright/test/package.json', import.meta.url)),
  ),
);
const { chromium } = require('playwright');

const BASE = process.argv[2] ?? 'http://127.0.0.1:3024';
const CHROME = process.env.PLAYWRIGHT_CHROME || undefined;

const NIGHT = {
  timestamp_utc: '2026-10-24T09:00:00Z',
  observer: {
    latitude: 37.7749,
    longitude: -122.4194,
    local_sidereal_time_deg: 298.11,
    local_sidereal_time_hms: '19:52:26',
  },
  moon: { phase_name: 'Waxing Crescent', illumination: 22.6 },
  planets: [
    { id: 'sun', name: 'Sun', glyph: '☉', altitude: -30, azimuth: 270, sign: 'Libra', sign_glyph: '♎', visible: false, color: '#f59e0b', esoteric_quality: 'q' },
    { id: 'moon', name: 'Moon', glyph: '☽', altitude: 22, azimuth: 180, sign: 'Cancer', sign_glyph: '♋', visible: true, color: '#e2e8f0', esoteric_quality: 'q' },
    { id: 'mars', name: 'Mars', glyph: '♂', altitude: 45, azimuth: 0, sign: 'Cancer', sign_glyph: '♋', visible: true, color: '#ef4444', esoteric_quality: 'q' },
    { id: 'jupiter', name: 'Jupiter', glyph: '♃', altitude: 30, azimuth: 120, sign: 'Cancer', sign_glyph: '♋', visible: true, color: '#a855f7', esoteric_quality: 'q' },
  ],
  visible_planets_count: 3,
  sacred_stars: [
    { id: 'sirius', name: 'Sirius (Mrigavyadha)', altitude: 35, azimuth: 60, magnitude: -1.46, visible: true, color: '#a6d8ff', nakshatra: 'Ardra', quality: 'q' },
  ],
  visible_stars_count: 1,
  provenance: { observer: 'computed' },
  position_frame: 'topocentric',
};
const EARTH = {
  at: '2026-10-24T09:00:00Z',
  ephemeris: 'stub',
  gast_deg: 60,
  sun: { id: 'sun', name: 'Sun', ra_deg: 0, dec_deg: 0, lat: 0, lon: 0 },
  moon: { id: 'moon', name: 'Moon', ra_deg: 0, dec_deg: 0, lat: 0, lon: 0 },
  planets: [],
  provenance: {},
};
const SUN_EVENTS = {
  at: '2026-10-24T09:00:00Z',
  latitude: 37.7749,
  longitude: -122.4194,
  previous_sunrise: '2026-10-24T14:30:00.000Z',
  sunset: '2026-10-25T01:10:00.000Z',
  next_sunrise: '2026-10-25T14:31:00.000Z',
  previous_sunset: '2026-10-24T01:09:00.000Z',
  next_sunset: '2026-10-25T01:10:00.000Z',
  provenance: {},
};

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME,
  args: ['--disable-dev-shm-usage'],
});
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  isMobile: true,
  deviceScaleFactor: 1,
});
const page = await context.newPage();
await page.route('**/api/v1/**', async (route) => {
  const url = route.request().url();
  if (url.includes('/astrology/night-sky')) return route.fulfill({ json: NIGHT });
  if (url.includes('/astrology/sun-events')) return route.fulfill({ json: SUN_EVENTS });
  if (url.includes('/astrology/earth-state/series'))
    return route.fulfill({ status: 422, json: { detail: 'stub' } });
  if (url.includes('/astrology/earth-state')) return route.fulfill({ json: EARTH });
  return route.fulfill({ json: {} });
});
const pageErrors = [];
page.on('pageerror', (error) => pageErrors.push(String(error)));

await page.goto(`${BASE}/operations/broadcast`, { waitUntil: 'domcontentloaded' });
const canvas = page.locator('[data-testid="celestial-sky-dome-canvas"]');
await canvas.waitFor({ state: 'visible', timeout: 40000 });
await page.waitForFunction(
  () => {
    const element = document.querySelector('[data-testid="celestial-sky-dome-canvas"]');
    return element?.getAttribute('role') === 'application' && (element.dataset.skyMarkers ?? '').includes('mars');
  },
  { timeout: 20000 },
);
await canvas.evaluate((element) => element.scrollIntoView({ block: 'center' }));
await page.waitForTimeout(500);

// ---- switch single-toggle checks -----------------------------------------
const switchEl = page.locator('[data-testid="sky-switch-planets"] [role="switch"]');
const row = page.locator('[data-testid="sky-switch-planets"]');
const target = page.locator('[data-testid="sky-switch-target-planets"]');
const readSwitch = () => switchEl.getAttribute('aria-checked');
const states = [await readSwitch()];
await page.locator('[data-testid="sky-switch-planets"] > span:last-child').click();
await page.waitForTimeout(120);
states.push(await readSwitch());
const targetBox = await target.boundingBox();
const switchBox = await switchEl.boundingBox();
if (!targetBox || !switchBox) throw new Error('switch boxes missing');
const paddingPoint = { x: targetBox.x + targetBox.width / 2, y: targetBox.y + 2 };
const paddingHit = await page.evaluate(
  ([x, y]) => {
    const el = document.elementFromPoint(x, y);
    return el === null
      ? 'none'
      : `${el.tagName.toLowerCase()}.${String(el.className).split(' ').slice(0, 2).join('.')}`;
  },
  [paddingPoint.x, paddingPoint.y],
);
await page.mouse.click(paddingPoint.x, paddingPoint.y);
await page.waitForTimeout(120);
states.push(await readSwitch());
await switchEl.focus();
await page.keyboard.press('Space');
await page.waitForTimeout(120);
states.push(await readSwitch());
await page.keyboard.press('Enter');
await page.waitForTimeout(120);
states.push(await readSwitch());
const expected = [states[0], states[0] === 'true' ? 'false' : 'true'];
const toggleOnce =
  states[1] === expected[1] &&
  states[2] === expected[0] &&
  states[3] === expected[1] &&
  states[4] === expected[0];

// ---- tap the DISPLAYED Mars ring ----------------------------------------
await canvas.evaluate((element) => element.scrollIntoView({ block: 'center' }));
await page.waitForTimeout(300);
const markers = await canvas.evaluate((element) => element.dataset.skyMarkers ?? '');
const marsMarker = markers
  .split(';')
  .map((entry) => entry.split(':'))
  .map(([id, point]) => ({ id, point: (point ?? '').split(',').map(Number) }))
  .find((entry) => entry.id === 'mars');
if (!marsMarker || marsMarker.point.length !== 2 || marsMarker.point.some(Number.isNaN)) {
  throw new Error(`mars marker missing: ${markers}`);
}
const canvasBox = await canvas.boundingBox();
if (!canvasBox) throw new Error('canvas box missing');
const tapPoint = { x: canvasBox.x + marsMarker.point[0], y: canvasBox.y + marsMarker.point[1] };

await page.evaluate(() => {
  window.__compat = { move: 0, leave: 0 };
  document.addEventListener('mousemove', () => {
    window.__compat.move += 1;
  }, true);
  document.addEventListener('mouseleave', () => {
    window.__compat.leave += 1;
  }, true);
});

await page.touchscreen.tap(tapPoint.x, tapPoint.y);
await page.waitForTimeout(350);
const tapCount = await page.locator('[data-testid="sky-hover-tooltip"]').count();
const tapText = tapCount > 0 ? await page.locator('[data-testid="sky-hover-tooltip"]').innerText() : '';
const liveAfterTap = await page.locator('[data-testid="sky-dome-live"]').textContent();
const compat = await page.evaluate(() => {
  return window.__compat ?? { move: -1, leave: -1 };
});
await page.waitForTimeout(600);
const tapAfterGuard = await page.locator('[data-testid="sky-hover-tooltip"]').count();
const focusedAfterTap = await page.evaluate(
  () => document.activeElement?.getAttribute('data-testid') ?? '',
);

// ---- Escape closes --------------------------------------------------------
await canvas.evaluate((element) => element.focus());
await page.keyboard.press('Escape');
await page.waitForTimeout(120);
const afterEscape = await page.locator('[data-testid="sky-hover-tooltip"]').count();

// ---- outside tap closes ---------------------------------------------------
await page.touchscreen.tap(tapPoint.x, tapPoint.y);
await page.waitForTimeout(150);
const reopened = await page.locator('[data-testid="sky-hover-tooltip"]').count();
await page.touchscreen.tap(10, 10);
await page.waitForTimeout(150);
const afterOutside = await page.locator('[data-testid="sky-hover-tooltip"]').count();

// ---- two fingers: press both, release the first --------------------------
const client = await context.newCDPSession(page);
const otherPoint = { x: tapPoint.x + 40, y: tapPoint.y };
let twoFinger = { afterFirstRelease: -1, afterBothReleased: -1 };
try {
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [
      { x: tapPoint.x, y: tapPoint.y, id: 1 },
      { x: otherPoint.x, y: otherPoint.y, id: 2 },
    ],
  });
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchEnd',
    touchPoints: [{ x: otherPoint.x, y: otherPoint.y, id: 2 }],
  });
  await page.waitForTimeout(150);
  const afterFirstRelease = await page.locator('[data-testid="sky-hover-tooltip"]').count();
  await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await page.waitForTimeout(150);
  const afterBothReleased = await page.locator('[data-testid="sky-hover-tooltip"]').count();
  twoFinger = { afterFirstRelease, afterBothReleased };
} catch (error) {
  twoFinger = { afterFirstRelease: -2, afterBothReleased: -2 };
  pageErrors.push(`two-finger: ${String(error)}`);
}

const result = {
  role: await canvas.getAttribute('role'),
  roledescription: await canvas.getAttribute('aria-roledescription'),
  states,
  toggleOnce,
  paddingHit,
  targetSize: { width: Math.round(targetBox.width), height: Math.round(targetBox.height) },
  switchSize: { width: Math.round(switchBox.width), height: Math.round(switchBox.height) },
  markers,
  tapPoint,
  tapCount,
  tapText: tapText.slice(0, 80),
  liveAfterTap: (liveAfterTap ?? '').trim().slice(0, 80),
  compatEvents: compat,
  tapAfterGuard,
  focusedAfterTap,
  afterEscape,
  reopened,
  afterOutside,
  twoFinger,
  pageErrors: pageErrors.slice(0, 5),
};
console.log(JSON.stringify(result, null, 1));

// W6-D3: the tap proof is REQUIRED. A tap must open the tooltip at the
// displayed ring and announce it; the tap must survive compatibility mouse
// events; Escape and an outside tap must close it.
const pass =
  toggleOnce &&
  targetBox.width >= 24 &&
  targetBox.height >= 24 &&
  tapCount === 1 &&
  tapText.includes('Mars') &&
  result.liveAfterTap.includes('Mars') &&
  tapAfterGuard === 1 &&
  afterEscape === 0 &&
  reopened === 1 &&
  afterOutside === 0 &&
  twoFinger.afterFirstRelease === 0 &&
  twoFinger.afterBothReleased === 0 &&
  pageErrors.length === 0;
await browser.close();
process.exit(pass ? 0 : 1);
