/**
 * useAuthフックのテスト
 *
 * ユーザー認証ロジック (ログイン、ログアウト、認証状態管理) をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { Provider } from 'jotai'
import { useAuth } from '../../../src/hooks/useAuth'

// Mock Supabase client
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } }
      })),
      signUp: vi.fn(() => Promise.resolve({
        data: { user: { id: '123', email: 'test@example.com', user_metadata: { role: 'user' } }, session: null },
        error: null
      })),
      signInWithPassword: vi.fn(() => Promise.resolve({
        data: { user: { id: '123', email: 'test@example.com', user_metadata: { role: 'user' } }, session: null },
        error: null
      })),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
      signInWithOAuth: vi.fn(() => Promise.resolve({ data: { url: 'https://example.com' }, error: null })),
    }
  }
}))

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider>{children}</Provider>
  )

  it('初期状態では未認証である', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current[0].user).toBeNull()
      expect(result.current[0].loading).toBe(false)
    })
  })

  it('has required auth methods', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current[1].signIn).toBeDefined()
      expect(result.current[1].signUp).toBeDefined()
      expect(result.current[1].signOut).toBeDefined()
      expect(result.current[1].signInWithGoogle).toBeDefined()
    })
  })

  it('signIn returns correct structure', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current[0].loading).toBe(false)
    })

    const loginResult = await result.current[1].signIn('test@example.com', 'password123')

    expect(loginResult).toHaveProperty('user')
    expect(loginResult).toHaveProperty('session')
    expect(loginResult).toHaveProperty('error')
  })

  it('signOut returns correct structure', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current[0].loading).toBe(false)
    })

    const signOutResult = await result.current[1].signOut()

    expect(signOutResult).toHaveProperty('error')
  })

  it('signUp returns correct structure', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current[0].loading).toBe(false)
    })

    const signUpResult = await result.current[1].signUp('newuser@example.com', 'password123', 'New User')

    expect(signUpResult).toHaveProperty('user')
    expect(signUpResult).toHaveProperty('session')
    expect(signUpResult).toHaveProperty('error')
  })

  it('signInWithGoogle returns correct structure', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current[0].loading).toBe(false)
    })

    const googleResult = await result.current[1].signInWithGoogle()

    expect(googleResult).toHaveProperty('error')
  })
})
