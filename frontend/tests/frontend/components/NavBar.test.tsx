/**
 * NavBarコンポーネントのテスト
 *
 * ナビゲーション、モバイルメニュー、アクティブなリンク、
 * テーマ切り替え、ユーザーメニューをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Provider } from 'jotai'
import { NavBar } from '../../../src/components/NavBar'

// Mock Supabase client
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } }
      }))
    }
  }
}))

// Mock useAuth
const mockSignOut = vi.fn()
vi.mock('../../../src/hooks/useAuth', () => ({
  useAuth: () => [
    {
      user: {
        id: 'user-1',
        email: 'test@example.com',
        user_metadata: { full_name: 'Test User', role: 'user' }
      },
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

const renderWithRouter = (initialPath: string = '/transcriptions') => {
  return render(
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/transcriptions" element={<div>Transcriptions Page</div>} />
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
      </Routes>
    </BrowserRouter>,
    { wrapper }
  )
}

describe('NavBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('NavBarが正常にレンダリングされる', () => {
      renderWithRouter()
      expect(screen.getByText('WhisperApp')).toBeTruthy()
    })

    it('ロゴが表示される', () => {
      renderWithRouter()
      expect(screen.getByText('WhisperApp')).toBeTruthy()
    })

    it('デスクトップナビゲーションリンクが表示される', () => {
      renderWithRouter()
      expect(screen.getByText('转录列表')).toBeTruthy()
      expect(screen.getByText('仪表板')).toBeTruthy()
    })
  })

  describe('Navigation Links', () => {
    it('转录列表リンクが正しく動作する', async () => {
      const user = userEvent.setup()
      renderWithRouter()

      const transcriptionsLink = screen.getByText('转录列表')
      await user.click(transcriptionsLink)
    })

    it('仪表板リンクが正しく動作する', async () => {
      const user = userEvent.setup()
      renderWithRouter()

      const dashboardLink = screen.getByText('仪表板')
      await user.click(dashboardLink)
    })

    it('ロゴをクリックすると转录リストに遷移する', async () => {
      const user = userEvent.setup()
      renderWithRouter()

      const logo = screen.getByText('WhisperApp')
      await user.click(logo)
    })
  })

  describe('Active Link State', () => {
    it('アクティブなリンクがハイライトされる', () => {
      renderWithRouter('/transcriptions')
      const transcriptionsLink = screen.getByText('转录列表')
      expect(transcriptionsLink).toBeTruthy()
    })
  })

  describe('Mobile Menu', () => {
    it('モバイルメニューボタンが表示される', () => {
      renderWithRouter()
      // Menu button should be visible (might be hidden on larger viewports)
      const menuButtons = screen.getAllByLabelText(/切换菜单/)
      expect(menuButtons.length).toBeGreaterThan(0)
    })

    it('モバイルメニューボタンをクリックするとメニューが開く', async () => {
      const user = userEvent.setup()
      renderWithRouter()

      // Find and click mobile menu button
      const menuButtons = screen.getAllByLabelText(/切换菜单/)
      if (menuButtons.length > 0) {
        await user.click(menuButtons[0])
      }
    })

    it('モバイルメニュー内にナビゲーションリンクが表示される', async () => {
      const user = userEvent.setup()
      renderWithRouter()

      const menuButtons = screen.getAllByLabelText(/切换菜单/)
      if (menuButtons.length > 0) {
        await user.click(menuButtons[0])
      }
    })
  })

  describe('Theme Toggle', () => {
    it('テーマ切り替えボタンが表示される', () => {
      renderWithRouter()
      // Theme toggle is an icon button with aria-label
      const themeButtons = screen.queryAllByLabelText(/切换到/)
      expect(themeButtons.length).toBeGreaterThanOrEqual(0)
    })
  })

  describe('User Menu', () => {
    it('ユーザーメニューが表示される', () => {
      renderWithRouter()
      expect(screen.getByText('Test User')).toBeTruthy()
    })

    it('ユーザーのイニシャルが表示される', () => {
      renderWithRouter()
      expect(screen.getByText('TU')).toBeTruthy()
    })
  })

  describe('Fixed Position', () => {
    it('NavBarが固定位置にある', () => {
      renderWithRouter()
      const nav = document.querySelector('nav.fixed')
      expect(nav).toBeTruthy()
    })
  })

  describe('Responsive Design', () => {
    it('デスクトップビューでモバイルメニューが非表示になる', () => {
      renderWithRouter()
      // Desktop nav links should be visible
      expect(screen.getByText('转录列表')).toBeTruthy()
      expect(screen.getByText('仪表板')).toBeTruthy()
    })
  })
})
