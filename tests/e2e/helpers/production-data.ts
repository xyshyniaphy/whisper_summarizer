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

  console.log('[E2E Setup] Uploading 2_min.m4a to production...')

  // Get auth token
  const token = await getAuthToken(page)

  // Check audio file exists
  if (!(await fileExists(AUDIO_FILE))) {
    throw new Error(`Audio file not found: ${AUDIO_FILE}`)
  }

  // Upload audio file
  const formData = new FormData()
  const fileBuffer = await fs.readFile(AUDIO_FILE)
  formData.append('file', new Blob([fileBuffer]), '2_min.m4a')

  const uploadResponse = await page.request.post('/api/audio/upload', {
    headers: { 'Authorization': `Bearer ${token}` },
    data: formData
  })

  if (uploadResponse.status() !== 200) {
    throw new Error(`Upload failed: ${uploadResponse.status()}`)
  }

  const uploadData = await uploadResponse.json() as UploadResponse
  const transcriptionId = uploadData.id
  console.log(`[E2E Setup] Uploaded transcription ID: ${transcriptionId}`)

  // Poll for completion
  console.log('[E2E Setup] Polling for transcription completion...')
  await pollForCompletion(page, token, transcriptionId)

  // Save state for cleanup
  const state: TranscriptionState = {
    id: transcriptionId,
    file_name: '2_min.m4a',
    stage: 'completed'
  }
  await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2))

  console.log('[E2E Setup] Transcription complete!')
  return transcriptionId
}

export async function cleanupProductionTranscription(page: Page): Promise<void> {
  if (!(await fileExists(STATE_FILE))) {
    console.log('[E2E Cleanup] No state file, skipping cleanup')
    return
  }

  try {
    const stateContent = await fs.readFile(STATE_FILE, 'utf-8')
    const state = JSON.parse(stateContent) as TranscriptionState

    // Validate state content
    if (!state?.id) {
      console.error('[E2E Cleanup] Invalid state file: missing id')
      await fs.unlink(STATE_FILE)
      return
    }

    console.log(`[E2E Cleanup] Deleting transcription: ${state.id}`)

    const token = await getAuthToken(page)

    const deleteResponse = await page.request.delete(`/api/transcriptions/${state.id}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (deleteResponse.status() === 204 || deleteResponse.status() === 200) {
      console.log('[E2E Cleanup] Transcription deleted successfully')
    } else {
      console.error(`[E2E Cleanup] Delete failed: ${deleteResponse.status()}`)
    }
  } catch (error) {
    console.error(`[E2E Cleanup] Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  } finally {
    // Always remove state file
    try {
      await fs.unlink(STATE_FILE)
    } catch {
      // Ignore unlink errors
    }
  }
}

async function getAuthToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    const keys = Object.keys(localStorage)
    const authKey = keys.find(k => k.startsWith('sb-') && k.includes('-auth-token'))
    if (!authKey) throw new Error('No auth token found')
    const tokenData = JSON.parse(localStorage.getItem(authKey)!)
    return tokenData?.currentSession?.access_token || tokenData?.access_token || ''
  })

  if (!token) {
    throw new Error('Auth token is empty')
  }

  return token
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
