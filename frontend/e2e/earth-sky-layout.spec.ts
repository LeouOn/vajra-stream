/**
 * Earth & Sky — layout invariants against a FIXED sky (W3-M5).
 *
 * Why a fixture. The two columns of the Earth & Sky card do not have a fixed
 * height difference, and the difference is not a property of the layout: the
 * dome's side panel grows with what is overhead. Measured in real Chromium at
 * 1440 px (API on :8008, dev server on :3009, 2026-10-24):
 *
 *   - the planet list is 180..352 px tall and the nakshatra chip list 76..134 px,
 *     depending on how many planets and nakshatras are above the horizon;
 *   - sweeping the observer over twelve longitudes at one instant, the card's
 *     height went 748..823 px and the difference between the two column
 *     bottoms 1..98 px;
 *   - at 1280 px the difference is 170 px, because the dome's column has a
 *     610 px floor there (the dome needs 554 px inside for its canvas and its
 *     side panel) and that squeezes the left column.
 *
 * So a live bound on that number is a bound on the clock, not on the layout:
 * the real-routes smoke (earth-sky.spec.ts) prints the live difference and the
 * scrubbed one instead of asserting them. This spec freezes the sky - a real
 * /night-sky answer, captured once - and asserts what the layout does
 * guarantee:
 *
 *   1. the dome header shows its whole title and never collides with the
 *      Refresh button, at 1440, 480, 420, 356 and 320 px. Before W3-M5 the
 *      title was cut mid-word below ~460 px ("Celestial Night-Sky Do") and the
 *      Refresh button overlapped it by 19 px at 420 px and 83 px at 356 px;
 *   2. the two columns end within 100 px of each other at 1440 px;
 *   3. the card is one column below 1280 px and two columns from 1280 px;
 *   4. the flat strip stays capped at 720 px;
 *   5. the card fits the viewport at every width.
 *
 * The fixture is a real answer from the API (2026-10-24, 09:36 UTC, San
 * Francisco: 5 visible planets, 8 visible stars), captured once and never
 * fetched at test time. Raw response sha256
 * 8bd770fd6e02694fae741449727fa575dbabf62ad0e1ac35e0816bd9d4b489a2.
 *
 * Run: from frontend/, `npx playwright test e2e/earth-sky-layout.spec.ts`.
 * It needs no API: the night-sky route is mocked with the fixture.
 */
import { test, expect, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.resolve(SPEC_DIR, 'fixtures', 'night-sky-reference.json');
const NIGHT_SKY = readFileSync(FIXTURE, 'utf8');

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
  right: number;
  bottom: number;
}

interface HeaderFacts {
  title: Box | null;
  titleScrollWidth: number;
  titleClientWidth: number;
  titleText: string;
  button: Box | null;
  head: Box | null;
}

interface ColumnFacts {
  left: Box | null;
  right: Box | null;
  strip: Box | null;
  card: Box | null;
  innerWidth: number;
}

/** Mock the night-sky route with the captured answer: a fixed sky. */
async function freezeTheSky(page: Page): Promise<void> {
  await page.route('**/api/v1/astrology/night-sky*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: NIGHT_SKY }),
  );
}

async function openBroadcast(page: Page): Promise<void> {
  await page.goto('/operations/broadcast');
  await expect(page.getByTestId('earth-sky-card')).toBeVisible({ timeout: 30000 });
  // The dome's panel is what the fixed sky fills; wait for it to render.
  await expect(page.getByTestId('sky-side-panel')).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId('sky-planet-card').first()).toBeVisible({ timeout: 30000 });
}

