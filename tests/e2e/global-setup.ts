import { type FullConfig } from '@playwright/test';

/**
 * グローバルセットアップ
 *
 * E2Eテスト用のグローバルセットアップ。
 *
 * Note: Google OAuthのみを使用するため、事前にテストユーザーを作成する必要はありません。
 * E2Eテストモードでは、useAuthフックがモックユーザーを返します。
 */
async function globalSetup(config: FullConfig) {
  console.log('Global setup starting...');
  console.log('Using Google OAuth - no pre-created test user needed.');
  console.log('E2E test mode will use mock user from useAuth hook.');
  console.log('Global setup completed.');
}

export default globalSetup;
