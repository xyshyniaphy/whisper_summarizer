# Whisper Summarizer Frontend Enhancement Specification

## 概要 (Overview)

既存のWhisper Summarizerフロントエンドを拡張し、以下の機能を追加します：

- **ユーザーロール管理**: User/Adminの2つのロールとロールベースアクセス制御
- **管理パネル**: 管理者用ダッシュボードとユーザー管理機能
- **長文文字起こし表示**: 1000行以上の文字起こしを遅延ロードで表示
- **テーマ切り替え**: ライト/ダークモードの切り替え機能
- **PPT出力**: 文字起こしテキストからPowerPointファイルを生成
- **中国語UI**: すべてのインターフェースを中国語で表示

## 要件確認

| 項目 | 要件 |
|------|------|
| ユーザーロール | 2つ (User, Admin) |
| 文字起こし長さ | 1000+ 行 |
| 表示方法 | 遅延ロード (Lazy Loading) |
| PPT生成 | 直接テキスト変換、トピック別、カスタマイズ可能 |
| UI言語 | 100% 中国語 |

---

## 1. ロールベースアクセス制御 (RBAC)

### 1.1 ロール定義

| ロール | 権限 |
|--------|------|
| **User** | - 自分の文字起こしのみ閲覧・管理可能 |
| **Admin** | - 全ユーザーの文字起こしを閲覧・削除可能<br>- ユーザー管理（ロール変更等）<br>- シ統計の閲覧 |

### 1.2 データベース設計

**Supabase Auth User Metadata に role を保存:**
```typescript
// User metadata structure
user.user_metadata = {
  full_name: "string",
  role: "user" | "admin"  // 新規追加
}
```

### 1.3 実装方針

```typescript
// hooks/useAuth.ts の拡張
interface AuthState {
  user: User | null
  session: Session | null
  loading: boolean
  role: 'user' | 'admin' | null  // 新規追加
}

// Supabase user metadata から role を取得
const role = user?.user_metadata?.role || 'user'
```

```typescript
// components/auth/ProtectedRoute.tsx (新規作成)
interface ProtectedRouteProps {
  children: React.ReactNode
  requireRole?: 'user' | 'admin'
}

function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
  const { user, role, loading } = useAuth()
  
  if (loading) return <Loader />
  if (!user) return <Navigate to="/login" />
  if (requireRole === 'admin' && role !== 'admin') {
    return <Navigate to="/dashboard" />
  }
  return <>{children}</>
}
```

### 1.4 ルーティング構造

```typescript
// App.tsx 更新
<Routes>
  {/* パブリックルート */}
  <Route path="/login" element={<Login />} />
  
  {/* ユーザールート (認証必要) */}
  <Route path="/dashboard" element={
    <ProtectedRoute><Dashboard /></ProtectedRoute>
  } />
  <Route path="/transcriptions" element={
    <ProtectedRoute><TranscriptionList /></ProtectedRoute>
  } />
  <Route path="/transcriptions/:id" element={
    <ProtectedRoute><TranscriptionDetail /></ProtectedRoute>
  } />
  
  {/* 管理者ルート (adminロール必要) */}
  <Route path="/admin" element={
    <ProtectedRoute requireRole="admin"><AdminDashboard /></ProtectedRoute>
  } />
  <Route path="/admin/users" element={
    <ProtectedRoute requireRole="admin"><UserManagement /></ProtectedRoute>
  } />
  <Route path="/admin/all-transcriptions" element={
    <ProtectedRoute requireRole="admin"><AllTranscriptions /></ProtectedRoute>
  } />
</Routes>
```

---

## 2. テーマシステム (Light/Dark Mode)

### 2.1 実装方針

Mantine のネイティブ機能を使用:

```typescript
// main.tsx
import { MantineProvider, ColorSchemeScript } from '@mantine/core'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <>
    <ColorSchemeScript defaultColorScheme="light" />
    <MantineProvider defaultColorScheme="light">
      <App />
    </MantineProvider>
  </>
)
```

