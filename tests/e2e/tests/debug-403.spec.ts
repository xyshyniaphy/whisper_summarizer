import { test, expect } from '@playwright/test';

test('Debug 403 error', async ({ page }) => {
  // Log all requests
  page.on('request', request => {
    console.log('Request:', request.url());
  });

  page.on('response', response => {
    if (response.status() === 403 || response.status() === 404) {
      console.log('Failed response:', response.url(), 'Status:', response.status());
    }
  });

  page.on('console', msg => console.log('Console:', msg.text()));

  await page.goto('/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
});
