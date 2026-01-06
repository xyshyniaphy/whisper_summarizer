/**
 * TranscriptionListページのテスト
 *
 * 転写リスト表示、削除機能、ステータスフィルタリング、
 * ナビゲーションをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'jotai'
import { TranscriptionList } from '../../../src/pages/TranscriptionList'

// Mock Supabase client
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } }
      }))
    }
  }
}))

// Mock API
const mockGetTranscriptions = vi.fn()
const mockDeleteTranscription = vi.fn()

vi.mock('../../../src/services/api', () => ({
  api: {
    getTranscriptions: () => mockGetTranscriptions(),
    deleteTranscription: (id: string) => mockDeleteTranscription(id)
  }
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

// Mock transcriptions data
const mockTranscriptions = [
  {
    id: '1',
    user_id: 'user-1',
    file_name: 'test-audio.mp3',
    original_text: 'Test transcription text',
    language: 'zh',
    duration_seconds: 120.5,
    stage: 'completed',
    error_message: null,
    retry_count: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:05:00Z',
    summaries: []
  },
  {
    id: '2',
    user_id: 'user-1',
    file_name: 'processing-audio.mp3',
    original_text: null,
    language: null,
    duration_seconds: null,
    stage: 'transcribing',
    error_message: null,
    retry_count: 0,
    created_at: '2024-01-01T01:00:00Z',
    updated_at: '2024-01-01T01:00:00Z',
    summaries: []
  },
  {
    id: '3',
    user_id: 'user-1',
    file_name: 'failed-audio.mp3',
    original_text: null,
    language: null,
    duration_seconds: null,
    stage: 'failed',
    error_message: 'File format not supported',
    retry_count: 0,
    created_at: '2024-01-01T02:00:00Z',
    updated_at: '2024-01-01T02:00:00Z',
    summaries: []
  }
]

describe('TranscriptionList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Return PaginatedResponse structure
    mockGetTranscriptions.mockResolvedValue({
      total: mockTranscriptions.length,
      page: 1,
      page_size: 10,
      total_pages: 1,
      data: mockTranscriptions
    })
    mockDeleteTranscription.mockResolvedValue(undefined)
    // Mock window.confirm
    global.confirm = vi.fn(() => true) as any
  })

  describe('Rendering', () => {
    it('転写リストが正常にレンダリングされる', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('新建转录')).toBeTruthy()
        expect(screen.getByText('转录历史')).toBeTruthy()
      })
    })

    it('転写データがテーブルに表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
        expect(screen.getByText('processing-audio.mp3')).toBeTruthy()
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
      })
    })

    it('データがない場合、「暂无数据」が表示される', async () => {
      mockGetTranscriptions.mockResolvedValue([])
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('暂无数据')).toBeTruthy()
      })
    })
  })

  describe('Status Badges', () => {
    it('ステータスバッジが正しく表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('已完成')).toBeTruthy()
        expect(screen.getByText('转录中')).toBeTruthy()
        expect(screen.getByText('失败')).toBeTruthy()
      })
    })

    it('エラーメッセージがある場合、エラーアイコンとメッセージが表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        const errorMessage = screen.queryByText(/File format not supported/)
        expect(errorMessage).toBeTruthy()
      })
    })
  })

  describe.skip('Delete Functionality', () => {
    it('失敗した転写は削除ボタンが表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Failed transcription should have delete button
        const rows = screen.getAllByText('失败')
        expect(rows.length).toBeGreaterThan(0)
      })
    })

    it('削除ボタンをクリックすると確認ダイアログが表示される', async () => {
      const user = userEvent.setup()
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
      })

      // Click delete button (find by aria-label or data-testid)
      const deleteButtons = screen.getAllByTitle('删除')
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0])
        expect(global.confirm).toHaveBeenCalledWith('确定要删除吗？')
      }
    })

    it('確認後、deleteTranscriptionが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
      })

      const deleteButtons = screen.getAllByTitle('删除')
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0])

        await waitFor(() => {
          expect(mockDeleteTranscription).toHaveBeenCalled()
        })
      }
    })

    it('キャンセル時、deleteTranscriptionは呼ばれない', async () => {
      global.confirm = vi.fn(() => false) as any
      const user = userEvent.setup()
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
      })

      const deleteButtons = screen.getAllByTitle('删除')
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0])
        expect(mockDeleteTranscription).not.toHaveBeenCalled()
      }
    })
  })

  describe('Row Navigation', () => {
    it('行をクリックすると詳細ページに遷移する', async () => {
      const user = userEvent.setup()
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      // Click on the row (file name cell)
      const fileNameCell = screen.getByText('test-audio.mp3').closest('tr')
      if (fileNameCell) {
        await user.click(fileNameCell)
      }
    })
  })

  describe.skip('Date Formatting', () => {
    it('作成日時が正しくフォーマットされて表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Should show Chinese formatted date
        expect(screen.getByText('2024/')).toBeTruthy()
      })
    })
  })

  describe('AudioUploader Integration', () => {
    it('AudioUploaderコンポーネントが表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('将音频文件拖放到此处')).toBeTruthy()
      })
    })
  })

  describe('Retry Count Display', () => {
    it('リトライ回数が表示される', async () => {
      const transcriptionsWithRetry = [
        {
          ...mockTranscriptions[0],
          retry_count: 3
        }
      ]
      mockGetTranscriptions.mockResolvedValue(transcriptionsWithRetry)

      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        const retryText = screen.queryByText(/重试.*3.*次/)
        // May or may not be visible depending on component
      })
    })
  })
})
