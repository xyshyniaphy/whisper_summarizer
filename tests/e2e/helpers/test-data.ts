import { Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'

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

  // Read the test audio file
  const audioPath = path.join(__dirname, '../fixtures/test-audio.mp3');
  const audioBuffer = fs.readFileSync(audioPath);

  // Get baseURL from page context (matches playwright.config.ts baseURL)
  const baseURL = process.env.BASE_URL || 'http://whisper_nginx_dev';

  // Upload the file
  const uploadResponse = await page.request.post(`${baseURL}/api/audio/upload`, {
    headers: {
      'X-E2E-Test-Mode': 'true',
      // Don't set Content-Type, let Playwright handle it for multipart/form-data
    },
    multipart: {
      file: {
        name: 'test-audio.mp3',
        mimeType: 'audio/mpeg',
        buffer: audioBuffer,
      },
    },
  });

  if (!uploadResponse.ok()) {
    throw new Error(`Upload failed: ${uploadResponse.status()} ${uploadResponse.statusText()}`);
  }

  const uploadData = await uploadResponse.json();
  const transcriptionId = uploadData.id;

  console.log(`[Test Data] Upload complete, transcription ID: ${transcriptionId}`);

  // Poll for completion
  const startTime = Date.now();
  const pollInterval = 5000; // Check every 5 seconds

  while (Date.now() - startTime < timeout) {
    const checkResponse = await page.request.get(`${baseURL}/api/transcriptions/${transcriptionId}`, {
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

/**
 * Setup a test transcription with a share link for shared audio player tests.
 * This creates a transcription, generates a share link IMMEDIATELY (before completion),
 * then waits for transcription to finish. This ensures the share link exists when
 * the runner calls the /complete endpoint, preventing audio deletion.
 *
 * IMPORTANT: Share link must be created BEFORE transcription completes, otherwise
 * the /complete endpoint will delete the audio file to save disk space.
 *
 * @param page - Playwright page object
 * @returns The share token for accessing the shared transcription
 */
export async function setupTranscriptionWithShare(
  page: Page,
  options: { timeout?: number } = {}
): Promise<string> {
  const { timeout = 180000 } = options;

  console.log('[Test Data] Setting up transcription with share link for audio player tests...');

  // Read the test audio file
  const audioPath = path.join(__dirname, '../fixtures/test-audio.mp3');
  const audioBuffer = fs.readFileSync(audioPath);

  // Get baseURL from page context (matches playwright.config.ts baseURL)
  const baseURL = process.env.BASE_URL || 'http://whisper_nginx_dev';

  // Upload the file
  const uploadResponse = await page.request.post(`${baseURL}/api/audio/upload`, {
    headers: {
      'X-E2E-Test-Mode': 'true',
    },
    multipart: {
      file: {
        name: 'test-audio.mp3',
        mimeType: 'audio/mpeg',
        buffer: audioBuffer,
      },
    },
  });

  if (!uploadResponse.ok()) {
    throw new Error(`Upload failed: ${uploadResponse.status()} ${uploadResponse.statusText()}`);
  }

  const uploadData = await uploadResponse.json();
  const transcriptionId = uploadData.id;

  console.log(`[Test Data] Upload complete, transcription ID: ${transcriptionId}`);

  // CRITICAL: Create share link IMMEDIATELY after upload, BEFORE waiting for completion.
  // This ensures the share link exists when the runner calls /complete, preventing audio deletion.
  const shareResponse = await page.request.post(`${baseURL}/api/transcriptions/${transcriptionId}/share`, {
    headers: { 'X-E2E-Test-Mode': 'true' }
  });

  if (!shareResponse.ok()) {
    throw new Error(`Failed to create share link: ${shareResponse.status()} ${shareResponse.statusText()}`);
  }

  const shareData = await shareResponse.json();
  const shareToken = shareData.share_token;

  console.log(`[Test Data] Share link created with token: ${shareToken} (BEFORE completion)`);

  // Now poll for completion
  const startTime = Date.now();
  const pollInterval = 5000; // Check every 5 seconds

  while (Date.now() - startTime < timeout) {
    const checkResponse = await page.request.get(`${baseURL}/api/transcriptions/${transcriptionId}`, {
      headers: { 'X-E2E-Test-Mode': 'true' }
    });

    if (!checkResponse.ok()) {
      throw new Error(`Failed to check transcription status: ${checkResponse.status()}`);
    }

    const transcription = await checkResponse.json();

    if (transcription.status === 'completed') {
      console.log(`[Test Data] Transcription completed! Audio file preserved due to share link.`);
      return shareToken;
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
 * Shared transcription with share link for tests.
 * This avoids uploading multiple times for similar tests.
 */
let sharedShareToken: string | null = null;

/**
 * Get or create a shared test transcription with share link.
 * Multiple tests can use this to avoid re-uploading for each test.
 *
 * @param page - Playwright page object
 * @returns The shared share token
 */
export async function getOrCreateSharedTranscriptionWithShare(page: Page): Promise<string> {
  if (sharedShareToken) {
    console.log(`[Test Data] Reusing shared share token: ${sharedShareToken}`);
    return sharedShareToken;
  }

  sharedShareToken = await setupTranscriptionWithShare(page);
  return sharedShareToken;
}

/**
 * Clean up the shared share token.
 * Call this in test.afterAll() if needed.
 */
export function resetSharedShareToken(): void {
  sharedShareToken = null;
}
