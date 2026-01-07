/**
 * テストセットアップファイル
 *
 * Testing Library、グローバル設定を初期化する。
 */

import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import * as React from 'react'

// Mock Link component from react-router-dom as a simple <a> element
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<any>('react-router-dom')

  return {
    ...actual,
    Link: ({ children, to, className, ...props }: any) =>
      React.createElement('a', { href: to, className, ...props }, children)
  }
})

// window.matchMedia mock (Mantine uses this for color scheme/media queries)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    // Always match desktop breakpoint queries (md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px)
    // This makes Tailwind responsive classes like md:flex work correctly in tests
    matches: true,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// 各テスト後にクリーンアップ
afterEach(() => {
  cleanup()
})
