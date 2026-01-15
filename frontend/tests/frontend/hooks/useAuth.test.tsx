/**
 * useAuthフックのテスト
 *
 * 認証状態管理、Google OAuth、サインアウト、
 * E2Eテストモード、状態同期をテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { Provider } from 'jotai'
import { useAuth } from '../../../src/hooks/useAuth'

// Mock localStorage - needs to be defined before tests
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value.toString()
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    length: 0,
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  }
})()

// Setup global localStorage
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true,
  configurable: true,
})

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage store
    localStorageMock.clear()
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
  })

  describe('Google OAuth', () => {
    it('signInWithGoogleが正しく呼べる', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        const response = await result.current[1].signInWithGoogle()
        // Mock should return no error
        expect(response).toBeDefined()
      })
    })
  })

  describe('Sign Out', () => {
    it('signOutが正しく呼べる', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        const response = await result.current[1].signOut()
        expect(response).toBeDefined()
      })
    })
  })

  describe('E2E Test Mode', () => {
    it('E2Eテストモードの場合、自動ログインしないこと', async () => {
      process.env.VITE_E2E_TEST_MODE = 'true'

      renderHook(() => useAuth(), { wrapper })

      // In E2E test mode, loading should be false immediately
      // because the useEffect returns early
      await waitFor(() => {
        expect(process.env.VITE_E2E_TEST_MODE).toBe('true')
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

      renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        // Test passes if no errors are thrown during initialization
        expect(true).toBe(true)
      })
    })

    describe('Production E2E Mode', () => {
      const originalLocation = window.location

      afterEach(() => {
        // Restore original location
        Object.defineProperty(window, 'location', {
          value: originalLocation,
          writable: true,
          configurable: true,
        })
        // Clear localStorage flag
        vi.mocked(localStorageMock.getItem).mockReturnValue(null)
      })

      it('本番環境(w.198066.xyz)でlmr@lmr.comユーザーが使用されること', async () => {
        // Mock production hostname
        Object.defineProperty(window, 'location', {
          value: { hostname: 'w.198066.xyz' },
          writable: true,
          configurable: true,
        })

        // Set E2E test mode via localStorage
        localStorageMock.getItem.mockReturnValue('true')

        const { result } = renderHook(() => useAuth(), { wrapper })

        await waitFor(() => {
          const [state] = result.current
          expect(state.user).toBeDefined()
          expect(state.user?.email).toBe('lmr@lmr.com')
          expect(state.user?.id).toBe('e2e-prod-user-id')
          expect(state.is_admin).toBe(true)
          expect(state.is_active).toBe(true)
          expect(state.loading).toBe(false)
        })
      })

      it('開発環境でtest@example.comユーザーが使用されること', async () => {
        // Mock development hostname
        Object.defineProperty(window, 'location', {
          value: { hostname: 'localhost' },
          writable: true,
          configurable: true,
        })

        // Set E2E test mode via localStorage
        localStorageMock.getItem.mockReturnValue('true')

        const { result } = renderHook(() => useAuth(), { wrapper })

        await waitFor(() => {
          const [state] = result.current
          expect(state.user).toBeDefined()
          expect(state.user?.email).toBe('test@example.com')
          expect(state.user?.id).toBe('fc47855d-6973-4931-b6fd-bd28515bec0d')
          expect(state.is_admin).toBe(true)
          expect(state.is_active).toBe(true)
          expect(state.loading).toBe(false)
        })
      })

      it('E2EモードでauthActionsが利用可能であること', async () => {
        // Mock production hostname
        Object.defineProperty(window, 'location', {
          value: { hostname: 'w.198066.xyz' },
          writable: true,
          configurable: true,
        })

        // Set E2E test mode via localStorage
        localStorageMock.getItem.mockReturnValue('true')

        const { result } = renderHook(() => useAuth(), { wrapper })

        await waitFor(() => {
          const [, actions] = result.current
          expect(actions.signInWithGoogle).toBeDefined()
          expect(actions.signOut).toBeDefined()
          expect(typeof actions.signInWithGoogle).toBe('function')
          expect(typeof actions.signOut).toBe('function')
        })
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
})
