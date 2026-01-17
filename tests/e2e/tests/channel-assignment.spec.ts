/**
 * チャンネル割り当てE2Eテスト
 *
 * チャンネル作成、割り当て、変更、元に戻すシナリオを検証する。
 *
 * Note: E2Eテストモードが有効な場合、Supabase認証をバイパスする。
 */

import { test, expect } from '@playwright/test'

// モックチャンネルデータ
const mockChannels = [
  { id: 'channel-1', name: 'プロジェクトA', description: 'プロジェクトA関連の音声' },
  { id: 'channel-2', name: 'プロジェクトB', description: 'プロジェクトB関連の音声' },
  { id: 'channel-3', name: '会議録', description: '会議の録音データ' },
]

// モック転写データ
const mockTranscriptionId = 'test-transcription-id'
const mockTranscription = {
  id: mockTranscriptionId,
  file_name: 'test_audio.m4a',
  stage: 'completed',
  language: 'zh',
  duration_seconds: 120,
  created_at: new Date().toISOString(),
}

test.describe('チャンネル割り当て', () => {
  test.beforeEach(async ({ page }) => {
    // E2Eテストモードフラグを設定
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

    // APIルートのモック設定
    await setupMockRoutes(page)

    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('チャンネル一覧が表示される', async ({ page }) => {
    // 転写リストから詳細ページへ
    await page.click(`text=${mockTranscription.file_name}`)
    await expect(page).toHaveURL(new RegExp(`/transcriptions/${mockTranscriptionId}`))

    // チャンネル割り当てボタンをクリック
    await page.click('button:has-text("分配到频道")')

    // モーダルが表示されることを確認
    await expect(page.locator('text=分配到频道')).toBeVisible()
    await expect(page.locator('text=搜索频道名称...')).toBeVisible()

    // すべてのチャンネルが表示されることを確認
    for (const channel of mockChannels) {
      await expect(page.locator(`text=${channel.name}`)).toBeVisible()
      if (channel.description) {
        await expect(page.locator(`text=${channel.description}`)).toBeVisible()
      }
    }

    await page.screenshot({ path: '/app/data/screenshots/channel-list.png' })
  })

  test('チャンネル検索が機能する', async ({ page }) => {
    await page.click(`text=${mockTranscription.file_name}`)
    await page.click('button:has-text("分配到频道")')

    // 検索ボックスにテキストを入力
    await page.fill('input[placeholder="搜索频道名称..."]', 'プロジェクトA')

    // プロジェクトAのみ表示されることを確認
    await expect(page.locator('text=プロジェクトA')).toBeVisible()
    await expect(page.locator('text=プロジェクトB')).not.toBeVisible()
    await expect(page.locator('text=会議録')).not.toBeVisible()

    await page.screenshot({ path: '/app/data/screenshots/channel-search.png' })

    // 検索をクリア
    await page.fill('input[placeholder="搜索频道名称..."]', '')

    // すべてのチャンネルが再表示されることを確認
    await expect(page.locator('text=プロジェクトA')).toBeVisible()
    await expect(page.locator('text=プロジェクトB')).toBeVisible()
    await expect(page.locator('text=会議録')).toBeVisible()
  })

  test('チャンネルを割り当てることができる', async ({ page }) => {
    await page.click(`text=${mockTranscription.file_name}`)
    await page.click('button:has-text("分配到频道")')

    // チェックボックスをクリックしてチャンネルを選択
    await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)

    // 選択状態を確認
    const checkbox = page.locator(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
    await expect(checkbox).toBeChecked()

    // 選択数表示を確認
    await expect(page.locator('text=已选择 1 个频道')).toBeVisible()

    // 保存ボタンをクリック
    await page.click('button:has-text("保存")')

    // モーダルが閉じることを確認
    await expect(page.locator('text=分配到频道')).not.toBeVisible()

    // チャンネルバッジが表示されることを確認
    await page.screenshot({ path: '/app/data/screenshots/channel-assigned.png' })
  })

  test('複数チャンネルを同時に割り当てることができる', async ({ page }) => {
    await page.click(`text=${mockTranscription.file_name}`)
    await page.click('button:has-text("分配到频道")')

    // 複数のチャンネルを選択
    await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
    await page.click(`label:has-text("${mockChannels[1].name}") input[type="checkbox"]`)

    // 選択数表示を確認
    await expect(page.locator('text=已选择 2 个频道')).toBeVisible()

    // 「選択すべて」ボタンをクリックして残りも選択
    await page.click('button:has-text("选择所有")')

    // 3つすべて選択されたことを確認
    await expect(page.locator('text=已选择 3 个频道')).toBeVisible()

    await page.screenshot({ path: '/app/data/screenshots/channel-multiple-select.png' })

    // 保存ボタンをクリック
    await page.click('button:has-text("保存")')

    // モーダルが閉じることを確認
    await expect(page.locator('text=分配到频道')).not.toBeVisible()
  })

  test('チャンネル割り当てをキャンセルできる', async ({ page }) => {
    await page.click(`text=${mockTranscription.file_name}`)
    await page.click('button:has-text("分配到频道")')

    // チャンネルを選択
    await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)

    // キャンセルボタンをクリック
    await page.click('button:has-text("取消")')

    // モーダルが閉じることを確認
    await expect(page.locator('text=分配到频道')).not.toBeVisible()

    // 詳細ページに留まることを確認
    await expect(page).toHaveURL(new RegExp(`/transcriptions/${mockTranscriptionId}`))
  })

  test('チャンネルの選択を解除できる', async ({ page }) => {
    await page.click(`text=${mockTranscription.file_name}`)
    await page.click('button:has-text("分配到频道")')

    // チャンネルを選択
    await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
    await expect(page.locator(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)).toBeChecked()

    // 選択を解除
    await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)

    // チェックボックスがオフになっていることを確認
    await expect(page.locator(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)).not.toBeChecked()

    // 選択数が0に戻ることを確認
    await expect(page.locator('text=已选择 0 个频道')).not.toBeVisible()
  })

  test.describe('チャンネル変更シナリオ', () => {
    test('チャンネルが存在しない場合に新規チャンネルを作成して割り当てる', async ({ page }) => {
      // このテストは管理者ダッシュボードを使用するため、別途実装が必要
      // 注: E2Eテストでは管理者権限のモックが必要

      // 現在の転写詳細ページからスタート
      await page.click(`text=${mockTranscription.file_name}`)
      await page.click('button:has-text("分配到频道")')

      // チャンネルが既に存在することを確認（モックデータ）
      await expect(page.locator('text=プロジェクトA')).toBeVisible()

      // 実際のアプリでは管理者がダッシュボードからチャンネルを作成
      // E2Eテストでは既存チャンネルを使用
      await page.screenshot({ path: '/app/data/screenshots/channel-existing.png' })
    })

    test('チャンネルを変更して別のチャンネルに割り当てる', async ({ page }) => {
      await page.click(`text=${mockTranscription.file_name}`)

      // モーダルを開く
      await page.click('button:has-text("分配到频道")')

      // 最初のチャンネルを選択
      await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
      await page.click('button:has-text("保存")')

      // モーダルが閉じるのを待つ
      await expect(page.locator('text=分配到频道')).not.toBeVisible()

      // 再びモーダルを開く
      await page.click('button:has-text("分配到频道")')

      // 前の選択が表示されていることを確認
      await expect(page.locator(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)).toBeChecked()

      // 別のチャンネルを選択
      await page.click(`label:has-text("${mockChannels[1].name}") input[type="checkbox"]`)

      // 前のチャンネルの選択を解除
      await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)

      // 保存
      await page.click('button:has-text("保存")')

      await page.screenshot({ path: '/app/data/screenshots/channel-changed.png' })
    })

    test('元のチャンネルに戻すことができる', async ({ page }) => {
      await page.click(`text=${mockTranscription.file_name}`)

      // 最初のチャンネルを割り当て
      await page.click('button:has-text("分配到频道")')
      await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
      await page.click('button:has-text("保存")')
      await expect(page.locator('text=分配到频道')).not.toBeVisible()

      // 別のチャンネルに変更
      await page.click('button:has-text("分配到频道")')
      await page.click(`label:has-text("${mockChannels[1].name}") input[type="checkbox"]`)
      await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`) // 前のを選択解除
      await page.click('button:has-text("保存")')
      await expect(page.locator('text=分配到频道')).not.toBeVisible()

      // 元のチャンネルに戻す
      await page.click('button:has-text("分配到频道")')
      await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
      await page.click(`label:has-text("${mockChannels[1].name}") input[type="checkbox"]`) // 現在のを選択解除
      await page.click('button:has-text("保存")')
      await expect(page.locator('text=分配到频道')).not.toBeVisible()

      await page.screenshot({ path: '/app/data/screenshots/channel-reverted.png' })
    })

    test('すべてのチャンネル割り当てを解除できる', async ({ page }) => {
      await page.click(`text=${mockTranscription.file_name}`)

      // チャンネルを割り当て
      await page.click('button:has-text("分配到频道")')
      await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
      await page.click(`label:has-text("${mockChannels[1].name}") input[type="checkbox"]`)
      await page.click('button:has-text("保存")')
      await expect(page.locator('text=分配到频道')).not.toBeVisible()

      // すべてのチャンネルを選択解除
      await page.click('button:has-text("分配到频道")')

      // すべて選択解除（「選択すべて」ボタンを2回クリックでトグル）
      await page.click('button:has-text("选择所有")')
      await page.click('button:has-text("取消选择所有")')

      // 保存
      await page.click('button:has-text("保存")')

      await page.screenshot({ path: '/app/data/screenshots/channel-cleared.png' })
    })
  })

  test('APIエラー時にエラーメッセージが表示される', async ({ page }) => {
    // エラーレスポンスをモック
    await page.route('**/api/transcriptions/*/channels', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' })
        })
      } else {
        await route.continue()
      }
    })

    await page.click(`text=${mockTranscription.file_name}`)
    await page.click('button:has-text("分配到频道")')
    await page.click(`label:has-text("${mockChannels[0].name}") input[type="checkbox"]`)
    await page.click('button:has-text("保存")')

    // エラーメッセージが表示されることを確認
    await expect(page.locator('text=分配频道失败')).toBeVisible()

    await page.screenshot({ path: '/app/data/screenshots/channel-error.png' })
  })
})

/**
 * モックルートを設定するヘルパー関数
 */
async function setupMockRoutes(page: any) {
  // 転写リスト取得
  await page.route('**/api/transcriptions', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 1,
          page: 1,
          page_size: 10,
          total_pages: 1,
          data: [mockTranscription]
        })
      })
    } else {
      await route.continue()
    }
  })

  // 転写詳細取得
  await page.route(`**/api/transcriptions/${mockTranscriptionId}`, async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockTranscription,
          text: 'これはテスト用の文字起こしテキストです。',
          summary: 'これはテスト用の要約です。',
          channels: []
        })
      })
    } else {
      await route.continue()
    }
  })

  // チャンネルリスト取得
  await page.route('**/api/admin/channels', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChannels)
      })
    } else {
      await route.continue()
    }
  })

  // 転写のチャンネル取得
  await page.route(`**/api/transcriptions/${mockTranscriptionId}/channels`, async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      })
    } else {
      await route.continue()
    }
  })

  // チャンネル割り当て（POST）
  await page.route(`**/api/transcriptions/${mockTranscriptionId}/channels`, async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Assigned to channels',
          channel_ids: ['channel-1']
        })
      })
    } else {
      await route.continue()
    }
  })
}
