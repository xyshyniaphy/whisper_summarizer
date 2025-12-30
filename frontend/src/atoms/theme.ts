/**
 * Theme state management with Jotai
 */

import { atom } from 'jotai'

export type Theme = 'light' | 'dark'

// Primitive theme atom
export const themeAtom = atom<Theme>('light')

// Theme atom with localStorage persistence and DOM manipulation
export const themeWithPersistenceAtom = atom(
  (get) => get(themeAtom),
  (get, set, newTheme: Theme) => {
    set(themeAtom, newTheme)

    // Persist to localStorage
    localStorage.setItem('theme', newTheme)

    // Update DOM class for Tailwind dark mode
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }
)

// Initialize theme from localStorage on first subscription
themeWithPersistenceAtom.onMount = (set) => {
  const storedTheme = localStorage.getItem('theme') as Theme | null
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches

  const initialTheme: Theme = storedTheme || (prefersDark ? 'dark' : 'light')
  set(initialTheme)
}
