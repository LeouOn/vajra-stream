/**
 * E2E smoke tests for Vajra Stream.
 *
 * These verify the dev server boots and the shell renders.
 * They do NOT require the backend (port 8008) to be running.
 * For backend-dependent flows, see tests marked with @backend-required.
 */
import { test, expect } from '@playwright/test';

test.describe('App shell', () => {
  test('home page loads with a non-empty body', async ({ page }) => {
    const response = await page.goto('/');
    expect(response, 'no response from /').not.toBeNull();
    expect(response!.status()).toBeLessThan(400);
    const body = await page.locator('body').textContent();
    expect(body).toBeTruthy();
    expect(body!.length).toBeGreaterThan(0);
  });

  test('page has a <title>', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });

  test('Vite dev server returns 200 on root', async ({ request }) => {
    const res = await request.get('/');
    expect(res.status()).toBe(200);
  });
});
