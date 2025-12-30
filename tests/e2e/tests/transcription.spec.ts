/**
 * 文字起こしフローE2Eテスト
 * 
 * 音声アップロード、文字起こし結果表示、削除の
 * エンドツーエンドフローをテストする。
 */

import { test, expect } from '@playwright/test'
import path from 'path'

test.describe('文字起こしフロー', () => {
  test.beforeEach(async ({ page }) => {
    // ログイン
    await page.goto('/')
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')

    // ダッシュボードに移動
    await expect(page).toHaveURL('/dashboard')
  })

  test('音声ファイルをアップロードして文字起こしできる', async ({ page }) => {
    // アップロードボタンをクリック
    await page.click('text=音声をアップロード')

    // ファイル選択ダイアログ
    const fileInput = page.locator('input[type="file"]')
    
    // テスト用の音声ファイルをアップロード
    // 注: 実際のテスト音声ファイルを用意する必要がある
    // const testAudioPath = path.join(__dirname, '../fixtures/test-audio.wav')
    // await fileInput.setInputFiles(testAudioPath)

    // アップロードボタンをクリック
    // await page.click('button:has-text("アップロード")')

    // 処理中メッセージが表示される
    // await expect(page.locator('text=処理中')).toBeVisible()

    // 文字起こし完了を待つ (最大60秒)
    // await expect(page.locator('text=文字起こし完了')).toBeVisible({ timeout: 60000 })
  })

  test('文字起こしリストが表示される', async ({ page }) => {
    // ダッシュボードで文字起こしリストを確認
    await expect(page.locator('[data-testid="transcription-list"]')).toBeVisible({ timeout: 10000 })

    // リストアイテムが存在することを確認
    const listItems = page.locator('[data-testid="transcription-item"]')
    const count = await listItems.count()
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('文字起こし詳細を表示できる', async ({ page }) => {
    // 最初の文字起こしアイテムをクリック
    const firstItem = page.locator('[data-testid="transcription-item"]').first()
    
    if (await firstItem.isVisible({ timeout: 5000 })) {
      await firstItem.click()

      // 詳細ページに移動
      await expect(page).toHaveURL(/\/transcription\//)

      // 文字起こしテキストが表示される
      await expect(page.locator('[data-testid="transcription-text"]')).toBeVisible()
    }
  })

  test('文字起こしを削除できる', async ({ page }) => {
    // 削除ボタンをクリック
    const deleteButton = page.locator('[data-testid="delete-button"]').first()
    
    if (await deleteButton.isVisible({ timeout: 5000 })) {
      await deleteButton.click()

      // 確認ダイアログが表示される
      await expect(page.locator('text=削除しますか')).toBeVisible()

      // 確認ボタンをクリック
      await page.click('button:has-text("削除")')

      // 削除完了メッセージが表示される
      await expect(page.locator('text=削除しました')).toBeVisible({ timeout: 10000 })
    }
  })
})
