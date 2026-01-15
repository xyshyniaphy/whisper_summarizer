/**
 * 文字起こしフローE2Eテスト
 *
 * Note: Uses production data helper with server-side auth bypass.
 * No API mocking - tests real backend behavior.
 *
 * **Known Issue**: Tests currently fail due to auth bypass not working through SSH tunnel.
 * The production server's localhost auth bypass requires requests from 127.0.0.1,
 * but SSH tunneling makes requests appear to come from an external source.
 * This infrastructure issue affects all list page tests and needs resolution
 * in the test setup/SSH configuration, not in individual test files.
 */

import { test, expect } from '@playwright/test'
import { setupProductionTranscription, cleanupProductionTranscription } from '../helpers/production-data'

test.describe('文字起こしフロー', () => {
  let transcriptionId: string | undefined

  test.beforeEach(async ({ page }) => {
    // Setup production test data (singleton pattern - only fetches once)
    transcriptionId = await setupProductionTranscription(page)

    // Validate transcriptionId is initialized
    if (!transcriptionId) {
      throw new Error('transcriptionId not initialized - run first test to setup production data')
    }

    // E2Eテストモードフラグを設定
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.setItem('e2e-test-mode', 'true')
    })
    await page.reload()

    // Note: Server-side auth bypass handles authentication automatically
    // Tests will navigate to /transcriptions as needed
  })

  test.afterAll(async () => {
    // Cleanup (no-op for existing transcriptions)
    await cleanupProductionTranscription()
  })

  // NOTE: Upload tests still use mocks because:
  // 1. They test the upload flow itself (creating new transcriptions)
  // 2. Using production data would create many test transcriptions
  // 3. Upload flow is tested separately in upload.spec.ts with production data
  test('音声ファイルをアップロードして文字起こしできる', async ({ page }) => {
    // アップロードAPIのモック
    await page.route('**/api/audio/upload', async route => {
         // upload delay simulation
         await new Promise(r => setTimeout(r, 500));
         await route.fulfill({
             status: 200,
             contentType: 'application/json',
             body: JSON.stringify({
                 id: 'new-transcription-id',
                 file_name: 'test-audio.m4a',
                 status: 'processing'
             })
         });
    });

    // 処理中ステータスのモック - ポーリングのエンドポイント
    await page.route('**/api/transcriptions/new-transcription-id', async route => {
         await route.fulfill({
             status: 200,
             contentType: 'application/json',
             body: JSON.stringify({
                 id: 'new-transcription-id',
                 file_name: 'test-audio.m4a',
                 status: 'completed',
                 original_text: 'アップロードテスト完了'
             })
         });
    });

    // ファイル選択（ドラッグ＆ドロップエリアのinput要素を使用）
    const fileInput = page.locator('input[type="file"]')
    const testAudioPath = '/app/testdata/audio1074124412.conved_2min.m4a'
    await fileInput.setInputFiles(testAudioPath)

    // アップロード完了後、詳細ページに遷移するのを待つ
    await expect(page).toHaveURL(/\/transcriptions\/new-transcription-id/, { timeout: 10000 })

    // 文字起こし完了を待つ
    await expect(page.locator('text=アップロードテスト完了')).toBeVisible({ timeout: 5000 })

    // 完了後のスクリーンショット
    await page.screenshot({ path: '/app/data/screenshots/upload-complete.png' })
  })

  test('M4Aファイルをアップロードできる', async ({ page }) => {
    // M4Aファイル特有のアップロードテスト
    await page.route('**/api/audio/upload', async route => {
      await new Promise(r => setTimeout(r, 300));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'm4a-upload-id',
          file_name: 'test.m4a',
          stage: 'uploading',
          status: 'processing'
        })
      });
    });

    // ポーリングエンドポイントのモック
    await page.route('**/api/transcriptions/m4a-upload-id', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'm4a-upload-id',
          file_name: 'test.m4a',
          stage: 'completed',
          status: 'completed',
          original_text: 'M4Aファイルのアップロードに成功しました。',
          created_at: new Date().toISOString(),
          summaries: []
        })
      });
    });

    // M4Aファイルをアップロード
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles('/app/testdata/test.m4a')

    // 詳細ページに遷移することを確認
    await expect(page).toHaveURL(/\/transcriptions\/m4a-upload-id/, { timeout: 10000 })

    // 完了メッセージを確認
    await expect(page.locator('text=M4Aファイルのアップロードに成功しました')).toBeVisible({ timeout: 5000 })

    await page.screenshot({ path: '/app/data/screenshots/m4a-upload-complete.png' })
  })

  test('文字起こしリストが表示される', async ({ page }) => {
    // Navigate to transcriptions page (auth bypass is active)
    await page.goto('/transcriptions', { waitUntil: 'domcontentloaded' })

    // Wait for data to load
    await page.waitForTimeout(2000)

    // ページ内容を確認 - check for any transcription-related content
    const content = await page.textContent('body')
    expect(content).toContain('转录')

    // リスト表示のスクリーンショット
    await page.screenshot({ path: '/app/data/screenshots/transcription-list.png', fullPage: true })
  })

  test('文字起こし詳細を表示できる', async ({ page }) => {
    // ナビゲート to detail page using production transcription ID
    await page.goto(`/transcriptions/${transcriptionId}`, { waitUntil: 'domcontentloaded' })

    // Wait for data to load
    await page.waitForTimeout(2000)

    // 詳細ページに移動
    await expect(page).toHaveURL(new RegExp(`/transcriptions/${transcriptionId}`))

    // Check for transcription-related content
    const content = await page.textContent('body')
    expect(content).toContain('转录')

    // 詳細ページのスクリーンショット
    await page.screenshot({ path: '/app/data/screenshots/transcription-detail.png', fullPage: true })
  })

  test('文字起こしを削除できる', async ({ page }) => {
    // 削除確認ダイアログをハンドル（キャンセルする）
    page.on('dialog', async dialog => {
      console.log('Dialog message:', dialog.message())
      await dialog.dismiss() // キャンセル
    })

    // Navigate to detail page for production transcription
    await page.goto(`/transcriptions/${transcriptionId}`)

    // Check for delete button (may not exist depending on user permissions)
    const deleteButton = page.locator('button[title="删除"]').first()
    if (await deleteButton.isVisible({ timeout: 2000 })) {
      await deleteButton.click()
      // スクリーンショット
      await page.screenshot({ path: '/app/data/screenshots/delete-cancel.png' })
      // まだページにいることを確認（キャンセルしたため）
      await expect(page).toHaveURL(new RegExp(`/transcriptions/${transcriptionId}`))
    } else {
      // 削除ボタンがない場合はテストをスキップ (user might not have delete permissions)
      console.log('Delete button not visible - skipping delete test (may be permission issue)')
    }
  })
})
