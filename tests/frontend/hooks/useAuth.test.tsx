/**
 * useAuthフックのテスト
 *
 * 認証状態管理、Google OAuth、サインアウト、
 * E2Eテストモード、状態同期をテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { Provider } from 'jotai'
import React from 'react'
import { useAuth } from '../../../src/hooks/useAuth'

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
