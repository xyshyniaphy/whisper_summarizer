/**
 * Dashboard state management with Jotai
 */

import { atom } from 'jotai'

export type DashboardTab = 'users' | 'channels' | 'audio'

export const dashboardActiveTabAtom = atom<DashboardTab>('users')
export const sidebarCollapsedAtom = atom<boolean>(
  // Load from localStorage
  typeof localStorage !== 'undefined' && localStorage.getItem('sidebar-collapsed') === 'true'
)

// Persist sidebar state to localStorage
export const persistSidebarCollapseAtom = atom(
  (get) => get(sidebarCollapsedAtom),
  (get, set, collapsed: boolean) => {
    set(sidebarCollapsedAtom, collapsed)
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('sidebar-collapsed', String(collapsed))
    }
  }
)
