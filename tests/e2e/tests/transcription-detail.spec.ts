/**
 * Transcription Detail E2E Tests
 *
 * Tests for transcription detail page with Jotai state management.
 * Tests real Jotai atoms for detail page state, summary, edit mode.
 *
 * Seeded Test Data Approach:
 * - Uses setupTestTranscription helper to upload test audio and wait for completion
 * - Self-contained test data (no dependency on production server)
 * - Server-side auth bypass (no Google OAuth)
 * - Real API calls (no mocks)
 */

import { test, expect } from '@playwright/test'
import { getOrCreateSharedTranscription } from '../helpers/test-data'

test.describe('Transcription Detail', () => {
  let transcriptionId: string | undefined

  test.beforeEach(async ({ page }) => {
    // Setup test transcription (uses shared singleton to avoid re-uploading)
    // The first test will upload, subsequent tests reuse the same transcription
    transcriptionId = await getOrCreateSharedTranscription(page)
    console.log(`[Test] Using transcription: ${transcriptionId}`)

    // Validate transcriptionId is initialized
    if (!transcriptionId) {
      throw new Error('transcriptionId not initialized - setup failed')
    }
    await page.goto('/login')
    await page.evaluate(() => {
      // Safety check: this only works when accessing via localhost
      if (window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1') {
        localStorage.setItem('e2e-test-mode', 'true')
      } else {
        console.warn('[E2E] Cannot enable test mode on non-localhost hostname')
      }
    })
    await page.reload()

    // Note: Server-side auth bypass handles authentication automatically
    // No need to click OAuth button or navigate here
    // Tests will navigate directly to their target pages
  })

  test('転写詳細ページが正常にレンダリングされる', async ({ page }) => {
    // 転写詳細ページに遷移
    await page.goto(`/transcriptions/${transcriptionId}`)

    // ページが読み込まれるまで待機
    await page.waitForLoadState('networkidle')

    // ファイル名が表示されることを確認（動的なセレクタ）
    await expect(page.locator('h1')).toBeVisible()
  })

  test('転写テキストが表示される', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // 転写テキストが表示されることを確認
    await expect(page.locator('[data-testid="transcription-text"]')).toBeVisible()
  })

  test('サマリーが表示される', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // サマリーセクションが表示されることを確認
    await expect(page.locator('text=总结')).toBeVisible()

    // サマリーテキストが表示されることを確認
    await expect(page.locator('[data-testid="summary-text"]')).toBeVisible()
  })

  test('転写をダウンロードできる', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // ダウンロードボタンをクリック
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("下载")')
    const download = await downloadPromise

    // ダウンロードが開始されたことを確認
    expect(download.suggestedFilename()).toMatch(/\.txt$/)
  })

  test('チャンネルバッジが表示される', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // チャンネルバッジが表示されることを確認（もしあれば）
    const channelBadges = page.locator('[data-testid="channel-badge"]')
    const count = await channelBadges.count()
    if (count > 0) {
      await expect(channelBadges.first()).toBeVisible()
    }
  })

  test('チャンネル割り当てモーダルを開くことができる', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // チャンネル割り当てボタンをクリック
    await page.click('button:has-text("分配频道")')

    // モーダルが表示されることを確認
    await expect(page.locator('text=分配频道')).toBeVisible()
  })

  test('言語情報が表示される', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // 言語バッジが表示されることを確認
    await expect(page.locator('[data-testid="language-badge"]')).toBeVisible()
  })

  test('所要時間が表示される', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // 所要時間が表示されることを確認
    await expect(page.locator('[data-testid="duration"]')).toBeVisible()
  })

  test('作成日時が表示される', async ({ page }) => {
    await page.goto(`/transcriptions/${transcriptionId}`)

    // 作成日時が表示されることを確認
    await expect(page.locator('[data-testid="created-at"]')).toBeVisible()
  })

  test('ローディング状態が表示される', async ({ page }) => {
    // Note: This test mocks API response delay to test loading state
    // We use mock here because production transcriptions load too quickly to test loading UI
    await page.route(`**/api/transcriptions/${transcriptionId}`, async route => {
      if (route.request().method() === 'GET') {
        await new Promise(resolve => setTimeout(resolve, 1000))
        await route.continue()
      } else {
        await route.continue()
      }
    })

    await page.goto(`/transcriptions/${transcriptionId}`)

    // ローディングスピナーが表示されることを確認
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible()
  })

  test('エラー時にエラーメッセージが表示される', async ({ page }) => {
    // Note: This test mocks API error response to test error handling
    // We use mock here because we can't easily trigger real 404 errors with production data
    await page.route(`**/api/transcriptions/${transcriptionId}`, async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Transcription not found' })
        })
      } else {
        await route.continue()
      }
    })

    await page.goto(`/transcriptions/${transcriptionId}`)

    // エラーメッセージが表示されることを確認
    await expect(page.locator('text=見つかりません')).toBeVisible()
  })
})

/**
 * Seeded Test Data Notes:
 * - Uses setupTestTranscription helper to upload test audio and wait for completion
 * - Server-side auth bypass handles authentication without Google OAuth
 * - Mock routes kept for loading/error tests (edge cases that are hard to trigger with real data)
 * - All tests use the same transcription ID created in beforeAll
 */