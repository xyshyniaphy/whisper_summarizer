/**
 * Authentication state management with Jotai
 */

import { atom } from 'jotai'
import type { User, Session } from '@supabase/supabase-js'

// Extended User interface with local database fields
export interface ExtendedUser extends User {
  is_active?: boolean
  is_admin?: boolean
  activated_at?: string | null
}

// Primitive atoms
export const userAtom = atom<ExtendedUser | null>(null)
export const sessionAtom = atom<Session | null>(null)
export const roleAtom = atom<'user' | 'admin' | null>(null)
export const isActiveAtom = atom<boolean>(false)
export const loadingAtom = atom(true)

// Derived atoms
export const isAuthenticatedAtom = atom((get) => {
  return get(userAtom) !== null
})

export const isAdminAtom = atom((get) => {
  return get(roleAtom) === 'admin'
})

export const isAccountActiveAtom = atom((get) => {
  const user = get(userAtom)
  return user?.is_active ?? false
})

// Combined auth state atom for convenience
export const authStateAtom = atom((get) => ({
  user: get(userAtom),
  session: get(sessionAtom),
  role: get(roleAtom),
  is_active: get(userAtom)?.is_active ?? false,
  is_admin: get(userAtom)?.is_admin ?? false,
  loading: get(loadingAtom),
  isAuthenticated: get(userAtom) !== null,
  isAdmin: get(roleAtom) === 'admin',
}))
