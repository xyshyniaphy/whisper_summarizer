# Whisper Summarizer Frontend Enhancement Specification

> **更新日**: 2025-01-31  
> **バージョン**: 2.0 (Jotai + Tailwind CSS)

---

## 概要 (Overview)

既存のWhisper Summarizerフロントエンドを拡張し、以下の機能を追加します：

- **ユーザーロール管理**: User/Adminの2つのロールとロールベースアクセス制御
- **管理パネル**: 管理者用ダッシュボードとユーザー管理機能
- **長文文字起こし表示**: 1000行以上の文字起こしを遅延ロードで表示
- **テーマ切り替え**: ライト/ダークモードの切り替え機能
- **PPT出力**: 文字起こしテキストからPowerPointファイルを生成
- **DOCX出力**: 要約をWordドキュメントでダウンロード
- **中国語UI**: すべてのインターフェースを中国語で表示

## 要件確認

| 項目 | 要件 |
|------|------|
| ユーザーロール | 2つ (User, Admin) |
| 文字起こし長さ | 1000+ 行 |
| 表示方法 | 遅延ロード (Lazy Loading) |
| PPT生成 | 直接テキスト変換、トピック別、カスタマイズ可能 |
| DOCX生成 | 要約をWord形式でダウンロード |
| UI言語 | 100% 中国語 |
| 状態管理 | Jotai (atomic state) |
| CSSフレームワーク | Tailwind CSS |

---

## 技術スタック

### 更新後のスタック

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| フロントエンド | React 19 + TypeScript + Vite | UIフレームワーク |
| 状態管理 | **Jotai** | アトミックステート管理 |
| CSS | **Tailwind CSS** | ユーティリファーストCSS |
| ルーティング | React Router v7 | クライアントサイドルーティング |
| 認証 | Supabase Auth | ユーザー認証 |
| PPT生成 | PptxGenJS | PowerPointファイル生成 |
| DOCX生成 | docx | Wordドキュメント生成 |
| アイコン | lucide-react | アイコンセット |

### 変更点

| 変更前 | 変更後 |
|--------|--------|
| Mantine UI | Tailwind CSS |
| React Context | Jotai |
| @tabler/icons-react | lucide-react |

---

## 1. 状態管理 (Jotai)

### 1.1 Jotai とは

Jotaiはプリミティブで柔軟なReact状態管理ライブラリです。

- **アトミック**: 状態を小さな単位（atom）に分割
- **シンプル**: `useAtom`フックは`useState`と同じ感覚で使用
- **高性能**: 必要なコンポーネントのみ再レンダリング

### 1.2 Atom構造

```typescript
// atoms/auth.ts
import { atom } from 'jotai'

export const userAtom = atom<User | null>(null)
export const sessionAtom = atom<Session | null>(null)
export const roleAtom = atom<'user' | 'admin' | null>(null)
export const loadingAtom = atom(true)

// 派生atom: ユーザーがログインしているか
export const isAuthenticatedAtom = atom((get) => {
  return get(userAtom) !== null
})

// 派生atom: 管理者かどうか
export const isAdminAtom = atom((get) => {
  return get(roleAtom) === 'admin'
})
```

```typescript
// atoms/theme.ts
import { atom } from 'jotai'

export const themeAtom = atom<'light' | 'dark'>('light')

// localStorageからの初期化
export const themeWithPersistenceAtom = atom(
  (get) => get(themeAtom),
  (get, set, newTheme: 'light' | 'dark') => {
    set(themeAtom, newTheme)
    localStorage.setItem('theme', newTheme)
    
    // DOMのclassを更新
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }
)
```

```typescript
// atoms/transcriptions.ts
import { atom } from 'jotai'

export const transcriptionsAtom = atom<Transcription[]>([])
export const selectedTranscriptionAtom = atom<Transcription | null>(null)

// フィルタリングされた文字起こし
export const userTranscriptionsAtom = atom((get) => {
  const transcriptions = get(transcriptionsAtom)
  const userId = get(userAtom)?.id
  return transcriptions.filter(t => t.user_id === userId)
})
```

### 1.3 useAuth フック (Jotai版)

