import { expect, afterEach, vi, beforeAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'
import { atom } from 'jotai'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Mock Jotai atoms - create mock atoms for testing
const mockAtom = <T>(initialValue: T) => atom(initialValue)

// Store for atom values that can be modified in tests
const atomStore = new Map<any, any>()

// Create mock Jotai atoms that components use
export const mockAtoms = {
  // Auth atoms
  isAuthenticated: mockAtom(false),
  currentUser: mockAtom(null),
  authToken: mockAtom(null),
  supabase: mockAtom(null),

  // Theme atoms
  theme: mockAtom('light' as const),

  // Transcription atoms
  transcriptions: mockAtom([]),
  selectedTranscriptionId: mockAtom<string | null>(null),

  // Channel atoms
  channels: mockAtom([]),
  selectedChannelIds: mockAtom<string[]>([]),

  // Dashboard atoms
  dashboardView: mockAtom('users' as const),
}

// Initialize atom store
Object.entries(mockAtoms).forEach(([key, value]) => {
  atomStore.set(value, key === 'theme' ? 'light' : key === 'isAuthenticated' ? false : null)
})

// Helper to set atom value in tests
export function setAtomValue(atomKey: string, value: any) {
  if (mockAtoms[atomKey as keyof typeof mockAtoms]) {
    atomStore.set(mockAtoms[atomKey as keyof typeof mockAtoms], value)
  }
}

// Mock useAtom hook - use importOriginal to get createStore
vi.mock('jotai', async () => {
  const actual = await vi.importActual('jotai')
  return {
    ...(actual as any),
    atom: vi.fn((initialValue) => {
      const newAtom = initialValue
      atomStore.set(newAtom, initialValue)
      return newAtom
    }),
    useAtom: vi.fn((atomToUse) => {
      const value = atomStore.get(atomToUse)
      const setValue = vi.fn((newValue: any) => {
        atomStore.set(atomToUse, newValue)
      })
      return [value, setValue]
    }),
    useAtomValue: vi.fn((atomToUse) => {
      return atomStore.get(atomToUse)
    }),
    useSetAtom: vi.fn((atomToUse) => {
      return vi.fn((newValue: any) => {
        atomStore.set(atomToUse, newValue)
      })
    }),
    useAtomDevtools: vi.fn(),
    Provider: ({ children }: { children: React.ReactNode }) => children,
  }
})

// Mock React Router
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: '/', search: '', hash: '', state: null }),
    useParams: () => ({}),
    useSearchParams: () => [
      new URLSearchParams(),
      vi.fn(),
    ],
    Navigate: ({ to }: { to: string }) => null,
    Link: ({ children, to, ...props }: any) => `Link to ${to}`,
    BrowserRouter: ({ children }: { children: any }) => children,
  }
})

// Mock API calls to prevent network errors
// Note: We mock axios instead since api.ts uses it internally
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
      put: vi.fn(() => Promise.resolve({ data: {} })),
      delete: vi.fn(() => Promise.resolve({ data: {} })),
      patch: vi.fn(() => Promise.resolve({ data: {} })),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    }))
  }
}))

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
} as any

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any

// Mock Element.scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

// Mock HTMLElement.scrollTo
HTMLElement.prototype.scrollTo = vi.fn()

// Suppress console errors in tests
const originalError = console.error
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render')
    ) {
      return
    }
    originalError.call(console, ...args)
  }
})

afterAll(() => {
  console.error = originalError
})
