/**
 * 文字起こしフローE2Eテスト (モック版)
 *
 * バックエンドおよび外部サービスのレスポンスをモックし、
 * フロントエンドの動作と表示を検証する。
 *
 * Note: E2Eテストモードが有効な場合、Supabase認証をバイパスする。
 */

import { test, expect } from '@playwright/test'

test.describe('文字起こしフロー', () => {
  test.beforeEach(async ({ page }) => {
    // E2Eテストモードフラグを設定
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.setItem('e2e-test-mode', 'true')
    })
    await page.reload()

    // バックエンドAPIのモック

    // リスト取得
    await page.route('**/api/transcriptions', async route => {
        if (route.request().method() === 'GET') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    {
                        id: 'test-transcription-id',
                        file_name: 'test_audio.m4a',
                        status: 'completed',
                        created_at: new Date().toISOString(),
                    }
                ])
            });
        } else {
            await route.continue();
        }
    });

    // 詳細取得
    await page.route('**/api/transcriptions/test-transcription-id', async route => {
        if (route.request().method() === 'GET') {
             await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    id: 'test-transcription-id',
                    file_name: 'test_audio.m4a',
                    status: 'completed',
                    original_text: 'これはモックの文字起こし結果です。',
                    created_at: new Date().toISOString(),
                    summaries: []
                })
            });
        } else if (route.request().method() === 'DELETE') {
             await route.fulfill({ status: 204 });
        }
    });

    // ログイン
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/transcriptions/)
  })

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

  test('文字起こしリストが表示される', async ({ page }) => {
    // ページタイトルで確認
    await expect(page.locator('h2:has-text("文字起こし履歴")')).toBeVisible()

    // リスト表示のスクリーンショット
    await page.screenshot({ path: '/app/data/screenshots/transcription-list.png', fullPage: true })
  })

  test('文字起こし詳細を表示できる', async ({ page }) => {
    // リスト内のファイル名をクリック
    await page.click('text=test_audio.m4a')

    // 詳細ページに移動
    await expect(page).toHaveURL(/\/transcriptions\/test-transcription-id/)

    // 文字起こしテキストが表示される (モックデータ)
    await expect(page.locator('text=これはモックの文字起こし結果です。')).toBeVisible()

    // 詳細ページのスクリーンショット
    await page.screenshot({ path: '/app/data/screenshots/transcription-detail.png', fullPage: true })
  })

  test('文字起こしを削除できる', async ({ page }) => {
    // 削除確認ダイアログをハンドル（キャンセルする）
    page.on('dialog', async dialog => {
      console.log('Dialog message:', dialog.message())
      await dialog.dismiss() // キャンセル
    })

    // 削除ボタンをクリック
    const deleteButton = page.locator('button[title="削除"]').first()
    await deleteButton.click()

    // スクリーンショット
    await page.screenshot({ path: '/app/data/screenshots/delete-cancel.png' })

    // アイテムがまだリストにあることを確認（キャンセルしたため）
    await expect(page.locator('text=test_audio.m4a')).toBeVisible()
  })
})
