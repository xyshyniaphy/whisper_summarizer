import { type FullConfig } from '@playwright/test';

/**
 * グローバルセットアップ
 * 
 * テスト実行前に実行されるスクリプト。
 * テストユーザーの作成など、環境の初期化を行う。
 */
async function globalSetup(config: FullConfig) {
  console.log('Global setup starting...');
  
  const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceRoleKey) {
    console.warn('⚠️ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found. Skipping test user seeding.');
    console.warn('If tests fail due to missing user, please check .env configuration.');
    return;
  }

  const email = 'test@example.com';
  const password = 'password123';
  
  // Supabase Admin API URL
  // 末尾のスラッシュを削除して結合
  const baseUrl = supabaseUrl.replace(/\/$/, '');
  
  // ヘッダー設定
  const headers = {
    'Authorization': `Bearer ${serviceRoleKey}`,
    'apikey': serviceRoleKey,
    'Content-Type': 'application/json',
  };

  try {
    // 1. ユーザーリストを取得して既存ユーザーを検索
    console.log(`Checking for existing user: ${email}`);
    // admin/users ENDPOINT requires query params? No, list returns page.
    const listRes = await fetch(`${baseUrl}/auth/v1/admin/users`, {
      method: 'GET',
      headers: headers,
    });
    
    if (!listRes.ok) {
        throw new Error(`Failed to list users: ${listRes.status} ${await listRes.text()}`);
    }

    const listData = await listRes.json();
    const existingUser = listData.users.find((u: any) => u.email === email);

    if (existingUser) {
      console.log(`User ${email} exists (ID: ${existingUser.id}). Deleting...`);
      const deleteRes = await fetch(`${baseUrl}/auth/v1/admin/users/${existingUser.id}`, {
        method: 'DELETE',
        headers: headers,
      });
      
      if (!deleteRes.ok) {
        throw new Error(`Failed to delete user: ${deleteRes.status} ${await deleteRes.text()}`);
      }
      console.log('User deleted.');
    }

    // 2. 新規ユーザー作成 (自動確認済み)
    console.log(`Creating user: ${email}`);
    const createRes = await fetch(`${baseUrl}/auth/v1/admin/users`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        email: email,
        password: password,
        email_confirm: true,
        user_metadata: { name: 'Test User' }
      }),
    });

    if (!createRes.ok) {
        // 422 Unprocessable Entity - User already registered? (Concurrency case)
        if (createRes.status === 422) {
             console.log('User creation returned 422, possibly already exists now. proceeding.');
        } else {
            throw new Error(`Failed to create user: ${createRes.status} ${await createRes.text()}`);
        }
    } else {
        const userData = await createRes.json();
        console.log(`User created successfully (ID: ${userData.id}).`);
    }

  } catch (error) {
    console.error('Error during global setup:', error);
    // Setup failure should usually fail the tests, but strictly speaking we might want to continue 
    // if maybe connection was bad but tests might work (unlikely).
    // Throwing error stops tests.
    throw error;
  }
  
  console.log('Global setup completed.');
}

export default globalSetup;
