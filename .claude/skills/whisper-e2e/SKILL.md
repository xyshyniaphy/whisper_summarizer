---
name: whisper-e2e
description: E2E testing patterns for Whisper Summarizer. Playwright tests, file upload testing, auth token handling, and common patterns.
---

# whisper-e2e - E2E Testing Patterns

## Purpose

E2E testing patterns and best practices for Whisper Summarizer:
- **Playwright-based tests** for end-to-end workflows
- **File upload testing** - NEVER click upload buttons
- **Auth token handling** for Supabase OAuth
- **Common testing patterns** and examples

## Quick Start

```bash
# Run E2E tests (requires dev env running)
./run_test.sh e2e

# Run specific test file
bunx playwright test tests/e2e/audio-upload.spec.ts

# Run with UI
bunx playwright test --ui
```

## Critical Pattern: File Upload Testing

**NEVER click upload buttons** - Opens native file picker, blocks automation.

### Correct Pattern: Direct API Calls

```typescript
// Get auth token from localStorage
const getAuthToken = async (page: Page) => {
  return await page.evaluate(() => {
    const keys = Object.keys(localStorage);
    const authKey = keys.find(k =>
      k.startsWith('sb-') && k.includes('-auth-token')
    );
    if (!authKey) return null;
    const tokenData = JSON.parse(localStorage.getItem(authKey)!);
    return tokenData?.currentSession?.access_token ||
           tokenData?.access_token ||
           null;
  });
};

// Upload via API
const uploadFileViaAPI = async (page: Page, filePath: string) => {
  const token = await getAuthToken(page);
  const formData = new FormData();
  const fileBuffer = await fs.readFile(filePath);
  formData.append('file', new Blob([fileBuffer]), path.basename(filePath));

  const response = await page.request.post('/api/audio/upload', {
    headers: { 'Authorization': `Bearer ${token}` },
    data: formData
  });
  return response.json();
};
```

## Test Structure

### Example Test File

```typescript
import { test, expect } from '@playwright/test';
import { uploadFileViaAPI, getAuthToken } from './helpers/api';

test.describe('Audio Upload', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto('/');

    // Login (uses localhost auth bypass in dev)
    await page.waitForLoadState('networkidle');
  });

  test('uploads audio file via API', async ({ page }) => {
    // Upload test file
    const result = await uploadFileViaAPI(
      page,
      'tests/fixtures/test.m4a'
    );

    expect(result).toHaveProperty('id');
    expect(result).toHaveProperty('file_name', 'test.m4a');

    // Navigate to transcription detail
    await page.goto(`/transcriptions/${result.id}`);

    // Wait for transcription to complete
    await page.waitForSelector('[data-status="completed"]', {
      timeout: 120000
    });

    // Verify content
    await expect(page.locator('h1')).toContainText('test.m4a');
  });
});
```

## Common Patterns

### 1. Authentication

**Development (localhost bypass)**:
```typescript
test.beforeEach(async ({ page }) => {
  await page.goto('/');
  // No login needed - localhost auth bypass
});
```

**Production (Supabase OAuth)**:
```typescript
test.beforeEach(async ({ page }) => {
  await page.goto('/');

  // Click Google OAuth button
  await page.click('button:has-text("Sign in with Google")');

  // Wait for redirect (requires test credentials)
  await page.waitForURL('/');
});
```

### 2. Waiting for State

```typescript
// Wait for element
await page.waitForSelector('.transcription-item');

// Wait for text
await page.waitForText('Processing complete');

// Wait for network idle
await page.waitForLoadState('networkidle');

// Wait for specific status (with timeout)
await page.waitForSelector(
  '[data-status="completed"]',
  { timeout: 120000 }
);

// Poll for condition
await page.waitForFunction(() => {
  const status = document.querySelector('[data-status]')?.getAttribute('data-status');
  return status === 'completed' || status === 'failed';
}, { timeout: 120000 });
```

### 3. Navigation

```typescript
// Navigate to URL
await page.goto('/transcriptions/abc123');

// Click link
await page.click('a[href="/transcriptions/abc123"]');

// Navigate back/forward
await page.goBack();
await page.goForward();
```

### 4. Forms

```typescript
// Fill input
await page.fill('input[name="email"]', 'test@example.com');

// Select dropdown
await page.selectOption('select[name="channel"]', 'channel-1');

// Upload (via API, not click!)
const result = await uploadFileViaAPI(page, filePath);

// Submit form
await page.click('button[type="submit"]');
```

### 5. Assertions

```typescript
// Text content
await expect(page.locator('h1')).toHaveText('Transcription');

// Attribute value
await expect(page.locator('[data-status]')).toHaveAttribute('data-status', 'completed');

// Element visibility
await expect(page.locator('.loading')).not.toBeVisible();

// Element count
await expect(page.locator('.transcription-item')).toHaveCount(5);

// URL
await expect(page).toHaveURL('/transcriptions/abc123');
```

### 6. Interactive Elements

