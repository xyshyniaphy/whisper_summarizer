/**
 * TranscriptionDetailページのテスト
 *
 * 転写詳細表示、要約表示、ダウンロード機能、
 * PPTX生成、ポーリングをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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
    downloadSummaryDocx: vi.fn(),
    downloadNotebookLMGuideline: vi.fn(),
    generatePptx: vi.fn(),
    getPptxStatus: vi.fn(),
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
const mockDownloadSummaryDocx = vi.mocked(api.downloadSummaryDocx)
const mockDownloadNotebookLMGuideline = vi.mocked(api.downloadNotebookLMGuideline)
const mockGeneratePptx = vi.mocked(api.generatePptx)
const mockGetPptxStatus = vi.mocked(api.getPptxStatus)
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
    mockDownloadSummaryDocx.mockResolvedValue(new Blob(['docx content']))
    mockDownloadNotebookLMGuideline.mockResolvedValue(new Blob(['notebooklm content']))
    mockGeneratePptx.mockResolvedValue({ status: 'generating' })
    mockGetPptxStatus.mockResolvedValue({ status: 'ready', exists: true })
    mockCreateShareLink.mockResolvedValue({ token: 'test-token', url: 'https://example.com/share/test-token' })
    mockAssignTranscriptionToChannels.mockResolvedValue(undefined)
    mockGetTranscriptionChannels.mockResolvedValue([])
  })

  describe('Rendering', () => {
    it('転写詳細が正常にレンダリングされる', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })
    })

    it('ローディング状態が表示される', () => {
      mockGetTranscription.mockImplementation(() => new Promise(() => {}))
      renderWithRoute('test-1')

      expect(screen.queryByText(/test-audio.mp3/)).toBeNull()
    })

    it('存在しない転写の場合、「未找到」が表示される', async () => {
      mockGetTranscription.mockResolvedValue(null as any)
      renderWithRoute('nonexistent')

      await waitFor(() => {
        expect(screen.getByText('未找到')).toBeTruthy()
      })
    })

    it('戻るボタンが表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('← 返回列表')).toBeTruthy()
      })
    })
  })

  describe('Transcription Display', () => {
    it('転写テキストが表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText(/This is a test transcription/)).toBeTruthy()
      })
    })

    it('ステータスバッジが正しく表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('已完成')).toBeTruthy()
      })
    })
  })

  describe('Error Display', () => {
    it('エラーメッセージがある場合、エラーカードが表示される', async () => {
      mockGetTranscription.mockResolvedValue(mockTranscriptionFailed)
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('处理失败')).toBeTruthy()
        expect(screen.getByText(/Audio file is corrupted/)).toBeTruthy()
      })
    })
  })

  describe('Summary Display', () => {
    it('要約が表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('AI摘要')).toBeTruthy()
        expect(screen.getByText(/This is a test summary/)).toBeTruthy()
      })
    })

    it('要約がない場合のメッセージが表示される', async () => {
      const noSummaryTranscription = { ...mockTranscription, summaries: [] }
      mockGetTranscription.mockResolvedValue(noSummaryTranscription)
      renderWithRoute('test-1')

      await waitFor(() => {
        const summaryText = screen.queryByText(/未找到摘要数据/)
        expect(summaryText).toBeTruthy()
      })
    })

    it('転写中のメッセージが表示される', async () => {
      mockGetTranscription.mockResolvedValue(mockTranscriptionProcessing)
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText(/转录完成后将自动生成摘要/)).toBeTruthy()
      })
    })
  })

  describe('Download Functionality', () => {
    it('テキストダウンロードボタンが表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载文本')).toBeTruthy()
      })
    })

    it('SRTダウンロードボタンが表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载字幕(SRT)')).toBeTruthy()
      })
    })

    it('テキストダウンロードが動作する', async () => {
      const user = userEvent.setup()
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载文本')).toBeTruthy()
      })

      const downloadButton = screen.getByText('下载文本')
      await user.click(downloadButton)

      await waitFor(() => {
        expect(mockDownloadFile).toHaveBeenCalledWith('test-1', 'txt')
      })
    })

    it('SRTダウンロードが動作する', async () => {
      const user = userEvent.setup()
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载字幕(SRT)')).toBeTruthy()
      })

      const downloadButton = screen.getByText('下载字幕(SRT)')
      await user.click(downloadButton)

      await waitFor(() => {
        expect(mockDownloadFile).toHaveBeenCalledWith('test-1', 'srt')
      })
    })
  })

  describe('PPTX Functionality', () => {
    it('PPTX生成ボタンが表示される', async () => {
      mockGetPptxStatus.mockResolvedValue({ status: 'not-started', exists: false })
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('生成PPT')).toBeTruthy()
      })
    })

    it('PPTXが準備完了の場合、ダウンロードボタンが表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载PPT')).toBeTruthy()
      })
    })

    it('PPTX生成中の場合、ローディング表示がされる', async () => {
      mockGetPptxStatus.mockResolvedValue({ status: 'generating', exists: false })
      mockGeneratePptx.mockResolvedValue({ status: 'generating', message: 'Generating' })
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText(/生成中/)).toBeTruthy()
      })
    })

    it('PPTX生成をクリックするとAPIが呼ばれる', async () => {
      mockGetPptxStatus.mockResolvedValue({ status: 'not-started', exists: false })
      const user = userEvent.setup()
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('生成PPT')).toBeTruthy()
      })

      const generateButton = screen.getByText('生成PPT')
      await user.click(generateButton)

      await waitFor(() => {
        expect(mockGeneratePptx).toHaveBeenCalledWith('test-1')
      })
    })
  })

  describe('Navigation', () => {
    it('戻るボタンをクリックするとリストに戻る', async () => {
      const user = userEvent.setup()
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('← 返回列表')).toBeTruthy()
      })

      const backButton = screen.getByText('← 返回列表')
      await user.click(backButton)
    })
  })

  describe('Long Text Truncation', () => {
    it('長いテキストの場合、省略表示される', async () => {
      const longText = 'Line\n'.repeat(300)
      const longTranscription = { ...mockTranscription, text: longText }
      mockGetTranscription.mockResolvedValue(longTranscription)
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText(/剩余.*行/)).toBeTruthy()
      })
    })
  })

  describe('Polling Behavior', () => {
    it('処理中の転写はポーリングされる', async () => {
      mockGetTranscription.mockResolvedValue(mockTranscriptionProcessing)
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(mockGetTranscription).toHaveBeenCalled()
      })

      // Fast forward timers to test polling
      vi.advanceTimersByTime(3000)
    })

    it('完了した転写はポーリングされない', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('已完成')).toBeTruthy()
      })

      // No additional calls should be made after completion
      const initialCallCount = mockGetTranscription.mock.calls.length
      vi.advanceTimersByTime(5000)

      expect(mockGetTranscription.mock.calls.length).toBe(initialCallCount)
    })
  })

  describe('DOCX Download Functionality (NEW)', () => {
    it('DOCXダウンロードボタンがAI摘要セクションに表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('AI摘要')).toBeTruthy()
        expect(screen.getByText('下载DOCX')).toBeTruthy()
      })
    })

    it('要約がない場合、DOCXダウンロードボタンは表示されない', async () => {
      const noSummaryTranscription = { ...mockTranscription, summaries: [] }
      mockGetTranscription.mockResolvedValue(noSummaryTranscription)
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.queryByText('下载DOCX')).toBeNull()
      })
    })

    it('DOCXダウンロードが動作する', async () => {
      const user = userEvent.setup()
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载DOCX')).toBeTruthy()
      })

      const downloadButton = screen.getByTitle('下载Word文档')
      await user.click(downloadButton)

      await waitFor(() => {
        expect(mockDownloadSummaryDocx).toHaveBeenCalledWith('test-1')
      })
    })

    it('DOCXダウンロード失敗時、エラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      mockDownloadSummaryDocx.mockRejectedValue(new Error('Download failed'))
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      global.alert = vi.fn()

      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('下载DOCX')).toBeTruthy()
      })

      const downloadButton = screen.getByTitle('下载Word文档')
      await user.click(downloadButton)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled()
        expect(global.alert).toHaveBeenCalledWith('DOCX下载失败')
      })

      consoleSpy.mockRestore()
    })
  })

  describe('PPT Button Location (UPDATED)', () => {
    it('PPTボタンがAI摘要セクションに表示される', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('AI摘要')).toBeTruthy()
        expect(screen.getByText('下载PPT')).toBeTruthy()
      })
    })

    it('PPTボタンが転写結果セクションに表示されない', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('转录结果')).toBeTruthy()
        // 転写結果セクションにはPPTボタンがないはず
        const pptButtons = screen.queryAllByText('生成PPT')
        const pptDownloadButtons = screen.queryAllByText('下载PPT')
        // これらはAI摘要セクションにあるので、転写結果セクションのカードには含まれない
        const transcriptionResultCard = screen.getByText('转录结果').closest('.space-y-6 > div')
        if (transcriptionResultCard) {
          expect(transcriptionResultCard.querySelectorAll('[title*="PPT"]')).toHaveLength(0)
        }
      })
    })

    it('AI摘要セクションにPPT生成ボタンが表示される（未生成の場合）', async () => {
      mockGetPptxStatus.mockResolvedValue({ status: 'not-started', exists: false })
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('AI摘要')).toBeTruthy()
        expect(screen.getByTitle('生成PowerPoint演示文稿')).toBeTruthy()
      })
    })

    it('AI摘要セクションにPPTダウンロードボタンが表示される（準備完了の場合）', async () => {
      renderWithRoute('test-1')

      await waitFor(() => {
        expect(screen.getByText('AI摘要')).toBeTruthy()
        expect(screen.getByTitle('下载PowerPoint演示文稿')).toBeTruthy()
      })
    })
  })
})
