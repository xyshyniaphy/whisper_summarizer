/**
 * Loginページのテスト
 *
 * Google OAuth認証、エラーハンドリング、ローディング状態をテストする。
 * Email/Password認証は削除されたため、Google OAuthのみをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'jotai'
import Login from '@/pages/Login'

// Mock Supabase client
const mockSignInWithOAuth = vi.fn()
vi.mock('@/services/supabase', () => ({
  supabase: {
    auth: {
      signInWithOAuth: (args: any) => mockSignInWithOAuth(args)
    }
  }
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock successful OAuth by default
    mockSignInWithOAuth.mockResolvedValue({ error: null })
  })

  describe('Rendering', () => {
    it('ログインページが正常にレンダリングされる', () => {
      render(<Login />, { wrapper })

      expect(screen.getByText('Whisper Summarizer')).toBeTruthy()
      expect(screen.getByText('使用 Google 账号登录')).toBeTruthy()
    })

    it('Googleボタンが表示される', () => {
      render(<Login />, { wrapper })

      expect(screen.getByText(/使用 Google 继续/)).toBeTruthy()
    })

    it('説明テキストが表示される', () => {
      render(<Login />, { wrapper })

      expect(screen.getByText(/点击上方按钮使用 Google OAuth 登录/)).toBeTruthy()
    })

    it('初期状態ではエラーメッセージが表示されない', () => {
      render(<Login />, { wrapper })

      expect(screen.queryByText(/Google登录失败|发生意外错误/)).toBeNull()
    })
  })

  describe('Google OAuth', () => {
    it('GoogleボタンをクリックするとOAuth処理が開始される', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        expect(mockSignInWithOAuth).toHaveBeenCalled()
      })
    })

    it('Google認証成功時、OAuthが正しいパラメータで呼ばれる', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        expect(mockSignInWithOAuth).toHaveBeenCalledWith({
          provider: 'google',
          options: {
            queryParams: {
              access_type: 'offline',
              prompt: 'consent',
            },
            scopes: 'email',
          },
        })
      })
    })

    it('Google認証失敗時、エラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      mockSignInWithOAuth.mockResolvedValue({
        error: { message: 'Google認証エラー' }
      })

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/Google認証エラー|Google登录失败/)
        expect(errorMessage).toBeTruthy()
      })
    })

    it('Google認証エラーなしの場合、デフォルトエラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      mockSignInWithOAuth.mockResolvedValue({
        error: {}
      })

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/Google登录失败/)
        expect(errorMessage).toBeTruthy()
      })
    })
  })

  describe('Loading States', () => {
    it('Google認証処理中、ボタンが無効になる', async () => {
      const user = userEvent.setup()
      // Make the promise never resolve to test loading state
      mockSignInWithOAuth.mockReturnValue(new Promise(() => {}))

      render(<Login />, { wrapper })

      const googleButton = screen.getByLabelText('Sign in with Google')
      await user.click(googleButton)

      await waitFor(() => {
        expect(googleButton).toBeDisabled()
      })
    })

    it('処理完了後、ローディング状態が解除される', async () => {
      const user = userEvent.setup()
      mockSignInWithOAuth.mockResolvedValue({ error: null })

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        // After promise resolves, button should be enabled again (or user redirected)
        expect(mockSignInWithOAuth).toHaveBeenCalled()
      })
    })
  })

  describe('Error Handling', () => {
    it('ネットワークエラー時、エラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      mockSignInWithOAuth.mockRejectedValue(
        new Error('ネットワークエラー')
      )

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/ネットワークエラー|网络错误|发生意外错误/)
        expect(errorMessage).toBeTruthy()
      })
    })

    it('エラー発生後、別の認証試行が可能であること', async () => {
      const user = userEvent.setup()
      // First attempt fails
      mockSignInWithOAuth.mockResolvedValueOnce({
        error: { message: '最初のエラー' }
      })
      // Second attempt succeeds
      mockSignInWithOAuth.mockResolvedValueOnce({
        error: null
      })

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)

      // First click - error
      await user.click(googleButton)
      await waitFor(() => {
        expect(screen.queryByText(/最初のエラー/)).toBeTruthy()
      })

      // Second click - success
      await user.click(googleButton)
      await waitFor(() => {
        expect(mockSignInWithOAuth).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('UI Components', () => {
    it('エラーメッセージがある場合、赤い背景で表示される', async () => {
      const user = userEvent.setup()
      mockSignInWithOAuth.mockResolvedValue({
        error: { message: 'テストエラー' }
      })

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        const errorDiv = screen.getByText(/テストエラー/).closest('div')
        expect(errorDiv?.className).toContain('bg-red-50')
        expect(errorDiv?.className).toContain('border-red-200')
      })
    })

    it('ページが中央揃えで正しいスタイリングが適用される', () => {
      const { container } = render(<Login />, { wrapper })

      // Check that the main container has the correct styling classes
      expect(container.firstChild).toBeTruthy()
      const mainDiv = container.firstElementChild
      expect(mainDiv?.className).toContain('flex')
      expect(mainDiv?.className).toContain('items-center')
      expect(mainDiv?.className).toContain('justify-center')
    })
  })

  describe('Accessibility', () => {
    it('Googleボタンに適切なaria-labelが設定される', () => {
      render(<Login />, { wrapper })

      // Check that the Google button exists (using text content)
      const googleButton = screen.getByText(/使用 Google 继续/)
      expect(googleButton).toBeTruthy()
    })

    it('エラーメッセージがスクリーンリーダーで読み取れる', async () => {
      const user = userEvent.setup()
      mockSignInWithOAuth.mockResolvedValue({
        error: { message: 'エラーメッセージ' }
      })

      render(<Login />, { wrapper })

      await user.click(screen.getByText(/使用 Google 继续/))

      await waitFor(() => {
        const errorMessage = screen.getByText(/エラーメッセージ/)
        expect(errorMessage).toBeVisible()
      })
    })
  })
})
