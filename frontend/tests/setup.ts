import { expect, afterEach, vi, beforeAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'
import { atom } from 'jotai'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Mock Jotai atoms - create mock atoms for testing
const mockAtom = <T>(initialValue: T) => atom(initialValue)

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

// Mock useAtom hook
vi.mock('jotai', () => ({
  atom: vi.fn((initialValue) => initialValue),
  useAtom: vi.fn((atomToUse) => {
    // Find the corresponding mock atom value
    const atomKey = Object.keys(mockAtoms).find(key => mockAtoms[key as keyof typeof mockAtoms] === atomToUse)
    if (atomKey) {
      const value = mockAtoms[atomKey as keyof typeof mockAtoms]
      return [value, vi.fn()]
    }
    // Default fallback
    return [null, vi.fn()]
  }),
  useAtomValue: vi.fn((atomToUse) => {
    const atomKey = Object.keys(mockAtoms).find(key => mockAtoms[key as keyof typeof mockAtoms] === atomToUse)
    if (atomKey) {
      return mockAtoms[atomKey as keyof typeof mockAtoms]
    }
    return null
  }),
  useSetAtom: vi.fn((atomToUse) => {
    return vi.fn()
  }),
  useAtomDevtools: vi.fn(),
  Provider: ({ children }: { children: React.ReactNode }) => children,
}))

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
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    sendChatMessageStream: vi.fn(async () => ({
      done: true,
    })),
  },
  getTranscriptions: vi.fn(() => Promise.resolve([])),
  getTranscription: vi.fn(() => Promise.resolve({})),
  createTranscription: vi.fn(() => Promise.resolve({})),
  deleteTranscription: vi.fn(() => Promise.resolve({})),
  updateTranscription: vi.fn(() => Promise.resolve({})),
  generateSummary: vi.fn(() => Promise.resolve({})),
  getChatHistory: vi.fn(() => Promise.resolve([])),
  sendChatMessage: vi.fn(() => Promise.resolve({})),
  sendChatMessageStream: vi.fn(async () => ({
    done: true,
  })),
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
