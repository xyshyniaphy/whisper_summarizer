const { test, expect } = require('@playwright/test');

test('Direct E2E bypass check', async ({ page }) => {
  // Capture ALL console logs
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    console.log(`[${type.toUpperCase()}] ${text}`);
  });

  // Also capture uncaught errors
  page.on('pageerror', error => {
    console.error('PAGE ERROR:', error.message);
  });

  console.log('Navigating to home page...');
  await page.goto('/');

  // Wait for React to initialize
  await page.waitForTimeout(3000);

  console.log('\n=== CHECKING isE2ETestMode() FUNCTION ===\n');

  // Check if isE2ETestMode() returns true
  const e2eModeResult = await page.evaluate(() => {
    // Get the localStorage flag
    const flag = localStorage.getItem('e2e-test-mode');
    const hostname = window.location.hostname;

    // Call the isE2ETestMode function by importing it from the module
    // We'll check the conditions manually
    const flagCheck = flag === 'true';
    const hostnameCheck = hostname === 'localhost' ||
                         hostname === '127.0.0.1' ||
                         hostname === '::1' ||
                         hostname === 'whisper_frontend_dev' ||
                         hostname === 'whisper_nginx_dev' ||
                         hostname === 'frontend-test';

    return {
      flag: flag,
      hostname: hostname,
      flagCheck: flagCheck,
      hostnameCheck: hostnameCheck,
      wouldReturnTrue: flagCheck && hostnameCheck
    };
  });

  console.log('E2E Mode Check:', JSON.stringify(e2eModeResult, null, 2));

  if (e2eModeResult.wouldReturnTrue) {
    console.log('✅ E2E mode SHOULD be enabled!');
  } else {
    console.log('❌ E2E mode would NOT be enabled');
    if (!e2eModeResult.flagCheck) console.log('  - Flag check failed');
    if (!e2eModeResult.hostnameCheck) console.log('  - Hostname check failed');
  }

  console.log('\n=== CHECKING USER MENU ===\n');
  const userMenuCount = await page.locator('[data-testid="user-menu"]').count();
  console.log('User menu elements found:', userMenuCount);

  if (userMenuCount === 0) {
    console.log('❌ User menu not rendered - E2E bypass not working!');
  } else {
    console.log('✅ User menu rendered!');
  }

  console.log('\n=== CHECKING PAGE CONTENT ===\n');
  const pageContent = await page.content();
  const hasUserEmail = pageContent.includes('lmr@lmr.com') || pageContent.includes('test@example.com');
  console.log('Page contains test user email:', hasUserEmail);

  console.log('\n=== TAKING SCREENSHOT ===\n');
  await page.screenshot({ path: '/tmp/e2e-bypass-screenshot.png' });
  console.log('Screenshot saved to /tmp/e2e-bypass-screenshot.png');
});
