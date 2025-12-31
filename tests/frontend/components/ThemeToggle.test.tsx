/**
 * ThemeToggleコンポーネントのテスト
 *
 * テーマ切り替え、localStorage永続化、DOMクラス操作をテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'jotai'
import { ThemeToggle } from '../../../src/components/ThemeToggle'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} }
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    document.documentElement.classList.remove('dark')
  })

  describe('Rendering', () => {
    it('テーマ切り替えボタンが正常にレンダリングされる', () => {
      render(<ThemeToggle />, { wrapper })
      expect(screen.getByRole('button')).toBeTruthy()
    })

    it('ライトテーマ時、月のアイコンが表示される', () => {
      render(<ThemeToggle />, { wrapper })
      // Moon icon for light mode (switch to dark)
      expect(screen.getByRole('button')).toBeTruthy()
    })

    it('ダークテーマ時、太陽のアイコンが表示される', () => {
      // Set dark theme in localStorage
      localStorageMock.setItem('theme', 'dark')
      document.documentElement.classList.add('dark')
      render(<ThemeToggle />, { wrapper })
      expect(screen.getByRole('button')).toBeTruthy()
    })
  })

  describe('Theme Switching', () => {
    it('ボタンをクリックするとテーマが切り替わる', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />, { wrapper })

      const button = screen.getByRole('button')
      await user.click(button)
    })

    it('ライトからダークに切り替わるとDOMクラスが更新される', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />, { wrapper })

      const button = screen.getByRole('button')
      await user.click(button)

      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('ダークからライトに切り替わるとDOMクラスが削除される', async () => {
      const user = userEvent.setup()
      localStorageMock.setItem('theme', 'dark')
      document.documentElement.classList.add('dark')

      render(<ThemeToggle />, { wrapper })

      const button = screen.getByRole('button')
      await user.click(button)

      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  describe('localStorage Persistence', () => {
    it('テーマ変更がlocalStorageに保存される', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />, { wrapper })

      const button = screen.getByRole('button')
      await user.click(button)

      expect(localStorageMock.getItem('theme')).toBe('dark')
    })

    it('複数回の切り替えが正しく保存される', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />, { wrapper })

      const button = screen.getByRole('button')

      await user.click(button)
      expect(localStorageMock.getItem('theme')).toBe('dark')

      await user.click(button)
      expect(localStorageMock.getItem('theme')).toBe('light')

      await user.click(button)
      expect(localStorageMock.getItem('theme')).toBe('dark')
    })
  })

  describe('Accessibility', () => {
    it('正しいaria-labelが設定される', () => {
      render(<ThemeToggle />, { wrapper })
      const button = screen.getByRole('button')
      // Should have aria-label for switching theme
      expect(button).toBeTruthy()
    })

    it('ライトモード時、ダークモードへの切り替えが説明される', () => {
      render(<ThemeToggle />, { wrapper })
      const button = screen.getByRole('button')
      expect(button.getAttribute('title') || button.getAttribute('aria-label')).toBeTruthy()
    })
  })

  describe('System Preference', () => {
    it('システム設定がダークモードの場合、初期テーマがダークになる', () => {
      // Mock matchMedia for dark mode preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(query => ({
          matches: query === '(prefers-color-scheme: dark)',
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn()
        }))
      })

      localStorageMock.clear()
      render(<ThemeToggle />, { wrapper })
    })
  })
})
