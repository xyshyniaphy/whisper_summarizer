# Database Schema Reference

**Last Updated**: 2025-01-13
**Database**: PostgreSQL 18
**Schema Version**: 001_add_runner_status + 002_add_segments_path

---

## Table: `users`

User accounts with activation and admin status.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `email` | VARCHAR | | | User email (unique, indexed) |
| `created_at` | TIMESTAMPTZ | | now() | Account creation time |
| `is_active` | BOOLEAN | NOT NULL | false | Account activated? |
| `is_admin` | BOOLEAN | NOT NULL | false | Admin privileges? |
| `activated_at` | TIMESTAMPTZ | | | Activation timestamp |
| `deleted_at` | TIMESTAMPTZ | | | Soft delete timestamp |

**Indexes**:
- `ix_users_email` (UNIQUE)

**Relationships**:
- Has many: `channel_memberships`, `transcriptions`, `chat_messages`

---

## Table: `channels`

Content categories/topics for organizing transcriptions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `name` | VARCHAR(255) | NOT NULL | | Channel name (unique) |
| `description` | TEXT | | | Channel description |
| `created_by` | UUID | | | User who created channel (FK: users.id) |
| `created_at` | TIMESTAMPTZ | | now() | Creation time |
| `updated_at` | TIMESTAMPTZ | | now() | Last update time |

**Indexes**:
- `channels_name_key` (UNIQUE)

**Relationships**:
- Has many: `channel_memberships`, `transcription_channels`

---

## Table: `channel_memberships`

Junction table for users ↔ channels many-to-many relationship.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `channel_id` | UUID | NOT NULL (PK) | | Channel ID (FK: channels.id) |
| `user_id` | UUID | NOT NULL (PK) | | User ID (FK: users.id) |
| `assigned_at` | TIMESTAMPTZ | | now() | Assignment time |
| `assigned_by` | UUID | | | User who made assignment (FK: users.id) |

**Constraints**:
- PRIMARY KEY: (`channel_id`, `user_id`)
- FOREIGN KEY: `channel_id` → `channels.id` (ON DELETE CASCADE)
- FOREIGN KEY: `user_id` → `users.id` (ON DELETE CASCADE)
- FOREIGN KEY: `assigned_by` → `users.id` (ON DELETE SET NULL)

---

## Table: `transcriptions`

Audio transcription records with server/runner architecture fields.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `user_id` | UUID | | | User who uploaded (FK: users.id) |
| `file_name` | VARCHAR | NOT NULL | | Original filename |
| `file_path` | TEXT | | | Original file path |
| `storage_path` | VARCHAR | | | Compressed text path ({uuid}.txt.gz) |
| `segments_path` | VARCHAR | | | Compressed segments path ({uuid}.segments.json.gz) |
| `language` | VARCHAR | | | Detected language |
| `duration_seconds` | FLOAT | | | Audio duration |
| `stage` | VARCHAR | NOT NULL | 'uploading' | Processing stage |
| `error_message` | TEXT | | | Last error message |
| `retry_count` | INTEGER | NOT NULL | 0 | Number of retries |
| `completed_at` | TIMESTAMPTZ | | | Completion time |
| `status` | VARCHAR(20) | NOT NULL | 'pending' | pending/processing/completed/failed |
| `runner_id` | VARCHAR(100) | | | Runner processing this job |
| `started_at` | TIMESTAMPTZ | | | When runner started |
| `processing_time_seconds` | INTEGER | | | Total processing time |
| `pptx_status` | VARCHAR | NOT NULL | 'not-started' | PPTX generation status |
| `pptx_error_message` | TEXT | | | PPTX error details |
| `created_at` | TIMESTAMPTZ | | now() | Creation time |
| `updated_at` | TIMESTAMPTZ | | now() | Last update time |

**Indexes**:
- `idx_transcriptions_status` (for pending/processing queries)
- `idx_transcriptions_status_created` (for job ordering)

**Relationships**:
- Has many: `summaries`, `chat_messages`, `share_links`, `gemini_request_logs`, `transcription_channels`

---

## Table: `transcription_channels`

Junction table for transcriptions ↔ channels many-to-many relationship.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `transcription_id` | UUID | NOT NULL (PK) | | Transcription ID (FK: transcriptions.id) |
| `channel_id` | UUID | NOT NULL (PK) | | Channel ID (FK: channels.id) |
| `assigned_at` | TIMESTAMPTZ | | now() | Assignment time |
| `assigned_by` | UUID | | | User who made assignment (FK: users.id) |

**Constraints**:
- PRIMARY KEY: (`transcription_id`, `channel_id`)
- FOREIGN KEY: `transcription_id` → `transcriptions.id` (ON DELETE CASCADE)
- FOREIGN KEY: `channel_id` → `channels.id` (ON DELETE CASCADE)
- FOREIGN KEY: `assigned_by` → `users.id` (ON DELETE SET NULL)

