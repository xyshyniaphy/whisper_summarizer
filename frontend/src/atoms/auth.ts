/**
 * Authentication state management with Jotai
 */

import { atom } from 'jotai'
import type { User, Session } from '@supabase/supabase-js'

// Primitive atoms
export const userAtom = atom<User | null>(null)
export const sessionAtom = atom<Session | null>(null)
export const roleAtom = atom<'user' | 'admin' | null>(null)
export const loadingAtom = atom(true)

// Derived atoms
export const isAuthenticatedAtom = atom((get) => {
  return get(userAtom) !== null
})

export const isAdminAtom = atom((get) => {
  return get(roleAtom) === 'admin'
})

// Combined auth state atom for convenience
export const authStateAtom = atom((get) => ({
  user: get(userAtom),
  session: get(sessionAtom),
  role: get(roleAtom),
  loading: get(loadingAtom),
  isAuthenticated: get(userAtom) !== null,
  isAdmin: get(roleAtom) === 'admin',
}))
