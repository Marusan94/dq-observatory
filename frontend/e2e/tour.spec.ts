import { test, expect } from '@playwright/test';

test.describe('DQ Observatory — recorrido guiado', () => {
  test('tour walks nav → dataset → drift → correlations → jobs → webhooks', async ({ page }) => {
    test.setTimeout(120000);
    await page.goto('/');
    await page.waitForSelector('select[aria-label="Dataset selector"]', { timeout: 15000 });
    await page.screenshot({ path: 'screenshots/16-tour-overview.png', fullPage: false });

    await page.click('button[aria-label="Iniciar recorrido"]');
    await expect(page.locator('text=Navegación principal').first()).toBeVisible({ timeout: 10000 });

    await page.click('button:has-text("Siguiente")');
    await expect(page.locator('text=Selector de dataset').first()).toBeVisible({ timeout: 10000 });

    await page.click('button:has-text("Siguiente")');
    await expect(page).toHaveURL(/\/drift/, { timeout: 10000 });
    await expect(page.locator('text=Detección de drift').first()).toBeVisible({ timeout: 10000 });

    await page.click('button:has-text("Siguiente")');
    await expect(page).toHaveURL(/\/correlations/, { timeout: 10000 });

    await page.click('button:has-text("Siguiente")');
    await expect(page).toHaveURL(/\/jobs/, { timeout: 10000 });

    await page.click('button:has-text("Siguiente")');
    await expect(page).toHaveURL(/\/webhooks/, { timeout: 10000 });
    await expect(page.locator('text=Fin del recorrido.')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/15-tour-webhooks.png', fullPage: false });

    await page.click('button:has-text("Terminar")');
    await expect(page.locator('button[aria-label="Iniciar recorrido"]')).toBeVisible({ timeout: 10000 });
  });
});
