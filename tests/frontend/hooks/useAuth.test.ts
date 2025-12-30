/**
 * useAuthフックのテスト
 *
 * ユーザー認証ロジック (ログイン、ログアウト、認証状態管理) をテストする。
 */

import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useAuth } from '../../../src/hooks/useAuth'

describe('useAuth', () => {
  it('初期状態では未認証である', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toBeNull()
    expect(result.current.loading).toBe(true)
  })

  it('has required auth methods', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.signIn).toBeDefined()
    expect(result.current.signUp).toBeDefined()
    expect(result.current.signOut).toBeDefined()
  })

  it('signIn returns correct structure', async () => {
    const { result } = renderHook(() => useAuth())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // ログイン実行 - tests against real Supabase
    const loginResult = await result.current.signIn('test@example.com', 'password123')

    // Verify result structure
    expect(loginResult).toHaveProperty('user')
    expect(loginResult).toHaveProperty('session')
    expect(loginResult).toHaveProperty('error')
  })

  it('signOut returns correct structure', async () => {
    const { result } = renderHook(() => useAuth())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // ログアウト実行
    const signOutResult = await result.current.signOut()

    // Verify result structure
    expect(signOutResult).toHaveProperty('error')
  })

  it('signUp returns correct structure', async () => {
    const { result } = renderHook(() => useAuth())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // ユーザー登録実行
    const signUpResult = await result.current.signUp('newuser@example.com', 'password123', 'New User')

    // Verify result structure
    expect(signUpResult).toHaveProperty('user')
    expect(signUpResult).toHaveProperty('session')
    expect(signUpResult).toHaveProperty('error')
  })
})
