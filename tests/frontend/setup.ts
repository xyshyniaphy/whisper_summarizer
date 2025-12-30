/**
 * テストセットアップファイル
 *
 * Testing Library、グローバル設定を初期化する。
 */

import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// 各テスト後にクリーンアップ
afterEach(() => {
  cleanup()
})
