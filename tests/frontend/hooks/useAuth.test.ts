/**
 * useAuthフックのテスト
 * 
 * ユーザー認証ロジック (ログイン、ログアウト、認証状態管理) をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useAuth } from '../../../src/hooks/useAuth'

// Supabaseサービスのモック
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      signUp: vi.fn(),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
    },
  },
}))

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初期状態では未認証である', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toBeNull()
    expect(result.current.loading).toBe(true)
  })

  it('ログインが成功する', async () => {
    const mockUser = {
      id: 'test-user-id',
      email: 'test@example.com',
    }

    const { supabase } = await import('../../../src/services/supabase')
    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValue({
      data: {
        user: mockUser,
        session: {
          access_token: 'test-token',
          refresh_token: 'test-refresh',
        },
      },
      error: null,
    } as any)

    const { result } = renderHook(() => useAuth())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // ログイン実行
    const loginResult = await result.current.signIn('test@example.com', 'password123')

    expect(loginResult.error).toBeUndefined() // フックが成功時にdataを返すため
    expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123',
    })
  })

  it('ログアウトが成功する', async () => {
    const { supabase } = await import('../../../src/services/supabase')
    vi.mocked(supabase.auth.signOut).mockResolvedValue({
      error: null,
    })

    const { result } = renderHook(() => useAuth())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // ログアウト実行
    await result.current.signOut()

    expect(supabase.auth.signOut).toHaveBeenCalled()
  })

  it('ユーザー登録が成功する', async () => {
    const mockUser = {
      id: 'new-user-id',
      email: 'newuser@example.com',
    }

    const { supabase } = await import('../../../src/services/supabase')
    vi.mocked(supabase.auth.signUp).mockResolvedValue({
      data: {
        user: mockUser,
        session: {
          access_token: 'test-token',
          refresh_token: 'test-refresh',
        },
      },
      error: null,
    } as any)

    const { result } = renderHook(() => useAuth())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // ユーザー登録実行
    const signUpResult = await result.current.signUp('newuser@example.com', 'password123', 'New User')

    expect(signUpResult.user).toEqual(mockUser)
    expect(supabase.auth.signUp).toHaveBeenCalledWith({
      email: 'newuser@example.com',
      password: 'password123',
      options: {
        data: {
          full_name: 'New User',
        },
      },
    })
  })
})
