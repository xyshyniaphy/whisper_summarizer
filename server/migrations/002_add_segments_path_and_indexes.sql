-- Database Migration: Add segments_path column and missing indexes
-- Date: 2025-01-13
-- Description: This migration ensures all columns and indexes from the SQLAlchemy models exist in the database

-- =============================================================================
-- 1. Add segments_path column to transcriptions table (if not exists)
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'transcriptions' AND column_name = 'segments_path'
    ) THEN
        ALTER TABLE transcriptions ADD COLUMN segments_path VARCHAR(255);
    END IF;
END $$;

-- =============================================================================
-- 2. Create indexes for transcriptions table (for runner performance)
-- =============================================================================

-- Index on status column (for pending/processing queries)
CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);

-- Composite index on status and created_at (for job ordering)
CREATE INDEX IF NOT EXISTS idx_transcriptions_status_created ON transcriptions(status, created_at);

-- =============================================================================
-- 3. Verify all required columns exist
-- =============================================================================

-- Check transcriptions table columns
DO $$
DECLARE
    missing_columns TEXT[];
BEGIN
    -- Check for required columns in transcriptions table
    SELECT ARRAY_AGG(column_name)
    INTO missing_columns
    FROM (
        SELECT 'segments_path' AS column_name
        WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'transcriptions' AND column_name = 'segments_path'
        )
    ) missing;

    IF missing_columns IS NOT NULL THEN
        RAISE NOTICE 'All required columns exist in transcriptions table';
    END IF;
END $$;

-- =============================================================================
-- 4. Verify all required indexes exist
-- =============================================================================

DO $$
DECLARE
    required_indexes TEXT[] := ARRAY[
        'idx_transcriptions_status',
        'idx_transcriptions_status_created'
    ];
    missing_indexes TEXT[];
    idx TEXT;
BEGIN
    FOREACH idx IN ARRAY required_indexes LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'public' AND indexname = idx
        ) THEN
            missing_indexes := array_append(missing_indexes, idx);
        END IF;
    END LOOP;

    IF missing_indexes IS NOT NULL THEN
        RAISE EXCEPTION 'Missing indexes: %', array_to_string(missing_indexes, ', ');
    ELSE
        RAISE NOTICE 'All required indexes exist';
    END IF;
END $$;

-- =============================================================================
-- Migration Complete
-- =============================================================================
