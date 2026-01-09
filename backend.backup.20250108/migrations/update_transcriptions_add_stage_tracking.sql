-- Migration: Update transcriptions table with stage tracking
-- Description: Add process stage, error tracking, retry count, and completion time

-- Add new columns for process tracking
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS stage VARCHAR(50) DEFAULT 'uploading' NOT NULL;
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transcriptions_stage ON transcriptions(stage);
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transcriptions_completed_at ON transcriptions(completed_at);

-- Add comments for documentation
COMMENT ON COLUMN transcriptions.stage IS 'Process stage: uploading, transcribing, summarizing, completed, failed';
COMMENT ON COLUMN transcriptions.error_message IS 'Last error message if processing failed';
COMMENT ON COLUMN transcriptions.retry_count IS 'Number of retry attempts made';
COMMENT ON COLUMN transcriptions.completed_at IS 'Timestamp when processing fully completed';

-- Update existing records to have appropriate stage
UPDATE transcriptions SET stage = CASE
    WHEN status = 'completed' THEN 'completed'
    WHEN status = 'processing' THEN 'transcribing'
    ELSE 'failed'
END WHERE stage IS NULL OR stage = 'uploading';
