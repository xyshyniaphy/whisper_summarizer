import { test, expect } from '@playwright/test';
import { setupTestTranscription } from '../helpers/test-data';

test('setupTestTranscription creates a completed transcription', async ({ page }) => {
  // Set test timeout to 3 minutes to account for transcription processing
  test.setTimeout(180000);

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
