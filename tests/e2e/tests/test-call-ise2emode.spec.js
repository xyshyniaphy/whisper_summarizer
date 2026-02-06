const { test } = require('@playwright/test');

test('Call isE2ETestMode() directly', async ({ page }) => {
  // Capture console logs
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[E2E') || text.includes('isE2ETestMode') || text.includes('useAuth')) {
      console.log('BROWSER:', text);
    }
  });

  page.on('pageerror', error => {
    if (!error.message.includes('Supabase')) {
      console.error('ERROR:', error.message);
    }
  });

  console.log('Navigating to home page...');
  await page.goto('/');

  // Wait for page to load
  await page.waitForTimeout(2000);

  console.log('\n=== CALLING isE2ETestMode() DIRECTLY ===\n');

  // Try to call the isE2ETestMode function
  const result = await page.evaluate(() => {
    // Method 1: Check if the function is available globally
    if (typeof window.isE2ETestMode === 'function') {
      return { method: 'window.isE2ETestMode', result: window.isE2ETestMode() };
    }

    // Method 2: Try to import it from the utils
    try {
      // We can't import in the browser, but we can check the conditions
      const flag = localStorage.getItem('e2e-test-mode');
      const hostname = window.location.hostname;

      // The logic from isE2ETestMode
      const flagCheck = flag === 'true';
      const hostnameCheck = hostname === 'localhost' ||
                           hostname === '127.0.0.1' ||
                           hostname === '::1' ||
                           hostname === 'whisper_frontend_dev' ||
                           hostname === 'whisper_nginx_dev' ||
                           hostname === 'frontend-test';

      return {
        method: 'manual_check',
        flag: flag,
        hostname: hostname,
        flagCheck: flagCheck,
        hostnameCheck: hostnameCheck,
        wouldReturnTrue: flagCheck && hostnameCheck
      };
    } catch (e) {
      return { method: 'error', error: e.message };
    }
  });

  console.log('isE2ETestMode() result:', JSON.stringify(result, null, 2));

  console.log('\n=== CHECKING IF APP LOADED ===\n');

  // Check if React app loaded
  const appLoaded = await page.evaluate(() => {
    return !!document.querySelector('#root');
  });
  console.log('React root element exists:', appLoaded);

  // Check for user menu
  const userMenuCount = await page.locator('[data-testid="user-menu"]').count();
  console.log('User menu count:', userMenuCount);

  // Check for any nav elements
  const navCount = await page.locator('nav').count();
  console.log('Nav elements count:', navCount);

  console.log('\n=== CHECKING USEAUTH HOOK ===\n');

  // Check if useAuth hook was called by looking for Jotai atoms
  const authState = await page.evaluate(() => {
    // Try to find evidence of useAuth being called
    const hasUser = !!window.user; // Some hooks set window.user
    const hasSession = !!window.session;
    return { hasUser, hasSession };
  });
  console.log('Auth state check:', authState);
});