---

## Table: `summaries`

AI-generated summaries of transcriptions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `transcription_id` | UUID | NOT NULL | | Transcription (FK: transcriptions.id) |
| `summary_text` | TEXT | NOT NULL | | Summary content |
| `model_name` | VARCHAR | | | Model used (e.g., gemini-2.0-flash) |
| `created_at` | TIMESTAMPTZ | | now() | Creation time |

**Constraints**:
- FOREIGN KEY: `transcription_id` → `transcriptions.id` (ON DELETE CASCADE)

---

## Table: `chat_messages`

AI chat messages about transcriptions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `transcription_id` | UUID | NOT NULL | | Transcription (FK: transcriptions.id) |
| `user_id` | UUID | NOT NULL | | User who sent message (FK: users.id) |
| `role` | VARCHAR | NOT NULL | | 'user' or 'assistant' |
| `content` | TEXT | NOT NULL | | Message content |
| `created_at` | TIMESTAMPTZ | | now() | Creation time |

**Indexes**:
- `ix_chat_messages_transcription_id` (for querying chat history)

**Constraints**:
- FOREIGN KEY: `transcription_id` → `transcriptions.id` (ON DELETE CASCADE)
- FOREIGN KEY: `user_id` → `users.id`

---

## Table: `share_links`

Public share links for transcriptions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `transcription_id` | UUID | NOT NULL | | Transcription (FK: transcriptions.id) |
| `share_token` | VARCHAR | NOT NULL | | Unique URL-safe token |
| `created_at` | TIMESTAMPTZ | | now() | Creation time |
| `expires_at` | TIMESTAMPTZ | | | Optional expiration |
| `access_count` | INTEGER | NOT NULL | 0 | Access tracking |

**Indexes**:
- `ix_share_links_share_token` (UNIQUE)
- `ix_share_links_transcription_id`

**Constraints**:
- FOREIGN KEY: `transcription_id` → `transcriptions.id` (ON DELETE CASCADE)

---

## Table: `gemini_request_logs`

Detailed logs of Gemini API requests for debugging.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | uuid_generate() | Primary key |
| `transcription_id` | UUID | NOT NULL | | Transcription (FK: transcriptions.id) |
| `file_name` | VARCHAR(500) | | | Original filename |
| `model_name` | VARCHAR(100) | NOT NULL | | Model used |
| `prompt` | TEXT | NOT NULL | | System prompt |
| `input_text` | TEXT | NOT NULL | | Transcription text |
| `input_text_length` | INTEGER | NOT NULL | | Input character count |
| `output_text` | TEXT | | | Generated summary |
| `output_text_length` | INTEGER | | | Output character count |
| `input_tokens` | INTEGER | | | Token count (in) |
| `output_tokens` | INTEGER | | | Token count (out) |
| `total_tokens` | INTEGER | | | Total tokens |
| `response_time_ms` | FLOAT | | | API response time |
| `temperature` | FLOAT | | | Temperature setting |
| `status` | VARCHAR(50) | NOT NULL | 'success' | success/error/timeout |
| `error_message` | TEXT | | | Error details |
| `created_at` | TIMESTAMPTZ | | now() | Creation time |

**Constraints**:
- FOREIGN KEY: `transcription_id` → `transcriptions.id` (ON DELETE CASCADE)

---

## Migration History

| Version | Date | Description |
|---------|------|-------------|
| `001_add_runner_status` | 2026-01-05 | Added status, runner_id, started_at, processing_time_seconds + indexes |
| `002_add_segments_path` | 2025-01-13 | Added segments_path for Whisper timestamp preservation |

---

## Schema Validation

To validate the production schema matches the SQLAlchemy models:

```bash
# On production server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Check all tables
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c "\dt+"

# Check specific table structure
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c "\d+ transcriptions"

# Check all indexes
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c "SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;"
```

---

## Important Notes

1. **CASCADE Deletes**: Most foreign keys use `ON DELETE CASCADE` for automatic cleanup
2. **Soft Deletes**: Users table has `deleted_at` for soft delete functionality
3. **Timezone Awareness**: All timestamps use `TIMESTAMPTZ` (timezone-aware)
4. **UUID Primary Keys**: All tables use UUID for primary keys
5. **Server/Runner Architecture**: `status`, `runner_id`, `started_at` fields enable job queue system
6. **Segments Preservation**: `segments_path` stores Whisper's native segment data for accurate SRT export

---

## Related Documentation

- `server/app/models/` - SQLAlchemy ORM model definitions
- `server/alembic/versions/` - Alembic migration scripts
- `server/migrations/` - Raw SQL migration scripts
