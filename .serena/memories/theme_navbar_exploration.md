# Theme Selection & Navigation Bar Exploration

## Current State

### Existing Theme Infrastructure
- **Jotai Atom**: `frontend/src/atoms/theme.ts`
  - `themeAtom` - Primitive theme state
  - `themeWithPersistenceAtom` - localStorage persistence + DOM manipulation
  - Supports system preference detection via `prefers-color-scheme`
  - Uses Tailwind's `dark:` class strategy

### Existing UI Components
- Location: `frontend/src/components/ui/`
- Available: Button, Card, Modal, Badge, Accordion
- Styling: Tailwind CSS with dark mode variants

### Current Routes
```
/login          - Public (Google OAuth login)
/transcriptions - Protected (List view)
/transcriptions/:id - Protected (Detail view)
/dashboard      - Protected (Dashboard)
```

## Design Options

### Option A: Top Navigation Bar (Recommended)
```
┌─────────────────────────────────────────────────┐
│ WhisperApp 🔊    Home  Transcriptions  🌙 User▼ │
├─────────────────────────────────────────────────┤
│                                                 │
│  Content                                      │
│                                                 │
└─────────────────────────────────────────────────┘
```
- Fixed header at top
- Left: Logo/Brand
- Center-left: Navigation links
- Right: Theme toggle + User menu
- Mobile: Hamburger menu

### Option B: Sidebar Navigation
```
┌──────┬──────────────────────────────────────────┐
│ Logo  │  Content                               │
│ 🌙    │                                        │
│ Home  │                                        │
│ Trans│                                        │
│      │                                        │
└──────┴──────────────────────────────────────────┘
```
- Fixed left sidebar
- Better for dashboard-heavy apps
- More vertical space for nav items

## Key Questions to Resolve

1. **Theme Toggle Style**
   - Simple sun/moon toggle button?
   - 3-option dropdown (Light/Dark/System)?
   - Icon-only or with text label?

2. **Navigation Layout**
   - Top nav bar or Sidebar?
   - Fixed or static positioning?

3. **User Menu**
   - Display user name/avatar?
   - Include sign out button?
   - Separate dropdown or inline?

4. **Mobile Behavior**
   - Hamburger menu for nav links?
   - Bottom navigation bar?
   - Full-screen drawer?

## Implementation Plan

### Components to Create
1. `ThemeToggle.tsx` - Theme switcher button
2. `NavBar.tsx` - Main navigation component
3. `UserMenu.tsx` - User dropdown with sign out

### Files to Modify
1. `App.tsx` - Add NavBar to protected routes
2. `components/ui/index.ts` - Export new components

### Tailwind Classes Reference
From Context7 research:
```jsx
// Nav links pattern
<a href="/url" className="rounded-lg px-3 py-2 text-slate-700 font-medium hover:bg-slate-100 hover:text-slate-900 dark:text-slate-200 dark:hover:bg-gray-800">
  Link Text
</a>

// Responsive nav bar
<nav className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
```

## Technical Notes
- Use existing `themeWithPersistenceAtom` from `atoms/theme.ts`
- No new Jotai atoms required
- lucide-react for icons (already in dependencies)
- Follow existing component patterns in `components/ui/`
