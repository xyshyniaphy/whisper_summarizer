/**
 * テストセットアップファイル
 *
 * Testing Library、グローバル設定を初期化する。
 */

import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// window.matchMedia mock (Mantine uses this for color scheme/media queries)
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

// 各テスト後にクリーンアップ
afterEach(() => {
  cleanup()
})