```typescript
// Button click
await page.click('button:has-text("Delete")');

// Confirm dialog (use custom component)
await page.click('[data-testid="confirm-delete"]');
await page.click('button:has-text("Confirm")');

// Wait for response
await page.waitForResponse(resp => resp.url().includes('/api/transcriptions'));

// Verify action
await expect(page.locator('.toast')).toHaveText('Deleted successfully');
```

## Test Helpers

### API Helper

```typescript
// tests/helpers/api.ts
import { Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => {
    const keys = Object.keys(localStorage);
    const authKey = keys.find(k =>
      k.startsWith('sb-') && k.includes('-auth-token')
    );
    if (!authKey) return null;
    const tokenData = JSON.parse(localStorage.getItem(authKey)!);
    return tokenData?.currentSession?.access_token ||
           tokenData?.access_token ||
           null;
  });
}

export async function uploadFileViaAPI(
  page: Page,
  filePath: string
): Promise<any> {
  const token = await getAuthToken(page);
  const formData = new FormData();
  const fileBuffer = await fs.readFile(filePath);
  formData.append('file', new Blob([fileBuffer]), path.basename(filePath));

  const response = await page.request.post('/api/audio/upload', {
    headers: { 'Authorization': `Bearer ${token}` },
    data: formData
  });
  return response.json();
}

export async function createTranscription(
  page: Page,
  filePath: string
): Promise<string> {
  const result = await uploadFileViaAPI(page, filePath);
  return result.id;
}

export async function waitForTranscription(
  page: Page,
  id: string,
  timeout = 120000
): Promise<void> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    const response = await page.request.get(`/api/transcriptions/${id}`);
    const data = await response.json();

    if (data.status === 'completed') return;
    if (data.status === 'failed') {
      throw new Error(`Transcription failed: ${data.error_message}`);
    }

    await page.waitForTimeout(2000);
  }
  throw new Error('Transcription timeout');
}
```

### Page Object Model

```typescript
// tests/pages/TranscriptionListPage.ts
import { Page, expect } from '@playwright/test';

export class TranscriptionListPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/');
  }

  async getTranscriptionItems() {
    return this.page.locator('.transcription-item');
  }

  async getTranscriptionByName(name: string) {
    return this.page.locator(`.transcription-item:has-text("${name}")`);
  }

  async clickTranscription(name: string) {
    await this.getTranscriptionByName(name).click();
  }

  async waitForTranscriptionCount(count: number) {
    await expect(this.getTranscriptionItems()).toHaveCount(count);
  }
}

// Usage
test('displays transcriptions', async ({ page }) => {
  const listPage = new TranscriptionListPage(page);
  await listPage.goto();
  await listPage.waitForTranscriptionCount(5);
});
```

## Fixtures

```typescript
// tests/fixtures.ts
import { test as base } from '@playwright/test';

type MyFixtures = {
  authenticatedPage: Page;
};

export const test = base.extend<MyFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/');
    // Auth happens automatically in dev (localhost bypass)
    await use(page);
  },
});

export const expect = test.expect;
```

## Running Tests

### Development Mode

```bash
# Start dev environment first
./run_dev.sh up-d

# Run E2E tests
./run_test.sh e2e
```

### Test Commands

```bash
# Run all E2E tests
bunx playwright test

# Run specific file
bunx playwright test tests/e2e/upload.spec.ts

# Run with headed browser
bunx playwright test --headed

# Run with debug mode
bunx playwright test --debug

# Run with UI
bunx playwright test --ui
```

### Configuration

**playwright.config.ts**:
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:8130',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],
  webServer: {
    command: 'cd ../ && ./run_dev.sh up-d',
    url: 'http://localhost:8130',
    reuseExistingServer: !process.env.CI,
  },
});
```

## Troubleshooting

### Issue: "File picker blocked"

**Cause**: Clicked file input button directly

**Solution**: Use API upload pattern instead
```typescript
// ❌ WRONG
await page.click('input[type="file"]');
await page.setInputFiles('input[type="file']", filePath);

// ✅ CORRECT
const result = await uploadFileViaAPI(page, filePath);
```

### Issue: "Auth required"

**Cause**: Not running in localhost/dev mode

**Solution**:
```bash
# Ensure dev environment is running
./run_dev.sh up-d

# Use localhost URL
baseURL: 'http://localhost:8130'
```

### Issue: "Timeout waiting for element"

**Cause**: Element not loading or slow network

**Solution**:
```typescript
// Increase timeout
await page.waitForSelector('.element', { timeout: 60000 });

// Or wait for network idle
await page.waitForLoadState('networkidle');
```

### Issue: "Flaky tests"

**Cause**: Race conditions or timing issues

**Solution**:
```typescript
// Use waitForFunction for custom conditions
await page.waitForFunction(() => {
  const el = document.querySelector('.element');
  return el && el.offsetParent !== null;
});

// Add retries in playwright.config.ts
retries: 2,
```

## Related Skills

```bash
# Frontend UI patterns
/whisper-frontend

# Audio player component
/whisper-player

# Production debugging
/prd_debug
```

## See Also

- [CLAUDE.md - E2E Testing with File Uploads](../../CLAUDE.md#e2e-testing-with-file-uploads)
- [tests/e2e/](../../tests/e2e/)
- [playwright.config.ts](../../frontend/playwright.config.ts)
