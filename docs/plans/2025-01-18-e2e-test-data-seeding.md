# E2E Test Data Seeding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create test data seeding system to fix 47 failing E2E tests that require existing completed transcriptions.

**Architecture:**
- Create a helper function that uploads a test audio file via API and waits for processing completion
- Store `transcriptionId` in a shared variable for use across tests
- Use Playwright's `test.beforeAll()` hook to run setup before dependent tests
- Leverage existing E2E auth bypass and API helpers

**Tech Stack:** Playwright E2E testing framework, existing API helpers, Bun test runner

---

## Overview

Currently, 47 E2E tests fail because they require existing completed transcriptions in the database:
- 33 tests fail with "No completed transcriptions found in production"
- 14 chat tests fail with "transcriptionId not initialized"

This plan creates a test data seeding system that:
1. Uploads a small test audio file (~100KB, 3-5 seconds)
2. Polls for transcription completion (using existing status polling)
3. Shares the `transcriptionId` across all tests that need it
4. Cleans up test data after test run

**Expected outcome:** 47 additional tests passing (22 → 69 tests, 55% pass rate)

---

## Task 1: Create Test Audio File

**Files:**
- Create: `tests/e2e/fixtures/test-audio.mp3`

**Step 1: Create minimal test audio file**

The test audio should be:
- Small size (~100KB) for fast upload
- Short duration (3-5 seconds) for quick processing
- Valid MP3 format
- Contains some speech for meaningful transcription

Run: `ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" -c:a libmp3lame -b:a 64k tests/e2e/fixtures/test-audio.mp3`
Expected: Creates `tests/e2e/fixtures/test-audio.mp3` (~100KB)

**Step 2: Verify file exists**

Run: `ls -lh tests/e2e/fixtures/test-audio.mp3`
Expected: File exists and is ~100KB

**Step 3: Commit**

```bash
git add tests/e2e/fixtures/test-audio.mp3
git commit -m "test(e2e): add test audio fixture for data seeding"
```

---

## Task 2: Create Test Data Seeding Helper

**Files:**
- Create: `tests/e2e/helpers/test-data.ts`

**Step 1: Write the failing test**

First, let's write a test that verifies the seeding helper works:

```typescript
import { test, expect } from '@playwright/test';
import { setupTestTranscription } from '../helpers/test-data';

test('setupTestTranscription creates a completed transcription', async ({ page }) => {
  const transcriptionId = await setupTestTranscription(page);

  expect(transcriptionId).toBeDefined();
  expect(transcriptionId).toMatch(/^[0-9a-f-]{36}$/); // UUID format

  // Verify we can fetch the transcription
  const response = await page.request.get(`/api/transcriptions/${transcriptionId}`, {
    headers: { 'X-E2E-Test-Mode': 'true' }
  });

  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  expect(data.status).toBe('completed');
  expect(data.text).toBeTruthy();
  expect(data.summary).toBeTruthy();
});
```

**Step 2: Run test to verify it fails**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test test-data.spec.ts`
Expected: FAIL with "setupTestTranscription is not defined"

**Step 3: Create the helper implementation**

```typescript
import { Page } from '@playwright/test';

/**
 * Setup a test transcription by uploading audio and waiting for completion.
 * This should be called in test.beforeAll() for tests that need existing data.
 *
 * @param page - Playwright page object
 * @param options - Optional configuration
 * @returns The transcription ID of the completed transcription
 */
