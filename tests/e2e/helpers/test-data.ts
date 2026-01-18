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

  // Upload the file
  const uploadResponse = await page.request.post('/api/audio/upload', {
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
