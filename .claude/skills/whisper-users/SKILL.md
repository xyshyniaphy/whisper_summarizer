---
name: whisper-users
description: User and channel management for Whisper Summarizer. Roles, access control, admin setup, dashboard endpoints, and permission management.
---

# whisper-users - User & Channel Management

## Purpose

User and channel management system for Whisper Summarizer:
- **Inactive by default** - New users require admin approval
- **Role-based access** - Admin vs regular user permissions
- **Channel-based sharing** - Assign content to channels
- **Admin dashboard** - Manage users, channels, and audio

## Quick Start

```bash
# Set first admin (development)
./scripts/set_first_admin.sh user@example.com

# Set first admin (production)
DATABASE_URL="postgresql://..." ./scripts/set_first_admin.sh user@example.com
```

## Roles & Access

### Role Types

| Role | Content Visibility | Dashboard Access |
|------|-------------------|------------------|
| **Admin** | ALL content | ✅ Yes |
| **Regular User** | Own content + assigned channels only | ❌ No |

### User States

| State | Can Login | Can View Content | Can Access Dashboard |
|-------|-----------|------------------|---------------------|
| `is_active=false` | ❌ No | ❌ No | ❌ No |
| `is_active=true` | ✅ Yes | ✅ Yes | Only if admin |
| `deleted_at != null` | ❌ No | ❌ No | ❌ No |

## First-Time Admin Setup

### Development

```bash
./scripts/set_first_admin.sh user@example.com
```

### Production

```bash
DATABASE_URL="postgresql://..." ./scripts/set_first_admin.sh user@example.com
```

**What it does**:
1. Creates user if doesn't exist
2. Sets `is_admin=true`
3. Sets `is_active=true`
4. Sets `activated_at` timestamp

## Admin Dashboard

Access: `/dashboard` (admin only)

### Tabs

1. **User Management** (`/dashboard?tab=users`)
   - Activate/inactivate users
   - Toggle admin status
   - Soft delete users

2. **Channel Management** (`/dashboard?tab=channels`)
   - Create/edit/delete channels
   - Assign users to channels
   - View channel members

3. **Audio Management** (`/dashboard?tab=audio`)
   - Assign audio to channels
   - View all transcriptions
   - Manage permissions

## API Endpoints

### User-Accessible Endpoints

**Get transcription channels**:
```http
GET /api/transcriptions/{id}/channels
```

**Assign to channels**:
```http
POST /api/transcriptions/{id}/channels
Content-Type: application/json

{
  "channel_ids": ["uuid-1", "uuid-2"]
}
```

### Admin-Only Endpoints

**User management**:
```http
GET    /api/admin/users           # List all users
PATCH  /api/admin/users/{id}      # Update user (activate, admin)
DELETE /api/admin/users/{id}      # Soft delete user
```

**Channel management**:
```http
GET    /api/admin/channels        # List all channels
POST   /api/admin/channels        # Create channel
PATCH  /api/admin/channels/{id}   # Update channel
DELETE /api/admin/channels/{id}   # Delete channel
```

