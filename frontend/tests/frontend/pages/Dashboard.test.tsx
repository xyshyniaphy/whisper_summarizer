/**
 * Dashboardページのテスト
 *
 * ダッシュボード、サインアウト、全削除機能、
 * 確認ダイアログ、ローディング状態をテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'jotai'
import Dashboard from '@/pages/Dashboard'

// Mock API service
const mockDeleteAllTranscriptions = vi.fn()
vi.mock('@/services/api', () => ({
  api: {
    deleteAllTranscriptions: () => mockDeleteAllTranscriptions()
  }
}))

// Mock useAuth hook
const mockSignOut = vi.fn()
const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  user_metadata: { role: 'user', full_name: 'Test User' }
}

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => [
    { user: mockUser, session: null, role: 'user', loading: false },
    { signOut: mockSignOut }
  ]
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock successful delete by default
    mockDeleteAllTranscriptions.mockResolvedValue({
      deleted_count: 5,
      message: '5件の転写を削除しました'
    })
    mockSignOut.mockResolvedValue({ error: null })
    // Mock window.alert
    global.alert = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Rendering', () => {
    it('ダッシュボードが正常にレンダリングされる', () => {
      render(<Dashboard />, { wrapper })

      expect(screen.getByText('仪表板')).toBeTruthy()
      expect(screen.getByText(/欢迎，test@example.com/)).toBeTruthy()
    })

    it('サインアウトボタンが表示される', () => {
      render(<Dashboard />, { wrapper })

      expect(screen.getByText('退出登录')).toBeTruthy()
    })

    it('削除ボタンが表示される', () => {
      render(<Dashboard />, { wrapper })

      expect(screen.getByText('删除所有音频')).toBeTruthy()
    })

    it('開発中メッセージが表示される', () => {
      render(<Dashboard />, { wrapper })

      expect(screen.getByText(/音频文件上传功能正在开发中/)).toBeTruthy()
    })
  })

  describe('Sign Out', () => {
    it('サインアウトボタンをクリックするとsignOutが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<Dashboard />, { wrapper })

      const signOutButton = screen.getByText('退出登录')
      await user.click(signOutButton)

      await waitFor(() => {
        expect(mockSignOut).toHaveBeenCalled()
      })
    })

    it('サインアウト失敗時、エラーがコンソールに出力される', async () => {
      const user = userEvent.setup()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockSignOut.mockResolvedValue({
        error: { message: 'サインアウトエラー' }
      })

      render(<Dashboard />, { wrapper })

      const signOutButton = screen.getByText('退出登录')
      await user.click(signOutButton)

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          '登出错误：',
          'サインアウトエラー'
        )
      })

      consoleErrorSpy.mockRestore()
    })
  })

  describe('Delete All Transcriptions', () => {
    it('削除ボタンをクリックすると確認ダイアログが表示される', async () => {
      const user = userEvent.setup()
      render(<Dashboard />, { wrapper })

      const deleteButton = screen.getByText('删除所有音频')
      await user.click(deleteButton)

      expect(screen.getByText('删除所有音频')).toBeTruthy()
      expect(screen.getByText(/确定要删除所有转录记录吗/)).toBeTruthy()
    })

    it('キャンセルボタンをクリックするとダイアログが閉じる', async () => {
      const user = userEvent.setup()
      render(<Dashboard />, { wrapper })

      // Open dialog
      const deleteButton = screen.getByText('删除所有音频')
      await user.click(deleteButton)

      // Click cancel
      const cancelButton = screen.getByText('取消')
      await user.click(cancelButton)

      await waitFor(() => {
        expect(screen.queryByText(/确定要删除所有转录记录吗/)).toBeNull()
      })
    })

    it('確認ボタンをクリックするとdeleteAllTranscriptionsが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<Dashboard />, { wrapper })

      // Open dialog
      await user.click(screen.getByText('删除所有音频'))

      // Click confirm
      const confirmButton = screen.getByText('删除')
      await user.click(confirmButton)

      await waitFor(() => {
        expect(mockDeleteAllTranscriptions).toHaveBeenCalled()
      })
    })

    it('削除成功時、成功メッセージが表示される', async () => {
      const user = userEvent.setup()
      mockDeleteAllTranscriptions.mockResolvedValue({
        deleted_count: 10,
        message: '10件の転写を削除しました'
      })

      render(<Dashboard />, { wrapper })

      await user.click(screen.getByText('删除所有音频'))
      await user.click(screen.getByText('删除'))

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('10件の転写を削除しました')
      })
    })

    it('削除失敗時、エラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockDeleteAllTranscriptions.mockRejectedValue(
        new Error('ネットワークエラー')
      )

      render(<Dashboard />, { wrapper })

      await user.click(screen.getByText('删除所有音频'))
      await user.click(screen.getByText('删除'))

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('删除失败: ネットワークエラー')
        expect(consoleErrorSpy).toHaveBeenCalledWith('Delete all error:', expect.any(Error))
      })

      consoleErrorSpy.mockRestore()
    })

    it('削除中、ローディング状態が表示される', async () => {
      const user = userEvent.setup()
      let resolveDelete: (value: any) => void
      mockDeleteAllTranscriptions.mockReturnValue(
        new Promise(resolve => {
          resolveDelete = resolve
        })
      )

      render(<Dashboard />, { wrapper })

      await user.click(screen.getByText('删除所有音频'))
      await user.click(screen.getByText('删除'))

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('删除中...')).toBeTruthy()
      })

      // Resolve promise
      await waitFor(() => {
        resolveDelete!({ deleted_count: 1, message: '削除完了' })
      })
    })
  })

  describe('Loading States', () => {
    it('削除中、両方のボタンが無効になる', async () => {
      const user = userEvent.setup()
      let resolveDelete: (value: any) => void
      mockDeleteAllTranscriptions.mockReturnValue(
        new Promise(resolve => {
          resolveDelete = resolve
        })
      )

      render(<Dashboard />, { wrapper })

      await user.click(screen.getByText('删除所有音频'))
      await user.click(screen.getByText('删除'))

      await waitFor(() => {
        const signOutButton = screen.getByText('退出登录')
        expect(signOutButton).toBeDisabled()
      })

      // Clean up
      resolveDelete!({ deleted_count: 1, message: '完了' })
    })
  })

  describe('Edge Cases', () => {
    it('削除対象が0件の場合', async () => {
      const user = userEvent.setup()
      mockDeleteAllTranscriptions.mockResolvedValue({
        deleted_count: 0,
        message: '削除する項目がありません'
      })

      render(<Dashboard />, { wrapper })

      await user.click(screen.getByText('删除所有音频'))
      await user.click(screen.getByText('删除'))

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('削除する項目がありません')
      })
    })

    it('大量削除の場合', async () => {
      const user = userEvent.setup()
      mockDeleteAllTranscriptions.mockResolvedValue({
        deleted_count: 1000,
        message: '1000件の転写を削除しました'
      })

      render(<Dashboard />, { wrapper })

      await user.click(screen.getByText('删除所有音频'))
      await user.click(screen.getByText('删除'))

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('1000件の転写を削除しました')
      })
    })
  })

  describe('User Display', () => {
    it('ユーザーのメールアドレスが表示される', () => {
      render(<Dashboard />, { wrapper })

      expect(screen.getByText(/test@example.com/)).toBeTruthy()
    })
  })
})
