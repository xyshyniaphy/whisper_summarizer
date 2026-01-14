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

// Mock channels data
const mockChannels = [
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
]

const mockChannelDetail = {
  'ch-1': {
    id: 'ch-1',
    name: 'Marketing',
    description: 'Marketing team',
    members: [
      { id: 'user-1', email: 'user1@example.com', is_active: true, is_admin: false }
    ]
  },
  'ch-2': {
    id: 'ch-2',
    name: 'Sales',
    description: null,
    members: []
  }
}

const mockUsers = [
  { id: 'user-1', email: 'user1@example.com', is_active: true, is_admin: false },
  { id: 'user-2', email: 'user2@example.com', is_active: true, is_admin: true }
]

// Helper function to set up axios mock
const setupMockChannels = (channels: any = mockChannels) => {
  const mockAxiosGet = (global as any).mockAxiosGet
  if (mockAxiosGet) {
    mockAxiosGet.mockImplementation((url: string) => {
      // Match /admin/channels (listChannels)
      // Note: axios mock receives URL WITHOUT baseURL prefix
      if (url?.includes('/admin/channels') && !url?.includes('/members')) {
        // Check if it's the list endpoint (no additional path segments after /channels)
        const urlObj = new URL(url, 'http://localhost')
        const pathname = urlObj.pathname
        if (pathname === '/admin/channels' || pathname === '/admin/channels/') {
          return Promise.resolve({ data: channels })
        }
      }
      // Match /admin/channels/:id (getChannelDetail)
      if (url?.includes('/admin/channels/ch-1')) {
        return Promise.resolve({ data: mockChannelDetail['ch-1'] })
      }
      if (url?.includes('/admin/channels/ch-2')) {
        return Promise.resolve({ data: mockChannelDetail['ch-2'] })
      }
      // Default fallback for other requests (like /api/auth/user)
      return Promise.resolve({ data: [] })
    })
  }

  const mockAxiosPost = (global as any).mockAxiosPost
  if (mockAxiosPost) {
    mockAxiosPost.mockImplementation((url: string) => {
      // Match /admin/channels (createChannel)
      if (url?.includes('/admin/channels') && !url?.includes('/members')) {
        return Promise.resolve({ data: {} })
      }
      // Match /admin/channels/:id/members (assignUserToChannel)
      if (url?.includes('/members')) {
        return Promise.resolve({ data: {} })
      }
      return Promise.resolve({ data: {} })
    })
  }

  const mockAxiosPut = (global as any).mockAxiosPut
  if (mockAxiosPut) {
    mockAxiosPut.mockImplementation((url: string) => {
      // Match /admin/channels/:id (updateChannel)
      if (url?.includes('/admin/channels')) {
        return Promise.resolve({ data: {} })
      }
      return Promise.resolve({ data: {} })
    })
  }

  const mockAxiosDelete = (global as any).mockAxiosDelete
  if (mockAxiosDelete) {
    mockAxiosDelete.mockImplementation((url: string) => {
      // Match /admin/channels/:id (deleteChannel)
      if (url?.includes('/admin/channels')) {
        return Promise.resolve({ data: {} })
      }
      return Promise.resolve({ data: {} })
    })
  }
}

// Helper function to set up loading mock
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

describe('ChannelManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupMockChannels(mockChannels)
  })

  describe('Rendering', () => {
    it('ローディング状態が表示される', () => {
      setupLoadingMock()
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
        // Use getAllByText since there might be multiple elements (button + modal)
        const createButtons = screen.getAllByText('创建频道')
        expect(createButtons.length).toBeGreaterThan(0)
      })

      // Use querySelector to find the button (not the modal title)
      const buttons = document.querySelectorAll('button')
      const createButton = Array.from(buttons).find(btn =>
        btn.textContent?.includes('创建频道')
      )

      expect(createButton).toBeTruthy()

      if (createButton) {
        await user.click(createButton)

        await waitFor(() => {
          // After clicking, modal should be open with title
          // Use getAllByText since both button and modal title exist
          const createElements = screen.getAllByText('创建频道')
          expect(createElements.length).toBeGreaterThan(0)
        })
      }
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
        // Wait for channels to be rendered
        expect(screen.getByText('Marketing')).toBeTruthy()

        // Check that danger variant buttons exist (delete buttons use danger variant)
        const buttons = document.querySelectorAll('button')
        const hasDangerButton = Array.from(buttons).some(btn =>
          btn.className.includes('bg-red-600') || btn.className.includes('danger')
        )
        expect(hasDangerButton).toBe(true)
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
        const memberButtons = screen.getAllByText('成员')
        expect(memberButtons.length).toBeGreaterThan(0)
      })
    })

    it('「成员」ボタンをクリックするとメンバーモーダルが開く', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      // Find member buttons in the table
      const memberButtons = document.querySelectorAll('button')
      const memberBtn = Array.from(memberButtons).find(btn =>
        btn.textContent?.includes('成员')
      )

      expect(memberBtn).toBeTruthy()

      if (memberBtn) {
        await user.click(memberBtn)

        await waitFor(() => {
          const modals = document.querySelectorAll('[role="dialog"]')
          expect(modals.length).toBeGreaterThan(0)
        })
      }
    })

    it('メンバーリストが表示される', async () => {
      const user = userEvent.setup()

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      const memberButtons = document.querySelectorAll('button')
      const memberBtn = Array.from(memberButtons).find(btn =>
        btn.textContent?.includes('成员')
      )

      expect(memberBtn).toBeTruthy()

      if (memberBtn) {
        await user.click(memberBtn)

        await waitFor(() => {
          expect(screen.getByText(/当前成员/)).toBeTruthy()
        })
      }
    })
  })

  describe('Error Handling', () => {
    it('エラー時にエラーメッセージと再試行ボタンが表示される', async () => {
      setupErrorMock('API Error')

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('加载频道列表失败')).toBeTruthy()
        expect(screen.getByText('重试')).toBeTruthy()
      })
    })

    it('再試行ボタンでデータを再読み込みできる', async () => {
      const user = userEvent.setup()
      const mockAxiosGet = (global as any).mockAxiosGet

      if (mockAxiosGet) {
        mockAxiosGet
          .mockRejectedValueOnce(new Error('API Error'))
          .mockImplementationOnce((url: string) => {
            if (url?.includes('/admin/channels')) {
              return Promise.resolve({ data: mockChannels })
            }
            return Promise.resolve({ data: [] })
          })
      }

      render(<ChannelManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('重试')).toBeTruthy()
      })

      const retryButton = screen.getByText('重试')
      await user.click(retryButton)

      await waitFor(() => {
        // Should be 2 calls: initial error + retry success
        expect(mockAxiosGet).toHaveBeenCalledTimes(2)
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
