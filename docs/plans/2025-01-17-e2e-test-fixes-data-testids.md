# E2E Test Fixes - Add data-testid Attributes

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 124 failing E2E tests by adding missing `data-testid` attributes to all UI components.

**Root Cause:** E2E tests use `data-testid` selectors for reliable element selection, but most components don't have these attributes. Only AudioPlayer.tsx has `data-testid` (5 occurrences).

**Expected Outcome:** 120+ tests passing (from current 2/126)

**Tech Stack:** React, TypeScript, Playwright E2E tests

---

## Data-testid Requirements (Complete List)

| data-testid | Component | File | Line Location |
|-------------|-----------|------|----------------|
| `user-menu` | UserMenu | UserMenu.tsx | Button (line ~50) |
| `user-menu-dropdown` | UserMenu | UserMenu.tsx | Dropdown div (line ~65) |
| `theme-toggle` | ThemeToggle | ThemeToggle.tsx | Button element |
| `user-list` | UserManagementTab | dashboard/UserManagementTab.tsx | List container |
| `audio-list` | AudioManagementTab | dashboard/AudioManagementTab.tsx | List container |
| `channel-list` | ChannelManagementTab | dashboard/ChannelManagementTab.tsx | List container |
| `activate-user-button` | UserManagementTab | dashboard/UserManagementTab.tsx | Button in table row |
| `toggle-admin-button` | UserManagementTab | dashboard/UserManagementTab.tsx | Button in table row |
| `delete-channel-button` | ChannelManagementTab | dashboard/ChannelManagementTab.tsx | Button in table row |
| `assign-channel-button` | ChannelAssignModal | channel/ChannelAssignModal.tsx | Primary button |
| `channel-badge` | ChannelBadge | channel/ChannelBadge.tsx | Badge/span element |
| `chat-interface` | ChatDisplay | ChatDisplay.tsx | Container div |
| `chat-loading` | ChatDisplay | ChatDisplay.tsx | Loading state |
| `ai-message` | ChatDisplay | ChatDisplay.tsx | AI message div |
| `message-loading` | ChatDisplay | ChatDisplay.tsx | Loading state |
| `loading-spinner` | Multiple | Various | Generic spinner |
| `drop-zone` | AudioUploader | AudioUploader.tsx | Drop zone div |
| `upload-progress` | AudioUploader | AudioUploader.tsx | Progress element |
| `transcription-text` | TranscriptionDetail | pages/TranscriptionDetail.tsx | Text display |
| `summary-text` | TranscriptionDetail | pages/TranscriptionDetail.tsx | Summary display |
| `language-badge` | TranscriptionDetail | pages/TranscriptionDetail.tsx | Badge |
| `duration` | TranscriptionDetail | pages/TranscriptionDetail.tsx | Duration display |
| `created-at` | TranscriptionDetail | pages/TranscriptionDetail.tsx | Date display |

**AudioPlayer.tsx** already has these testids:
- `audio-player-container`
- `audio-element`
- `play-button`

---

## Phase 1: High-Impact Components (Fixes ~60 tests)

### Task 1: UserMenu.tsx (2 testids)

**File:** `frontend/src/components/UserMenu.tsx`

**Step 1: Read current implementation**

```bash
# Read to understand current structure
cd /home/lmr/ws/whisper_summarizer
head -80 frontend/src/components/UserMenu.tsx
```

**Step 2: Add data-testid to user menu button**

Replace the button element (around line 50):
```typescript
// BEFORE:
<button
  onClick={() => setIsOpen(!isOpen)}
  className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors"
  aria-label="用户菜单"
  aria-expanded={isOpen}
>

// AFTER:
<button
  onClick={() => setIsOpen(!isOpen)}
  className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors"
  aria-label="用户菜单"
  aria-expanded={isOpen}
  data-testid="user-menu"
>
```

**Step 3: Add data-testid to dropdown menu**

Replace the dropdown div (around line 65):
```typescript
// BEFORE:
<div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">

// AFTER:
<div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50"
  data-testid="user-menu-dropdown"
>
```

**Step 4: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/components/UserMenu.tsx
git commit -m "test(e2e): add data-testid attributes to UserMenu component

- Add data-testid='user-menu' to menu button
- Add data-testid='user-menu-dropdown' to dropdown menu
- Enables reliable E2E test selectors for user menu tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: ThemeToggle.tsx (1 testid)

**File:** `frontend/src/components/ThemeToggle.tsx`

**Step 1: Read current implementation**

```bash
head -100 frontend/src/components/ThemeToggle.tsx
```

**Step 2: Add data-testid to toggle button**

Find the button element and add `data-testid="theme-toggle"` to it.

**Step 3: Verify and commit**