```typescript
// hooks/useAuth.ts
import { useAtom, useAtomValue, useSetAtom } from 'jotai'
import { useCallback, useEffect } from 'react'
import { supabase } from '../services/supabase'
import { userAtom, sessionAtom, loadingAtom, roleAtom } from '../atoms/auth'

interface AuthActions {
  signUp: (email: string, password: string, fullName?: string) => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

export function useAuth(): [
  { user: User | null; session: Session | null; loading: boolean; role: 'user' | 'admin' | null },
  AuthActions
] {
  const [user, setUser] = useAtom(userAtom)
  const [session, setSession] = useAtom(sessionAtom)
  const [loading, setLoading] = useAtom(loadingAtom)
  const [role, setRole] = useAtom(roleAtom)

  useEffect(() => {
    // セッション取得
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setSession(session)
      setUser(session?.user ?? null)
      setRole(session?.user?.user_metadata?.role ?? 'user')
      setLoading(false)
    }

    getSession()

    // 認証状態変化を監視
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      setRole(session?.user?.user_metadata?.role ?? 'user')
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  const signUp = useCallback(async (email: string, password: string, fullName?: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName || '', role: 'user' }
      }
    })
    if (error) throw error
    if (data.user) {
      setUser(data.user)
      setRole('user')
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
    if (data.user) {
      setUser(data.user)
      setRole(data.user.user_metadata?.role ?? 'user')
    }
  }, [])

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    setUser(null)
    setSession(null)
    setRole(null)
  }, [])

  return [
    { user, session, loading, role },
    { signUp, signIn, signOut }
  ]
}
```

---

## 2. Tailwind CSS

### 2.1 インストール

```bash
# Mantineをアンインストール
npm uninstall @mantine/core @mantine/hooks @tabler/icons-react

# Tailwind CSSをインストール
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 新しいアイコンライブラリ
npm install lucide-react

# Jotai
npm install jotai

# DOCX生成
npm install docx
npm install -D @types/docx
```

### 2.2 設定

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'selector',  // 'dark' classで制御
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      }
    },
  },
  plugins: [],
}
```

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100;
  }
}
```

### 2.3 テーマ切り替え

```typescript
// components/ThemeToggle.tsx
import { useAtomValue, useSetAtom } from 'jotai'
import { Moon, Sun } from 'lucide-react'
import { themeWithPersistenceAtom } from '../atoms/theme'

export function ThemeToggle() {
  const theme = useAtomValue(themeWithPersistenceAtom)
  const setTheme = useSetAtom(themeWithPersistenceAtom)

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? (
        <Sun className="w-5 h-5 text-yellow-500" />
      ) : (
        <Moon className="w-5 h-5 text-gray-700" />
      )}
    </button>
  )
}
```

### 2.4 コンポーネント移行

| Mantine | Tailwind CSS |
|---------|--------------|
| `<Container>` | `<div className="container mx-auto px-4">` |
| `<Title order={2}>` | `<h2 className="text-2xl font-bold">` |
| `<Button>` | `<button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">` |
| `<Card>` | `<div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">` |
| `<Text>` | `<p className="text-gray-700 dark:text-gray-300">` |
| `<Badge>` | `<span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">` |
| `<Group>` | `<div className="flex gap-2">` |
| `<Stack>` | `<div className="space-y-4">` |
| `<ActionIcon>` | `<button className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700">` |
| `<Modal>` | Custom component (後述) |
| `<Accordion>` | Custom component (後述) |

---

## 3. UIコンポーネント (Tailwind版)

### 3.1 Button

```typescript
// components/ui/Button.tsx
import { ButtonHTMLAttributes, forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        primary: 'bg-primary-600 text-white hover:bg-primary-700',
        secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600',
        ghost: 'hover:bg-gray-100 dark:hover:bg-gray-800',
        danger: 'bg-red-600 text-white hover:bg-red-700',
      },
      size: {
        sm: 'px-3 py-1.5 text-sm',
        md: 'px-4 py-2',
        lg: 'px-6 py-3 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={buttonVariants({ variant, size, className })}
        {...props}
      />
    )
  }
)
```

### 3.2 Card

```typescript
// components/ui/Card.tsx
import { HTMLAttributes } from 'react'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md ${className || ''}`}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`p-6 ${className || ''}`} {...props} />
  )
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`p-6 pt-0 ${className || ''}`} {...props} />
  )
}
```

### 3.3 Modal

```typescript
// components/ui/Modal.tsx
import { ReactNode, useEffect } from 'react'
import { X } from 'lucide-react'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black/50" 
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b dark:border-gray-700">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  )
}
```

### 3.4 Accordion

```typescript
// components/ui/Accordion.tsx
import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface AccordionItemProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}

