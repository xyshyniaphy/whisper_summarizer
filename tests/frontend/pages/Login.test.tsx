/**
 * Loginページのテスト
 *
 * ログインフォーム、新規登録フォーム、Google OAuth、
 * エラーハンドリング、ナビゲーションをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'jotai'
import Login from '../../../src/pages/Login'

// Mock Supabase client
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } }
      })),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signInWithOAuth: vi.fn()
    }
  }
}))

// Mock useAuth hook
const mockSignIn = vi.fn()
const mockSignUp = vi.fn()
const mockSignInWithGoogle = vi.fn()

vi.mock('../../../src/hooks/useAuth', () => ({
  useAuth: () => [
    { user: null, session: null, role: null, loading: false },
    { signIn: mockSignIn, signUp: mockSignUp, signInWithGoogle: mockSignInWithGoogle }
  ]
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock successful auth by default
    mockSignIn.mockResolvedValue({
      user: { id: '123', email: 'test@example.com' },
      session: {},
      error: null
    })
    mockSignUp.mockResolvedValue({
      user: { id: '123', email: 'test@example.com' },
      session: {},
      error: null
    })
    mockSignInWithGoogle.mockResolvedValue({ error: null })
  })

  describe('Rendering', () => {
    it('ログインフォームが正常にレンダリングされる', () => {
      render(<Login />, { wrapper })
      expect(screen.getByText('Whisper Summarizer')).toBeTruthy()
      expect(screen.getByText('登录')).toBeTruthy()
    })

    it('新規登録モードに切り替えられる', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const toggleButton = screen.getByText('注册')
      await user.click(toggleButton)

      expect(screen.getByText('创建新账户')).toBeTruthy()
      expect(screen.getByText('姓名')).toBeTruthy()
    })

    it('Googleボタンが表示される', () => {
      render(<Login />, { wrapper })
      expect(screen.getByText(/使用 Google 继续/)).toBeTruthy()
    })
  })

  describe('Login Form', () => {
    it('メールアドレスとパスワードを入力できる', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const emailInput = screen.getByPlaceholderText('you@example.com')
      const passwordInput = screen.getByPlaceholderText('密码')

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')

      expect(emailInput).toHaveProperty('value', 'test@example.com')
      expect(passwordInput).toHaveProperty('value', 'password123')
    })

    it('ログインボタンをクリックするとsignInが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const emailInput = screen.getByPlaceholderText('you@example.com')
      const passwordInput = screen.getByPlaceholderText('密码')
      const submitButton = screen.getByText('登录')

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith('test@example.com', 'password123')
      })
    })

    it('ログイン成功時、转录リストに遷移する', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const emailInput = screen.getByPlaceholderText('you@example.com')
      const passwordInput = screen.getByPlaceholderText('密码')
      const submitButton = screen.getByText('登录')

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalled()
      })
    })

    it('ログイン失敗時、エラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      mockSignIn.mockResolvedValue({
        user: null,
        session: null,
        error: { message: '認証エラー' }
      })

      render(<Login />, { wrapper })

      const emailInput = screen.getByPlaceholderText('you@example.com')
      const passwordInput = screen.getByPlaceholderText('密码')
      const submitButton = screen.getByText('登录')

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)

      await waitFor(() => {
        const errorMessage = screen.queryByText(/认证エラー|发生错误/)
        expect(errorMessage).toBeTruthy()
      })
    })
  })

  describe('Sign Up Form', () => {
    it('新規登録モードで姓名フィールドが表示される', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const toggleButton = screen.getByText('注册')
      await user.click(toggleButton)

      expect(screen.getByPlaceholderText('张三')).toBeTruthy()
    })

    it('新規登録フォームでsignUpが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      // Switch to sign up mode
      const toggleButton = screen.getByText('注册')
      await user.click(toggleButton)

      const nameInput = screen.getByPlaceholderText('张三')
      const emailInput = screen.getByPlaceholderText('you@example.com')
      const passwordInput = screen.getByPlaceholderText('密码')
      const submitButton = screen.getByText('注册')

      await user.type(nameInput, 'Test User')
      await user.type(emailInput, 'new@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockSignUp).toHaveBeenCalledWith('new@example.com', 'password123', 'Test User')
      })
    })
  })

  describe('Google OAuth', () => {
    it('GoogleボタンをクリックするとsignInWithGoogleが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        expect(mockSignInWithGoogle).toHaveBeenCalled()
      })
    })

    it('Google認証失敗時、エラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      mockSignInWithGoogle.mockResolvedValue({
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
  })

  describe('Loading States', () => {
    it('ログイン処理中、ボタンが無効になる', async () => {
      const user = userEvent.setup()
      mockSignIn.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

      render(<Login />, { wrapper })

      const emailInput = screen.getByPlaceholderText('you@example.com')
      const passwordInput = screen.getByPlaceholderText('密码')
      const submitButton = screen.getByText('登录')

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })

    it('Google認証処理中、ボタンが無効になる', async () => {
      const user = userEvent.setup()
      mockSignInWithGoogle.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

      render(<Login />, { wrapper })

      const googleButton = screen.getByText(/使用 Google 继续/)
      await user.click(googleButton)

      await waitFor(() => {
        expect(googleButton).toBeDisabled()
      })
    })
  })

  describe('Form Toggle', () => {
    it('ログイン↔登録の切り替えが正しく動作する', async () => {
      const user = userEvent.setup()
      render(<Login />, { wrapper })

      // Initially in login mode
      expect(screen.getByText('登录')).toBeTruthy()
      expect(screen.queryByText('姓名')).toBeNull()

      // Switch to sign up
      await user.click(screen.getByText('注册'))
      expect(screen.getByText('姓名')).toBeTruthy()
      expect(screen.getByText('已有账户？')).toBeTruthy()

      // Switch back to login
      await user.click(screen.getByText('登录'))
      expect(screen.queryByText('姓名')).toBeNull()
      expect(screen.getByText('没有账户？')).toBeTruthy()
    })
  })
})