```typescript
// components/theme/ThemeToggle.tsx (新規作成)
import { ActionIcon, useMantineColorScheme, useComputedColorScheme } from '@mantine/core'
import { IconSun, IconMoon } from '@tabler/icons-react'

export function ThemeToggle() {
  const { setColorScheme } = useMantineColorScheme()
  const computedColorScheme = useComputedColorScheme('light')
  
  return (
    <ActionIcon
      onClick={() => setColorScheme(computedColorScheme === 'dark' ? 'light' : 'dark')}
      variant="default"
      size="lg"
    >
      {computedColorScheme === 'dark' ? <IconSun /> : <IconMoon />}
    </ActionIcon>
  )
}
```

### 2.2 レイアウト構造

```typescript
// components/layout/AppShell.tsx (新規作成)
import { AppShell as MantineAppShell, Header, Navbar } from '@mantine/core'
import { ThemeToggle } from '../theme/ThemeToggle'

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth()
  
  return (
    <MantineAppShell
      header={
        <Header height={60} padding="xs">
          <Group justify="space-between">
            <Title order={3}>Whisper Summarizer</Title>
            <Group gap="xs">
              <ThemeToggle />
              {user && <Button onClick={signOut}>ログアウト</Button>}
            </Group>
          </Group>
        </Header>
      }
    >
      {children}
    </MantineAppShell>
  )
}
```

---

## 3. 長文文字起こし表示 (1000+ 行)

### 3.1 問題点

現在の実装:
- 最初の200行のみ表示 (`getDisplayText()`関数)
- 残りは「ダウンロードしてください」と表示
- 1000+行の文字起こしに対応していない

### 3.2 解決策: 遅延ロード + セクション別表示

**アプローチ:**

1. **トピック別セクション分割** (Mantine Accordion)
2. **Intersection Observer** による遅延ロード
3. **仮想リスト** (オプション: @tanstack/react-virtual)

```typescript
// components/transcription/LazyTranscriptionContent.tsx (新規作成)
import { useState, useEffect, useRef } from 'react'
import { Accordion, Text, Box } from '@mantine/core'

interface TopicSection {
  id: string
  title: string  // タイムスタンプまたはトピック名
  content: string
  loaded: boolean
}

// 文字起こしをトピック別に分割
function parseTopics(text: string): TopicSection[] {
  const lines = text.split('\n')
  const topics: TopicSection[] = []
  let currentTopic: string[] = []
  let topicIndex = 0
  
  // タイムスタンプパターンまたは空行で分割
  for (const line of lines) {
    if (line.match(/^\[\d{2}:\d{2}:\d{2}\]/) || line.trim() === '') {
      if (currentTopic.length > 0) {
        topics.push({
          id: `topic-${topicIndex++}`,
          title: currentTopic[0] || `セクション ${topicIndex}`,
          content: currentTopic.join('\n'),
          loaded: false
        })
        currentTopic = []
      }
      currentTopic.push(line)
    } else {
      currentTopic.push(line)
    }
  }
  
  // 最後のセクション
  if (currentTopic.length > 0) {
    topics.push({
      id: `topic-${topicIndex}`,
      title: currentTopic[0] || `セクション ${topicIndex}`,
      content: currentTopic.join('\n'),
      loaded: false
    })
  }
  
  return topics
}

export function LazyTranscriptionContent({ text }: { text: string }) {
  const [topics, setTopics] = useState<TopicSection[]>(() => parseTopics(text))
  
  const loadSection = (sectionId: string) => {
    setTopics(prev => prev.map(topic => 
      topic.id === sectionId ? { ...topic, loaded: true } : topic
    ))
  }
  
  return (
    <Accordion>
      {topics.map((topic, index) => (
        <Accordion.Item 
          key={topic.id} 
          value={topic.id}
          onChange={() => {
            if (!topic.loaded) {
              loadSection(topic.id)
            }
          }}
        >
          <Accordion.Control>
            <Group>
              <Text fw={500}>{topic.title}</Text>
              {topic.lines && <Text size="sm" c="dimmed">{topic.lines}行</Text>}
            </Group>
          </Accordion.Control>
          <Accordion.Panel>
            {topic.loaded ? (
              <Text style={{ whiteSpace: 'pre-wrap' }}>
                {topic.content}
              </Text>
            ) : (
              <Text c="dimmed">読み込み中...</Text>
            )}
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion>
  )
}
```