async function headerFacts(page: Page): Promise<HeaderFacts> {
  return page.evaluate(() => {
    const box = (el: Element | null): Box | null => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
        right: Math.round(r.right),
        bottom: Math.round(r.bottom),
      };
    };
    const title = Array.from(document.querySelectorAll('span')).find(
      (s) => (s.textContent ?? '').trim() === 'Celestial Night-Sky Dome',
    );
    const button = Array.from(document.querySelectorAll('button')).find(
      (b) => (b.textContent ?? '').trim() === 'Refresh',
    );
    const head = document.querySelector('[data-testid="celestial-sky-dome-card"] .ant-card-head');
    return {
      title: box(title),
      titleScrollWidth: title ? title.scrollWidth : 0,
      titleClientWidth: title ? title.clientWidth : 0,
      titleText: (title?.textContent ?? '').trim(),
      button: box(button),
      head: box(head),
    };
  });
}

/** The whole title is readable and nothing sits on top of it. */
async function assertHeaderIntact(page: Page, label: string): Promise<void> {
  const facts = await headerFacts(page);
  console.log('DOME HEADER', label, JSON.stringify(facts));
  expect(facts.title, `${label}: no dome title`).not.toBeNull();
  expect(facts.button, `${label}: no Refresh button`).not.toBeNull();
  expect(facts.titleText, `${label}: the title text changed`).toBe('Celestial Night-Sky Dome');
  expect(
    facts.titleScrollWidth,
    `${label}: the title is cut (${facts.titleScrollWidth} > ${facts.titleClientWidth})`,
  ).toBeLessThanOrEqual(facts.titleClientWidth + 1);
  const title = facts.title!;
  const button = facts.button!;
  const overlapX = Math.min(title.right, button.right) - Math.max(title.x, button.x);
  const overlapY = Math.min(title.bottom, button.bottom) - Math.max(title.y, button.y);
  expect(
    overlapX > 0 && overlapY > 0,
    `${label}: the title overlaps the Refresh button by ${overlapX} x ${overlapY} px ${JSON.stringify(facts)}`,
  ).toBe(false);
}

async function columnFacts(page: Page): Promise<ColumnFacts> {
  return page.evaluate(() => {
    const box = (sel: string): Box | null => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
        right: Math.round(r.right),
        bottom: Math.round(r.bottom),
      };
    };
    return {
      left: box('[data-testid="earth-sky-left"]'),
      right: box('[data-testid="earth-sky-right"]'),
      strip: box('[data-testid="world-strip"]'),
      card: box('[data-testid="earth-sky-card"]'),
      innerWidth: window.innerWidth,
    };
  });
}

test.describe.configure({ mode: 'serial' });
// The header test drives five viewports in one browser session; Playwright's
// default 30 s per test is shorter than that run needs.
test.setTimeout(120_000);

test('the dome header shows its whole title at every width', async ({ page }) => {
  await freezeTheSky(page);
  for (const width of [1440, 480, 420, 356, 320]) {
    await page.setViewportSize({ width, height: 3200 });
    await openBroadcast(page);
    await assertHeaderIntact(page, `${width}px`);
    // The card must still fit the viewport.
    const facts = await columnFacts(page);
    expect(facts.card, `${width}: no card`).not.toBeNull();
    expect(facts.card!.x, `${width}: the card starts left of the viewport`).toBeGreaterThanOrEqual(-0.5);
    expect(facts.card!.right, `${width}: the card is wider than the viewport`).toBeLessThanOrEqual(
      facts.innerWidth + 0.5,
    );
  }
});

test('with a fixed sky the two columns end together at 1440 px', async ({ page }) => {
  await freezeTheSky(page);
  await page.setViewportSize({ width: 1440, height: 3200 });
  await openBroadcast(page);

  const facts = await columnFacts(page);
  expect(facts.left, 'no left column').not.toBeNull();
  expect(facts.right, 'no right column').not.toBeNull();
  const delta = Math.abs(facts.right!.bottom - facts.left!.bottom);
  console.log('CARD COLUMNS (fixed sky) 1440', JSON.stringify({ ...facts, bottomDelta: delta }));
  expect(delta, `the columns end ${delta} px apart`).toBeLessThanOrEqual(100);
  // The strip keeps its cap in the two-column layout.
  expect(facts.strip!.w, `the strip is ${facts.strip!.w} px wide (cap 720)`).toBeLessThanOrEqual(720.5);
});

