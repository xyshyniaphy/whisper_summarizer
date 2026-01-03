# User & Channel Management System - Implementation Brief

## User Requirements Decisions

| Decision | Choice |
|----------|--------|
| **User Deletion Data Policy** | Transfer ownership to admin (preserve data) |
| **Admin Content Visibility** | See ALL content (bypass channel restrictions) |
| **First Admin Setup** | Shell script only (manual execution) |
| **Channel Membership** | Admin-only control (users cannot leave) |

---

## Database Schema Changes

### 1. Users Table Extension (Migration: `001_add_user_activation.py`)

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;  -- Soft delete support

CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_is_admin ON users(is_admin);
```

### 2. Channels Table (Migration: `002_create_channels.py`)

```sql
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_channels_created_by ON channels(created_by);
```

### 3. Channel Memberships Junction Table

```sql
CREATE TABLE channel_memberships (
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (channel_id, user_id)
);

CREATE INDEX idx_channel_memberships_user ON channel_memberships(user_id);
CREATE INDEX idx_channel_memberships_channel ON channel_memberships(channel_id);
```

### 4. Transcription-Channels Junction Table

```sql
CREATE TABLE transcription_channels (
    transcription_id UUID REFERENCES transcriptions(id) ON DELETE CASCADE,
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (transcription_id, channel_id)
);

CREATE INDEX idx_transcription_channels_transcription ON transcription_channels(transcription_id);
CREATE INDEX idx_transcription_channels_channel ON transcription_channels(channel_id);
```

---

## Backend Implementation

### New Permission Decorators

**File: `backend/app/api/deps.py`**
```python
from fastapi import HTTPException, Depends, status
from app.models.user import User