### 3.3 仮想リスト（オプション）

非常に長いリスト（10,000行以上）の場合:

```bash
npm install @tanstack/react-virtual
```

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

function VirtualizedTranscription({ lines }: { lines: string[] }) {
  const parentRef = useRef<HTMLDivElement>(null)
  
  const virtualizer = useVirtualizer({
    count: lines.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 20,  // 1行あたりの推定高さ
    overscan: 5
  })
  
  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`
            }}
          >
            <Text>{lines[virtualRow.index]}</Text>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 4. ダウンロード機能拡張 (TXT, SRT, PPT)

### 4.1 既存機能

- **TXT ダウンロード**: 実装済み
- **SRT ダウンロード**: 実装済み

### 4.2 PPT生成 (新規)

**ライブラリ:** PptxGenJS

```bash
npm install pptxgenjs
npm install --save-dev @types/pptxgenjs
```

**実装:**

```typescript
// components/transcription/PPTGenerator.tsx (新規作成)
import pptxgen from 'pptxgenjs'
import { Button, Modal, Select, NumberInput } from '@mantine/core'
import { IconFilePresentation } from '@tabler/icons-react'
import { useState } from 'react'

interface PPTOptions {
  template: 'simple' | 'professional' | 'modern'
  slidesPerTopic: number
  includeSummary: boolean
}

export function PPTGenerator({ transcription }: { transcription: Transcription }) {
  const [opened, setOpened] = useState(false)
  const [options, setOptions] = useState<PPTOptions>({
    template: 'simple',
    slidesPerTopic: 1,
    includeSummary: true
  })
  const [generating, setGenerating] = useState(false)
  
  // 文字起こしをトピック別に分割
  const parseTopics = (text: string): Array<{ title: string; content: string }> => {
    const lines = text.split('\n')
    const topics: Array<{ title: string; content: string }> = []
    let currentContent: string[] = []
    let currentTitle = 'イントロダクション'
    
    for (const line of lines) {
      // タイムスタンプパターン
      const timeMatch = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.+)$/)
      if (timeMatch) {
        if (currentContent.length > 0) {
          topics.push({ title: currentTitle, content: currentContent.join('\n') })
        }
        currentTitle = timeMatch[2] || timeMatch[1]
        currentContent = []
      } else if (line.trim() === '') {
        // 空行でセクション区切り
        if (currentContent.length > 0) {
          topics.push({ title: currentTitle, content: currentContent.join('\n') })
          currentContent = []
        }
      } else {
        currentContent.push(line)
      }
    }
    
    // 最後のセクション
    if (currentContent.length > 0) {
      topics.push({ title: currentTitle, content: currentContent.join('\n') })
    }
    
    return topics
  }
  
  const generatePPT = async () => {
    setGenerating(true)
    
    try {
      const pptx = new pptxgen()
      
      // タイトルスライド
      const titleSlide = pptx.addSlide()
      titleSlide.addText(transcription.file_name, {
        x: 1,
        y: 2.5,
        fontSize: 36,
        bold: true,
        align: 'center'
      })
      titleSlide.addText(new Date().toLocaleDateString('zh-CN'), {
        x: 1,
        y: 4,
        fontSize: 18,
        align: 'center'
      })
      
      // トピック別スライド
      const topics = parseTopics(transcription.original_text || '')
      
      topics.forEach((topic, index) => {
        pptx.addSection({ title: topic.title })
        
        const slide = pptx.addSlide({ sectionTitle: topic.title })
        
        // タイトル
        slide.addText(topic.title, {
          x: 0.5,
          y: 0.5,
          fontSize: 24,
          bold: true
        })
        
        // コンテンツ（最大10行、スライドごと）
        const lines = topic.content.split('\n')
        const maxLinesPerSlide = 10
        
        for (let i = 0; i < lines.length; i += maxLinesPerSlide) {
          const slideLines = lines.slice(i, i + maxLinesPerSlide)
          
          slide.addText(slideLines.join('\n'), {
            x: 0.5,
            y: 1.5,
            w: 9,
            h: 4,
            fontSize: 14,
            valign: 'top'
          })
        }
      })
      
      // サマリースライド
      if (options.includeSummary && transcription.summaries?.[0]) {
        const summarySlide = pptx.addSlide()
        summarySlide.addText('要約', {
          x: 0.5,
          y: 0.5,
          fontSize: 24,
          bold: true
        })
        summarySlide.addText(transcription.summaries[0].summary_text, {
          x: 0.5,
          y: 1.5,
          w: 9,
          h: 5,
          fontSize: 14,
          valign: 'top'
        })
      }
      
      // 保存
      await pptx.writeFile({ 
        fileName: `${transcription.file_name}.pptx` 
      })
      
      setOpened(false)
    } catch (error) {
      console.error('PPT生成エラー:', error)
      alert('PPT生成に失敗しました')
    } finally {
      setGenerating(false)
    }
  }
  
  return (
    <>
      <Button
        leftSection={<IconFilePresentation size={18} />}
        onClick={() => setOpened(true)}
        variant="light"
      >
        PPT生成
      </Button>
      
      <Modal opened={opened} onClose={() => setOpened(false)} title="PPT生成オプション">
        <Stack>
          <Select
            label="テンプレート"
            data={[
              { value: 'simple', label: 'シンプル' },
              { value: 'professional', label: 'プロフェッショナル' },
              { value: 'modern', label: 'モダン' }
            ]}
            value={options.template}
            onChange={(value) => setOptions({ ...options, template: value as any })}
          />
          
          <NumberInput
            label="トピックあたりのスライド数"
            min={1}
            max={5}
            value={options.slidesPerTopic}
            onChange={(value) => setOptions({ ...options, slidesPerTopic: value as number })}
          />
          
          <Button
            onClick={generatePPT}
            loading={generating}
            fullWidth
          >
            生成開始
          </Button>
        </Stack>
      </Modal>
    </>
  )
}
```

### 4.3 TranscriptionDetail.tsx の更新

```typescript
// pages/TranscriptionDetail.tsx 更新
import { PPTGenerator } from '../components/transcription/PPTGenerator'

