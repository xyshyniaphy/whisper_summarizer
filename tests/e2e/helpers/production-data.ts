// tests/e2e/helpers/production-data.ts
import { Page } from '@playwright/test'
import path from 'path'
import fs from 'fs'

const STATE_FILE = '/tmp/e2e-test-transcription.json'
const AUDIO_FILE = path.join(process.cwd(), 'testdata/2_min.m4a')

interface TranscriptionState {
  id: string
  file_name: string
  stage: string
}

export async function setupProductionTranscription(page: Page): Promise<string> {
  // Check if already setup (singleton pattern)
  if (fs.existsSync(STATE_FILE)) {
    const state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8')) as TranscriptionState
    console.log(`[E2E Setup] Using existing transcription: ${state.id}`)
    return state.id
  }

  console.log('[E2E Setup] Uploading 2_min.m4a to production...')

  // Get auth token
  const token = await getAuthToken(page)

  // Upload audio file
  const formData = new FormData()
  const fileBuffer = await fs.promises.readFile(AUDIO_FILE)
  formData.append('file', new Blob([fileBuffer]), '2_min.m4a')

  const uploadResponse = await page.request.post('/api/audio/upload', {
    headers: { 'Authorization': `Bearer ${token}` },
    data: formData
  })

  if (uploadResponse.status() !== 200) {
    throw new Error(`Upload failed: ${uploadResponse.status()}`)
  }

  const uploadData = await uploadResponse.json() as any
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
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2))

  console.log('[E2E Setup] Transcription complete!')
  return transcriptionId
}

export async function cleanupProductionTranscription(page: Page): Promise<void> {
  if (!fs.existsSync(STATE_FILE)) {
    console.log('[E2E Cleanup] No state file, skipping cleanup')
    return
  }

  const state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8')) as TranscriptionState
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

  // Remove state file
  fs.unlinkSync(STATE_FILE)
}

async function getAuthToken(page: Page): Promise<string> {
  return await page.evaluate(() => {
    const keys = Object.keys(localStorage)
    const authKey = keys.find(k => k.startsWith('sb-') && k.includes('-auth-token'))
    if (!authKey) throw new Error('No auth token found')
    const tokenData = JSON.parse(localStorage.getItem(authKey)!)
    return tokenData?.currentSession?.access_token || tokenData?.access_token || ''
  })
}

async function pollForCompletion(page: Page, token: string, transcriptionId: string): Promise<void> {
  const maxAttempts = 120  // 10 minutes (5s intervals)
  const interval = 5000   // 5 seconds

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const response = await page.request.get(`/api/transcriptions/${transcriptionId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (response.status() === 200) {
      const data = await response.json() as any
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