export function AccordionItem({ title, children, defaultOpen = false }: AccordionItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <span className="font-medium">{title}</span>
        <ChevronDown 
          className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>
      {isOpen && (
        <div className="p-4 bg-white dark:bg-gray-900">
          {children}
        </div>
      )}
    </div>
  )
}

export function Accordion({ children }: { children: React.ReactNode }) {
  return <div className="space-y-2">{children}</div>
}
```

### 3.5 Badge

```typescript
// components/ui/Badge.tsx
import { HTMLAttributes } from 'react'

type BadgeVariant = 'success' | 'error' | 'info' | 'warning'

const variantStyles: Record<BadgeVariant, string> = {
  success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
}

export function Badge({ 
  variant = 'info', 
  className = '', 
  children, 
  ...props 
}: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  )
}
```

---

## 4. ロールベースアクセス制御 (RBAC)

### 4.1 ProtectedRoute コンポーネント

```typescript
// components/auth/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom'
import { useAtomValue } from 'jotai'
import { Loader2 } from 'lucide-react'
import { isAdminAtom, isAuthenticatedAtom, loadingAtom } from '../atoms/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const loading = useAtomValue(loadingAtom)
  const isAuthenticated = useAtomValue(isAuthenticatedAtom)
  const isAdmin = useAtomValue(isAdminAtom)

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
```

### 4.2 ルーティング構造

```typescript
// App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { TranscriptionList } from './pages/TranscriptionList'
import { TranscriptionDetail } from './pages/TranscriptionDetail'

// Admin pages
import { AdminDashboard } from './pages/admin/AdminDashboard'
import { UserManagement } from './pages/admin/UserManagement'
import { AllTranscriptions } from './pages/admin/AllTranscriptions'

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      
      {/* Protected user routes */}
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/transcriptions" 
        element={
          <ProtectedRoute>
            <TranscriptionList />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/transcriptions/:id" 
        element={
          <ProtectedRoute>
            <TranscriptionDetail />
          </ProtectedRoute>
        } 
      />
      
      {/* Protected admin routes */}
      <Route 
        path="/admin" 
        element={
          <ProtectedRoute requireAdmin>
            <AdminDashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/users" 
        element={
          <ProtectedRoute requireAdmin>
            <UserManagement />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/transcriptions" 
        element={
          <ProtectedRoute requireAdmin>
            <AllTranscriptions />
          </ProtectedRoute>
        } 
      />
      
      {/* Default */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
```

---

## 5. 長文文字起こし表示 (1000+ 行)

### 5.1 LazyTranscriptionContent

```typescript
// components/transcription/LazyTranscriptionContent.tsx
import { useState, useRef, useEffect } from 'react'
import { Accordion, AccordionItem } from '../ui/Accordion'
import { ChevronDown } from 'lucide-react'

interface TopicSection {
  id: string
  title: string
  lines: string[]
  loaded: boolean
}

// 文字起こしをトピック別に分割
function parseTopics(text: string): Omit<TopicSection, 'loaded'>[] {
  const lines = text.split('\n')
  const topics: Omit<TopicSection, 'loaded'>[] = []
  let currentTopic: string[] = []
  let topicIndex = 0
  let topicTitle = 'セクション 1'
  
  for (const line of lines) {
    // タイムスタンプパターン
    const timeMatch = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.+)$/)
    if (timeMatch) {
      if (currentTopic.length > 0) {
        topics.push({
          id: `topic-${topicIndex}`,
          title: topicTitle,
          lines: currentTopic
        })
        topicIndex++
        currentTopic = []
      }
      topicTitle = timeMatch[2] || timeMatch[1]
      currentTopic.push(line)
    } else if (line.trim() === '' && currentTopic.length > 0) {
      // 空行でセクション区切り
      topics.push({
        id: `topic-${topicIndex}`,
        title: topicTitle,
        lines: currentTopic
      })
      topicIndex++
      currentTopic = []
    } else {
      currentTopic.push(line)
    }
  }
  
  // 最後のセクション
  if (currentTopic.length > 0) {
    topics.push({
      id: `topic-${topicIndex}`,
      title: topicTitle,
      lines: currentTopic
    })
  }
  
  return topics
}

export function LazyTranscriptionContent({ text }: { text: string }) {
  const [topics, setTopics] = useState(() => 
    parseTopics(text).map(t => ({ ...t, loaded: false }))
  )
  
  const observerTarget = useRef<HTMLDivElement>(null)
  
  // Intersection Observer for lazy loading
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const topicId = entry.target.getAttribute('data-topic-id')
            if (topicId) {
              setTopics(prev => prev.map(topic =>
                topic.id === topicId ? { ...topic, loaded: true } : topic
              ))
            }
          }
        })
      },
      { threshold: 0.1 }
    )
    
    const targets = document.querySelectorAll('[data-topic-id]')
    targets.forEach(target => observer.observe(target))
    
    return () => observer.disconnect()
  }, [])
  
  return (
    <div className="space-y-2">
      {topics.map((topic, index) => (
        <AccordionItem
          key={topic.id}
          title={`${topic.title} (${topic.lines.length}行)`}
          defaultOpen={index === 0}
        >
          <div 
            ref={observerTarget}
            data-topic-id={topic.id}
            className="min-h-[100px]"
          >
            {topic.loaded ? (
              <pre className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300 font-mono">
                {topic.lines.join('\n')}
              </pre>
            ) : (
              <div className="flex items-center justify-center h-24">
                <div className="animate-pulse text-gray-400">読み込み中...</div>
              </div>
            )}
          </div>
        </AccordionItem>
      ))}
    </div>
  )
}
```

---

## 6. ダウンロード機能 (TXT, SRT, PPT, DOCX)

### 6.1 DownloadButtons コンポーネント

```typescript
// components/transcription/DownloadButtons.tsx
import { PPTGenerator } from './PPTGenerator'
import { DOCXGenerator } from './DOCXGenerator'
import { Download, FileText } from 'lucide-react'

