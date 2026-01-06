/**
 * Jotai Atomsのテスト
 *
 * auth, theme, transcriptionsアトムの機能をテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { Provider, useAtom, useSetAtom } from 'jotai'
import { renderHook, act } from '@testing-library/react'

import {
  userAtom,
  sessionAtom,
  roleAtom,
  loadingAtom,
  isAuthenticatedAtom,
  isAdminAtom,
  authStateAtom
} from '@/atoms/auth'
import {
  themeAtom,
  themeWithPersistenceAtom,
  type Theme
} from '@/atoms/theme'
import {
  transcriptionsAtom,
  selectedTranscriptionAtom,
  userTranscriptionsAtom,
  transcriptionsLoadingAtom
} from '@/atoms/transcriptions'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} }
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

// Mock document.documentElement
Object.defineProperty(document.documentElement, 'classList', {
  value: {
    add: vi.fn(),
    remove: vi.fn()
  },
  writable: true
})

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

describe('Auth Atoms', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Primitive Atoms', () => {
    it('userAtomの初期値はnullである', () => {
      const { result } = renderHook(() => useAtom(userAtom), { wrapper })
      expect(result.current[0]).toBeNull()
    })

    it('userAtomに値を設定できる', () => {
      const { result } = renderHook(() => useAtom(userAtom), { wrapper })
      const mockUser = { id: '123', email: 'test@example.com' } as any

      act(() => {
        result.current[1](mockUser)
      })

      expect(result.current[0]).toEqual(mockUser)
    })

    it('sessionAtomの初期値はnullである', () => {
      const { result } = renderHook(() => useAtom(sessionAtom), { wrapper })
      expect(result.current[0]).toBeNull()
    })

    it('roleAtomの初期値はnullである', () => {
      const { result } = renderHook(() => useAtom(roleAtom), { wrapper })
      expect(result.current[0]).toBeNull()
    })

    it('roleAtomに"user"または"admin"を設定できる', () => {
      const { result } = renderHook(() => useAtom(roleAtom), { wrapper })

      act(() => {
        result.current[1]('user')
      })

      expect(result.current[0]).toBe('user')
    })

    it('loadingAtomの初期値はtrueである', () => {
      const { result } = renderHook(() => useAtom(loadingAtom), { wrapper })
      expect(result.current[0]).toBe(true)
    })

    it('loadingAtomをfalseに設定できる', () => {
      const { result } = renderHook(() => useAtom(loadingAtom), { wrapper })

      act(() => {
        result.current[1](false)
      })

      expect(result.current[0]).toBe(false)
    })
  })

  describe('Derived Atoms', () => {
    it('isAuthenticatedAtomはuserAtomがnullの場合falseを返す', () => {
      const { result } = renderHook(() => useAtom(isAuthenticatedAtom), { wrapper })
      expect(result.current[0]).toBe(false)
    })

    it('isAuthenticatedAtomはuserAtomがある場合trueを返す', () => {
      const { result } = renderHook(() => {
        const [user, setUser] = useAtom(userAtom)
        const [isAuthenticated] = useAtom(isAuthenticatedAtom)
        return { user, setUser, isAuthenticated }
      }, { wrapper })

      act(() => {
        result.current.setUser({ id: '123' } as any)
      })

      expect(result.current.isAuthenticated).toBe(true)
    })

    it('isAdminAtomはroleAtomが"admin"の場合trueを返す', () => {
      const { result } = renderHook(() => {
        const [role, setRole] = useAtom(roleAtom)
        const [isAdmin] = useAtom(isAdminAtom)
        return { role, setRole, isAdmin }
      }, { wrapper })

      act(() => {
        result.current.setRole('admin')
      })

      expect(result.current.isAdmin).toBe(true)
    })

    it('isAdminAtomはroleAtomが"user"の場合falseを返す', () => {
      const { result } = renderHook(() => {
        const [role, setRole] = useAtom(roleAtom)
        const [isAdmin] = useAtom(isAdminAtom)
        return { role, setRole, isAdmin }
      }, { wrapper })

      act(() => {
        result.current.setRole('user')
      })

      expect(result.current.isAdmin).toBe(false)
    })
  })

  describe('authStateAtom', () => {
    it('すべての認証状態を正しく返す', () => {
      const { result } = renderHook(() => {
        const [user, setUser] = useAtom(userAtom)
        const [role, setRole] = useAtom(roleAtom)
        const [loading, setLoading] = useAtom(loadingAtom)
        const [authState] = useAtom(authStateAtom)
        return { user, setUser, role, setRole, loading, setLoading, authState }
      }, { wrapper })

      act(() => {
        result.current.setUser({ id: '123' } as any)
        result.current.setRole('user')
        result.current.setLoading(false)
      })

      expect(result.current.authState).toEqual({
        user: { id: '123' },
        session: null,
        role: 'user',
        loading: false,
        isAuthenticated: true,
        isAdmin: false,
        is_active: false,
        is_admin: false
      })
    })
  })
})

describe('Theme Atoms', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  describe('themeAtom', () => {
    it('初期値は"light"である', () => {
      const { result } = renderHook(() => useAtom(themeAtom), { wrapper })
      expect(result.current[0]).toBe('light')
    })

    it('テーマを"dark"に設定できる', () => {
      const { result } = renderHook(() => useAtom(themeAtom), { wrapper })

      act(() => {
        result.current[1]('dark')
      })

      expect(result.current[0]).toBe('dark')
    })
  })

  describe('themeWithPersistenceAtom', () => {
    it('テーマ変更時にlocalStorageに保存される', () => {
      const { result } = renderHook(() => useAtom(themeWithPersistenceAtom), { wrapper })

      act(() => {
        result.current[1]('dark')
      })

      expect(localStorageMock.getItem('theme')).toBe('dark')
    })

    it('ダークテーマ設定時にDOMクラスが追加される', () => {
      const { result } = renderHook(() => useAtom(themeWithPersistenceAtom), { wrapper })

      act(() => {
        result.current[1]('dark')
      })

      expect(document.documentElement.classList.add).toHaveBeenCalledWith('dark')
    })

    it('ライトテーマ設定時にDOMクラスが削除される', () => {
      const { result } = renderHook(() => useAtom(themeWithPersistenceAtom), { wrapper })

      act(() => {
        result.current[1]('dark')
      })
      act(() => {
        result.current[1]('light')
      })

      expect(document.documentElement.classList.remove).toHaveBeenCalledWith('dark')
    })
  })
})

describe('Transcription Atoms', () => {
  describe('transcriptionsAtom', () => {
    it('初期値は空配列である', () => {
      const { result } = renderHook(() => useAtom(transcriptionsAtom), { wrapper })
      expect(result.current[0]).toEqual([])
    })

    it('転写リストを設定できる', () => {
      const { result } = renderHook(() => useAtom(transcriptionsAtom), { wrapper })
      const mockTranscriptions = [
        { id: '1', file_name: 'test.mp3' }
      ] as any

      act(() => {
        result.current[1](mockTranscriptions)
      })

      expect(result.current[0]).toEqual(mockTranscriptions)
    })
  })

  describe('selectedTranscriptionAtom', () => {
    it('初期値はnullである', () => {
      const { result } = renderHook(() => useAtom(selectedTranscriptionAtom), { wrapper })
      expect(result.current[0]).toBeNull()
    })

    it('選択された転写を設定できる', () => {
      const { result } = renderHook(() => useAtom(selectedTranscriptionAtom), { wrapper })
      const mockTranscription = { id: '1', file_name: 'test.mp3' } as any

      act(() => {
        result.current[1](mockTranscription)
      })

      expect(result.current[0]).toEqual(mockTranscription)
    })
  })

  describe('userTranscriptionsAtom', () => {
    it('transcriptionsAtomの値を返す', () => {
      const { result } = renderHook(() => {
        const [transcriptions, setTranscriptions] = useAtom(transcriptionsAtom)
        const [userTranscriptions] = useAtom(userTranscriptionsAtom)
        return { transcriptions, setTranscriptions, userTranscriptions }
      }, { wrapper })

      const mockTranscriptions = [
        { id: '1', file_name: 'test.mp3' }
      ] as any

      act(() => {
        result.current.setTranscriptions(mockTranscriptions)
      })

      expect(result.current.userTranscriptions).toEqual(mockTranscriptions)
    })
  })

  describe('transcriptionsLoadingAtom', () => {
    it('初期値はfalseである', () => {
      const { result } = renderHook(() => useAtom(transcriptionsLoadingAtom), { wrapper })
      expect(result.current[0]).toBe(false)
    })

    it('ローディング状態を設定できる', () => {
      const { result } = renderHook(() => useAtom(transcriptionsLoadingAtom), { wrapper })

      act(() => {
        result.current[1](true)
      })

      expect(result.current[0]).toBe(true)
    })
  })
})
