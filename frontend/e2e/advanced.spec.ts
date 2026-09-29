import { test, expect } from '@playwright/test';

test.describe('DQ Observatory — advanced pages (jobs/webhooks/drift/correlations)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('select[aria-label="Dataset selector"]', { timeout: 15000 });
  });

  test('nav smoke: all four pages render', async ({ page }) => {
    for (const [link, heading] of [
      ['Jobs', 'Scheduled jobs'],
      ['Webhooks', 'Webhooks'],
      ['Drift', 'Drift detection'],
      ['Correlations', 'Correlations'],
      ['Contracts', 'Data contracts'],
    ] as const) {
      await page.click(`nav a:has-text("${link}")`);
      await expect(page.locator(`text=${heading}`).first()).toBeVisible({ timeout: 10000 });
    }
    await page.screenshot({ path: 'screenshots/13-advanced-nav.png', fullPage: false });
  });

  test('jobs RBAC: admin creates, viewer gets 403', async ({ page }) => {
    test.setTimeout(120000);
    await page.click('nav a:has-text("Jobs")');
    await expect(page.locator('text=Scheduled jobs').first()).toBeVisible();

    // admin creates a job
    await page.selectOption('select[aria-label="Role"]', 'admin');
    await page.fill('input[aria-label="Job name"]', 'e2e-nightly');
    await page.fill('input[aria-label="Cron expression"]', '0 3 * * *');
    await page.click('button:has-text("Create job")');
    await expect(page.locator('text=Job created.')).toBeVisible({ timeout: 15000 });

    // viewer is denied
    await page.selectOption('select[aria-label="Role"]', 'viewer');
    await page.fill('input[aria-label="Job name"]', 'e2e-denied');
    await page.click('button:has-text("Create job")');
    await expect(page.locator('text=Error: 403')).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: 'screenshots/14-jobs-rbac.png', fullPage: false });
  });

  test('jobs pause/resume', async ({ page }) => {
    test.setTimeout(120000);
    await page.click('nav a:has-text("Jobs")');
    await expect(page.locator('text=Scheduled jobs').first()).toBeVisible();

    // admin creates a job
    await page.selectOption('select[aria-label="Role"]', 'admin');
    await page.fill('input[aria-label="Job name"]', 'e2e-pause-test');
    await page.fill('input[aria-label="Cron expression"]', '0 4 * * *');
    await page.click('button:has-text("Create job")');
    await expect(page.locator('text=Job created.')).toBeVisible({ timeout: 15000 });

    // pause the job
    await page.click('button:has-text("Pause")');
    await expect(page.locator('text=Job paused.')).toBeVisible({ timeout: 10000 });

    // resume the job
    await page.click('button:has-text("Resume")');
    await expect(page.locator('text=Job resumed.')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/17-jobs-pause-resume.png', fullPage: false });
  });

  test('contracts CRUD + breaking-change check', async ({ page }) => {
    test.setTimeout(120000);
    await page.click('nav a:has-text("Contracts")');
    await expect(page.locator('text=Data contracts').first()).toBeVisible();
    await expect(page.locator('select[aria-label="Dataset"] option')).not.toHaveCount(0, { timeout: 15000 });
    await page.selectOption('select[aria-label="Role"]', 'editor');
    await page.fill('input[aria-label="Contract name"]', 'e2e-contract');
    await page.click('button:has-text("Create contract")');
    await expect(page.locator('text=created (v1).')).toBeVisible({ timeout: 15000 });
    await page.locator('button:has-text("Run check")').first().click();
    await expect(page.locator('text=Check passed').or(page.locator('text=Check failed'))).toBeVisible({ timeout: 15000 });
    // viewer is denied
    await page.selectOption('select[aria-label="Role"]', 'viewer');
    await page.fill('input[aria-label="Contract name"]', 'e2e-denied');
    await page.click('button:has-text("Create contract")');
    await expect(page.locator('text=Error: 403')).toBeVisible({ timeout: 15000 });
  });

  test('drift page validates empty versions', async ({ page }) => {
    await page.click('nav a:has-text("Drift")');
    await expect(page.locator('text=Drift detection').first()).toBeVisible();
    await page.click('button:has-text("Detect drift")');
    await expect(page.locator('text=Pick a dataset and both version IDs.')).toBeVisible({ timeout: 10000 });
  });
});
