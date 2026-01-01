/**
 * 認証状態管理カスタムフック (Jotai版)
 *
 * Google OAuthのみをサポートしています。
 */

import { useEffect, useCallback } from 'react'
import { User, Session, AuthError } from '@supabase/supabase-js'
import { useAtom } from 'jotai'
import { supabase } from '../services/supabase'
import {
  userAtom,
  sessionAtom,
  roleAtom,
  loadingAtom,
} from '../atoms/auth'

interface AuthActions {
  signInWithGoogle: () => Promise<{ error: AuthError | null }>
  signOut: () => Promise<{ error: AuthError | null }>
}

// E2Eテストモードチェック
const isE2ETestMode = () => {
  // ビルド時の環境変数をチェック
  if (import.meta.env.VITE_E2E_TEST_MODE === 'true') {
    return true
  }
  // 実行時のlocalStorageをチェック（Playwrightなどから設定可能）
  try {
    return localStorage.getItem('e2e-test-mode') === 'true'
  } catch {
    return false
  }
}

// モックユーザー（E2Eテスト用）
const mockUser: User = {
  id: 'test-user-id',
  aud: 'authenticated',
  role: 'authenticated',
  email: 'test@example.com',
  email_confirmed_at: new Date().toISOString(),
  phone: '',
  updated_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  user_metadata: { role: 'user', full_name: 'Test User' },
  app_metadata: {},
}

export function useAuth(): [
  { user: User | null; session: Session | null; loading: boolean; role: 'user' | 'admin' | null },
  AuthActions
] {
  const [user, setUser] = useAtom(userAtom)
  const [session, setSession] = useAtom(sessionAtom)
  const [role, setRole] = useAtom(roleAtom)
  const [loading, setLoading] = useAtom(loadingAtom)

  useEffect(() => {
    // E2Eテストモードの場合は自動ログインしない（auth呼び出しをモックするだけ）
    if (isE2ETestMode()) {
      setLoading(false)
      return
    }

    // 現在のセッションを取得
    const getSession = async () => {
      const { data: { session }, error } = await supabase.auth.getSession()
      if (error) {
        console.error('Error getting session:', error.message)
      }
      setUser(session?.user ?? null)
      setSession(session)
      setRole(session?.user?.user_metadata?.role ?? 'user')
      setLoading(false)
    }

    getSession()

    // 認証状態の変更を監視
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      setSession(session)
      setRole(session?.user?.user_metadata?.role ?? 'user')
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [setUser, setSession, setRole, setLoading])

  // Google OAuthサインイン
  const signInWithGoogle = useCallback(async () => {
    if (isE2ETestMode()) {
      setUser(mockUser)
      setRole('user')
      return { error: null }
    }

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
        scopes: 'email',
      },
    })

    return { error }
  }, [])

  // サインアウト
  const signOut = useCallback(async () => {
    if (isE2ETestMode()) {
      setUser(null)
      setSession(null)
      setRole(null)
      return { error: null }
    }

    const { error } = await supabase.auth.signOut()
    setUser(null)
    setSession(null)
    setRole(null)
    return { error }
  }, [setUser, setSession, setRole])

  return [
    { user, session, loading, role },
    { signInWithGoogle, signOut },
  ]
}
