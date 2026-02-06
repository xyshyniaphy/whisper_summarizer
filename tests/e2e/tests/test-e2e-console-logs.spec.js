const { test } = require('@playwright/test');

test('Debug E2E bypass initialization with console logs', async ({ page }) => {
  // Capture ALL console logs
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    console.log(`[${type.toUpperCase()}] ${text}`);
  });

  // Also capture uncaught errors
  page.on('pageerror', error => {
    console.error('PAGE ERROR:', error.message);
    console.error('ERROR STACK:', error.stack);
  });

  console.log('\n=== NAVIGATING TO HOME PAGE ===\n');
  await page.goto('/');

  // Wait for React to initialize
  await page.waitForTimeout(3000);

  console.log('\n=== CHECKING LOCALSTORAGE ===\n');
  const localStorageData = await page.evaluate(() => {
    return {
      e2eTestMode: localStorage.getItem('e2e-test-mode'),
      hostname: window.location.hostname,
      href: window.location.href,
    };
  });
  console.log('localStorage data:', JSON.stringify(localStorageData, null, 2));

  console.log('\n=== CHECKING IF USER IS SET ===\n');
  const userCheck = await page.evaluate(() => {
    // Try to access window-level test flag
    const hasFlag = !!window.TEST_E2E_MODE;
    // Check Jotai atoms (if accessible)
    const hasUser = !!window.__JOITAI__;
    return { TEST_E2E_MODE: hasFlag, JOITAI_EXISTS: hasUser };
  });
  console.log('User check:', JSON.stringify(userCheck, null, 2));

  console.log('\n=== CHECKING USER MENU ===\n');
  const userMenuCount = await page.locator('[data-testid="user-menu"]').count();
  console.log('User menu elements found:', userMenuCount);

  console.log('\n=== TAKING SCREENSHOT ===\n');
  await page.screenshot({ path: '/tmp/e2e-debug-screenshot.png' });
  console.log('Screenshot saved to /tmp/e2e-debug-screenshot.png');
});
