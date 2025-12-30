/**
 * 認証フローE2Eテスト
 * 
 * ユーザー登録、ログイン、ログアウトの
 * エンドツーエンドフローをテストする。
 */

import { test, expect } from '@playwright/test'

test.describe('認証フロー', () => {
  test.beforeEach(async ({ page }) => {
    // トップページにアクセス
    await page.goto('/')
  })

  test('新規ユーザーがサインアップできる', async ({ page }) => {
    // サインアップページに移動
    await page.click('text=サインアップ')

    // フォームに入力
    const timestamp = Date.now()
    const email = `test-${timestamp}@example.com`
    const password = 'TestPassword123!'

    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)

    // サインアップボタンをクリック
    await page.click('button[type="submit"]')

    // 確認メール送信メッセージが表示される
    await expect(page.locator('text=確認メールを送信しました')).toBeVisible({ timeout: 10000 })
  })

  test('既存ユーザーがログインできる', async ({ page }) => {
    // テスト用のユーザーでログイン
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')

    // ログインボタンをクリック
    await page.click('button[type="submit"]')

    // ダッシュボードにリダイレクトされる
    await expect(page).toHaveURL('/dashboard')
  })

  test('無効な認証情報でログインできない', async ({ page }) => {
    // 誤った認証情報でログイン試行
    await page.fill('input[type="email"]', 'invalid@example.com')
    await page.fill('input[type="password"]', 'wrongpassword')

    // ログインボタンをクリック
    await page.click('button[type="submit"]')

    // エラーメッセージが表示される
    await expect(page.locator('text=認証に失敗しました')).toBeVisible({ timeout: 10000 })
  })

  test('ログアウトできる', async ({ page }) => {
    // まずログイン
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')

    // ダッシュボードに移動
    await expect(page).toHaveURL('/dashboard')

    // ログアウトボタンをクリック
    await page.click('text=ログアウト')

    // ログインページにリダイレクトされる
    await expect(page).toHaveURL('/')
  })
})
