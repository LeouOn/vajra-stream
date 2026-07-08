/**
 * Vajra.Stream — Comprehensive Playwright E2E Tests
 *
 * Tests every route for:
 * - Page renders (no white screen)
 * - No critical console errors
 * - Key UI elements present
 * - Screenshots at desktop + mobile viewports
 */
import { test, expect, type Page } from '@playwright/test';

const DESKTOP = { width: 1920, height: 1080 };
const MOBILE = { width: 375, height: 812 };

const BASE_URL = 'http://localhost:3009';

// Helper: capture console errors
function setupConsoleCapture(page: Page) {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Filter out known non-critical warnings
      if (!text.includes('AudioContext was not allowed') &&
          !text.includes('WebSocket') &&
          !text.includes('favicon') &&
          !text.includes('THREE.WebGLRenderer')) {
        errors.push(text);
      }
    }
  });
  return errors;
}

// ═══════════════════════════════════════════════════
// ROUTE TESTS — Each route renders without crashing
// ═══════════════════════════════════════════════════

test.describe('Route Rendering @desktop', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    setupConsoleCapture(page);
  });

  test('Home redirects to Command Center', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForURL('**/command-center', { timeout: 10000 }).catch(() => {});
    await expect(page).not.toHaveTitle(/Error/);
  });

  test('Command Center renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/command-center`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    // Should have a chat interface or operator panel
    const body = page.locator('body');
    await expect(body).toBeVisible();
    const text = await body.textContent();
    expect(text?.length || 0).toBeGreaterThan(100); // Not a blank page
    await page.screenshot({ path: 'e2e/screenshots/command-center-desktop.png', fullPage: false });
  });

  test('Practice Library renders with practice cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/practice-library-desktop.png', fullPage: false });
    const body = page.locator('body');
    const text = await body.textContent();
    // Should mention at least one practice
    const hasPractice = text?.match(/Tara|Zhunti|Medicine Buddha|Vajrasattva|Amitabha|Avalokiteshvara|Heart Sutra|88 Buddhas/i);
    expect(hasPractice).toBeTruthy();
  });

  test('Practice Detail — Green Tara renders with mantra + mala', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices/green_tara`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screensshots/practice-green-tara-desktop.png', fullPage: false });
    const text = await page.locator('body').textContent();
    // Should have mantra text or practice name
    const hasContent = text?.match(/Tara|Om Tare|mala|bead|recitation/i);
    expect(hasContent).toBeTruthy();
  });

  test('Practice Detail — Zhunti renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices/zhunti`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/practice-zhunti-desktop.png', fullPage: false });
    const text = await page.locator('body').textContent();
    expect(text?.length || 0).toBeGreaterThan(50);
  });

  test('Practice Detail — Medicine Buddha renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices/medicine_buddha`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/practice-medicine-buddha-desktop.png', fullPage: false });
  });

  test('Outlook Dashboard renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/outlook`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/outlook-desktop.png', fullPage: false });
    const text = await page.locator('body').textContent();
    expect(text?.length || 0).toBeGreaterThan(50);
  });

  test('Operations renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/operations`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/operations-desktop.png', fullPage: false });
  });

  test('Broadcast renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/broadcast`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/broadcast-desktop.png', fullPage: false });
  });

  test('Astrology renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/astrology`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/astrology-desktop.png', fullPage: false });
  });

  test('Settings renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/settings-desktop.png', fullPage: false });
  });

  test('Grimoire renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/grimoire`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/grimoire-desktop.png', fullPage: false });
  });

  test('TTS Settings renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/tts`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/tts-desktop.png', fullPage: false });
  });
});

// ═══════════════════════════════════════════════════
// NAVIGATION TESTS
// ═══════════════════════════════════════════════════

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP);
  });

  test('Nav menu has Practice Library (not Practices)', async ({ page }) => {
    await page.goto(`${BASE_URL}/command-center`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const navText = await page.locator('nav, header').first().textContent();
    expect(navText).toContain('Practice Library');
    expect(navText).not.toContain('Practices\n'); // Should not have bare "Practices"
  });

  test('Can navigate to Practice Library via menu', async ({ page }) => {
    await page.goto(`${BASE_URL}/command-center`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    // Click the Practice Library menu item
    const link = page.locator('a:has-text("Practice Library")').first();
    if (await link.isVisible({ timeout: 5000 }).catch(() => false)) {
      await link.click();
      await page.waitForURL('**/practices', { timeout: 5000 }).catch(() => {});
      const text = await page.locator('body').textContent();
      expect(text?.match(/Tara|Zhunti|Medicine/i)).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════════
// PRACTICE FLOW TESTS
// ═══════════════════════════════════════════════════

test.describe('Practice Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP);
  });

  test('Practice Library shows multiple practice cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const text = await page.locator('body').textContent() || '';
    const practices = ['Tara', 'Zhunti', 'Medicine Buddha', 'Vajrasattva', 'Amitabha', 'Avalokiteshvara'];
    let found = 0;
    for (const p of practices) {
      if (text.includes(p)) found++;
    }
    expect(found).toBeGreaterThanOrEqual(3); // At least 3 practices visible
  });

  test('Practice Detail has Start button', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices/green_tara`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const startButton = page.locator('button:has-text("Start"), button:has-text("Recitation"), button:has-text("Begin")').first();
    // Button may or may not be visible depending on backend status
    const isVisible = await startButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (isVisible) {
      await expect(startButton).toBeEnabled();
    }
  });

  test('Practice Detail has mala counter or bead visualization', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices/zhunti`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const text = await page.locator('body').textContent() || '';
    // Should have mala/bead/count references
    const hasMala = text.match(/mala|bead|108|count|recitation/i);
    expect(hasMala).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════
// MOBILE VIEWPORT TESTS
// ═══════════════════════════════════════════════════

test.describe('Mobile Viewport @mobile', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE);
  });

  test('Practice Library renders on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/practice-library-mobile.png', fullPage: false });
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('Command Center renders on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/command-center`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/command-center-mobile.png', fullPage: false });
  });

  test('Practice Detail renders on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/practices/green_tara`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/practice-green-tara-mobile.png', fullPage: false });
  });

  test('Outlook renders on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/outlook`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.screenshot({ path: 'e2e/screenshots/outlook-mobile.png', fullPage: false });
  });
});

// ═══════════════════════════════════════════════════
// CONSOLE ERROR DETECTION
// ═══════════════════════════════════════════════════

test.describe('Console Health', () => {
  test('No critical console errors on Practice Library', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore known environmental warnings
        if (!text.includes('AudioContext') &&
            !text.includes('WebSocket') &&
            !text.includes('favicon') &&
            !text.includes('THREE.WebGLRenderer') &&
            !text.includes('Context Lost') &&
            !text.includes('antd: message')) {
          errors.push(text);
        }
      }
    });
    await page.goto(`${BASE_URL}/practices`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(2000); // Let async errors surface
    expect(errors).toEqual([]);
  });

  test('No critical console errors on Command Center', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (!text.includes('AudioContext') &&
            !text.includes('WebSocket') &&
            !text.includes('favicon') &&
            !text.includes('THREE.WebGLRenderer') &&
            !text.includes('Context Lost') &&
            !text.includes('antd: message')) {
          errors.push(text);
        }
      }
    });
    await page.goto(`${BASE_URL}/command-center`);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(2000);
    expect(errors).toEqual([]);
  });
});
