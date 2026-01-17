/**
 * Theme toggle button component
 * Switches between light and dark themes
 */

import { useAtom } from 'jotai'
import { Moon, Sun } from 'lucide-react'
import { themeWithPersistenceAtom } from '../atoms/theme'

export function ThemeToggle() {
  const [theme, setTheme] = useAtom(themeWithPersistenceAtom)

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors"
      aria-label={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
      title={theme === 'light' ? '深色模式' : '浅色模式'}
      data-testid="theme-toggle"
    >
      {theme === 'light' ? (
        <Moon className="w-5 h-5" />
      ) : (
        <Sun className="w-5 h-5" />
      )}
    </button>
  )
}
