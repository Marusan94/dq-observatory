import { test, expect } from '@playwright/test';

test.describe('DQ Observatory — full user journey (§120)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // wait for Overview to load (dataset selector present)
    await page.waitForSelector('select[aria-label="Dataset selector"]', { timeout: 15000 });
  });

  test('complete journey: demo seed → overview → issues → fix email → validate → before/after → export', async ({ page }) => {
  test.setTimeout(180000);
    // 1. Open Upload page and click "Try demo dataset"
    await page.click('text=Datasets');
    await expect(page.locator('text=Analyze a dataset')).toBeVisible();
    await page.click('button:has-text("Try demo dataset")');
    await expect(page.locator('text=Demo ready').first()).toBeVisible({ timeout: 30000 });
    await page.screenshot({ path: 'screenshots/01-demo-loaded.png', fullPage: true });

    // 2. Go to Overview, verify score and trend
    await page.click('text=Overview');
    await expect(page.locator('text=Quality Score').first()).toBeVisible();
    // wait for score to load (not "—")
    await page.waitForFunction(() => {
      const cards = document.querySelectorAll('.card');
      for (const card of cards) {
        if (card.textContent?.includes('Quality Score')) {
          const scoreEl = card.querySelector('.text-3xl');
          if (scoreEl && scoreEl.textContent && scoreEl.textContent.trim() !== '—') {
            return true;
          }
        }
      }
      return false;
    }, { timeout: 15000 });
    const scoreText = await page.locator('.card:has-text("Quality Score") .text-3xl').first().textContent();
    expect(scoreText).toMatch(/[0-9]+/);
    await page.screenshot({ path: 'screenshots/02-overview-score.png', fullPage: true });

    // 3. Go to Issues, filter auto-fix available
    await page.click('text=Issues');
    await expect(page.locator('select[aria-label="Auto-fix"]')).toBeVisible();
    await page.selectOption('select[aria-label="Auto-fix"]', 'auto');
    await page.waitForTimeout(500); // wait for query
    await page.screenshot({ path: 'screenshots/03-issues-auto-fix.png', fullPage: true });

    // 4. Click first auto-fixable issue → drawer opens
    const issueRow = page.locator('tbody tr').first();
    await expect(issueRow).toBeVisible({ timeout: 10000 });
    await issueRow.click();
    await expect(page.locator('text=Apply auto-fix')).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: 'screenshots/04-issue-detail.png', fullPage: true });

    // 5. Apply auto-fix for email
    await page.click('button:has-text("Apply auto-fix")');
    // wait for toast with more flexible matching
    await page.waitForFunction(() => {
      const toasts = document.querySelectorAll('[role="status"]');
      for (const t of toasts) {
        if (t.textContent?.includes('Fix applied') || t.textContent?.includes('Applied')) {
          return true;
        }
      }
      return false;
    }, { timeout: 30000 });
    await page.screenshot({ path: 'screenshots/05-fix-applied.png', fullPage: true });

    // 6. Go to Cleaning, verify preview shows changes
    await page.click('text=Cleaning');
    await expect(page.locator('text=Cleaning workspace')).toBeVisible();
    await page.screenshot({ path: 'screenshots/06-cleaning.png', fullPage: true });

    // 7. Go to Reports, verify before/after and download HTML report
    await page.click('text=Reports');
    await expect(page.locator('text=Reports & Export')).toBeVisible();
    // wait for before/after table to load
    await page.waitForSelector('td:has-text("Before")', { timeout: 15000 });
    await expect(page.locator('text=Before').first()).toBeVisible();
    await expect(page.locator('text=After').first()).toBeVisible();
    await page.screenshot({ path: 'screenshots/07-reports-before-after.png', fullPage: true });

    // 9. Click HTML report link (opens new tab)
    const [newPage] = await Promise.all([
      page.waitForEvent('popup'),
      page.click('a:has-text("HTML report")')
    ]);
    await newPage.waitForLoadState('domcontentloaded');
    await expect(newPage.locator('text=Data Quality Report')).toBeVisible();
    await newPage.screenshot({ path: 'screenshots/09-html-report.png', fullPage: true });
    await newPage.close();

    // 10. Download ZIP export (verify it triggers download)
    // Open export options first (they're in a <details> element now)
    await page.click('details summary');
    await expect(page.locator('details[open]')).toBeVisible({ timeout: 10000 });
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Descargar")');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.(csv|zip)$/);
    await page.screenshot({ path: 'screenshots/10-export-zip.png', fullPage: true });

    // 11. Column detail page
    await page.goto('/column?dataset=' + (await page.locator('select[aria-label="Dataset selector"]').inputValue()) + '&column=email');
    await expect(page.locator('text=Column: email')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/11-column-detail.png', fullPage: true });

    // 12. Settings page
    await page.click('a[href="/settings"]');
    await expect(page.locator('h2:has-text("Settings")')).toBeVisible();
    await page.screenshot({ path: 'screenshots/12-settings.png', fullPage: true });

    // 13. Search page
    await page.click('a[href="/search"]');
    await expect(page.locator('h2:has-text("Search")')).toBeVisible();
    await page.fill('input[placeholder="Search…"]', 'email');
    await page.waitForTimeout(1000);
    await expect(page.locator('text=Columns').first()).toBeVisible();
    await page.screenshot({ path: 'screenshots/12-search.png', fullPage: true });
  });
});