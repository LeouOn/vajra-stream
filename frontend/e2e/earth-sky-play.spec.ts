/**
 * W5-C real-browser check: the time-lapse on the Sky time control.
 *
 * Needs the real API on :8008 (`python run.py serve` from the repo root) and a
 * frontend (dev server or preview). Press Play at 3600x: the shown instant must
 * advance by about an hour per second; Stop must freeze it; the fixed scrub
 * window must not refetch more than once or twice; at 420 px the card must not
 * overflow.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

const SHOT_DIR =
  process.env.EARTHSKY_PLAY_SHOT_DIR ?? path.resolve(process.cwd(), 'test-results', 'earth-sky-play');
const BACKEND = 'http://localhost:8008';

let backendUp = false;

test.beforeAll(async ({ request }) => {
  mkdirSync(SHOT_DIR, { recursive: true });
  try {
    const res = await request.get(`${BACKEND}/api/v1/astrology/night-sky`, {
      params: { latitude: 37.7749, longitude: -122.4194 },
      timeout: 5000,
    });
    backendUp = res.ok();
  } catch {
    backendUp = false;
  }
});

test.beforeEach(() => {
  test.skip(
    !backendUp,
    'API on localhost:8008 is unreachable — start it from the repo root with `python run.py serve`',
  );
});

async function readInstant(page: Page): Promise<number> {
  const text = (await page.getByTestId('sky-time-readout').textContent()) ?? '';
  const match = /(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) UTC/.exec(text);
  expect(match, `no UTC instant in the readout: ${text}`).not.toBeNull();
  return Date.parse(`${match![1]}T${match![2]}Z`);
}

test('Play at 3600x advances about an hour per second; Stop freezes it', async ({ page }) => {
  const series: string[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.endsWith('/astrology/earth-state/series')) {
      series.push(request.url());
    }
  });

  await page.setViewportSize({ width: 1440, height: 3200 });
  await page.goto('/operations/broadcast');
  await expect(page.getByTestId('earth-sky-card')).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId('celestial-sky-dome-canvas')).toBeVisible({ timeout: 30000 });

  await page.getByLabel('Time-lapse speed').selectOption('3600');
  await page.getByLabel('Play the time-lapse').click();
  await expect(page.getByLabel('Stop the time-lapse')).toHaveAttribute('aria-pressed', 'true');
  await page.waitForTimeout(150);
  const t0 = await readInstant(page);
  await page.waitForTimeout(1000);
  const t1 = await readInstant(page);
  const advanced = t1 - t0;
  console.log('PLAY ADVANCE', JSON.stringify({ t0, t1, advancedSeconds: advanced / 1000 }));
  expect(advanced).toBeGreaterThan(2_400_000); // at least ~40 min in one second
  expect(advanced).toBeLessThan(4_200_000); // and not more than ~70 min

  await page.getByLabel('Stop the time-lapse').click();
  const frozen = await readInstant(page);
  await page.waitForTimeout(700);
  expect(await readInstant(page)).toBe(frozen);

  console.log('SERIES REQUESTS', JSON.stringify(series));
  expect(series.length).toBeGreaterThanOrEqual(1);
  expect(series.length).toBeLessThanOrEqual(2);

  // Pictures with Play running, 1440 then 420 (the loop keeps running).
  await page.getByLabel('Play the time-lapse').click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOT_DIR, 'play-1440.png') });
  await page.getByTestId('earth-sky-card').screenshot({ path: path.join(SHOT_DIR, 'play-1440-card.png') });
  await page.setViewportSize({ width: 420, height: 3200 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SHOT_DIR, 'play-420.png') });
  await page.getByTestId('earth-sky-card').screenshot({ path: path.join(SHOT_DIR, 'play-420-card.png') });

  const layout = await page.evaluate(() => {
    const card = document.querySelector('[data-testid="earth-sky-card"]') as HTMLElement;
    const play = document.querySelector('[data-testid="sky-play-controls"]') as HTMLElement;
    const r = card.getBoundingClientRect();
    return {
      scrollWidth: card.scrollWidth,
      clientWidth: card.clientWidth,
      innerWidth: window.innerWidth,
      cardRight: r.right,
      play: play ? { scrollWidth: play.scrollWidth, clientWidth: play.clientWidth, right: play.getBoundingClientRect().right } : null,
      playing: document.querySelector('[data-testid="sky-play-status"]')?.textContent ?? null,
    };
  });
  console.log('PLAY 420', JSON.stringify(layout));
  expect(layout.scrollWidth, 'the card overflows horizontally at 420').toBeLessThanOrEqual(
    layout.clientWidth + 1,
  );
  expect(layout.cardRight, 'the card is wider than the 420 viewport').toBeLessThanOrEqual(
    layout.innerWidth + 0.5,
  );
  expect(layout.play?.scrollWidth ?? 0).toBeLessThanOrEqual((layout.play?.clientWidth ?? 0) + 1);
  expect(layout.playing).toContain('Playing at 3600x');

  await page.getByLabel('Stop the time-lapse').click();
});

test('a full +24 h run stays within one or two series windows', async ({ page }) => {
  const series: string[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.endsWith('/astrology/earth-state/series')) {
      series.push(request.url());
    }
  });
  await page.setViewportSize({ width: 1440, height: 3200 });
  await page.goto('/operations/broadcast');
  await expect(page.getByTestId('earth-sky-card')).toBeVisible({ timeout: 30000 });
  await page.getByLabel('Time-lapse speed').selectOption('3600');
  await page.getByLabel('Play the time-lapse').click();
  await expect(page.getByTestId('sky-play-status')).toHaveText(
    /Reached the end of the \+?-24 h window/,
    { timeout: 45000 },
  );
  console.log('FULL RUN SERIES', JSON.stringify(series));
  expect(series.length).toBeGreaterThanOrEqual(1);
  expect(series.length).toBeLessThanOrEqual(2);
  await expect(page.getByLabel('Play the time-lapse')).toHaveAttribute('aria-pressed', 'false');
});
