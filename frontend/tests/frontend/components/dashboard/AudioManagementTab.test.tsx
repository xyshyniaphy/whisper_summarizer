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

// Mock adminApi
vi.mock('@/services/api', () => ({
  adminApi: {
    listAllAudio: vi.fn(() => Promise.resolve([
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
    ])),
    listChannels: vi.fn(() => Promise.resolve([
      { id: 'ch-1', name: 'Marketing', description: 'Marketing team' },
      { id: 'ch-2', name: 'Sales', description: 'Sales team' }
    ])),
    getAudioChannels: vi.fn(() => Promise.resolve([
      { id: 'ch-1', name: 'Marketing' }
    ])),
    assignAudioToChannels: vi.fn(() => Promise.resolve())
  }
}))

// Mock window.alert
global.alert = vi.fn()

describe('AudioManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('ローディング状態が表示される', () => {
      const { adminApi } = require('../../../../src/services/api')
      adminApi.listAllAudio.mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      )

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
        expect(screen.getByText('分配频道')).toBeTruthy()
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
        expect(screen.getByText('分配频道')).toBeTruthy()
      })
    })

    it('「分配频道」ボタンをクリックするとモーダルが開く', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('分配频道')).toBeTruthy()
      })

      const assignButtons = screen.getAllByText('分配频道')
      await user.click(assignButtons[0])

      await waitFor(() => {
        const modals = document.querySelectorAll('[role="dialog"]')
        expect(modals.length).toBeGreaterThan(0)
      })
    })

    it('チャンネル選択モーダルにチャンネルリストが表示される', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('分配频道')).toBeTruthy()
      })

      const assignButtons = screen.getAllByText('分配频道')
      await user.click(assignButtons[0])

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })
    })
  })

  describe('Channel Selection in Modal', () => {
    it('チャンネルのチェックボックスをクリックして選択できる', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('分配频道')).toBeTruthy()
      })

      const assignButtons = screen.getAllByText('分配频道')
      await user.click(assignButtons[0])

      await waitFor(() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]')
        expect(checkboxes.length).toBeGreaterThan(0)
      })
    })

    it('選択したチャンネル数が表示される', async () => {
      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('分配频道')).toBeTruthy()
      })

      const assignButtons = screen.getAllByText('分配频道')
      await user.click(assignButtons[0])

      await waitFor(() => {
        expect(screen.getByText(/已选择.*个频道/)).toBeTruthy()
      })
    })
  })

  describe('Save Assignment', () => {
    it('「保存」ボタンをクリックして割り当てを保存できる', async () => {
      const user = userEvent.setup()
      const { adminApi } = require('../../../../src/services/api')

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('分配频道')).toBeTruthy()
      })

      const assignButtons = screen.getAllByText('分配频道')
      await user.click(assignButtons[0])

      await waitFor(() => {
        expect(screen.getByText('保存')).toBeTruthy()
      })

      const saveButton = screen.getByText('保存')
      await user.click(saveButton)

      await waitFor(() => {
        expect(adminApi.assignAudioToChannels).toHaveBeenCalled()
      })
    })
  })

  describe('Error Handling', () => {
    it('エラー時にエラーメッセージと再試行ボタンが表示される', async () => {
      const { adminApi } = require('../../../../src/services/api')
      adminApi.listAllAudio.mockRejectedValueOnce(new Error('API Error'))

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('加载音频列表失败')).toBeTruthy()
        expect(screen.getByText('重试')).toBeTruthy()
      })
    })

    it('再試行ボタンでデータを再読み込みできる', async () => {
      const user = userEvent.setup()
      const { adminApi } = require('../../../../src/services/api')
      adminApi.listAllAudio
        .mockRejectedValueOnce(new Error('API Error'))
        .mockResolvedValueOnce([
          {
            id: '1',
            file_name: 'test.mp3',
            created_at: '2025-01-01T00:00:00Z',
            user_id: 'user-1',
            user_email: 'test@example.com',
            channels: []
          }
        ])

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('重试')).toBeTruthy()
      })

      const retryButton = screen.getByText('重试')
      await user.click(retryButton)

      await waitFor(() => {
        expect(adminApi.listAllAudio).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Empty States', () => {
    it('チャンネルがない場合「暂无可用频道」と表示される', async () => {
      const { adminApi } = require('../../../../src/services/api')
      adminApi.listChannels.mockResolvedValueOnce([])

      const user = userEvent.setup()

      render(<AudioManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('分配频道')).toBeTruthy()
      })

      const assignButtons = screen.getAllByText('分配频道')
      await user.click(assignButtons[0])

      await waitFor(() => {
        expect(screen.getByText('暂无可用频道')).toBeTruthy()
      })
    })
  })
})
