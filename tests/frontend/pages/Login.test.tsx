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
import React from 'react'
import Login from '../../../src/pages/Login'

// Mock Supabase client
const mockSignInWithOAuth = vi.fn()

vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      signInWithOAuth: mockSignInWithOAuth
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

      expect(screen.queryByText(/登录失败/)).not.toBeTruthy()
    })

    it('Googleボタンにaria-labelがある', () => {
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      expect(button).toBeTruthy()
    })
  })

  describe('UI Components', () => {
    it('ページが中央揃えで正しいスタイリングが適用される', () => {
      const { container } = render(<Login />, { wrapper })

      // Check for min-h-screen with flex (centering container)
      const centerContainer = container.querySelector('.min-h-screen')
      expect(centerContainer).toBeTruthy()
      expect(centerContainer?.className).toContain('flex')
      expect(centerContainer?.className).toContain('items-center')
      expect(centerContainer?.className).toContain('justify-center')

      // Check for max-w-md container
      const contentContainer = container.querySelector('.max-w-md')
      expect(contentContainer).toBeTruthy()
    })
  })

  describe('Google OAuth', () => {
    it('GoogleボタンをクリックするとOAuth処理が開始される', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      // Button should show loading state
      expect(screen.getByText('连接中...')).toBeTruthy()
    })

    it('Google認証成功時、OAuthが正しいパラメータで呼ばれる', async () => {
      mockSignInWithOAuth.mockResolvedValue({ error: null })

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

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
  })

  describe('Loading States', () => {
    it('Google認証処理中、ボタンが無効になる', async () => {
      mockSignInWithOAuth.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ error: null }), 1000))
      )

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      // Button should be disabled during loading
      expect(button).toBeDisabled()
      expect(screen.getByText('连接中...')).toBeTruthy()
    })

    it('読み込み中、ローディングテキストが表示される', async () => {
      mockSignInWithOAuth.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ error: null }), 100))
      )

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      expect(screen.getByText('连接中...')).toBeTruthy()
    })
  })

  describe('Error Handling', () => {
    it('ネットワークエラー時、エラーメッセージが表示される', async () => {
      mockSignInWithOAuth.mockResolvedValue({
        error: { message: 'Network error' }
      })

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeTruthy()
      })
    })

    it('OAuth失敗時、ボタンが再有効化される', async () => {
      mockSignInWithOAuth.mockResolvedValue({
        error: { message: 'OAuth failed' }
      })

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText(/OAuth failed/)).toBeTruthy()
        expect(button).not.toBeDisabled()
      })
    })
  })

  describe('Accessibility', () => {
    it('Googleボタンに適切なaria-labelが設定される', () => {
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      expect(button).toBeTruthy()
      expect(button).toHaveAttribute('aria-label', 'Sign in with Google')
    })

    it('読み込み中、aria-labelが保持される', async () => {
      mockSignInWithOAuth.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ error: null }), 100))
      )

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      expect(button).toHaveAttribute('aria-label', 'Sign in with Google')
    })
  })
})