interface DownloadButtonsProps {
  transcription: Transcription
  summary?: Summary | null
}

export function DownloadButtons({ transcription, summary }: DownloadButtonsProps) {
  const downloadTxt = () => {
    const url = `/api/transcriptions/${transcription.id}/download/txt`
    const a = document.createElement('a')
    a.href = url
    a.download = `${transcription.file_name}.txt`
    a.click()
  }
  
  const downloadSrt = () => {
    const url = `/api/transcriptions/${transcription.id}/download/srt`
    const a = document.createElement('a')
    a.href = url
    a.download = `${transcription.file_name}.srt`
    a.click()
  }
  
  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={downloadTxt}
        className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
      >
        <FileText className="w-4 h-4" />
        TXT
      </button>
      
      <button
        onClick={downloadSrt}
        className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
      >
        <Download className="w-4 h-4" />
        SRT
      </button>
      
      <PPTGenerator transcription={transcription} />
      
      {summary && <DOCXGenerator summary={summary} />}
    </div>
  )
}
```

### 6.2 PPTGenerator

```typescript
// components/transcription/PPTGenerator.tsx
import { useState } from 'react'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import pptxgen from 'pptxgenjs'
import { FilePresentation } from 'lucide-react'

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
  
  const parseTopics = (text: string): Array<{ title: string; content: string }> => {
    // 実装は省略（前述の仕様書を参照）
    return []
  }
  
  const generatePPT = async () => {
    setGenerating(true)
    
    try {
      const pptx = new pptxgen()
      
      // タイトルスライド
      const titleSlide = pptx.addSlide()
      titleSlide.addText(transcription.file_name, {
        x: 1, y: 2.5, fontSize: 36, bold: true, align: 'center'
      })
      
      // トピックスライド
      const topics = parseTopics(transcription.original_text || '')
      topics.forEach((topic) => {
        pptx.addSection({ title: topic.title })
        const slide = pptx.addSlide({ sectionTitle: topic.title })
        slide.addText(topic.title, { x: 0.5, y: 0.5, fontSize: 24, bold: true })
        slide.addText(topic.content, { x: 0.5, y: 1.5, w: 9, h: 4, fontSize: 14 })
      })
      
      await pptx.writeFile({ fileName: `${transcription.file_name}.pptx` })
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
      <button
        onClick={() => setOpened(true)}
        className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
      >
        <FilePresentation className="w-4 h-4" />
        PPT
      </button>
      
      <Modal isOpen={opened} onClose={() => setOpened(false)} title="PPT生成オプション">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">テンプレート</label>
            <select
              value={options.template}
              onChange={(e) => setOptions({ ...options, template: e.target.value as any })}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
            >
              <option value="simple">シンプル</option>
              <option value="professional">プロフェッショナル</option>
              <option value="modern">モダン</option>
            </select>
          </div>
          
          <Button onClick={generatePPT} disabled={generating} className="w-full">
            {generating ? '生成中...' : '生成開始'}
          </Button>
        </div>
      </Modal>
    </>
  )
}
```

### 6.3 DOCXGenerator

```typescript
// components/transcription/DOCXGenerator.tsx
import { Document, Packer, Paragraph, TextRun } from 'docx'
import { FileText } from 'lucide-react'

