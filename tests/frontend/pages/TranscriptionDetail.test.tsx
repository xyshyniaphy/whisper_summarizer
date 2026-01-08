/**
 * TranscriptionDetailページのテスト
 *
 * 転写詳細表示、要約表示、ダウンロード機能、
 * PPTX生成、ポーリングをテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { Provider } from 'jotai'
import React from 'react'
import { TranscriptionDetail } from '@/pages/TranscriptionDetail'

// Mock Supabase client
vi.mock('@/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } }
      }))
    }
  }
}))

// Mock API - mock must be defined inline due to hoisting
vi.mock('@/services/api', () => ({
  api: {
    getTranscription: vi.fn(),
    downloadFile: vi.fn(),
    createShareLink: vi.fn(),
    assignTranscriptionToChannels: vi.fn(),
    getTranscriptionChannels: vi.fn(),
    getDownloadUrl: (id: string, format: string) => `/api/transcriptions/${id}/download?format=${format}`
  }
}))

// Import the mocked api module to access and control the mocks
import { api } from '@/services/api'

// Get references to the mocked functions
const mockGetTranscription = vi.mocked(api.getTranscription)
const mockDownloadFile = vi.mocked(api.downloadFile)
const mockCreateShareLink = vi.mocked(api.createShareLink)
const mockAssignTranscriptionToChannels = vi.mocked(api.assignTranscriptionToChannels)
const mockGetTranscriptionChannels = vi.mocked(api.getTranscriptionChannels)

// Mock DOM methods
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url') as any
global.URL.revokeObjectURL = vi.fn() as any

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

// Helper to render with route - use MemoryRouter for testing
const renderWithRoute = (id: string) => {
  return render(
    <MemoryRouter initialEntries={[`/transcriptions/${id}`]}>
      <Provider>
        <Routes>
          <Route path="/transcriptions/:id" element={<TranscriptionDetail />} />
        </Routes>
      </Provider>
    </MemoryRouter>
  )
}

// Mock transcription data
const mockTranscription = {
  id: 'test-1',
  user_id: 'user-1',
  file_name: 'test-audio.mp3',
  text: 'This is a test transcription.\n\nIt has multiple paragraphs.\n\nAnd even more content to display.',
  language: 'en',
  duration_seconds: 120.5,
  stage: 'completed',
  error_message: null,
  retry_count: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:05:00Z',
  summaries: [
    {
      id: 'summary-1',
      transcription_id: 'test-1',
      summary_text: 'This is a test summary with key points.',
      created_at: '2024-01-01T00:06:00Z'
    }
  ]
}

const mockTranscriptionProcessing = {
  ...mockTranscription,
  stage: 'transcribing',
  text: null
}

const mockTranscriptionFailed = {
  ...mockTranscription,
  stage: 'failed',
  error_message: 'Audio file is corrupted'
}

describe('TranscriptionDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetTranscription.mockResolvedValue(mockTranscription)
    mockDownloadFile.mockResolvedValue(new Blob(['test content']))
    mockCreateShareLink.mockResolvedValue({ token: 'test-token', url: 'https://example.com/share/test-token' })
    mockAssignTranscriptionToChannels.mockResolvedValue(undefined)
    mockGetTranscriptionChannels.mockResolvedValue([])
  })

  afterEach(() => {
    cleanup()
  })

  describe('Rendering', () => {
    it('ローディング状態が表示される', () => {
      mockGetTranscription.mockImplementation(() => new Promise(() => {}))
      renderWithRoute('test-1')

      expect(screen.queryByText(/test-audio.mp3/)).toBeNull()
    })
  })

})