**Audio management**:
```http
GET    /api/admin/audio           # List all audio
PATCH  /api/admin/audio/{id}      # Update audio (channels)
DELETE /api/admin/audio/{id}      # Delete audio
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  is_active BOOLEAN DEFAULT FALSE,        -- Admin approval required
  is_admin BOOLEAN DEFAULT FALSE,
  activated_at TIMESTAMP,
  deleted_at TIMESTAMP,                   -- Soft delete
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Channels Table

```sql
CREATE TABLE channels (
  id UUID PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Channel Memberships (Junction)

```sql
CREATE TABLE channel_memberships (
  channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  PRIMARY KEY (channel_id, user_id)
);
```

### Transcription Channels (Junction)

```sql
CREATE TABLE transcription_channels (
  transcription_id UUID REFERENCES transcriptions(id) ON DELETE CASCADE,
  channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
  assigned_by UUID REFERENCES users(id),
  assigned_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (transcription_id, channel_id)
);
```

## Permission Logic

### Content Visibility

```python
def get_visible_transcriptions(user):
    """Get transcriptions visible to user"""
    if user.is_admin:
        # Admin sees everything
        return Transcription.query.all()
    else:
        # Regular user sees own + assigned channels
        own_transcriptions = Transcription.filter_by(user_id=user.id).all()
        channel_ids = [c.id for c in user.channels]
        channel_transcriptions = Transcription.filter(
            Transcription.channels.any(Channel.id.in_(channel_ids))
        ).all()
        return own_transcriptions + channel_transcriptions
```

### Channel Assignment

```python
def assign_to_channels(transcription_id, channel_ids, user):
    """Assign transcription to channels (replaces existing)"""
    # Delete existing assignments
    TranscriptionChannel.filter_by(
        transcription_id=transcription_id
    ).delete()

    # Create new assignments
    for channel_id in channel_ids:
        TranscriptionChannel.create(
            transcription_id=transcription_id,
            channel_id=channel_id,
            assigned_by=user.id
        )
```

## Admin Operations

### Activate User

```bash
# Via API
curl -X PATCH http://localhost:8130/api/admin/users/{id} \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'

# Via dashboard
# Navigate to /dashboard?tab=users
# Click "Activate" button
```

### Make User Admin

```bash
# Via API
curl -X PATCH http://localhost:8130/api/admin/users/{id} \
  -H "Content-Type: application/json" \
  -d '{"is_admin": true}'
```

### Create Channel

```bash
# Via API
curl -X POST http://localhost:8130/api/admin/channels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marketing Team",
    "description": "Marketing department transcriptions"
  }'
```

### Assign User to Channel

```bash
# Via API (add to channel)
curl -X POST http://localhost:8130/api/admin/channels/{id}/members \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["uuid-1", "uuid-2"]}'
```

### Assign Audio to Channel

```bash
# Via API
curl -X PATCH http://localhost:8130/api/admin/audio/{id} \
  -H "Content-Type: application/json" \
  -d '{"channel_ids": ["channel-uuid-1", "channel-uuid-2"]}'
```

## User Registration Flow

```
1. User signs in with Google OAuth
    ↓
2. User record created/updated
    - is_active = FALSE (default)
    - is_admin = FALSE (default)
    ↓
3. User redirected to "Pending Approval" page
    ↓
4. Admin receives notification
    ↓
5. Admin activates user via dashboard or API
    ↓
6. User can now login and access content
```

## Cascade Deletes

All related records are deleted when user/channel is deleted:

```sql
-- Delete user → deletes:
-- - channel_memberships (user's channel memberships)
-- - transcriptions (user's own content)
-- - transcription_channels (assignments made by user)

-- Delete channel → deletes:
-- - channel_memberships (channel's members)
-- - transcription_channels (audio assignments to channel)
```

## Troubleshooting

### Issue: New user cannot login

**Cause**: User not activated by admin

**Solution**:
```bash
# Check user status
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \
  "SELECT email, is_active, is_admin FROM users WHERE email='user@example.com';"

# Activate user
./scripts/set_first_admin.sh user@example.com
```

### Issue: User cannot see content

**Cause**: User not assigned to channels

**Solution**:
```bash
# Check channel memberships
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \
  "SELECT c.name FROM channels c
   JOIN channel_memberships cm ON c.id = cm.channel_id
   JOIN users u ON cm.user_id = u.id
   WHERE u.email='user@example.com';"

# Assign user to channels via dashboard or API
```

### Issue: Admin dashboard not accessible

**Cause**: User not admin

**Solution**:
```bash
# Make user admin
curl -X PATCH http://localhost:8130/api/admin/users/{id} \
  -H "Content-Type: application/json" \
  -d '{"is_admin": true}'
```

## Related Skills

```bash
# Production deployment
/whisper-deploy

# Production debugging
/prd_debug

# Database operations via SQL
(prd_debug) db "SELECT * FROM users;"
```

## See Also

- [CLAUDE.md - User & Channel Management](../../CLAUDE.md#user--channel-management)
- [CLAUDE.md - Database Schema](../../CLAUDE.md#database-schema)
- [server/app/api/admin.py](../../server/app/api/admin.py)