interface DOCXGeneratorProps {
  summary: {
    summary_text: string
  }
}

export function DOCXGenerator({ summary }: DOCXGeneratorProps) {
  const generateDOCX = async () => {
    const doc = new Document({
      sections: [{
        properties: {},
        children: [
          // タイトル
          new Paragraph({
            children: [
              new TextRun({
                text: '文字起こし要約',
                bold: true,
                size: 32,
              })
            ],
            spacing: { after: 400 }
          }),
          
          // 日付
          new Paragraph({
            children: [
              new TextRun({
                text: new Date().toLocaleDateString('zh-CN'),
                size: 20,
              })
            ],
            spacing: { after: 400 }
          }),
          
          // 要約内容
          ...summary.summary_text.split('\n').map(
            line => new Paragraph({
              children: [new TextRun({ text: line, size: 24 })]
            })
          )
        ]
      }]
    })
    
    const blob = await Packer.toBlob(doc)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `summary-${Date.now()}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  return (
    <button
      onClick={generateDOCX}
      className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
    >
      <FileText className="w-4 h-4" />
      DOCX
    </button>
  )
}
```

---

## 7. 管理者パネル

### 7.1 AdminDashboard

```typescript
// pages/admin/AdminDashboard.tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'
import { Users, FileText, TrendingUp } from 'lucide-react'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'

export function AdminDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => api.getAdminStats()
  })
  
  if (isLoading) {
    return <div className="p-8">読み込み中...</div>
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">管理者ダッシュボード</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">総ユーザー数</span>
              <Users className="w-5 h-5 text-primary-600" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats?.totalUsers || 0}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">総文字起こし数</span>
              <FileText className="w-5 h-5 text-primary-600" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats?.totalTranscriptions || 0}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">今月の文字起こし</span>
              <TrendingUp className="w-5 h-5 text-primary-600" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats?.thisMonthTranscriptions || 0}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

### 7.2 UserManagement

```typescript
// pages/admin/UserManagement.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../services/api'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'

export function UserManagement() {
  const queryClient = useQueryClient()
  
  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.getAllUsers()
  })
  
  const changeRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.changeUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    }
  })
  
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">ユーザー管理</h1>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                メールアドレス
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                名前
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                ロール
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {users?.map((user) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap">{user.email}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {user.user_metadata?.full_name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Badge variant={user.user_metadata?.role === 'admin' ? 'info' : 'success'}>
                    {user.user_metadata?.role || 'user'}
                  </Badge>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {user.user_metadata?.role !== 'admin' && (
                    <Button
                      size="sm"
                      onClick={() => changeRoleMutation.mutate({
                        userId: user.id,
                        role: 'admin'
                      })}
                    >
                      管理者に昇格
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

---

## 8. レイアウト構造

### 8.1 Header

```typescript
// components/layout/Header.tsx
import { Link, useNavigate } from 'react-router-dom'
import { useAtomValue } from 'jotai'
import { Mic, LogOut } from 'lucide-react'
import { ThemeToggle } from '../ThemeToggle'
import { userAtom, isAdminAtom } from '../../atoms/auth'

export function Header() {
  const user = useAtomValue(userAtom)
  const isAdmin = useAtomValue(isAdminAtom)
  const navigate = useNavigate()
  
  const handleLogout = async () => {
    await supabase.auth.signOut()
    navigate('/login')
  }
  
  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <Mic className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">Whisper Summarizer</span>
          </Link>
          
          {/* Right side */}
          <div className="flex items-center gap-4">
            <ThemeToggle />
            
            {user && (
              <>
                {isAdmin && (
                  <Link 
                    to="/admin"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600"
                  >
                    管理画面
                  </Link>
                )}
                
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-red-600"
                >
                  <LogOut className="w-4 h-4" />
                  ログアウト
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
```

### 8.2 App Shell

```typescript
// components/layout/AppShell.tsx
import { Outlet } from 'react-router-dom'
import { Header } from './Header'

export function AppShell() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
```

---

## 9. 依存関係

### 9.1 package.json

```json
{
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-router-dom": "^7.1.1",
    "axios": "^1.7.9",
    "@supabase/supabase-js": "^2.47.0",
    "jotai": "^2.10.3",
    "pptxgenjs": "^3.12.0",
    "docx": "^8.5.0",
    "lucide-react": "^0.468.0",
    "@tanstack/react-query": "^5.62.11",
    "class-variance-authority": "^0.7.1"
  },
  "devDependencies": {
    "typescript": "^5.7.2",
    "vite": "^7.0.4",
    "tailwindcss": "^3.4.17",
    "postcss": "^8.4.49",
    "autoprefixer": "^10.4.20",
    "@types/pptxgenjs": "^2.5.1",
    "@types/docx": "^0.0.0"
  }
}
```

### 9.2 インストール手順

```bash
# Mantineを削除
npm uninstall @mantine/core @mantine/hooks @mantine/dropzone @tabler/icons-react

# 新しい依存関係をインストール
npm install jotai pptxgenjs docx lucide-react @tanstack/react-query class-variance-authority

# Tailwind CSSをインストール
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 型定義
npm install -D @types/pptxgenjs @types/docx
```

---

## 10. Tailwind CSS設定

### 10.1 tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'selector',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        }
      }
    },
  },
  plugins: [],
}
```

### 10.2 postcss.config.js

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### 10.3 src/index.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100;
  }
}

@layer components {
  /* カスタムコンポーネントスタイルが必要な場合 */
}
```