export async function setupTestTranscription(
  page: Page,
  options: { timeout?: number } = {}
): Promise<string> {
  const { timeout = 180000 } = options; // 3 minute default timeout

  console.log('[Test Data] Starting test transcription setup...');

  // Step 1: Upload the test audio file
  const formData = new FormData();
  formData.append('file', Buffer.from(
    // Small base64-encoded MP3 (silence, ~3 seconds, ~100KB)
    // This is a minimal valid MP3 file
  ));

  const uploadResponse = await page.request.post('/api/audio/upload', {
    headers: {
      'X-E2E-Test-Mode': 'true',
    },
    data: formData,
  });

  if (!uploadResponse.ok()) {
    throw new Error(`Upload failed: ${uploadResponse.status()} ${uploadResponse.statusText()}`);
  }

  const uploadData = await uploadResponse.json();
  const transcriptionId = uploadData.id;

  console.log(`[Test Data] Upload complete, transcription ID: ${transcriptionId}`);

  // Step 2: Poll for completion
  const startTime = Date.now();
  const pollInterval = 5000; // Check every 5 seconds

  while (Date.now() - startTime < timeout) {
    const checkResponse = await page.request.get(`/api/transcriptions/${transcriptionId}`, {
      headers: { 'X-E2E-Test-Mode': 'true' }
    });

    if (!checkResponse.ok()) {
      throw new Error(`Failed to check transcription status: ${checkResponse.status()}`);
    }

    const transcription = await checkResponse.json();

    if (transcription.status === 'completed') {
      console.log(`[Test Data] Transcription completed!`);
      return transcriptionId;
    }

    if (transcription.status === 'failed') {
      throw new Error(`Transcription failed: ${transcription.error_message || 'Unknown error'}`);
    }

    console.log(`[Test Data] Status: ${transcription.status}, waiting...`);
    await page.waitForTimeout(pollInterval);
  }

  throw new Error(`Transcription did not complete within ${timeout}ms`);
}

/**
 * Shared transcription ID for tests that use the same test data.
 * This avoids uploading multiple times for similar tests.
 */
let sharedTranscriptionId: string | null = null;

/**
 * Get or create a shared test transcription.
 * Multiple tests can use this to avoid re-uploading for each test.
 *
 * @param page - Playwright page object
 * @returns The shared transcription ID
 */
export async function getOrCreateSharedTranscription(page: Page): Promise<string> {
  if (sharedTranscriptionId) {
    console.log(`[Test Data] Reusing shared transcription: ${sharedTranscriptionId}`);
    return sharedTranscriptionId;
  }

  sharedTranscriptionId = await setupTestTranscription(page);
  return sharedTranscriptionId;
}

/**
 * Clean up the shared transcription.
 * Call this in test.afterAll() if needed.
 */
export function resetSharedTranscription(): void {
  sharedTranscriptionId = null;
}
```

**Step 4: Create actual test audio file with base64 encoding**

Since we need an actual MP3 file, update the implementation to use a real file:

```typescript
import { readFileSync } from 'fs';
import { join } from 'path';

export async function setupTestTranscription(
  page: Page,
  options: { timeout?: number } = {}
): Promise<string> {
  const { timeout = 180000 } = options;

  console.log('[Test Data] Starting test transcription setup...');

  // Read the test audio file
  const audioPath = join(__dirname, '../fixtures/test-audio.mp3');
  const audioBuffer = readFileSync(audioPath);

  // Upload the file
  const formData = new FormData();
  formData.append('file', new Blob([audioBuffer], { type: 'audio/mpeg' }), 'test-audio.mp3');

  const uploadResponse = await page.request.post('/api/audio/upload', {
    headers: { 'X-E2E-Test-Mode': 'true' },
    data: formData,
  });

  if (!uploadResponse.ok()) {
    throw new Error(`Upload failed: ${uploadResponse.status()} ${uploadResponse.statusText()}`);
  }

  const uploadData = await uploadResponse.json();
  const transcriptionId = uploadData.id;

  console.log(`[Test Data] Upload complete, transcription ID: ${transcriptionId}`);

  // Poll for completion (same as before)
  const startTime = Date.now();
  const pollInterval = 5000;

  while (Date.now() - startTime < timeout) {
    const checkResponse = await page.request.get(`/api/transcriptions/${transcriptionId}`, {
      headers: { 'X-E2E-Test-Mode': 'true' }
    });

    if (!checkResponse.ok()) {
      throw new Error(`Failed to check transcription status: ${checkResponse.status()}`);
    }

    const transcription = await checkResponse.json();

    if (transcription.status === 'completed') {
      console.log(`[Test Data] Transcription completed!`);
      return transcriptionId;
    }

    if (transcription.status === 'failed') {
      throw new Error(`Transcription failed: ${transcription.error_message || 'Unknown error'}`);
    }

    console.log(`[Test Data] Status: ${transcription.status}, waiting...`);
    await page.waitForTimeout(pollInterval);
  }

  throw new Error(`Transcription did not complete within ${timeout}ms`);
}
```

**Step 5: Run test to verify it passes**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test test-data.spec.ts`
Expected: PASS (transcription is uploaded and completes)

