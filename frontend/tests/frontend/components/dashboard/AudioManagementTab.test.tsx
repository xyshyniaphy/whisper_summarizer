/**
 * AudioManagementTabコンポーネントのテスト
 *
 * 音楽管理タブの表示、チャンネル割り当て、
 * 保存機能をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

import { AudioManagementTab } from '../../../../src/components/dashboard/AudioManagementTab'

// Mock audio data
const mockAudioList = [
  {
    id: '1',
    file_name: 'test-audio.mp3',
    created_at: '2025-01-01T00:00:00Z',
    user_id: 'user-1',
    user_email: 'user@example.com',
    channels: [
      { id: 'ch-1', name: 'Marketing' }
    ]
  },
  {
    id: '2',
    file_name: 'another-audio.wav',
    created_at: '2025-01-02T00:00:00Z',
    user_id: 'user-2',
    user_email: 'another@example.com',
    channels: []
  }
]

const mockChannels = [
  { id: 'ch-1', name: 'Marketing', description: 'Marketing team' },
  { id: 'ch-2', name: 'Sales', description: 'Sales team' }
]

const mockAudioChannels = [
  { id: 'ch-1', name: 'Marketing' }
]

// Helper function to set up axios mock with custom audio list
const setupMockAudioList = (audioList: any = mockAudioList) => {
  const mockAxiosGet = (global as any).mockAxiosGet
  if (mockAxiosGet) {
    mockAxiosGet.mockImplementation((url: string) => {
      // Match /admin/audio (listAllAudio)
      // Note: listAllAudio returns response.data.items (see api.ts line 433)
      if (url?.includes('/admin/audio') && !url?.includes('/channels')) {
        return Promise.resolve({ data: { items: audioList } })
      }
      // Match /admin/channels (listChannels)
      if (url?.includes('/admin/channels')) {
        return Promise.resolve({ data: mockChannels })
      }
      // Match /admin/audio/:id/channels (getAudioChannels)
      if (url?.includes('/channels') && url?.includes('/audio')) {
        return Promise.resolve({ data: mockAudioChannels })
      }
      // Default fallback for other requests (like /api/auth/user)
      return Promise.resolve({ data: [] })
    })
  }

  const mockAxiosPost = (global as any).mockAxiosPost
  if (mockAxiosPost) {
    mockAxiosPost.mockImplementation((url: string) => {
      // Match /admin/audio/:id/channels (assignAudioToChannels)
      if (url?.includes('/channels') && url?.includes('/audio')) {
        return Promise.resolve({ data: {} })
      }
      return Promise.resolve({ data: {} })
    })
  }
}

// Helper function to set up loading mock (never resolves)
const setupLoadingMock = () => {
  const mockAxiosGet = (global as any).mockAxiosGet
  if (mockAxiosGet) {
    mockAxiosGet.mockImplementation(() => new Promise(() => {}))
  }
}

// Helper function to set up error mock
const setupErrorMock = (errorMessage: string = 'API Error') => {
  const mockAxiosGet = (global as any).mockAxiosGet
  if (mockAxiosGet) {
    mockAxiosGet.mockRejectedValue(new Error(errorMessage))
  }
}

// Mock window.alert
global.alert = vi.fn()

describe('AudioManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Use global axios mocks from setup.ts
    setupMockAudioList(mockAudioList)
  })

  describe('Rendering', () => {
    it('ローディング状態が表示される', () => {
      setupLoadingMock()
      render(<AudioManagementTab />)

      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
    })

    it('音楽リストが表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
        expect(screen.getByText('another-audio.wav')).toBeTruthy()
      })
    })

    it('ヘッダーが表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('音频列表')).toBeTruthy()
      })
    })

    it('統計が表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText(/共.*个音频文件/)).toBeTruthy()
      })
    })

    it('テーブルヘッダーが表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('文件名')).toBeTruthy()
        expect(screen.getByText('所有者')).toBeTruthy()
        // "分配频道" appears in both table header and buttons, so check it exists at least once
        expect(screen.getAllByText('分配频道').length).toBeGreaterThan(0)
        expect(screen.getByText('创建时间')).toBeTruthy()
        expect(screen.getByText('操作')).toBeTruthy()
      })
    })
  })

  describe('Audio Item Display', () => {
    it('音楽ファイル名が表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })
    })

    it('所有者のメールアドレスが表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('user@example.com')).toBeTruthy()
        expect(screen.getByText('another@example.com')).toBeTruthy()
      })
    })

    it('割り当てられたチャンネルが表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })
    })

    it('チャンネル未割り当ての場合「未分配」と表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('未分配')).toBeTruthy()
      })
    })
  })

  describe('Channel Assignment', () => {
    it('「分配频道」ボタンが表示される', async () => {
      render(<AudioManagementTab />)

      await waitFor(() => {
        // "分配频道" appears in both table header and buttons
        const elements = screen.getAllByText('分配频道')
        expect(elements.length).toBeGreaterThan(0)
      })
    })

    it('「分配频道」ボタンをクリックするとモーダルが開く', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      // Find the button elements (not table headers) by looking for buttons
      const buttons = document.querySelectorAll('button')
      const assignButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('分配频道')
      )

      expect(assignButton).toBeTruthy()

      if (assignButton) {
        await user.click(assignButton)

        await waitFor(() => {
          const modals = document.querySelectorAll('[role="dialog"]')
          expect(modals.length).toBeGreaterThan(0)
        })
      }
    })

    it('チャンネル選択モーダルにチャンネルリストが表示される', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      // Wait for initial data load (channels should be loaded)
      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      // Find the button elements (not table headers) by looking for buttons
      const buttons = document.querySelectorAll('button')
      const assignButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('分配频道')
      )

      expect(assignButton).toBeTruthy()

      if (assignButton) {
        await user.click(assignButton)

        await waitFor(() => {
          // First check that the modal opened
          expect(screen.getByText('分配频道 - test-audio.mp3')).toBeTruthy()
        }, { timeout: 3000 })

        await waitFor(() => {
          // Then check that channels are displayed in the modal
          // Check for "Sales" which should only be in the modal (not in the audio list)
          const salesText = screen.queryByText('Sales')
          expect(salesText).toBeTruthy()
        }, { timeout: 3000 })
      }
    })
  })

  describe('Channel Selection in Modal', () => {
    it('チャンネルのチェックボックスをクリックして選択できる', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      const buttons = document.querySelectorAll('button')
      const assignButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('分配频道')
      )

      expect(assignButton).toBeTruthy()

      if (assignButton) {
        await user.click(assignButton)

        await waitFor(() => {
          const checkboxes = document.querySelectorAll('input[type="checkbox"]')
          expect(checkboxes.length).toBeGreaterThan(0)
        })
      }
    })

    it('選択したチャンネル数が表示される', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      const buttons = document.querySelectorAll('button')
      const assignButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('分配频道')
      )

      expect(assignButton).toBeTruthy()

      if (assignButton) {
        await user.click(assignButton)

        await waitFor(() => {
          expect(screen.getByText(/已选择.*个频道/)).toBeTruthy()
        })
      }
    })
  })

  describe('Save Assignment', () => {
    it('「保存」ボタンをクリックして割り当てを保存できる', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      const buttons = document.querySelectorAll('button')
      const assignButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('分配频道')
      )

      expect(assignButton).toBeTruthy()

      if (assignButton) {
        await user.click(assignButton)

        await waitFor(() => {
          expect(screen.getByText('保存')).toBeTruthy()
        })

        const saveButton = screen.getByText('保存')
        await user.click(saveButton)

        await waitFor(() => {
          const mockAxiosPost = (global as any).mockAxiosPost
          expect(mockAxiosPost).toHaveBeenCalled()
        })
      }
    })
  })

  describe('Error Handling', () => {
    it('エラー時にエラーメッセージと再試行ボタンが表示される', async () => {
      setupErrorMock('API Error')

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('加载音频列表失败')).toBeTruthy()
        expect(screen.getByText('重试')).toBeTruthy()
      })
    })

    it('再試行ボタンでデータを再読み込みできる', async () => {
      const user = userEvent.setup()

      // First call fails, second succeeds
      const mockAxiosGet = (global as any).mockAxiosGet
      if (mockAxiosGet) {
        mockAxiosGet
          .mockRejectedValueOnce(new Error('API Error'))
          .mockImplementationOnce((url: string) => {
            if (url?.includes('/admin/audio') && !url?.includes('/channels')) {
              return Promise.resolve({ data: { items: mockAudioList } })
            }
            if (url?.includes('/admin/channels')) {
              return Promise.resolve({ data: mockChannels })
            }
            return Promise.resolve({ data: [] })
          })
      }

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('重试')).toBeTruthy()
      })

      const retryButton = screen.getByText('重试')
      await user.click(retryButton)

      await waitFor(() => {
        expect(mockAxiosGet).toHaveBeenCalledTimes(3) // Error retry + audio + channels
      })
    })
  })

  describe('Empty States', () => {
    it('チャンネルがない場合「暂无可用频道」と表示される', async () => {
      const user = userEvent.setup()

      // Setup empty channels list
      const mockAxiosGet = (global as any).mockAxiosGet
      if (mockAxiosGet) {
        mockAxiosGet.mockImplementation((url: string) => {
          if (url?.includes('/admin/audio') && !url?.includes('/channels')) {
            return Promise.resolve({ data: { items: mockAudioList } })
          }
          if (url?.includes('/admin/channels')) {
            return Promise.resolve({ data: [] })
          }
          if (url?.includes('/channels') && url?.includes('/audio')) {
            return Promise.resolve({ data: mockAudioChannels })
          }
          return Promise.resolve({ data: [] })
        })
      }

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('test-audio.mp3')).toBeTruthy()
      })

      const buttons = document.querySelectorAll('button')
      const assignButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('分配频道')
      )

      expect(assignButton).toBeTruthy()

      if (assignButton) {
        await user.click(assignButton)

        await waitFor(() => {
          expect(screen.getByText('暂无可用频道')).toBeTruthy()
        })
      }
    })
  })
})
