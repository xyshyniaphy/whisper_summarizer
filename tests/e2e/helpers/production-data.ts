// tests/e2e/helpers/production-data.ts
import { Page } from '@playwright/test'
import path from 'path'
import fs from 'fs/promises'

const STATE_FILE = '/tmp/e2e-test-transcription.json'
const AUDIO_FILE = path.join(process.cwd(), 'testdata/2_min.m4a')

interface TranscriptionState {
  id: string
  file_name: string
  stage: string
}

interface UploadResponse {
  id: string
  status: string
}

interface TranscriptionResponse {
  stage: string
  error_message?: string
}

export async function setupProductionTranscription(page: Page): Promise<string> {
  // Check if already setup (singleton pattern)
  if (await fileExists(STATE_FILE)) {
    try {
      const stateContent = await fs.readFile(STATE_FILE, 'utf-8')
      const state = JSON.parse(stateContent) as TranscriptionState

      // Validate state content
      if (!state?.id) {
        throw new Error('Invalid state file: missing id')
      }

      console.log(`[E2E Setup] Using existing transcription: ${state.id}`)
      return state.id
    } catch (error) {
      throw new Error(`Failed to read state file: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  console.log('[E2E Setup] Fetching existing completed transcription from production...')

  // Use an existing completed transcription instead of uploading new one
  // (Production server doesn't have a runner running, so new uploads won't be processed)
  const response = await page.request.get('/api/transcriptions?stage=completed&page=1&page_size=1')

  if (response.status() !== 200) {
    throw new Error(`Failed to fetch transcriptions: ${response.status()}`)
  }

  const data = await response.json() as any
  if (!data.data || data.data.length === 0) {
    throw new Error('No completed transcriptions found in production')
  }

  const transcriptionId = data.data[0].id
  console.log(`[E2E Setup] Using existing transcription: ${transcriptionId} (${data.data[0].file_name})`)

  // Save state for caching (no cleanup needed for existing transcriptions)
  const state: TranscriptionState = {
    id: transcriptionId,
    file_name: data.data[0].file_name,
    stage: 'completed'
  }
  await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2))

  console.log('[E2E Setup] Ready to test with existing transcription!')
  return transcriptionId
}

export async function cleanupProductionTranscription(page?: Page): Promise<void> {
  // Note: We're using existing completed transcriptions, so no cleanup needed
  // Just remove the state file
  // page parameter is optional (not used, kept for backward compatibility)
  if (!(await fileExists(STATE_FILE))) {
    console.log('[E2E Cleanup] No state file, skipping cleanup')
    return
  }

  try {
    const stateContent = await fs.readFile(STATE_FILE, 'utf-8')
    const state = JSON.parse(stateContent) as TranscriptionState

    console.log(`[E2E Cleanup] Using existing transcription: ${state.id} (${state.file_name})`)
    console.log('[E2E Cleanup] No deletion needed - using existing production data')
  } catch (error) {
    console.error(`[E2E Cleanup] Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  } finally {
    // Always remove state file for next test run
    try {
      await fs.unlink(STATE_FILE)
      console.log('[E2E Cleanup] State file removed')
    } catch {
      // Ignore unlink errors
    }
  }
}

async function getAuthToken(page: Page): Promise<string> {
  // Try to get Supabase auth token from localStorage (for normal auth)
  const token = await page.evaluate(() => {
    const keys = Object.keys(localStorage)
    const authKey = keys.find(k => k.startsWith('sb-') && k.includes('-auth-token'))
    if (!authKey) return null
    const tokenData = JSON.parse(localStorage.getItem(authKey)!)
    return tokenData?.currentSession?.access_token || tokenData?.access_token || ''
  })

  // If we have a token, return it
  if (token) {
    return token
  }

  // No token found - assume server-side auth bypass
  // Return a dummy token (server will bypass auth for localhost requests)
  console.log('[E2E Setup] No Supabase token found, using server-side auth bypass')
  return 'e2e-bypass-token'
}

async function pollForCompletion(page: Page, token: string, transcriptionId: string): Promise<void> {
  const maxAttempts = 120  // 10 minutes (5s intervals)
  const interval = 5000   // 5 seconds

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const response = await page.request.get(`/api/transcriptions/${transcriptionId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (response.status() === 200) {
      const data = await response.json() as TranscriptionResponse
      process.stdout.write(`.`)  // Progress dot

      if (data.stage === 'completed') {
        console.log('')  // New line after dots
        return
      }

      if (data.stage === 'failed') {
        throw new Error(`Transcription failed: ${data.error_message || 'Unknown error'}`)
      }
    }

    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, interval))
  }

  throw new Error('Transcription timeout: exceeded 10 minutes')
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}
