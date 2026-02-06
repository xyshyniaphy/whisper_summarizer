import { test, expect } from '@playwright/test';

test('E2E bypass check', async ({ page }) => {
  page.on('console', msg => console.log('Browser:', msg.text()));

  await page.goto('/');
  await page.waitForTimeout(2000);

  const e2eFlag = await page.evaluate(() => localStorage.getItem('e2e-test-mode'));
  console.log('e2e-test-mode:', e2eFlag);

  const userMenuCount = await page.locator('[data-testid="user-menu"]').count();
  console.log('User menu count:', userMenuCount);
});
