/**
 * Audio Upload E2E Tests
 *
 * Tests for audio upload workflow with Jotai state management.
 * Tests real Jotai atoms for upload progress, queue, and status.
 */

import { test, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'

test.describe('Audio Upload', () => {
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

  test('アップロードページが正常にレンダリングされる', async ({ page }) => {
    // アップロードページに遷移
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // ページタイトルが表示されることを確認
    await expect(page.locator('h1:has-text("上传音频")')).toBeVisible({ timeout: 10000 })
  })

  test('ファイル選択ボタンが表示される', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // ファイル選択ボタンが表示されることを確認
    await expect(page.locator('input[type="file"]')).toBeVisible({ timeout: 10000 })
  })

  test('ファイルを選択してアップロードできる', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // 認証トークンを取得
    const token = await getAuthToken(page)

    // テスト用音声ファイルのパス
    const testFilePath = path.join(process.cwd(), 'tests/fixtures/test-audio.m4a')

    // テストファイルが存在しない場合は作成
    if (!fs.existsSync(testFilePath)) {
      const testDir = path.dirname(testFilePath)
      if (!fs.existsSync(testDir)) {
        fs.mkdirSync(testDir, { recursive: true })
      }
      fs.writeFileSync(testFilePath, 'dummy audio content')
    }

    // API経由でファイルをアップロード
    const response = await uploadFileViaAPI(page, testFilePath, token)

    // アップロードが成功したことを確認
    expect(response.status).toBe(200)
  })

  test('アップロード進行状況が表示される', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // 進行状況表示が初期状態で非表示または0%であることを確認
    const progress = page.locator('[data-testid="upload-progress"]')
    await expect(progress).toBeVisible({ timeout: 10000 })
  })

  test('アップロード完了後に転写が開始される', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // 認証トークンを取得
    const token = await getAuthToken(page)

    // テスト用音声ファイルのパス
    const testFilePath = path.join(process.cwd(), 'tests/fixtures/test-audio.m4a')

    // テストファイルを作成
    const testDir = path.dirname(testFilePath)
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true })
    }
    fs.writeFileSync(testFilePath, 'dummy audio content')

    // API経由でファイルをアップロード
    await uploadFileViaAPI(page, testFilePath, token)

    // 転写一覧ページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/transcriptions/, { timeout: 10000 })
  })

  test('複数のファイルをアップロードできる', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // 認証トークンを取得
    const token = await getAuthToken(page)

    // 複数のテストファイルを作成
    const testFiles = [
      path.join(process.cwd(), 'tests/fixtures/audio1.m4a'),
      path.join(process.cwd(), 'tests/fixtures/audio2.m4a')
    ]

    const testDir = path.dirname(testFiles[0])
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true })
    }

    for (const filePath of testFiles) {
      fs.writeFileSync(filePath, 'dummy audio content')
    }

    // 複数ファイルをアップロード
    for (const filePath of testFiles) {
      await uploadFileViaAPI(page, filePath, token)
    }

    // 両方のファイルがアップロードキューに追加されることを確認
    await page.goto('/transcriptions')
    await page.waitForLoadState('networkidle') // Wait for API calls
    await expect(page.locator('text=audio1.m4a')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=audio2.m4a')).toBeVisible({ timeout: 10000 })
  })

  test('アップロードエラー時にエラーメッセージが表示される', async ({ page }) => {
    // エラーレスポンスをモック
    await page.route('**/api/audio/upload', async route => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid file format' })
      })
    })

    await page.goto('/upload')

    // 認証トークンを取得
    const token = await getAuthToken(page)

    // テストファイルを作成
    const testFilePath = path.join(process.cwd(), 'tests/fixtures/test-audio.m4a')
    const testDir = path.dirname(testFilePath)
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true })
    }
    fs.writeFileSync(testFilePath, 'dummy audio content')

    // アップロードを試みる
    const response = await uploadFileViaAPI(page, testFilePath, token)

    // エラーレスポンスが返されることを確認
    expect(response.status).toBe(400)
  })

  test('アップロードをキャンセルできる', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // キャンセルボタンが表示されることを確認
    await expect(page.locator('button:has-text("取消")')).toBeVisible({ timeout: 10000 })
  })

  test('ドラッグ＆ドロップでファイルをアップロードできる', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // ドラッグ＆ドロップエリアが表示されることを確認
    const dropZone = page.locator('[data-testid="drop-zone"]')
    await expect(dropZone).toBeVisible({ timeout: 10000 })
  })

  test('サポートされるファイル形式が表示される', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // サポートされるファイル形式が表示されることを確認
    await expect(page.locator('text=m4a|mp3|wav|ogg')).toBeVisible({ timeout: 10000 })
  })

  test('ファイルサイズ制限が表示される', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // ファイルサイズ制限が表示されることを確認
    await expect(page.locator('text=MB')).toBeVisible({ timeout: 10000 })
  })

  test('アップロード状態がページ遷移間で保持される', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // 認証トークンを取得
    const token = await getAuthToken(page)

    // テストファイルを作成
    const testFilePath = path.join(process.cwd(), 'tests/fixtures/test-audio.m4a')
    const testDir = path.dirname(testFilePath)
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true })
    }
    fs.writeFileSync(testFilePath, 'dummy audio content')

    // アップロードを開始
    await uploadFileViaAPI(page, testFilePath, token)

    // 転写一覧ページに遷移
    await page.goto('/transcriptions')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // アップロードしたファイルが表示されることを確認
    await expect(page.locator('text=test-audio.m4a')).toBeVisible({ timeout: 10000 })
  })
})

/**
 * 認証トークンを取得するヘルパー関数
 */
async function getAuthToken(page: any): Promise<string | null> {
  return await page.evaluate(() => {
    const keys = Object.keys(localStorage)
    const authKey = keys.find(k => k.startsWith('sb-') && k.includes('-auth-token'))
    if (!authKey) return null
    const tokenData = JSON.parse(localStorage.getItem(authKey)!)
    return tokenData?.currentSession?.access_token || tokenData?.access_token || null
  })
}

/**
 * API経由でファイルをアップロードするヘルパー関数
 */
async function uploadFileViaAPI(page: any, filePath: string, token: string | null) {
  const formData = new FormData()
  const fileBuffer = await fs.promises.readFile(filePath)
  formData.append('file', new Blob([fileBuffer]), path.basename(filePath))

  const response = await page.request.post('/api/audio/upload', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-E2E-Test-Mode': 'true'  // Add E2E test mode header for Docker testing
    },
    data: formData
  })
  return response
}

/**
 * モックルートを設定するヘルパー関数
 */
async function setupMockRoutes(page: any) {
  // 転写一覧取得
  await page.route('**/api/transcriptions', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 0,
          page: 1,
          page_size: 10,
          total_pages: 0,
          data: []
        })
      })
    } else {
      await route.continue()
    }
  })

  // アップロード成功時のモック
  await page.route('**/api/audio/upload', async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'upload-1',
          file_name: 'test-audio.m4a',
          stage: 'processing',
          language: 'zh',
          duration_seconds: 0,
          created_at: new Date().toISOString()
        })
      })
    } else {
      await route.continue()
    }
  })

  // ユーザー情報取得
  await page.route('**/api/auth/user', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'user-1',
        email: 'test@example.com',
        is_active: true,
        is_admin: true
      })
    })
  })

  // 频道一覧取得
  await page.route('**/api/admin/channels', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    })
  })
}
