---
name: whisper-frontend
description: Frontend UI patterns and coding standards for Whisper Summarizer React application. Jotai state management, Tailwind CSS, ConfirmDialog component, React hooks rules, and common patterns.
---

# whisper-frontend - Frontend UI Patterns

## Purpose

Coding standards and UI patterns for the Whisper Summarizer React frontend:
- **Jotai for state** (not React Context)
- **Tailwind CSS** for styling
- **ConfirmDialog** component (NEVER use `window.confirm`)
- **React hooks rules** - conditional returns only

## Quick Start

```bash
# Start development server
cd frontend && bun run dev

# Build for production
bun run build

# Run tests
bun run test
```

## Key Patterns

### State Management: Jotai

**Why Jotai instead of React Context?**
- **Simpler** - No Provider wrappers needed
- **Better performance** - Only re-renders components that use specific atoms
- **Type-safe** - Full TypeScript support
- **Smaller bundle** - 3KB vs 15KB for Context

**Example**:
```tsx
// atoms/auth.ts
import { atom } from 'jotai'

export const userAtom = atom<User | null>(null)
export const isAuthenticatedAtom = atom((get) => get(userAtom) !== null)

// components/NavBar.tsx
import { useAtom } from 'jotai'
import { userAtom } from '../atoms/auth'

export function NavBar() {
  const [user] = useAtom(userAtom)
  return user ? <UserMenu user={user} /> : <LoginButton />
}
```

### Styling: Tailwind CSS

**Utility-first approach** - No CSS modules needed:

```tsx
// ✅ GOOD - Tailwind utilities
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
  Submit
</button>

// ❌ BAD - Inline styles
<button style={{ padding: '1rem', backgroundColor: 'blue' }}>
  Submit
</button>
```

**Common patterns**:
```tsx
// Flexbox centering
<div className="flex items-center justify-center">

// Grid layout
<div className="grid grid-cols-1 md:grid-cols-3 gap-4">

// Responsive spacing
<div className="px-4 py-2 md:px-8 md:py-4">
```

### Icons: lucide-react

```tsx
import { Loader2, Upload, Trash2 } from 'lucide-react'

<Loader2 className="w-5 h-5 animate-spin" />
<Upload className="w-6 h-6" />
<Trash2 className="w-4 h-4 text-red-500" />
```

## UI Components

### 1. ConfirmDialog (REQUIRED)

**NEVER use `window.confirm()`** - blocks JS thread, can't be customized/tested.

```tsx
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { useState } from 'react'

function MyComponent() {
  const [confirm, setConfirm] = useState({ isOpen: false, id: null })

  return (
    <>
      <button onClick={() => setConfirm({ isOpen: true, id: '123' })}>
        Delete
      </button>

      <ConfirmDialog
        isOpen={confirm.isOpen}
        onClose={() => setConfirm({ isOpen: false, id: null })}
        onConfirm={async () => {
          await deleteItem(confirm.id)
          setConfirm({ isOpen: false, id: null })
        }}
        title="确认删除"
        message="确定要删除吗？"
        confirmLabel="删除"
        cancelLabel="取消"
        variant="danger"
      />
    </>
  )
}
```

**Props**:
```tsx
interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void | Promise<void>
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'info'
}
```

### 2. Loading States

```tsx
import { Loader2 } from 'lucide-react'

function MyComponent() {
  const { isLoading, data } = useData()

  return (
    <>
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
        </div>
      ) : (
        <DataList data={data} />
      )}
    </>
  )
}
```

### 3. Error States

```tsx
function MyComponent() {
  const { isLoading, data, error } = useData()

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-500">Error: {error.message}</p>
        <button onClick={retry} className="mt-4 text-blue-500">
          Retry
        </button>
      </div>
    )
  }

  return <DataList data={data} />
}
```

### 4. Empty States

```tsx
function MyComponent() {
  const { items } = useItems()

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">No items found</p>
        <button className="mt-4 btn-primary">Create First Item</button>
      </div>
    )
  }

  return <ItemList items={items} />
}
```

## React Hooks Rules

### CRITICAL: Conditional Returns

**ALWAYS use conditional returns, NOT early returns, for components with hooks:**

