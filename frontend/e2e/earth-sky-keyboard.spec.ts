/**
 * W6-D1a — the Earth & Sky card with a keyboard only (no mouse).
 *
 * Not a CI spec: it needs the real API behind the dev proxy. Run from a clean
 * clone with a dev server on the real backend:
 *   npx playwright test e2e/earth-sky-keyboard.spec.ts --config=pw.dev3073.config.ts
 */
import { expect, test, type Page } from '@playwright/test';

async function open(page: Page): Promise<void> {
  await page.goto('/operations/broadcast', { waitUntil: 'domcontentloaded' });
  await page.getByTestId('earth-sky-card').waitFor({ state: 'visible', timeout: 40000 });
  await page.getByTestId('world-strip').waitFor({ state: 'visible', timeout: 30000 });
}

function active(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el) return null;
    return {
      tag: el.tagName.toLowerCase(),
      testid: el.getAttribute('data-testid'),
      aria: el.getAttribute('aria-label'),
      role: el.getAttribute('role'),
      text: (el.textContent ?? '').trim().slice(0, 40),
    };
  });
}

async function tabTo(page: Page, predicate: (a: NonNullable<Awaited<ReturnType<typeof active>>>) => boolean, max = 40): Promise<NonNullable<Awaited<ReturnType<typeof active>>>> {
  for (let i = 0; i < max; i += 1) {
    await page.keyboard.press('Tab');
    const a = await active(page);
    if (a && predicate(a)) return a;
  }
  throw new Error(`Tab did not reach the target in ${max} presses; last ${JSON.stringify(await active(page))}`);
}

function parseObserver(label: string | null): { lat: number; lng: number } {
  const m = /observer (-?[\d.]+) ([NS]), (-?[\d.]+) ([EW])/.exec(label ?? '');
  if (!m) throw new Error(`no observer in aria-label: ${label}`);
  const lat = Number(m[1]) * (m[2] === 'S' ? -1 : 1);
  const lng = Number(m[3]) * (m[4] === 'W' ? -1 : 1);
  return { lat, lng };
}

test('Tab reaches the strip; ArrowRight five times moves the observer +5 degrees east', async ({ page }) => {
  await open(page);
  const strip = page.getByTestId('world-strip');
  const start = await tabTo(page, (a) => a.testid === 'world-strip');
  expect(start.role).toBe('application');
  const ring = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement;
    const style = getComputedStyle(el);
    return { style: style.outlineStyle, width: style.outlineWidth, color: style.outlineColor };
  });
  console.log('STRIP FOCUS RING', JSON.stringify(ring));
  expect(ring.style).not.toBe('none');
  expect(Number.parseFloat(ring.width)).toBeGreaterThan(0);
  const before = parseObserver(await strip.getAttribute('aria-label'));
  for (let i = 0; i < 5; i += 1) await page.keyboard.press('ArrowRight');
  await expect
    .poll(async () => parseObserver(await strip.getAttribute('aria-label')).lng, { timeout: 5000 })
    .toBeGreaterThan(before.lng + 4.9);
  const after = parseObserver(await strip.getAttribute('aria-label'));
  expect(after.lng).toBeLessThan(before.lng + 5.1);
  expect(after.lat).toBeCloseTo(before.lat, 1);
});

test('typing latitude/longitude and pressing Enter asks the dome for the new place', async ({ page }) => {
  await open(page);
  await tabTo(page, (a) => a.testid === 'world-strip');
  await tabTo(page, (a) => a.aria === 'Latitude, degrees north', 30);
  await page.keyboard.press('Control+A');
  await page.keyboard.type('36.1');
  await tabTo(page, (a) => a.aria === 'Longitude, degrees east', 5);
  await page.keyboard.press('Control+A');
  await page.keyboard.type('139.4');
  const response = page.waitForResponse(
    (res) =>
      res.url().includes('/astrology/night-sky') &&
      res.url().includes('latitude=36.1') &&
      res.url().includes('longitude=139.4') &&
      res.status() === 200,
    { timeout: 15000 },
  );
  await page.keyboard.press('Enter');
  const res = await response;
  expect(res.status()).toBe(200);
  const payload = (await res.json()) as { observer?: { latitude?: number; longitude?: number } };
  expect(payload.observer?.latitude).toBeCloseTo(36.1, 3);
  expect(payload.observer?.longitude).toBeCloseTo(139.4, 3);
  const label = await page.getByTestId('world-strip').getAttribute('aria-label');
  expect(label).toContain('observer 36.1 N, 139.4 E');
});

test('Tab walk from the Sky time card to the end of the card', async ({ page }) => {
  await open(page);
  const card = page.getByTestId('sky-time-controls');
  await page.getByLabel('Live sky time').focus();
  const stops: Array<{ tag: string; aria: string | null; role: string | null; text: string }> = [];
  for (let i = 0; i < 25; i += 1) {
    const a = await active(page);
    if (a) stops.push({ tag: a.tag, aria: a.aria, role: a.role, text: a.text });
    await page.keyboard.press('Tab');
    const next = await active(page);
    const inside = await page.evaluate(
      () => document.activeElement !== null && document.querySelector('[data-testid="sky-time-controls"]')?.contains(document.activeElement) === true,
    );
    if (!inside) break;
  }
  console.log('TAB STOPS FROM SKY TIME:', JSON.stringify(stops, null, 1));
  const expected = [
    'Live sky time',
    'Pause sky time at the current instant',
    'Play the time-lapse',
    'Time-lapse speed',
    'Time offset from now in minutes',
    'Latitude, degrees north',
    'Longitude, degrees east',
    'Set place from latitude and longitude',
    'Next sunrise at this location',
  ];
  const ids = stops.map((s) => s.aria ?? `${s.tag}:${s.text}`);
  expect(ids).toEqual(expected);
  expect(new Set(ids).size).toBe(expected.length);
  expect(ids).toContain('Set place from latitude and longitude');
});

test('a text the number control would strip is caught on the real blur-then-click path', async ({ page }) => {
  await open(page);
  const strip = page.getByTestId('world-strip');
  const before = parseObserver(await strip.getAttribute('aria-label'));
  const lng = page.getByLabel('Longitude, degrees east');
  await lng.focus();
  await page.keyboard.press('Control+A');
  await page.keyboard.type('37.7749°');
  // The mouse click is deliberate here: mousedown blurs the field before the
  // click, which is the exact order the happy-path Enter test does not cover.
  await page.getByRole('button', { name: 'Set place from latitude and longitude' }).click();
  await expect(page.getByTestId('sky-place-error')).toBeVisible();
  const after = parseObserver(await strip.getAttribute('aria-label'));
  expect(after.lng).toBe(before.lng);
  expect(after.lat).toBe(before.lat);
});

test('Alt+ArrowLeft on the focused strip is left to the browser (no longitude change)', async ({ page }) => {
  await open(page);
  await tabTo(page, (a) => a.testid === 'world-strip');
  const strip = page.getByTestId('world-strip');
  const before = parseObserver(await strip.getAttribute('aria-label')).lng;
  const prevented = await page.evaluate(() => {
    const el = document.querySelector('[data-testid="world-strip"]') as HTMLElement;
    const event = new KeyboardEvent('keydown', { key: 'ArrowLeft', altKey: true, bubbles: true, cancelable: true });
    el.dispatchEvent(event);
    return event.defaultPrevented;
  });
  expect(prevented).toBe(false);
  await expect
    .poll(async () => parseObserver(await strip.getAttribute('aria-label')).lng, { timeout: 3000 })
    .toBe(before);
});