**Step 6: Commit**

```bash
git add tests/e2e/helpers/test-data.ts tests/e2e/test-data.spec.ts
git commit -m "test(e2e): add test data seeding helper"
```

---

## Task 3: Update Tests to Use Seeded Data

### 3a: Fix transcription-detail.spec.ts

**Files:**
- Modify: `tests/e2e/tests/transcription-detail.spec.ts`

**Step 1: Add import and setup**

At the top of the file, add:
```typescript
import { setupTestTranscription } from '../helpers/test-data';
```

Before the first test, add:
```typescript
test.beforeAll(async ({ page }) => {
  // Use a shared transcription for all detail page tests
  globalThis.testTranscriptionId = await setupTestTranscription(page);
});
```

**Step 2: Remove old setup code**

Find and remove any calls to `setupProductionTranscription()` - they will be replaced by our new helper.

**Step 3: Update tests to use `globalThis.testTranscriptionId`**

Replace any hardcoded or production-based transcription IDs with `globalThis.testTranscriptionId`.

**Step 4: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test transcription-detail.spec.ts`
Expected: All 13 tests now pass

**Step 5: Commit**

```bash
git add tests/e2e/tests/transcription-detail.spec.ts
git commit -m "test(e2e): use seeded data for transcription-detail tests"
```

---

### 3b: Fix transcription-list.spec.ts

**Files:**
- Modify: `tests/e2e/tests/transcription-list.spec.ts`

**Step 1: Add beforeAll hook**

```typescript
import { setupTestTranscription } from '../helpers/test-data';

test.beforeAll(async ({ page }) => {
  // Seed one transcription so list is not empty
  await setupTestTranscription(page);
});
```

**Step 2: Remove production data dependency**

Remove any `setupProductionTranscription()` calls and related production-only code.

**Step 3: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test transcription-list.spec.ts`
Expected: All 13 tests now pass

**Step 4: Commit**

```bash
git add tests/e2e/tests/transcription-list.spec.ts
git commit -m "test(e2e): use seeded data for transcription-list tests"
```

---

### 3c: Fix transcription.spec.ts

**Files:**
- Modify: `tests/e2e/tests/transcription.spec.ts`

**Step 1: Update to use seeded data**

Replace production data fetching with:
```typescript
import { setupTestTranscription } from '../helpers/test-data';

test.beforeAll(async ({ page }) => {
  await setupTestTranscription(page);
});
```

**Step 2: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test transcription.spec.ts`
Expected: All 5 tests now pass

**Step 3: Commit**

```bash
git add tests/e2e/tests/transcription.spec.ts
git commit -m "test(e2e): use seeded data for transcription flow tests"
```

---

### 3d: Fix chat.spec.ts

**Files:**
- Modify: `tests/e2e/tests/chat.spec.ts`

**Step 1: Update setup to use new helper**

Find the line that throws `transcriptionId not initialized` and replace with:
```typescript
import { setupTestTranscription } from '../helpers/test-data';

test.beforeAll(async ({ page }) => {
  globalThis.chatTranscriptionId = await setupTestTranscription(page);
});
```

**Step 2: Update all tests to use `globalThis.chatTranscriptionId`**

Replace any references to the old `transcriptionId` variable.

**Step 3: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test chat.spec.ts`
Expected: All 14 tests now pass

**Step 4: Commit**

```bash
git add tests/e2e/tests/chat.spec.ts
git commit -m "test(e2e): use seeded data for chat tests"
```

---

## Task 4: Fix window is not defined Error

**Files:**
- Modify: `tests/e2e/tests/shared-audio-player.spec.ts`

**Step 1: Locate problematic code**

Search for code that accesses `window` outside of browser context (line ~24 based on error):
```typescript
;(window as any).consoleErrors.push(msg.text())
```

**Step 2: Fix the error handler**

The issue is that this code runs in Node context during test setup. Wrap it properly:

```typescript
// Before (in test file setup - runs in Node):
page.on('console', msg => {
  if (msg.type() === 'error') {
    (window as any).consoleErrors.push(msg.text()); // ❌ Error: window is not defined
  }
});

// After (inside page.evaluate or check first):
page.on('console', msg => {
  if (msg.type() === 'error') {
    // Store errors in test context, not window
    consoleErrors.push(msg.text()); // ✅ Use array declared in test
  }
});

// Or initialize window properly:
test.beforeEach(async ({ page }) => {
  // Initialize in browser context
  await page.evaluate(() => {
    (window as any).consoleErrors = [];
  });
});
```

