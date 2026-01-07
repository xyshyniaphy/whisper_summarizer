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
import React from 'react'
import { TranscriptionList } from '../../../src/pages/TranscriptionList'

// Import global mock functions from setup.ts
declare global {
  var mockAxiosGet: any
  var mockAxiosDelete: any
  var mockNavigate: any
}

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
    completed_at: '2024-01-01T00:05:00Z',
    time_remaining: 600000, // seconds
    summaries: [],
    channels: [],
    is_personal: false
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
    completed_at: null,
    time_remaining: null,
    summaries: [],
    channels: [],
    is_personal: false
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
    completed_at: null,
    time_remaining: null,
    summaries: [],
    channels: [],
    is_personal: false
  }
]

describe('TranscriptionList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Return PaginatedResponse structure
    global.mockAxiosGet.mockResolvedValue({
      data: {
        total: mockTranscriptions.length,
        page: 1,
        page_size: 10,
        total_pages: 1,
        data: mockTranscriptions
      }
    })
    global.mockAxiosDelete.mockResolvedValue({ data: undefined })
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
      global.mockAxiosGet.mockResolvedValue({
        data: {
          total: 0,
          page: 1,
          page_size: 10,
          total_pages: 0,
          data: []
        }
      })

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

  describe('Delete Functionality', () => {
    it('削除ボタンが表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Failed transcription should have delete button
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
        const deleteButtons = screen.getAllByTitle('删除')
        expect(deleteButtons.length).toBeGreaterThan(0)
      })
    })

    it('削除ボタンをクリックすると確認ダイアログが表示される', async () => {
      const user = userEvent.setup()
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
      })

      const deleteButtons = screen.getAllByTitle('删除')
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0])

        await waitFor(() => {
          // Check that dialog elements appear - look for any of the possible dialog texts
          const deleteText = screen.queryByText('删除')
          const cancelText = screen.queryByText('取消')
          // At least one dialog element should appear
          expect(deleteText || cancelText).toBeTruthy()
        }, { timeout: 3000 })
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

        // Click confirm in dialog
        const confirmButton = screen.getByText('删除')
        await user.click(confirmButton)

        await waitFor(() => {
          expect(global.mockAxiosDelete).toHaveBeenCalled()
        })
      }
    })

    it('キャンセル時、deleteTranscriptionは呼ばれない', async () => {
      const user = userEvent.setup()
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('failed-audio.mp3')).toBeTruthy()
      })

      const deleteButtons = screen.getAllByTitle('删除')
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0])

        // Click cancel in dialog
        const cancelButton = screen.getByText('取消')
        await user.click(cancelButton)

        expect(global.mockAxiosDelete).not.toHaveBeenCalled()
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

        await waitFor(() => {
          expect(global.mockNavigate).toHaveBeenCalledWith('/transcriptions/1')
        })
      }
    })
  })

  describe('Date Formatting', () => {
    it('作成日時が正しくフォーマットされて表示される', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Check for date elements - the component uses toLocaleString('zh-CN')
        // which will format dates like '2024-01-01 00:00:00'
        const dateElements = screen.getAllByText(/2024/)
        expect(dateElements.length).toBeGreaterThan(0)
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
    it('retry_countが0の場合、ステータスバッジの後に余分なテキストが表示されない（UI bug fix）', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Check that "已完成" badge doesn't have stray "0" after it
        const completedBadge = screen.getByText('已完成')
        const parent = completedBadge.closest('td')
        // The status cell should only contain the badge, not "已完成0"
        expect(parent?.textContent).not.toContain('已完成0')
        expect(parent?.textContent).toContain('已完成')
      })
    })

    it('retry_countが3の場合、「重试 3 次」が表示される', async () => {
      const transcriptionsWithRetry = [
        {
          ...mockTranscriptions[0],
          retry_count: 3
        }
      ]
      global.mockAxiosGet.mockResolvedValue({
        data: {
          total: 1,
          page: 1,
          page_size: 10,
          total_pages: 1,
          data: transcriptionsWithRetry
        }
      })

      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Use the correct simplified Chinese character
        const retryText = screen.queryByText(/重试.*3.*次/)
        expect(retryText).toBeTruthy()
      })
    })

    it('retry_countが0の場合、リトライ表示はされない', async () => {
      render(<TranscriptionList />, { wrapper })

      await waitFor(() => {
        // Should not show "重试 0 次" when retry_count is 0
        const retryTextZero = screen.queryByText(/重试.*0.*次/)
        expect(retryTextZero).toBeNull()
      })
    })
  })
})
