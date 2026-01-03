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
  isActiveAtom,
  loadingAtom,
  type ExtendedUser,
} from '../atoms/auth'
import { api } from '../services/api'

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

// Fetch extended user data from backend (includes is_active, is_admin)
const fetchUserData = async (user: User | null): Promise<ExtendedUser | null> => {
  if (!user) return null

  try {
    const response = await api.get('/users/me')
    return {
      ...user,
      ...response.data,
    }
  } catch (error) {
    console.error('Error fetching user data from backend:', error)
    // If backend returns 403 (inactive account), still return user with is_active=false
    if (error instanceof Error && 'status' in error && (error as any).status === 403) {
      return {
        ...user,
        is_active: false,
        is_admin: false,
      }
    }
    return user
  }
}

export function useAuth(): [
  {
    user: ExtendedUser | null
    session: Session | null
    loading: boolean
    role: 'user' | 'admin' | null
    is_active: boolean
    is_admin: boolean
  },
  AuthActions
] {
  const [user, setUser] = useAtom(userAtom)
  const [session, setSession] = useAtom(sessionAtom)
  const [role, setRole] = useAtom(roleAtom)
  const [isActive, setIsActive] = useAtom(isActiveAtom)
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

      if (session?.user) {
        const userData = await fetchUserData(session.user)
        setUser(userData)
        setSession(session)
        setRole(userData?.is_admin ? 'admin' : 'user')
        setIsActive(userData?.is_active ?? false)
      } else {
        setUser(null)
        setSession(null)
        setRole(null)
        setIsActive(false)
      }
      setLoading(false)
    }

    getSession()

    // 認証状態の変更を監視
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session?.user) {
        const userData = await fetchUserData(session.user)
        setUser(userData)
        setSession(session)
        setRole(userData?.is_admin ? 'admin' : 'user')
        setIsActive(userData?.is_active ?? false)
      } else {
        setUser(null)
        setSession(null)
        setRole(null)
        setIsActive(false)
      }
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [setUser, setSession, setRole, setIsActive, setLoading])

  // Google OAuthサインイン
  const signInWithGoogle = useCallback(async () => {
    if (isE2ETestMode()) {
      setUser(mockUser as ExtendedUser)
      setRole('user')
      setIsActive(true)
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
      setIsActive(false)
      return { error: null }
    }

    const { error } = await supabase.auth.signOut()
    setUser(null)
    setSession(null)
    setRole(null)
    setIsActive(false)
    return { error }
  }, [setUser, setSession, setRole, setIsActive])

  return [
    { user, session, loading, role, is_active: isActive, is_admin: role === 'admin' },
    { signInWithGoogle, signOut },
  ]
}
