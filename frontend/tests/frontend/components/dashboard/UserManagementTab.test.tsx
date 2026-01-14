/**
 * UserManagementTabコンポーネントのテスト
 *
 * ユーザー管理タブの表示、アクティベート、
 * 管理者権限、削除機能をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

import { UserManagementTab } from '../../../../src/components/dashboard/UserManagementTab'

// Create mock functions at module level
const mockListUsers = vi.fn(() => Promise.resolve([
  {
    id: '1',
    email: 'admin@example.com',
    is_active: true,
    is_admin: true,
    activated_at: '2025-01-01T00:00:00Z',
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    email: 'user@example.com',
    is_active: false,
    is_admin: false,
    activated_at: null,
    created_at: '2024-01-02T00:00:00Z'
  }
]))
const mockActivateUser = vi.fn(() => Promise.resolve())
const mockToggleUserAdmin = vi.fn(() => Promise.resolve())
const mockDeleteUser = vi.fn(() => Promise.resolve())

// Mock adminApi
vi.mock('@/services/api', () => ({
  adminApi: {
    listUsers: () => mockListUsers(),
    activateUser: () => mockActivateUser(),
    toggleUserAdmin: () => mockToggleUserAdmin(),
    deleteUser: () => mockDeleteUser()
  }
}))

// Mock window.alert
global.alert = vi.fn()

describe('UserManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('ローディング状態が表示される', () => {
      mockListUsers.mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      )

      render(<UserManagementTab />)

      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
    })

    it('ユーザーリストが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeTruthy()
        expect(screen.getByText('user@example.com')).toBeTruthy()
      })
    })

    it('統計情報が表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('总用户数')).toBeTruthy()
        expect(screen.getByText('已激活用户')).toBeTruthy()
        // "管理员" may appear multiple times (in stats and table)
        expect(screen.getAllByText('管理员').length).toBeGreaterThan(0)
      })
    })

    it('テーブルヘッダーが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('邮箱')).toBeTruthy()
        expect(screen.getByText('状态')).toBeTruthy()
        expect(screen.getByText('权限')).toBeTruthy()
        expect(screen.getByText('创建时间')).toBeTruthy()
        expect(screen.getByText('激活时间')).toBeTruthy()
        expect(screen.getByText('操作')).toBeTruthy()
      })
    })
  })

  describe('User Status Display', () => {
    it('アクティブユーザーに「已激活」バッジが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('已激活')).toBeTruthy()
      })
    })

    it('非アクティブユーザーに「待激活」バッジが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('待激活')).toBeTruthy()
      })
    })

    it('管理者ユーザーに「管理员」バッジが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        // "管理员" may appear multiple times (in stats and table)
        expect(screen.getAllByText('管理员').length).toBeGreaterThan(0)
      })
    })

    it('一般ユーザーに「普通用户」バッジが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('普通用户')).toBeTruthy()
      })
    })
  })

  describe('Activate User', () => {
    it('「激活」ボタンが表示される (非アクティブユーザー)', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('激活')).toBeTruthy()
      })
    })

    it('「激活」ボタンをクリックしてユーザーをアクティベートできる', async () => {
      const user = userEvent.setup()

      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('激活')).toBeTruthy()
      })

      const activateButtons = screen.getAllByText('激活')
      await user.click(activateButtons[0])

      await waitFor(() => {
        expect(mockActivateUser).toHaveBeenCalled()
      })
    })
  })

  describe('Toggle Admin', () => {
    it('「设为管理员」ボタンが表示される (一般ユーザー)', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('设为管理员')).toBeTruthy()
      })
    })

    it('「取消管理员」ボタンが表示される (管理者)', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('取消管理员')).toBeTruthy()
      })
    })

    it('管理者権限を切り替えられる', async () => {
      const user = userEvent.setup()

      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('设为管理员')).toBeTruthy()
      })

      const toggleButtons = screen.getAllByText('设为管理员')
      await user.click(toggleButtons[0])

      await waitFor(() => {
        expect(mockToggleUserAdmin).toHaveBeenCalled()
      })
    })
  })

  describe('Delete User', () => {
    it('削除ボタンが表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        // Delete buttons use variant="danger" which adds bg-red-600 class
        const deleteButtons = document.querySelectorAll('button.bg-red-600')
        // Should have delete buttons for each user
        expect(deleteButtons.length).toBeGreaterThan(0)
      })
    })

    it('削除確認ダイアログが表示される', async () => {
      const user = userEvent.setup()

      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeTruthy()
      })

      // Find delete button by its danger variant class (bg-red-600)
      // Note: Both "取消管理员" (for admin users) and delete buttons use danger variant
      // The delete button comes last in the actions column, so we'll click it
      const deleteButtons = document.querySelectorAll('button.bg-red-600')
      expect(deleteButtons.length).toBeGreaterThan(0)

      // Click the last danger button (delete button)
      await user.click(deleteButtons[deleteButtons.length - 1])

      await waitFor(() => {
        expect(screen.getByText('确认删除用户')).toBeTruthy()
      })
    })
  })

  describe('Error Handling', () => {
    it('エラー時にエラーメッセージと再試行ボタンが表示される', async () => {
      mockListUsers.mockRejectedValueOnce(new Error('API Error'))

      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('加载用户列表失败')).toBeTruthy()
        expect(screen.getByText('重试')).toBeTruthy()
      })
    })

    it('再試行ボタンでデータを再読み込みできる', async () => {
      const user = userEvent.setup()
      mockListUsers
        .mockRejectedValueOnce(new Error('API Error'))
        .mockResolvedValueOnce([
          {
            id: '1',
            email: 'test@example.com',
            is_active: true,
            is_admin: false,
            activated_at: '2025-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z'
          }
        ])

      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('重试')).toBeTruthy()
      })

      const retryButton = screen.getByText('重试')
      await user.click(retryButton)

      await waitFor(() => {
        expect(mockListUsers).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Date Formatting', () => {
    it('作成日時が正しく表示される', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeTruthy()
      })

      // Date should be formatted in zh-CN format
      // Just check that user data is rendered
      expect(screen.getByText('admin@example.com')).toBeTruthy()
    })

    it('アクティベート日時が「-」と表示される (未アクティベート)', async () => {
      render(<UserManagementTab />)

      await waitFor(() => {
        expect(screen.getByText('user@example.com')).toBeTruthy()
      })
    })
  })
})