// ... 既存コード ...

// ダウンロードボタングループに追加
<Group gap="xs">
  <Button component="a" href={downloadUrlTxt} download ...>
    テキストをダウンロード
  </Button>
  <Button component="a" href={downloadUrlSrt} download ...>
    字幕（SRT）をダウンロード
  </Button>
  <PPTGenerator transcription={transcription} />  {/* 新規追加 */}
</Group>

// 長文対応: LazyTranscriptionContent を使用
<LazyTranscriptionContent text={transcription.original_text || ''} />
```

---

## 5. 管理者パネル

### 5.1 AdminDashboard.tsx

```typescript
// pages/admin/AdminDashboard.tsx (新規作成)
import { Container, Title, SimpleGrid, Card, Text, Stack } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'

export function AdminDashboard() {
  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => api.getAdminStats()  // 新規エンドポイント
  })
  
  return (
    <Container size="xl" py="xl">
      <Title order={2} mb="lg">管理者ダッシュボード</Title>
      
      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <Card withBorder p="md">
          <Stack>
            <Text size="sm" c="dimmed">総ユーザー数</Text>
            <Text size="xl" fw={500}>{stats?.totalUsers || 0}</Text>
          </Stack>
        </Card>
        
        <Card withBorder p="md">
          <Stack>
            <Text size="sm" c="dimmed">総文字起こし数</Text>
            <Text size="xl" fw={500}>{stats?.totalTranscriptions || 0}</Text>
          </Stack>
        </Card>
        
        <Card withBorder p="md">
          <Stack>
            <Text size="sm" c="dimmed">今月の文字起こし</Text>
            <Text size="xl" fw={500}>{stats?.thisMonthTranscriptions || 0}</Text>
          </Stack>
        </Card>
      </SimpleGrid>
    </Container>
  )
}
```

### 5.2 UserManagement.tsx

```typescript
// pages/admin/UserManagement.tsx (新規作成)
import { Container, Title, Table, Button, Badge } from '@mantine/core'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export function UserManagement() {
  const queryClient = useQueryClient()
  
  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.getAllUsers()  // 新規エンドポイント
  })
  
  const changeRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.changeUserRole(userId, role),  // 新規エンドポイント
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    }
  })
  
  const rows = users?.map(user => (
    <Table.Tr key={user.id}>
      <Table.Td>{user.email}</Table.Td>
      <Table.Td>{user.user_metadata?.full_name || '-'}</Table.Td>
      <Table.Td>
        <Badge color={user.user_metadata?.role === 'admin' ? 'blue' : 'gray'}>
          {user.user_metadata?.role || 'user'}
        </Badge>
      </Table.Td>
      <Table.Td>
        {user.user_metadata?.role !== 'admin' && (
          <Button
            size="xs"
            onClick={() => changeRoleMutation.mutate({ 
              userId: user.id, 
              role: 'admin' 
            })}
          >
            管理者に昇格
          </Button>
        )}
      </Table.Td>
    </Table.Tr>
  ))
  
  return (
    <Container size="xl" py="xl">
      <Title order={2} mb="lg">ユーザー管理</Title>
      
      <Card withBorder>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>メールアドレス</Table.Th>
              <Table.Th>名前</Table.Th>
              <Table.Th>ロール</Table.Th>
              <Table.Th>操作</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>{rows}</Table.Tbody>
        </Table>
      </Card>
    </Container>
  )
}
```

### 5.3 AllTranscriptions.tsx

```typescript
// pages/admin/AllTranscriptions.tsx (新規作成)
// TranscriptionList.tsx と同様の構造で、
// api.getAllTranscriptions() を呼び出す管理者向けページ
```

---

## 6. バックエンドAPI変更

### 6.1 新規エンドポイント

```python
# backend/app/api/admin.py (新規作成)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.supabase import get_current_user
from app.db.session import get_db
from app.models import Transcription, User

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 管理者権限チェック
    if current_user.user_metadata.get("role") != "admin":
        raise HTTPException(403, "管理者権限が必要です")
    
    # 統計情報を返す
    ...

