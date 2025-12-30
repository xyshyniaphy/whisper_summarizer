/**
 * 認証状態管理カスタムフック (Jotai版)
 */

import { useEffect, useCallback } from 'react'
import { User, Session, AuthError } from '@supabase/supabase-js'
import { useAtom, useSetAtom } from 'jotai'
import { supabase } from '../services/supabase'
import {
  userAtom,
  sessionAtom,
  roleAtom,
  loadingAtom,
} from '../atoms/auth'

interface AuthActions {
  signUp: (email: string, password: string, fullName?: string) => Promise<{ user: User | null; session: Session | null; error: AuthError | null }>
  signIn: (email: string, password: string) => Promise<{ user: User | null; session: Session | null; error: AuthError | null }>
  signOut: () => Promise<{ error: AuthError | null }>
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

  // 新規ユーザー登録
  const signUp = useCallback(async (email: string, password: string, fullName?: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName || '',
          role: 'user',
        },
      },
    })

    if (data.user) {
      setUser(data.user)
      setRole('user')
    }

    return {
      user: data.user,
      session: data.session,
      error,
    }
  }, [setUser, setRole])

  // サインイン
  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (data.user) {
      setUser(data.user)
      setRole(data.user.user_metadata?.role ?? 'user')
    }

    return {
      user: data.user,
      session: data.session,
      error,
    }
  }, [setUser, setRole])

  // サインアウト
  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    setUser(null)
    setSession(null)
    setRole(null)
    return { error }
  }, [setUser, setSession, setRole])

  return [
    { user, session, loading, role },
    { signUp, signIn, signOut },
  ]
}