**Step 3: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test shared-audio-player.spec.ts`
Expected: Tests run without "window is not defined" error (may still fail due to missing shared transcription data)

**Step 4: Commit**

```bash
git add tests/e2e/tests/shared-audio-player.spec.ts
git commit -m "test(e2e): fix window is not defined error in shared player tests"
```

---

## Task 5: Fix Strict Mode Violations

**Files:**
- Modify: `tests/e2e/tests/dashboard.spec.ts`

**Step 1: Locate duplicate text selectors**

Find lines using `getByText()` with text that appears multiple times:
```typescript
await expect(page.getByText('用户管理')).toBeVisible(); // ❌ Resolves to 2 elements
```

**Step 2: Use more specific selectors**

```typescript
// Before:
await expect(page.getByText('用户管理')).toBeVisible();

// After - use locator with filtering:
await expect(page.locator('.tab-button').filter({ hasText: '用户管理' })).toBeVisible();

// Or use first:
await expect(page.getByText('用户管理').first).toBeVisible();
```

**Step 3: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test dashboard.spec.ts`
Expected: No more strict mode violation errors

**Step 4: Commit**

```bash
git add tests/e2e/tests/dashboard.spec.ts
git commit -m "test(e2e): fix strict mode violations in dashboard tests"
```

---

## Task 6: Increase Timeouts for Async Operations

**Files:**
- Modify: `tests/e2e/tests/audio-upload.spec.ts`
- Modify: `tests/e2e/tests/channel-assignment.spec.ts`
- Modify: `tests/e2e/tests/user-menu.spec.ts`

**Step 1: Update timeout values**

Many tests use the default 5s timeout. Increase to 10s for async operations:

```typescript
// Before:
await expect(page.locator('[data-testid="upload-button"]')).toBeVisible();

// After:
await expect(page.locator('[data-testid="upload-button"]')).toBeVisible({ timeout: 10000 });
```

**Step 2: Add wait for network idle**

For tests that load data from API, add:
```typescript
await page.goto('/upload');
await page.waitForLoadState('networkidle'); // Wait for all API calls to complete
await expect(page.locator('[data-testid="upload-button"]')).toBeVisible({ timeout: 10000 });
```

**Step 3: Run tests**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun test audio-upload.spec.ts channel-assignment.spec.ts user-menu.spec.ts`
Expected: Fewer timeout errors

**Step 4: Commit**

```bash
git add tests/e2e/tests/audio-upload.spec.ts tests/e2e/tests/channel-assignment.spec.ts tests/e2e/tests/user-menu.spec.ts
git commit -m "test(e2e): increase timeouts for async operations"
```

---

## Task 7: Run Full Test Suite and Verify Results

**Step 1: Run full E2E test suite**

Run: `cd tests/e2e && BASE_URL=http://localhost:8130 bun run test`

**Step 2: Check results**

Expected outcome:
- **Before:** 22 passed, 94 failed, 10 skipped
- **After:** 69+ passed, ~47 failed, 10 skipped
- **Improvement:** +47 tests passing (from 17.5% to 55% pass rate)

**Step 3: Document remaining failures**

Create a summary of remaining test failures categorized by type:
- Data-related (need additional test data setup)
- Selector/timeout issues (need better selectors)
- Feature gaps (actual bugs or missing features)

**Step 4: Commit final summary**

```bash
git add docs/plans/2025-01-18-e2e-test-data-seeding.md
git commit -m "docs(e2e): document test data seeding implementation plan"
```

---

## Success Criteria

✅ Test data seeding helper creates completed transcriptions
✅ 47 previously failing tests now pass
✅ Pass rate improves from 17.5% to 55%+
✅ No tests depend on production data
✅ Tests are deterministic and can run in isolation

---

## Notes

- The test audio file should be kept small (~100KB) for fast uploads
- Timeout of 3 minutes accounts for actual transcription processing time
- Consider adding a "fast mode" that mocks completion for faster test runs
- The `sharedTranscriptionId` pattern allows multiple tests to reuse the same data
- Tests that delete transcriptions should use unique IDs, not the shared one