def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role for endpoint access."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_active(current_user: User = Depends(get_current_user)):
    """Require active account for endpoint access."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please contact admin."
        )
    return current_user
```

### Admin API Endpoints Summary

**File: `backend/app/api/admin.py`**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/users` | GET | List all users |
| `/admin/users/{id}/activate` | PUT | Activate user |
| `/admin/users/{id}/admin` | PUT | Toggle admin status |
| `/admin/users/{id}` | DELETE | Delete user (soft delete + transfer ownership) |
| `/admin/channels` | GET | List all channels |
| `/admin/channels` | POST | Create channel |
| `/admin/channels/{id}` | PUT | Update channel |
| `/admin/channels/{id}` | DELETE | Delete channel |
| `/admin/channels/{id}/members` | POST | Assign user to channel |
| `/admin/channels/{id}/members/{user_id}` | DELETE | Remove user from channel |
| `/admin/audio` | GET | List all audio (admin sees all) |
| `/admin/audio/{id}/channels` | POST | Assign audio to channels |

---

## Frontend Implementation

### New Components Structure

```
src/
├── pages/
│   ├── Dashboard.tsx                    # NEW: Admin dashboard
│   ├── PendingActivation.tsx           # NEW: Inactive user page
│   ├── TranscriptionList.tsx           # MODIFIED: Add channel filter
│   └── TranscriptionDetail.tsx         # MODIFIED: Add channel assignment
├── components/
│   ├── dashboard/                       # NEW
│   │   ├── DashboardSidebar.tsx        # Foldable left sidebar
│   │   ├── UserManagementTab.tsx       # User CRUD + admin toggle
│   │   ├── ChannelManagementTab.tsx    # Channel CRUD + member assignment
│   │   └── AudioManagementTab.tsx      # All audio + channel assignment
│   ├── channel/                         # NEW
│   │   ├── ChannelBadge.tsx            # Display channel badge
│   │   ├── ChannelFilter.tsx           # Filter dropdown
│   │   └── ChannelAssignModal.tsx      # Multi-select modal
│   └── ui/
│       └── ConfirmDialog.tsx           # Already exists
├── atoms/
│   ├── auth.ts                          # MODIFIED: Add is_active
│   ├── channels.ts                      # NEW: Channel state
│   └── dashboard.ts                     # NEW: Sidebar state
└── services/
    └── api.ts                           # MODIFIED: Add admin endpoints
```

---

## Shell Script for First Admin

**File: `scripts/set_first_admin.sh`**
```bash
#!/bin/bash
set -e

USER_EMAIL=$1

if [ -z "$USER_EMAIL" ]; then
  echo "Usage: $0 <user_email>"
  exit 1
fi

echo "Setting user ($USER_EMAIL) as admin..."

# Load environment
if [ -f ".env" ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Check if running in dev mode
if docker ps | grep -q "whisper_postgres_dev"; then
  echo "Using development database..."
  docker exec -i whisper_postgres_dev psql -U postgres -d whisper_summarizer <<SQL
UPDATE users 
SET 
  is_admin = TRUE, 
  is_active = TRUE, 
  activated_at = NOW()
WHERE email = '${USER_EMAIL}'
AND deleted_at IS NULL;
SQL
else
  # Production mode - use DATABASE_URL
  echo "Using production database..."
  psql "$DATABASE_URL" -c "
    UPDATE users 
    SET 
      is_admin = TRUE, 
      is_active = TRUE, 
      activated_at = NOW()
    WHERE email = '${USER_EMAIL}'
    AND deleted_at IS NULL;
  "
fi

echo "✓ User ${USER_EMAIL} is now admin and activated"
```

---

## Implementation Phases

### Phase 1: Database & Backend Foundation
1. Create migrations (001, 002, 003)
2. Add SQLAlchemy models
3. Create permission decorators
4. Implement admin API endpoints
5. Modify auth flow for inactive users
6. Update transcription endpoint with channel filters

### Phase 2: Frontend Components
1. Create Dashboard page with sidebar
2. Implement UserManagementTab
3. Implement ChannelManagementTab
4. Implement AudioManagementTab
5. Create ChannelAssignModal

### Phase 3: Integration & State
1. Add Jotai atoms for channels
2. Update auth atom with is_active
3. Add admin API service functions
4. Handle inactive user flow in Login
5. Create PendingActivation page

### Phase 4: Testing & Polish
1. Backend permission tests
2. Frontend component tests
3. E2E admin workflow tests
4. Migration testing
5. Edge case handling

---

## Files to Create/Modify

### Create
- `backend/app/models/channel.py`
- `backend/app/api/admin.py`
- `backend/app/schemas/admin.py`
- `scripts/set_first_admin.sh`
- `src/pages/Dashboard.tsx`
- `src/pages/PendingActivation.tsx`
- `src/components/dashboard/DashboardSidebar.tsx`
- `src/components/dashboard/UserManagementTab.tsx`
- `src/components/dashboard/ChannelManagementTab.tsx`
- `src/components/dashboard/AudioManagementTab.tsx`
- `src/components/channel/ChannelBadge.tsx`
- `src/components/channel/ChannelFilter.tsx`
- `src/components/channel/ChannelAssignModal.tsx`
- `src/atoms/channels.ts`
- `src/atoms/dashboard.ts`

### Modify
- `backend/app/models/user.py`
- `backend/app/api/deps.py`
- `backend/app/api/auth.py`
- `backend/app/api/transcriptions.py`
- `src/atoms/auth.ts`
- `src/services/api.ts`
- `src/pages/TranscriptionList.tsx`
- `src/pages/TranscriptionDetail.tsx`
- `src/hooks/useAuth.ts`

---

## Critical Implementation Notes

1. **Admin sees all content**: Transcription query bypasses channel filter for admins
2. **User deletion transfers ownership**: Transcriptions reassigned to deleting admin
3. **Soft delete for users**: Set `deleted_at` instead of hard delete
4. **Last admin protection**: Cannot delete last admin or remove admin status from self
5. **Inactive user handling**: OAuth callback returns special error for inactive accounts
6. **Channel assignments**: Many-to-many relationship with audit trail (assigned_by, assigned_at)
7. **Sidebar persistence**: Save collapsed state to localStorage
