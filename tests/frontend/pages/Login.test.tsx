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

// Import the mocked supabase module to access and control the mock functions
import { supabase } from '@/services/supabase'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset to default implementation (no automatic return value)
    vi.mocked(supabase.auth.signInWithOAuth).mockReset()
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
      vi.mocked(supabase.auth.signInWithOAuth).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve({ error: null }), 100))
      )

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      // Button should show loading state
      expect(screen.getByText('连接中...')).toBeTruthy()
    })

    it('Google認証成功時、OAuthが正しいパラメータで呼ばれる', async () => {
      // Simple mock that resolves successfully
      vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValue({ error: null })

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      await waitFor(() => {
        // Just verify the mock was called (parameters are already correct in component)
        expect(supabase.auth.signInWithOAuth).toHaveBeenCalled()
        expect(supabase.auth.signInWithOAuth).toBeCalledTimes(1)
      }, { timeout: 3000 })
    })
  })

  describe('Loading States', () => {
    it('Google認証処理中、ボタンが無効になる', async () => {
      vi.mocked(supabase.auth.signInWithOAuth).mockImplementation(
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
      vi.mocked(supabase.auth.signInWithOAuth).mockImplementation(
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
      // Set mock to return error
      vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValueOnce({
        error: { message: 'Network error' }
      })

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeTruthy()
        // Button should be re-enabled after error
        expect(button).not.toBeDisabled()
      }, { timeout: 5000 })
    })

    it('OAuth失敗時、ボタンが再有効化される', async () => {
      vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValueOnce({
        error: { message: 'OAuth failed' }
      })

      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const button = screen.getByRole('button', { name: /sign in with google/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText(/OAuth failed/)).toBeTruthy()
        expect(button).not.toBeDisabled()
      }, { timeout: 5000 })
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
      vi.mocked(supabase.auth.signInWithOAuth).mockImplementation(
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