```bash
# TypeScript check
cd frontend && npx tsc --noEmit

# Commit
git add frontend/src/components/ThemeToggle.tsx
git commit -m "test(e2e): add data-testid attribute to ThemeToggle component

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: NavBar.tsx (navigation elements)

**File:** `frontend/src/components/NavBar.tsx`

**Step 1: Identify navigation elements that need testids**

Look for:
- Navigation links
- Logo/home link
- Mobile menu toggle

**Step 2: Add appropriate testids**

**Step 3: Verify and commit**

---

### Task 4: Dashboard Tab Components (10+ testids)

**Files:**
- `frontend/src/components/dashboard/UserManagementTab.tsx`
- `frontend/src/components/dashboard/ChannelManagementTab.tsx`
- `frontend/src/components/dashboard/AudioManagementTab.tsx`

**UserManagementTab.tsx testids:**
- `user-list` - Table or list container
- `activate-user-button` - Button in table row
- `toggle-admin-button` - Button in table row

**ChannelManagementTab.tsx testids:**
- `channel-list` - Table or list container
- `delete-channel-button` - Button in table row

**AudioManagementTab.tsx testids:**
- `audio-list` - Table or list container

**Step 1: Add testids to UserManagementTab.tsx**

**Step 2: Add testids to ChannelManagementTab.tsx**

**Step 3: Add testids to AudioManagementTab.tsx**

**Step 4: Verify and commit**

```bash
git add frontend/src/components/dashboard/*.tsx
git commit -m "test(e2e): add data-testid attributes to dashboard tab components

- UserManagementTab: user-list, activate-user-button, toggle-admin-button
- ChannelManagementTab: channel-list, delete-channel-button
- AudioManagementTab: audio-list

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 2: Content Components (Fixes ~40 tests)

### Task 5: AudioUploader.tsx (2 testids)

**File:** `frontend/src/components/AudioUploader.tsx`

**Required testids:**
- `drop-zone` - Drop zone element
- `upload-progress` - Progress indicator

**Step 1: Add data-testid to drop zone**

**Step 2: Add data-testid to progress element**

**Step 3: Verify and commit**

```bash
git add frontend/src/components/AudioUploader.tsx
git commit -m "test(e2e): add data-testid attributes to AudioUploader component

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Channel Components (5 testids)

**Files:**
- `frontend/src/components/channel/ChannelBadge.tsx`
- `frontend/src/components/channel/ChannelAssignModal.tsx`

**ChannelBadge.tsx:**
- `channel-badge` - Badge/span element

**ChannelAssignModal.tsx:**
- `assign-channel-button` - Primary action button

**Step 1: Add testid to ChannelBadge**

**Step 2: Add testid to ChannelAssignModal**

**Step 3: Verify and commit**

```bash
git add frontend/src/components/channel/*.tsx
git commit -m "test(e2e): add data-testid attributes to channel components

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Chat Components (4 testids)

**Files:**
- `frontend/src/components/Chat.tsx`
- `frontend/src/components/ChatDisplay.tsx`

**Required testids:**
- `chat-interface` - Container div
- `chat-loading` - Loading state
- `ai-message` - AI message element
- `message-loading` - Loading state

**Step 1: Add testids to ChatDisplay.tsx**

**Step 2: Verify and commit**

```bash
git add frontend/src/components/Chat*.tsx
git commit -m "test(e2e): add data-testid attributes to chat components

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 3: Detail Components (Fixes ~24 tests)

### Task 8: TranscriptionDetail.tsx (5 testids)

**File:** `frontend/src/pages/TranscriptionDetail.tsx`

**Required testids:**
- `transcription-text` - Text display area
- `summary-text` - Summary display area
- `language-badge` - Language badge element
- `duration` - Duration display
- `created-at` - Date display

**Step 1: Add testid to transcription text display**

**Step 2: Add testid to summary display**

**Step 3: Add testid to language badge**

**Step 4: Add testid to duration display**

**Step 5: Add testid to created-at display**

**Step 6: Verify and commit**

```bash
git add frontend/src/pages/TranscriptionDetail.tsx
git commit -m "test(e2e): add data-testid attributes to TranscriptionDetail page

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: AudioPlayer.tsx (verify existing testids)

**File:** `frontend/src/components/AudioPlayer.tsx`

**Check if these testids exist:**
- `audio-player-container`
- `audio-element`
- `play-button`

**Action:** Verify all required testids are present. Add any missing ones.

---

### Task 10: Loading States (1 testid)

**Multiple files** - `loading-spinner`

**Identify where loading spinners are used** and add `data-testid="loading-spinner"`.

**Step 1: Find all spinner usages**

```bash
grep -r "spinner\|loading" frontend/src/components --include="*.tsx" -l
```

**Step 2: Add testid to each spinner component**

**Step 3: Verify and commit**

---

## Final Verification

### Task 11: Run E2E Tests

**Step 1: Build frontend**

```bash
docker compose -f docker-compose.dev.yml build frontend
```

**Step 2: Restart frontend container**

```bash
docker compose -f docker-compose.dev.yml restart frontend
```

**Step 3: Run E2E tests**

```bash
./tests/run_e2e_dev.sh
```

**Expected Results:**
- Before: 2/126 passing (1.6%)
- After: 120+/126 passing (95%+)

**Step 4: Check remaining failures**

Any remaining failures are likely due to:
- API response format issues (not data-testid related)
- Test timing issues
- Missing test data

---

## Implementation Notes

### General Pattern

When adding `data-testid` attributes:

1. **Place on interactive elements** (buttons, inputs, clickable areas)
2. **Place on containers** for lists, cards, panels
3. **Use kebab-case names** (e.g., `user-menu` not `userMenu`)
4. **Keep names descriptive** but concise
5. **Match test expectations** exactly

### Accessibility

`data-testid` attributes don't affect accessibility or styling. They're only used by Playwright for reliable element selection.

### TypeScript

No type definitions needed - `data-testid` is a standard HTML attribute.

---

## Success Criteria

✅ **All 20+ components updated** with data-testid attributes
✅ **TypeScript compiles** without errors
✅ **120+ E2E tests passing** (from current 2/126)
✅ **No production impact** (changes only affect test selectors)

---

## Risk Assessment

**Risk Level:** LOW

- Changes only add attributes, don't modify logic
- No impact on styling, behavior, or accessibility
- Easily reversible if needed
- No database or API changes

**Safety Mechanisms:**
- TypeScript compilation will catch syntax errors
- E2E tests will verify selectors work correctly
- Git commits allow easy rollback