test('the card is one column below 1280 px and two columns from 1280 px', async ({ page }) => {  await freezeTheSky(page);
  for (const [width, columns] of [
    [1100, 1],
    [1200, 1],
    [1280, 2],
    [1440, 2],
  ] as Array<[number, number]>) {
    await page.setViewportSize({ width, height: 3200 });
    await openBroadcast(page);
    const facts = await columnFacts(page);
    console.log('CARD COLUMNS', width, JSON.stringify(facts));
    expect(facts.left, `${width}: no left column`).not.toBeNull();
    expect(facts.right, `${width}: no right column`).not.toBeNull();
    if (columns === 1) {
      expect(
        Math.abs(facts.left!.x - facts.right!.x),
        `${width}: the columns are not stacked (x differs)`,
      ).toBeLessThanOrEqual(1);
      expect(facts.right!.y, `${width}: the right column is not below the left`).toBeGreaterThanOrEqual(
        facts.left!.y + facts.left!.h - 1,
      );
    } else {
      expect(
        Math.abs(facts.left!.x - facts.right!.x),
        `${width}: the columns are not side by side (x is the same)`,
      ).toBeGreaterThan(1);
      expect(facts.right!.y, `${width}: the right column is not beside the left`).toBeLessThanOrEqual(
        facts.left!.y + 1,
      );
    }
    expect(facts.strip!.w, `${width}: the strip is ${facts.strip!.w} px wide (cap 720)`).toBeLessThanOrEqual(
      720.5,
    );
  }
});

test('the hover tooltip keeps its width and stays inside the card', async ({ page }) => {
  await freezeTheSky(page);
  // A planet that is overhead in the fixture, with the dome's own projection
  // (the same one the hit test uses), so the hover lands on it.
  const fixture = JSON.parse(NIGHT_SKY) as {
    planets: Array<{ name: string; altitude: number; azimuth: number }>;
  };
  const planet = fixture.planets.find((p) => p.altitude > 5 && p.altitude < 80);
  expect(planet, 'the fixture has no planet overhead').toBeDefined();

  for (const width of [1440, 420]) {
    await page.setViewportSize({ width, height: 3200 });
    await openBroadcast(page);
    const canvas = page.getByTestId('celestial-sky-dome-canvas');
    const box = await canvas.boundingBox();
    expect(box, `${width}: no canvas`).not.toBeNull();
    const size = Math.min(box!.width, box!.height);
    const radius = size * 0.42;
    const r = ((90 - Math.max(0, planet!.altitude)) / 90) * radius;
    const rad = (planet!.azimuth * Math.PI) / 180;
    const px = box!.x + size / 2 - r * Math.sin(rad);
    const py = box!.y + size / 2 - r * Math.cos(rad);
    await page.mouse.move(px, py);
    const tooltip = page.getByTestId('sky-hover-tooltip');
    await expect(tooltip, `${width}: no tooltip on ${planet!.name}`).toBeVisible({ timeout: 5000 });
    const tip = (await tooltip.boundingBox())!;
    const card = (await page.getByTestId('celestial-sky-dome-card').boundingBox())!;
    console.log('HOVER TOOLTIP', width, JSON.stringify({ planet: planet!.name, tip, canvas: box }));
    // It must not be squeezed into a narrow column (it used to collapse to
    // 74 px, one word per line) and it must stay inside the card.
    expect(tip.width, `${width}: the tooltip is squeezed to ${tip.width} px`).toBeGreaterThanOrEqual(200);
    expect(tip.x, `${width}: the tooltip starts left of the card`).toBeGreaterThanOrEqual(card.x - 1);
    expect(
      tip.x + tip.width,
      `${width}: the tooltip hangs ${Math.round(tip.x + tip.width - (card.x + card.width))} px outside the card`,
    ).toBeLessThanOrEqual(card.x + card.width + 1);
  }
});