```tsx
// ❌ WRONG - Early return after hook causes Hooks violation
export function Modal({ isOpen }) {
  useEffect(() => { ... }, [isOpen])  // Hook called
  if (!isOpen) return null            // Early return breaks hook order
  return ( ... )
}

// ✅ CORRECT - Conditional return preserves hook order
export function Modal({ isOpen }) {
  useEffect(() => { ... }, [isOpen])  // Hook always called
  return isOpen ? ( ... ) : null      // Conditional return
}
```

### Custom Hooks

```tsx
// hooks/useAuth.ts
import { useAtom } from 'jotai'
import { userAtom, isAuthenticatedAtom } from '../atoms/auth'

export function useAuth() {
  const [user] = useAtom(userAtom)
  const [isAuthenticated] = useAtom(isAuthenticatedAtom)

  return { user, isAuthenticated }
}

// Usage
function MyComponent() {
  const { user, isAuthenticated } = useAuth()
  // ...
}
```

## Page Structure

```tsx
// pages/TranscriptionDetail.tsx
import { useParams } from 'react-router-dom'
import { useTranscription } from '../hooks/useTranscription'
import { AudioPlayer } from '../components/AudioPlayer'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'

export function TranscriptionDetail() {
  const { id } = useParams<{ id: string }>()
  const { transcription, isLoading, error, deleteTranscription } = useTranscription(id)

  if (isLoading) return <Loader />
  if (error) return <Error message={error.message} />
  if (!transcription) return <NotFound />

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold">{transcription.file_name}</h1>
      <AudioPlayer transcription={transcription} />
      {/* ... */}
    </div>
  )
}
```

## API Integration

### Axios Instance

```tsx
// services/api.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

// Request interceptor - add auth token
api.interceptors.request.use(async (config) => {
  const token = await getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### Data Fetching Hook

```tsx
// hooks/useTranscription.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export function useTranscription(id: string) {
  return useQuery({
    queryKey: ['transcription', id],
    queryFn: async () => {
      const { data } = await api.get(`/transcriptions/${id}`)
      return data
    },
  })
}
```

## Common Patterns

### Form Handling

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function UploadForm() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/audio/upload', formData)
      navigate('/')
    } catch (error) {
      console.error('Upload failed', error)
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="file"
        accept="audio/*"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button type="submit" disabled={!file || uploading}>
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
    </form>
  )
}
```

### Pagination

```tsx
function TranscriptionList() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useTranscriptions(page)

  return (
    <>
      <List items={data?.items || []} />
      <Pagination
        currentPage={page}
        totalPages={data?.totalPages || 1}
        onPageChange={setPage}
      />
    </>
  )
}
```

### Search/Filter

```tsx
function TranscriptionList() {
  const [search, setSearch] = useState('')
  const { data } = useTranscriptions({ search })

  return (
    <>
      <input
        type="text"
        placeholder="Search transcriptions..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-4 py-2 border rounded"
      />
      <List items={data?.items || []} />
    </>
  )
}
```

## Testing

### Component Test

```tsx
import { render, screen } from '@testing-library/react'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'

test('calls onConfirm when confirm button clicked', async () => {
  const onConfirm = vi.fn()
  const onClose = vi.fn()

  render(
    <ConfirmDialog
      isOpen={true}
      onConfirm={onConfirm}
      onClose={onClose}
      title="Delete?"
      message="Are you sure?"
    />
  )

  await userEvent.click(screen.getByText('Delete'))
  expect(onConfirm).toHaveBeenCalledOnce()
})
```

## Troubleshooting

### Issue: "Hooks can only be called inside function body"

**Cause**: Early return before all hooks called

**Solution**: Use conditional return instead
```tsx
// ❌ WRONG
if (!isOpen) return null
useEffect(() => {}, [])

// ✅ CORRECT
useEffect(() => {}, [])
return isOpen ? <div /> : null
```

### Issue: State not updating

**Cause**: Direct mutation instead of setState

**Solution**:
```tsx
// ❌ WRONG
items.push(newItem)
setItems(items)

// ✅ CORRECT
setItems([...items, newItem])
```

## Related Skills

```bash
# Audio player component
/whisper-player

# E2E testing patterns
/whisper-e2e

# Nginx configuration
/whisper-nginx
```

## See Also

- [CLAUDE.md - Frontend UI Patterns](../../CLAUDE.md#frontend-ui-patterns)
- [frontend/src/components/](../../frontend/src/components/)
- [frontend/package.json](../../frontend/package.json)
