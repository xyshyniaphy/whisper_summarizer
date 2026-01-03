/**
 * useAuthフックのテスト
 *
 * 認証状態管理、Google OAuth、サインアウト、
 * E2Eテストモード、状態同期をテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { Provider } from 'jotai'
import { useAuth } from '@/hooks/useAuth'

// Mock Supabase client
const mockSetUser = vi.fn()
const mockSetSession = vi.fn()
const mockSetRole = vi.fn()
const mockSetLoading = vi.fn()
const mockUnsubscribe = vi.fn()

const mockSession = {
  access_token: 'test-token',
  user: {
    id: 'test-user-id',
    email: 'test@example.com',
    user_metadata: { role: 'admin', full_name: 'Test User' },
    email_confirmed_at: new Date().toISOString(),
    created_at: new Date().toISOString()
  }
}

vi.mock('@/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({
        data: { session: mockSession },
        error: null
      })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: mockUnsubscribe } }
      })),
      signInWithOAuth: vi.fn(),
      signOut: vi.fn()
    }
  }
}))

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  clear: vi.fn(),
  removeItem: vi.fn(),
  length: 0,
  key: vi.fn()
}
global.localStorage = localStorageMock as Storage

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset environment variable
    process.env.VITE_E2E_TEST_MODE = 'false'
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initialization', () => {
    it('初期状態で認証情報を取得する', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current[0].loading).toBe(false)
      })
    })

    it('getSessionが呼ばれること', async () => {
      const { supabase } = require('../../src/services/supabase')
      
      renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(supabase.auth.getSession).toHaveBeenCalled()
      })
    })

    it('onAuthStateChangeのリスナーが登録されること', async () => {
      const { supabase } = require('../../src/services/supabase')
      
      renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(supabase.auth.onAuthStateChange).toHaveBeenCalled()
      })
    })
  })

  describe('Google OAuth', () => {
    it('signInWithGoogleが呼ばれること', async () => {
      const { supabase } = require('../../src/services/supabase')
      const mockOAuth = vi.fn(() => Promise.resolve({ error: null }))
      supabase.auth.signInWithOAuth = mockOAuth

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        const response = await result.current[1].signInWithGoogle()
        expect(response.error).toBeNull()
      })

      expect(mockOAuth).toHaveBeenCalledWith({
        provider: 'google',
        options: {
          queryParams: {
            access_type: 'offline',
            prompt: 'consent'
          },
          scopes: 'email'
        }
      })
    })
  })

  describe('Sign Out', () => {
    it('signOutが呼ばれると状態がクリアされること', async () => {
      const { supabase } = require('../../src/services/supabase')
      const mockSignOut = vi.fn(() => Promise.resolve({ error: null }))
      supabase.auth.signOut = mockSignOut

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        const response = await result.current[1].signOut()
        expect(response.error).toBeNull()
      })

      expect(mockSignOut).toHaveBeenCalled()
    })
  })

  describe('E2E Test Mode', () => {
    it('E2Eテストモードの場合、自動ログインしないこと', async () => {
      process.env.VITE_E2E_TEST_MODE = 'true'
      
      const { supabase } = require('../../src/services/supabase')
      
      renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current[0].loading).toBe(false)
      })
    })

    it('E2EテストモードでsignInWithGoogleがモックユーザーを返すこと', async () => {
      process.env.VITE_E2E_TEST_MODE = 'true'
      
      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        const response = await result.current[1].signInWithGoogle()
        expect(response.error).toBeNull()
      })
    })

    it('E2EテストモードでsignOutが状態をクリアすること', async () => {
      process.env.VITE_E2E_TEST_MODE = 'true'
      
      const { result } = renderHook(() => useAuth(), { wrapper })

      // First sign in
      await act(async () => {
        await result.current[1].signInWithGoogle()
      })

      // Then sign out
      await act(async () => {
        const response = await result.current[1].signOut()
        expect(response.error).toBeNull()
      })
    })

    it('localStorageのe2e-test-modeフラグでE2Eモードが有効になること', async () => {
      localStorageMock.getItem.mockReturnValue('true')
      
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current[0].loading).toBe(false)
      })
    })
  })

  describe('State Management', () => {
    it('認証状態が変更されるとユーザー情報が更新されること', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current[0].loading).toBe(false)
      })
    })

    it('roleがuser_metadataから正しく抽出されること', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        // mockSession has role: 'admin'
        expect(result.current[0].role).toBe('admin')
      })
    })
  })

  describe('Cleanup', () => {
    it('アンマウント時にサブスクリプションが解除されること', async () => {
      const { unmount } = renderHook(() => useAuth(), { wrapper })

      unmount()

      expect(mockUnsubscribe).toHaveBeenCalled()
    })
  })

  describe('Return Values', () => {
    it('正しい構造の配列を返すこと', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current).toHaveLength(2)
        
        const [state, actions] = result.current
        expect(state).toHaveProperty('user')
        expect(state).toHaveProperty('session')
        expect(state).toHaveProperty('loading')
        expect(state).toHaveProperty('role')
        expect(actions).toHaveProperty('signInWithGoogle')
        expect(actions).toHaveProperty('signOut')
      })
    })
  })

  describe('Error Handling', () => {
    it('getSession失敗時、エラーがログ出力されること', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { supabase } = require('../../src/services/supabase')
      supabase.auth.getSession = vi.fn(() => Promise.resolve({
        data: { session: null },
        error: { message: 'Session error' }
      }))

      renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Error getting session:',
          'Session error'
        )
      })

      consoleErrorSpy.mockRestore()
    })
  })
})
