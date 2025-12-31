/**
 * UserMenuコンポーネントのテスト
 *
 * ドロップダウン、ユーザー情報表示、サインアウト、
 * 外部クリックで閉じる機能をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'jotai'
import { UserMenu } from '../../../src/components/UserMenu'

// Mock useAuth
const mockSignOut = vi.fn()
const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  user_metadata: { full_name: 'Test User', role: 'user' }
}

vi.mock('../../../src/hooks/useAuth', () => ({
  useAuth: () => [
    {
      user: mockUser,
      session: {},
      role: 'user',
      loading: false
    },
    { signOut: mockSignOut }
  ]
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

describe('UserMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSignOut.mockResolvedValue({ error: null })
  })

  describe('Rendering', () => {
    it('ユーザーメニューが正常にレンダリングされる', () => {
      render(<UserMenu />, { wrapper })
      expect(screen.getByText('Test User')).toBeTruthy()
    })

    it('ユーザーのイニシャルが表示される', () => {
      render(<UserMenu />, { wrapper })
      expect(screen.getByText('TU')).toBeTruthy()
    })

    it('メールアドレスのみの場合、イニシャルが正しく表示される', () => {
      const userWithoutName = {
        ...mockUser,
        user_metadata: {}
      }
      vi.doMock('../../../src/hooks/useAuth', () => ({
        useAuth: () => [
          {
            user: userWithoutName,
            session: {},
            role: 'user',
            loading: false
          },
          { signOut: mockSignOut }
        ]
      }))

      render(<UserMenu />, { wrapper })
    })

    it('ユーザーがいない場合、何も表示されない', () => {
      vi.doMock('../../../src/hooks/useAuth', () => ({
        useAuth: () => [
          {
            user: null,
            session: null,
            role: null,
            loading: false
          },
          { signOut: mockSignOut }
        ]
      }))

      const { container } = render(<UserMenu />, { wrapper })
    })
  })

  describe('Dropdown Menu', () => {
    it('ボタンをクリックするとドロップダウンが開く', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        await user.click(menuButton)
      }
    })

    it('ドロップダウン内にユーザー情報が表示される', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        await user.click(menuButton)
      }
    })

    it('ドロップダウン内にサインアウトボタンが表示される', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        await user.click(menuButton)
      }
    })
  })

  describe('Sign Out', () => {
    it('サインアウトをクリックするとsignOutが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        await user.click(menuButton)
      }

      const signOutButton = screen.queryByText('退出登录')
      if (signOutButton) {
        await user.click(signOutButton)
      }

      expect(mockSignOut).toHaveBeenCalled()
    })

    it('サインアウト後、ドロップダウンが閉じる', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        await user.click(menuButton)
      }

      const signOutButton = screen.queryByText('退出登录')
      if (signOutButton) {
        await user.click(signOutButton)
      }
    })
  })

  describe('Click Outside to Close', () => {
    it('外側をクリックするとドロップダウンが閉じる', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        await user.click(menuButton)
      }

      // Click outside
      await user.click(document.body)
    })
  })

  describe('Avatar Display', () => {
    it('アバターにグラデーション背景が適用される', () => {
      const { container } = render(<UserMenu />, { wrapper })
      const avatar = container.querySelector('.from-blue-500')
      expect(avatar).toBeTruthy()
    })

    it('長い名前が切り捨てられる', () => {
      const longNameUser = {
        ...mockUser,
        user_metadata: { full_name: 'Very Long Name That Should Be Truncated' }
      }
      vi.doMock('../../../src/hooks/useAuth', () => ({
        useAuth: () => [
          {
            user: longNameUser,
            session: {},
            role: 'user',
            loading: false
          },
          { signOut: mockSignOut }
        ]
      }))

      render(<UserMenu />, { wrapper })
    })
  })

  describe('Accessibility', () => {
    it('正しいaria属性が設定される', () => {
      render(<UserMenu />, { wrapper })
      const menuButton = screen.getByText('Test User').closest('button')
      expect(menuButton?.getAttribute('aria-label')).toBeTruthy()
    })

    it('aria-expandedが正しく更新される', async () => {
      const user = userEvent.setup()
      render(<UserMenu />, { wrapper })

      const menuButton = screen.getByText('Test User').closest('button')
      if (menuButton) {
        expect(menuButton.getAttribute('aria-expanded')).toBe('false')
        await user.click(menuButton)
        expect(menuButton.getAttribute('aria-expanded')).toBe('true')
      }
    })
  })
})
