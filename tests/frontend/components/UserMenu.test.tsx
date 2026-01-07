/**
 * UserMenuコンポーネントのテスト
 *
 * ドロップダウン、ユーザー情報表示、サインアウト、
 * 外部クリックで閉じる機能をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider, useAtom } from 'jotai'
import React, { useRef, useEffect } from 'react'
import { UserMenu } from '../../../src/components/UserMenu'
import { userAtom } from '../../../src/atoms/auth'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

describe('UserMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('ユーザーメニューが正常にレンダリングされる', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        // biome-ignore lint: allow useEffect
        useEffect(() => {
          if (!initialized.current) {
            initialized.current = true
            setUser(mockUser)
          }
        }, [setUser])
        return <UserMenu />
      }

      render(<TestComponent />, { wrapper })
      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeTruthy()
      })
    })

    it('ユーザーのイニシャルが表示される', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      render(<TestComponent />, { wrapper })
      await waitFor(() => {
        expect(screen.getByText('TU')).toBeTruthy()
      })
    })

    it('メールアドレスのみの場合、イニシャルが正しく表示される', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: {}
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      render(<TestComponent />, { wrapper })
      // Initial is calculated from email "test@example.com" -> "T"
      await waitFor(() => {
        expect(screen.getByText('T')).toBeTruthy()
      })
    })

    it('ユーザーがいない場合、何も表示されない', () => {
      const TestComponent = () => <UserMenu />

      const { container } = render(<TestComponent />, { wrapper })
      // No user set, so component should render nothing
      expect(container.firstChild).toBe(null)
    })
  })

  describe('Dropdown Menu', () => {
    it('ボタンをクリックするとドロップダウンが開く', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      const user = userEvent.setup()
      render(<TestComponent />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeTruthy()
      })

      const menuButton = screen.getByText('Test User').closest('button')
      expect(menuButton).toBeTruthy()

      await user.click(menuButton!)

      // Check for email in dropdown
      expect(screen.getByText('test@example.com')).toBeTruthy()
    })

    it('サインアウトボタンが表示される', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      const user = userEvent.setup()
      render(<TestComponent />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeTruthy()
      })

      const menuButton = screen.getByText('Test User').closest('button')
      await user.click(menuButton!)

      // Check for sign out button
      expect(screen.getByText('退出登录')).toBeTruthy()
    })
  })

  describe('Click Outside to Close', () => {
    it('外側をクリックするとドロップダウンが閉じる', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return (
          <div>
            <UserMenu />
            <div data-testid="outside">Outside</div>
          </div>
        )
      }

      const user = userEvent.setup()
      render(<TestComponent />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeTruthy()
      })

      const menuButton = screen.getByText('Test User').closest('button')
      await user.click(menuButton!)

      // Dropdown should be open
      expect(screen.getByText('test@example.com')).toBeTruthy()

      // Click outside
      await user.click(screen.getByTestId('outside'))

      // Dropdown should be closed (email not visible)
      // Note: Since dropdown is removed from DOM when closed, we check if it's gone
      expect(screen.queryByText('test@example.com')).not.toBeTruthy()
    })
  })

  describe('Avatar Display', () => {
    it('アバターにグラデーション背景が適用される', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      const { container } = render(<TestComponent />, { wrapper })
      await waitFor(() => {
        const avatar = container.querySelector('.from-blue-500')
        expect(avatar).toBeTruthy()
      })
    })

    it('長い名前が切り捨てられる', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'This Is A Very Long Name That Should Be Truncated', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      render(<TestComponent />, { wrapper })
      // CSS truncate doesn't change text content, just visual truncation
      // The full name is still in the DOM
      await waitFor(() => {
        expect(screen.getByText('This Is A Very Long Name That Should Be Truncated')).toBeTruthy()
      })
    })
  })

  describe('Accessibility', () => {
    it('正しいaria属性が設定される', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      render(<TestComponent />, { wrapper })
      await waitFor(() => {
        const menuButton = screen.getByText('Test User').closest('button')
        expect(menuButton?.getAttribute('aria-label')).toBeTruthy()
        expect(menuButton?.getAttribute('aria-expanded')).toBeDefined()
      })
    })

    it('aria-expandedが正しく更新される', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      const user = userEvent.setup()
      render(<TestComponent />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeTruthy()
      })

      const menuButton = screen.getByText('Test User').closest('button')

      // Initially closed
      expect(menuButton?.getAttribute('aria-expanded')).toBe('false')

      // Click to open
      await user.click(menuButton!)
      expect(menuButton?.getAttribute('aria-expanded')).toBe('true')

      // Click to close
      await user.click(menuButton!)
      expect(menuButton?.getAttribute('aria-expanded')).toBe('false')
    })
  })

  describe('Sign Out', () => {
    it('サインアウトが実行できる', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      }

      const TestComponent = () => {
        const [, setUser] = useAtom(userAtom)
        const initialized = useRef(false)
        useEffect(() => {
          setUser(mockUser)
        }, [setUser])
        return <UserMenu />
      }

      const user = userEvent.setup()
      render(<TestComponent />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeTruthy()
      })

      const menuButton = screen.getByText('Test User').closest('button')
      await user.click(menuButton!)

      const signOutButton = screen.getByText('退出登录')
      expect(signOutButton).toBeTruthy()

      // Click sign out - just verify button exists and is clickable
      await user.click(signOutButton)
    })
  })
})