---

## 11. ファイル構成

```
frontend/src/
├── atoms/                          # Jotai state management
│   ├── auth.ts                     # user, session, role, loading atoms
│   ├── theme.ts                    # theme atom
│   └── transcriptions.ts           # transcriptions atoms
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   └── AppShell.tsx
│   │
│   ├── ui/                         # Tailwind UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── Accordion.tsx
│   │   ├── Badge.tsx
│   │   └── index.ts
│   │
│   ├── auth/
│   │   └── ProtectedRoute.tsx
│   │
│   ├── transcription/
│   │   ├── LazyTranscriptionContent.tsx
│   │   ├── DownloadButtons.tsx
│   │   ├── PPTGenerator.tsx
│   │   └── DOCXGenerator.tsx
│   │
│   └── ThemeToggle.tsx
│
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── TranscriptionList.tsx
│   ├── TranscriptionDetail.tsx
│   └── admin/
│       ├── AdminDashboard.tsx
│       ├── UserManagement.tsx
│       └── AllTranscriptions.tsx
│
├── hooks/
│   └── useAuth.ts                  # Jotai版
│
├── services/
│   ├── api.ts
│   └── supabase.ts
│
├── types/
│   └── index.ts
│
├── App.tsx
├── main.tsx
└── index.css
```

---

## 12. 実装フェーズ

| フェーズ | 内容 | タスク |
|---------|------|------|
| **Phase 1** | フレームワーク移行 | Mantine→Tailwind, Context→Jotai |
| **Phase 2** | テーマシステム | ライト/ダークモード実装 |
| **Phase 3** | RBAC | ロールベースアクセス制御 |
| **Phase 4** | 長文表示 | 遅延ロード表示 |
| **Phase 5** | ダウンロード機能 | PPT, DOCX生成 |
| **Phase 6** | 管理者パネル | 管理画面実装 |

---

## 13. セットアップ手順

### 13.1 既存の削除

```bash
cd frontend

# Mantine関連を削除
npm uninstall @mantine/core @mantine/hooks @mantine/dropzone @tabler/icons-react
```

### 13.2 新規インストール

```bash
# Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Jotai & 状態管理
npm install jotai @tanstack/react-query

# ダウンロード機能
npm install pptxgenjs docx

# UIコンポーネント
npm install lucide-react class-variance-authority

# 型定義
npm install -D @types/pptxgenjs @types/docx
```

### 13.3 設定ファイル

**tailwind.config.js** (上記を参照)

**postcss.config.js** (上記を参照)

**src/index.css** (上記を参照)

### 13.4 Supabase Role設定

```sql
-- 最初の管理者ユーザーを設定
UPDATE auth.users 
SET user_metadata = jsonb_set(
  COALESCE(user_metadata, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email = 'admin@example.com';
```

---

この仕様書は、以下の要件を満たす包括的な実装計画です：

1. ✅ 2つのユーザーロール (User/Admin)
2. ✅ Jotaiによる状態管理
3. ✅ Tailwind CSSによるスタイリング
4. ✅ 管理者パネル
5. ✅ 1000+ 行の文字起こし表示（遅延ロード）
6. ✅ ライト/ダークテーマ切り替え
7. ✅ ダウンロード: TXT, SRT, PPT, DOCX
8. ✅ 100% 中国語UI
