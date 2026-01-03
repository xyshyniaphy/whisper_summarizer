/**
 * Test Utilities
 *
 * Provides helper functions and wrappers for testing React components
 * with proper providers (Supabase, Router, etc.)
 */

import { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi } from 'vitest'

// Types for test utilities
export interface MockAuthState {
  isAuthenticated: boolean
  user: {
    id: string
    email: string
    name?: string
  } | null
  accessToken?: string
}

export interface TestRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authState?: MockAuthState
  routerRoutes?: Array<{
    path: string
    element: ReactElement
  }>
  initialEntries?: string[]
}

/**
 * Creates a mock Supabase client with controllable auth state
 */
export function createMockSupabase(authState: MockAuthState = { isAuthenticated: false, user: null }) {
  return {
    auth: {
      getSession: vi.fn(() =>
        Promise.resolve({
          data: {
            session: authState.isAuthenticated
              ? {
                  access_token: authState.accessToken || 'mock-token',
                  user: authState.user,
                }
              : null,
          },
          error: null,
        })
      ),
      signInWithOAuth: vi.fn(() => Promise.resolve({ data: null, error: null })),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
      refreshSession: vi.fn(() =>
        Promise.resolve({
          data: {
            session: authState.isAuthenticated
              ? {
                  access_token: authState.accessToken || 'mock-token',
                  user: authState.user,
                }
              : null,
          },
          error: null,
        })
      ),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
  }
}

/**
 * Custom render function that wraps components with necessary providers
 *
 * @param ui - The React component to render
 * @param options - Test options including auth state and router configuration
 * @returns Render result with screen, container, etc.
 */
export function renderWithProviders(ui: ReactElement, options: TestRenderOptions = {}) {
  const { authState, routerRoutes, initialEntries = ['/'], ...renderOptions } = options

  // Mock Supabase client
  const mockSupabase = createMockSupabase(authState)
  vi.mock('@/services/supabase', () => ({ supabase: mockSupabase }))

  // Create wrapper with router
  const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
    // If routes are provided, render with Routes, otherwise just children
    if (routerRoutes && routerRoutes.length > 0) {
      return (
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            {routerRoutes.map((route, index) => (
              <Route key={index} path={route.path} element={route.element} />
            ))}
            {/* Render the test UI as a fallback route */}
            <Route path="*" element={children} />
          </Routes>
        </MemoryRouter>
      )
    }

    return (
      <MemoryRouter initialEntries={initialEntries}>
        {children}
      </MemoryRouter>
    )
  }

  return {
    ...render(ui, { wrapper: AllTheProviders, ...renderOptions }),
    mockSupabase,
  }
}

/**
 * Helper to create a mock user for testing
 */
export function createMockUser(overrides: Partial<MockAuthState['user']> = {}): MockAuthState['user'] {
  return {
    id: 'test-user-id',
    email: 'test@example.com',
    name: 'Test User',
    ...overrides,
  }
}

/**
 * Helper to create authenticated state for testing
 */
export function createAuthenticatedAuthState(user?: Partial<MockAuthState['user']>): MockAuthState {
  return {
    isAuthenticated: true,
    user: createMockUser(user),
    accessToken: 'test-access-token',
  }
}

/**
 * Helper to create unauthenticated state for testing
 */
export function createUnauthenticatedAuthState(): MockAuthState {
  return {
    isAuthenticated: false,
    user: null,
  }
}

/**
 * Re-export everything from React Testing Library
 */
export * from '@testing-library/react'

/**
 * Re-export userEvent for user interactions
 */
export { default as userEvent } from '@testing-library/user-event'