@router.get("/users")
async def get_all_users(...):
    # 全ユーザーリスト
    ...

@router.put("/users/{user_id}/role")
async def change_user_role(...):
    # ユーザーロール変更
    ...

@router.get("/transcriptions")
async def get_all_transcriptions(...):
    # 全ユーザーの文字起こし
    ...
```

### 6.2 Supabase Role設定

```sql
-- ユーザーメタデータに role を追加（最初の管理者設定）
UPDATE auth.users 
SET user_metadata = jsonb_set(
  COALESCE(user_metadata, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email = 'admin@example.com';
```

---

## 7. コンポーネント構造

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx          # Mantine AppShell ラッパー
│   │   ├── AppHeader.tsx         # ヘッダー（ロゴ、テーマ切り替え、ユーザーメニュー）
│   │   └── Sidebar.tsx           # サイドバー（ロール別ナビゲーション）
│   │
│   ├── auth/
│   │   ├── ProtectedRoute.tsx    # ロールベースルート保護
│   │   └── RequireAuth.tsx       # シンプルな認証チェック
│   │
│   ├── theme/
│   │   └── ThemeToggle.tsx       # ライト/ダークモード切り替え
│   │
│   ├── transcription/
│   │   ├── TranscriptionCard.tsx # リストビュー用サマリーカード
│   │   ├── LazyTranscriptionContent.tsx  # 遅延ロードフルコンテンツ
│   │   ├── TopicSection.tsx      # トピック別セクション（折りたたみ）
│   │   ├── DownloadButtons.tsx   # TXT, SRT, PPT ダウンロードグループ
│   │   └── PPTGenerator.tsx      # PPT生成（オプション付き）
│   │
│   └── admin/
│       ├── AdminDashboard.tsx    # 統計概要
│       ├── UserManagement.tsx    # ユーザーリスト＋ロール管理
│       └── AllTranscriptions.tsx # 全ユーザーのコンテンツ表示
```

---

## 8. 新規依存関係

```bash
# PPT生成用
npm install pptxgenjs
npm install --save-dev @types/pptxgenjs

# 仮想リスト（オプション、10000行以上の場合）
npm install @tanstack/react-virtual

# データフェッチ用（推奨）
npm install @tanstack/react-query
```

---

## 9. 実装フェーズ

| フェーズ | 内容 | 複雑さ |
|---------|------|--------|
| **Phase 1** | テーマ切り替え + レイアウト改善 | 中 |
| **Phase 2** | ロールベース RBAC + 管理者パネル | 高 |
| **Phase 3** | 長文文字起こし表示（遅延ロード） | 中 |
| **Phase 4** | PPT生成機能 | 中 |
| **Phase 5** | 中国語UI 完成 | 低 |

---

## 10. 中国語UI

### 既存の中国語テキスト（維持）

- "新しい文字起こし"
- "文字起こし履歴"
- "ステータス"
- "作成日時"
- "削除"
- "文字起こし結果"
- "AI要約"
- など...

### 新規追加の中国語テキスト

```typescript
// テーマ切り替え
"ライトモード" / "ダークモード"

// 管理者パネル
"管理者ダッシュボード"
"ユーザー管理"
"総ユーザー数"
"総文字起こし数"
"今月の文字起こし"
"管理者に昇格"

// PPT生成
"PPT生成"
"テンプレート"
"シンプル"
"プロフェッショナル"
"モダン"
"トピックあたりのスライド数"
"生成開始"

// ロール
"ユーザー"
"管理者"
```

---

## 11. ファイル変更リスト

### 変更ファイル

| ファイル | 変更内容 |
|---------|----------|
| `main.tsx` | MantineProvider, ColorSchemeScript 追加 |
| `App.tsx` | ルーティング構造変更（管理者ルート追加） |
| `hooks/useAuth.ts` | role プロパティ追加 |
| `pages/TranscriptionDetail.tsx` | PPTボタン、遅延ロード表示追加 |

### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `components/layout/AppShell.tsx` | アプリケーションシェル |
| `components/theme/ThemeToggle.tsx` | テーマ切り替えボタン |
| `components/auth/ProtectedRoute.tsx` | ロールベースルート保護 |
| `components/transcription/PPTGenerator.tsx` | PPT生成コンポーネント |
| `components/transcription/LazyTranscriptionContent.tsx` | 遅延ロード表示 |
| `pages/admin/AdminDashboard.tsx` | 管理者ダッシュボード |
| `pages/admin/UserManagement.tsx` | ユーザー管理 |
| `pages/admin/AllTranscriptions.tsx` | 全文字起こし表示 |

### バックエンド変更

| ファイル | 変更内容 |
|---------|----------|
| `backend/app/api/admin.py` | 新規管理者APIエンドポイント |

---

## 12. セットアップ手順

### 1. 依存関係インストール

```bash
cd frontend
npm install pptxgenjs @types/pptxgenjs @tanstack/react-query
```

### 2. 最初の管理者設定

Supabase Dashboard または SQLで実行:

```sql
UPDATE auth.users 
SET user_metadata = jsonb_set(
  COALESCE(user_metadata, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email = 'your-admin@example.com';
```

### 3. 環境変数確認

`.env` に必要な設定:

```bash
# 既存の設定（変更なし）
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
```

---

この仕様書は、以下の要件を満たす包括的な実装計画です：

1. ✅ 2つのユーザーロール (User/Admin)
2. ✅ 管理者パネル
3. ✅ 1000+ 行の文字起こし表示（遅延ロード）
4. ✅ ライト/ダークテーマ切り替え
5. ✅ ダウンロード: TXT, SRT, PPT
6. ✅ 100% 中国語UI

実装開始前に、この仕様書の内容をご確認ください。
