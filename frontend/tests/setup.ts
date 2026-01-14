/**
 * Test setup for Vitest with React 19 + jsdom
 *
 * IMPORTANT: This file runs BEFORE each test file.
 * Ensure jsdom globals are available before any imports.
 */

// Set global test mode flag to skip useAuth useEffect in tests
;(global as any).__VITEST_TEST_MODE__ = true

// Ensure jsdom globals are available (fixes "document is not defined")
if (typeof document === 'undefined') {
  // This should never happen with environment: 'jsdom', but adding as safety check
  throw new Error('jsdom environment not loaded. Check vitest.config.ts has environment: "jsdom"')
}

// Import testing utilities after jsdom is confirmed available
import { expect, afterEach, vi, beforeAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Create stable mock functions for React Router
const mockNavigate = vi.fn()
const mockSetSearchParams = vi.fn()

// Mock React Router - keep BrowserRouter real, mock only hooks
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/', search: '', hash: '', state: null }),
    useParams: () => ({}),
    useSearchParams: () => [
      new URLSearchParams(),
      mockSetSearchParams,
    ],
    // Keep real components for Router context
    BrowserRouter: actual.BrowserRouter,
    Routes: actual.Routes,
    Route: actual.Route,
    Navigate: ({ to }: { to: string }) => null,
    Link: ({ children, to, ...props }: any) => `Link to ${to}`,
  }
})

// Export mocks globally for tests to use
;(global as any).mockNavigate = mockNavigate
;(global as any).mockSetSearchParams = mockSetSearchParams

// Mock Supabase client
const mockSession = {
  access_token: 'mock-token',
  refresh_token: 'mock-refresh-token',
  user: {
    id: '123e4567-e89b-42d3-a456-426614174000',
    email: 'test@example.com',
    is_active: true,
    is_admin: false,
  }
}

vi.mock('@/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: mockSession }, error: null })),
      getUser: vi.fn(() => Promise.resolve({ data: { user: mockSession.user }, error: null })),
      signInWithOAuth: vi.fn(() => Promise.resolve({ data: { url: 'http://localhost:3000' }, error: null })),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
      refreshSession: vi.fn(() => Promise.resolve({ data: { session: mockSession }, error: null })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        eq: vi.fn(() => ({
          data: [],
          error: null,
        })),
        order: vi.fn(() => ({
          data: [],
          error: null,
        })),
      })),
      insert: vi.fn(() => ({
        data: null,
        error: null,
      })),
      update: vi.fn(() => ({
        eq: vi.fn(() => ({
          data: null,
          error: null,
        })),
      })),
      delete: vi.fn(() => ({
        eq: vi.fn(() => ({
          data: null,
          error: null,
        })),
      })),
    })),
  }
}))

// Create mock functions at module level so they can be accessed outside vi.mock
const mockGet = vi.fn(() => Promise.resolve({ data: [] }))
const mockPost = vi.fn(() => Promise.resolve({ data: {} }))
const mockPut = vi.fn(() => Promise.resolve({ data: {} }))
const mockDelete = vi.fn(() => Promise.resolve({ data: {} }))
const mockPatch = vi.fn(() => Promise.resolve({ data: {} }))

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: mockGet,
    post: mockPost,
    put: mockPut,
    delete: mockDelete,
    patch: mockPatch,
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    },
    defaults: {
      baseURL: '/api',
      headers: {}
    }
  }

  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      patch: mockPatch,
    }
  }
})

// Make mock functions available globally for tests to use
;(global as any).mockAxiosGet = mockGet
;(global as any).mockAxiosPost = mockPost
;(global as any).mockAxiosDelete = mockDelete
;(global as any).mockAxiosPut = mockPut
;(global as any).mockAxiosPatch = mockPatch

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

// Mock @tanstack/react-virtual for VirtualizedSrtList tests
const mockUseVirtualizer = vi.fn(() => ({
  getVirtualItems: () => [],
  getTotalSize: () => 0,
  scrollToIndex: vi.fn(),
}))

vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: mockUseVirtualizer,
}))

// Export for tests to use
;(global as any).mockUseVirtualizer = mockUseVirtualizer

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
