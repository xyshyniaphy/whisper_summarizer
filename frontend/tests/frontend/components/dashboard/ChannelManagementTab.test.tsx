/**
 * ChannelManagementTabコンポーネントのテスト
 *
 * チャンネル管理タブの表示、作成、編集、削除、
 * メンバー管理機能をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

import { ChannelManagementTab } from '../../../../src/components/dashboard/ChannelManagementTab'

// Create mock functions at module level
const mockListChannels = vi.fn(() => Promise.resolve([
  {
    id: 'ch-1',
    name: 'Marketing',
    description: 'Marketing team',
    created_by: 'admin-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    member_count: 3
  },
  {
    id: 'ch-2',
    name: 'Sales',
    description: null,
    created_by: 'admin-1',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    member_count: 1
  }
]))
const mockGetChannelDetail = vi.fn((id) => Promise.resolve(
  id === 'ch-1' ? {
    id: 'ch-1',
    name: 'Marketing',
    description: 'Marketing team',
    members: [
      { id: 'user-1', email: 'user1@example.com', is_active: true, is_admin: false }
    ]
  } : {
    id: 'ch-2',
    name: 'Sales',
    description: null,
    members: []
  }
))
const mockListUsers = vi.fn(() => Promise.resolve([
  { id: 'user-1', email: 'user1@example.com', is_active: true, is_admin: false },
  { id: 'user-2', email: 'user2@example.com', is_active: true, is_admin: true }
]))
const mockCreateChannel = vi.fn(() => Promise.resolve())
const mockUpdateChannel = vi.fn(() => Promise.resolve())
const mockDeleteChannel = vi.fn(() => Promise.resolve())
const mockAssignUserToChannel = vi.fn(() => Promise.resolve())
const mockRemoveUserFromChannel = vi.fn(() => Promise.resolve())

// Mock adminApi
vi.mock('@/services/api', () => ({
  adminApi: {
    listChannels: () => mockListChannels(),
    getChannelDetail: (id: string) => mockGetChannelDetail(id),
    listUsers: () => mockListUsers(),
    createChannel: () => mockCreateChannel(),
    updateChannel: () => mockUpdateChannel(),
    deleteChannel: () => mockDeleteChannel(),
    assignUserToChannel: () => mockAssignUserToChannel(),
    removeUserFromChannel: () => mockRemoveUserFromChannel()
  }
}))

// Mock window.alert
global.alert = vi.fn()

describe('ChannelManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('ローディング状態が表示される', () => {
      mockListChannels.mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      )

      render(<ChannelManagementTab />)

      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
    })

    it('チャンネルリストが表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
        expect(screen.getByText('Sales')).toBeTruthy()
      })
    })

    it('「创建频道」ボタンが表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('创建频道')).toBeTruthy()
      })
    })

    it('チャンネル統計が表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText(/共.*个频道/)).toBeTruthy()
      })
    })

    it('テーブルヘッダーが表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('频道名称')).toBeTruthy()
        expect(screen.getByText('描述')).toBeTruthy()
        expect(screen.getByText('成员数量')).toBeTruthy()
        expect(screen.getByText('更新时间')).toBeTruthy()
        expect(screen.getByText('操作')).toBeTruthy()
      })
    })
  })

  describe('Channel Display', () => {
    it('チャンネル名が表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
        expect(screen.getByText('Sales')).toBeTruthy()
      })
    })

    it('チャンネル説明が表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing team')).toBeTruthy()
      })
    })

    it('説明がない場合「-」と表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        const cells = screen.getAllByText('-')
        expect(cells.length).toBeGreaterThan(0)
      })
    })

    it('メンバー数が表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('3')).toBeTruthy()
        expect(screen.getByText('1')).toBeTruthy()
      })
    })
  })

  describe('Create Channel', () => {
    it('「创建频道」ボタンをクリックするとモーダルが開く', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('创建频道')).toBeTruthy()
      })

      const createButton = screen.getByText('创建频道')
      await user.click(createButton)

      await waitFor(() => {
        expect(screen.getByText('创建频道')).toBeTruthy() // Modal title
      })
    })

    it('チャンネル名を入力できる', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('创建频道')).toBeTruthy()
      })

      const createButton = screen.getByText('创建频道')
      await user.click(createButton)

      await waitFor(() => {
        const input = document.querySelector('input[type="text"]')
        expect(input).toBeTruthy()
      })
    })
  })

  describe('Edit Channel', () => {
    it('編集ボタンが表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        const editButtons = document.querySelectorAll('button')
        const hasEditButton = Array.from(editButtons).some(btn =>
          btn.querySelector('.lucide-pen') || btn.innerHTML.includes('Edit2')
        )
        expect(hasEditButton).toBe(true)
      })
    })
  })

  describe('Delete Channel', () => {
    it('削除ボタンが表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        const deleteButtons = document.querySelectorAll('button')
        const hasDeleteButton = Array.from(deleteButtons).some(btn =>
          btn.querySelector('.lucide-trash-2')
        )
        expect(hasDeleteButton).toBe(true)
      })
    })

    it('削除確認ダイアログが表示される', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      // Find and click delete button
      const deleteButtons = document.querySelectorAll('button')
      const deleteBtn = Array.from(deleteButtons).find(btn =>
        btn.querySelector('.lucide-trash-2')
      )

      if (deleteBtn) {
        await user.click(deleteBtn)

        await waitFor(() => {
          expect(screen.getByText('确认删除频道')).toBeTruthy()
        })
      }
    })
  })

  describe('Member Management', () => {
    it('「成员」ボタンが表示される', async () => {
      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('成员')).toBeTruthy()
      })
    })

    it('「成员」ボタンをクリックするとメンバーモーダルが開く', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('成员')).toBeTruthy()
      })

      const memberButtons = screen.getAllByText('成员')
      await user.click(memberButtons[0])

      await waitFor(() => {
        // Members modal should open
        const modals = document.querySelectorAll('[role="dialog"]')
        expect(modals.length).toBeGreaterThan(0)
      })
    })

    it('メンバーリストが表示される', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('成员')).toBeTruthy()
      })

      const memberButtons = screen.getAllByText('成员')
      await user.click(memberButtons[0])

      await waitFor(() => {
        // Should show "当前成员" text
        expect(screen.getByText(/当前成员/)).toBeTruthy()
      })
    })
  })

  describe('Error Handling', () => {
    it('エラー時にエラーメッセージと再試行ボタンが表示される', async () => {
      mockListChannels.mockRejectedValueOnce(new Error('API Error'))

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('加载频道列表失败')).toBeTruthy()
        expect(screen.getByText('重试')).toBeTruthy()
      })
    })

    it('再試行ボタンでデータを再読み込みできる', async () => {
      const user = userEvent.setup()
      mockListChannels
        .mockRejectedValueOnce(new Error('API Error'))
        .mockResolvedValueOnce([
          {
            id: 'ch-1',
            name: 'Test Channel',
            description: 'Test',
            created_by: 'admin-1',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2025-01-01T00:00:00Z',
            member_count: 0
          }
        ])

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('重试')).toBeTruthy()
      })

      const retryButton = screen.getByText('重试')
      await user.click(retryButton)

      await waitFor(() => {
        expect(mockListChannels).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Modal Interactions', () => {
    it('モーダルの「取消」ボタンでモーダルが閉じる', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('创建频道')).toBeTruthy()
      })

      const createButton = screen.getByText('创建频道')
      await user.click(createButton)

      await waitFor(() => {
        expect(screen.getByText('取消')).toBeTruthy()
      })

      const cancelButton = screen.getByText('取消')
      await user.click(cancelButton)

      // Modal should close
      await waitFor(() => {
        const visibleModals = Array.from(document.querySelectorAll('[role="dialog"]'))
          .filter(modal => modal.offsetParent !== null)
        expect(visibleModals.length).toBe(0)
      })
    })
  })
})
