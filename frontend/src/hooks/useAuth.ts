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

// Unit test mode check (for Vitest unit tests)
// Detect if we're in a test environment by checking for Vitest globals
const isUnitTestMode = () => {
  // Check for global test mode flag (set in tests/setup.ts)
  if (typeof global !== 'undefined' && (global as any).__VITEST_TEST_MODE__ === true) {
    return true
  }
  // Check if we're in a Vitest environment by checking for vi global
  if (typeof (global as any).vi !== 'undefined') {
    return true
  }
  // Check for process.env.NODE_ENV === 'test'
  if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'test') {
    return true
  }
  return false
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
  console.log('[fetchUserData] Starting with user:', user?.email || 'no user')
  if (!user) {
    console.log('[fetchUserData] No user, returning null')
    return null
  }

  try {
    console.log('[fetchUserData] Calling api.get("/users/me")')
    const response = await api.get('/users/me')
    console.log('[fetchUserData] API response:', response)
    // api.get() already returns response.data, so response is the data object
    return {
      ...user,
      ...response,
    }
  } catch (error) {
    console.error('[fetchUserData] Error fetching user data from backend:', error)
    // If backend returns 403 (inactive account), still return user with is_active=false
    if (error instanceof Error && 'status' in error && (error as any).status === 403) {
      console.log('[fetchUserData] 403 error, returning inactive user')
      return {
        ...user,
        is_active: false,
        is_admin: false,
      }
    }
    console.log('[fetchUserData] Other error, returning original user')
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
    // E2EテストモードまたはUnitテストモードの場合は自動ログインしない（auth呼び出しをモックするだけ）
    if (isE2ETestMode() || isUnitTestMode()) {
      setLoading(false)
      return
    }

    // Supabase client not initialized (missing env vars)
    if (!supabase) {
      console.error('[useAuth] Supabase client not initialized. Check VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY environment variables.')
      setLoading(false)
      return
    }

    // 現在のセッションを取得
    const getSession = async () => {
      console.log('[getSession] Starting...')
      let session
      let error

      // Try to get session from Supabase with a timeout fallback
      try {
        console.log('[getSession] Calling supabase.auth.getSession()')
        // Add a timeout fallback in case supabase.auth.getSession() hangs
        const sessionPromise = supabase.auth.getSession()
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Session retrieval timeout')), 3000)
        )

        const result = await Promise.race([sessionPromise, timeoutPromise]) as any
        session = result.data?.session
        error = result.error
        console.log('[getSession] Supabase result:', { hasSession: !!session, hasError: !!error })
      } catch (e: any) {
        console.warn('[getSession] Supabase getSession() failed, trying localStorage fallback:', e?.message)
        // Fallback: read session directly from localStorage
        try {
          const keys = Object.keys(localStorage)
          const authKey = keys.find(k => k.startsWith('sb-') && k.includes('-auth-token'))
          console.log('[getSession] Found auth key:', !!authKey)
          if (authKey) {
            const tokenData = JSON.parse(localStorage.getItem(authKey))
            const accessToken = tokenData?.currentSession?.access_token || tokenData?.access_token
            console.log('[getSession] Has access token:', !!accessToken)

            if (accessToken) {
              // Decode JWT to get user info
              const parts = accessToken.split('.')
              if (parts.length === 3) {
                const payload = JSON.parse(atob(parts[1]))
                console.log('[getSession] Decoded user from JWT:', payload.email)
                session = {
                  user: {
                    id: payload.sub,
                    email: payload.email,
                    email_confirmed_at: payload.email_verified ? new Date().toISOString() : null,
                    user_metadata: payload.user_metadata || {},
                    app_metadata: payload.app_metadata || {},
                  }
                }
                console.log('[getSession] Created session from localStorage')
              }
            }
          }
        } catch (localStorageError) {
          console.error('[getSession] LocalStorage fallback also failed:', localStorageError)
        }
      }

      if (error) {
        console.error('[getSession] Error getting session:', error.message)
      }

      console.log('[getSession] Final session state:', { hasSession: !!session, hasUser: !!session?.user, userEmail: session?.user?.email })

      if (session?.user) {
        try {
          console.log('[getSession] Calling fetchUserData for:', session.user.email)
          const userData = await fetchUserData(session.user)
          console.log('[getSession] fetchUserData returned:', userData?.email, 'is_active:', userData?.is_active, 'is_admin:', userData?.is_admin)
          setUser(userData)
          setSession(session)
          setRole(userData?.is_admin ? 'admin' : 'user')
          setIsActive(userData?.is_active ?? false)
        } catch (fetchError) {
          console.error('[getSession] Error in fetchUserData:', fetchError)
          // Set user with session data even if fetchUserData fails
          setUser(session.user as any)
          setSession(session)
          setRole('user')
          setIsActive(false)
        }
      } else {
        console.log('[getSession] No session.user, clearing auth state')
        setUser(null)
        setSession(null)
        setRole(null)
        setIsActive(false)
      }
      console.log('[getSession] Setting loading=false')
      setLoading(false)
    }

    getSession()

    // 認証状態の変更を監視
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      console.log('[onAuthStateChange] Event:', _event, 'hasSession:', !!session, 'userEmail:', session?.user?.email)
      if (session?.user) {
        try {
          const userData = await fetchUserData(session.user)
          console.log('[onAuthStateChange] fetchUserData returned:', userData?.email, 'is_active:', userData?.is_active, 'is_admin:', userData?.is_admin)
          setUser(userData)
          setSession(session)
          setRole(userData?.is_admin ? 'admin' : 'user')
          setIsActive(userData?.is_active ?? false)
        } catch (fetchError) {
          console.error('[onAuthStateChange] Error in fetchUserData:', fetchError)
          // Set user with session data even if fetchUserData fails
          setUser(session.user as any)
          setSession(session)
          setRole('user')
          setIsActive(false)
        }
      } else {
        console.log('[onAuthStateChange] No session.user, clearing auth state')
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

    if (!supabase) {
      return { error: { name: 'SupabaseError', message: 'Supabase client not initialized' } as AuthError }
    }

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${import.meta.env.VITE_PUBLIC_URL || window.location.origin}/dashboard`,
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

    if (!supabase) {
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
