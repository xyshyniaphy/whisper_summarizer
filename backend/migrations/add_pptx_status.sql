-- Manual Migration: Add PPTX status tracking to transcriptions table
-- Run this SQL to add the new columns to the existing database

-- Add pptx_status column
ALTER TABLE transcriptions 
ADD COLUMN IF NOT EXISTS pptx_status VARCHAR NOT NULL DEFAULT 'not-started';

-- Add pptx_error_message column  
ALTER TABLE transcriptions 
ADD COLUMN IF NOT EXISTS pptx_error_message TEXT;

-- Update existing records to have default status
UPDATE transcriptions 
SET pptx_status = 'not-started' 
WHERE pptx_status IS NULL;

-- Create index on pptx_status for faster queries
CREATE INDEX IF NOT EXISTS idx_transcriptions_pptx_status 
ON transcriptions(pptx_status);

-- Verify the changes
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'transcriptions' 
AND column_name IN ('pptx_status', 'pptx_error_message');
