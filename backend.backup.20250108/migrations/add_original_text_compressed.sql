-- Add original_text_compressed field for gzip-compressed binary text storage
-- This fixes PostgreSQL SSL connection issues with large text fields

-- Add the new column
ALTER TABLE transcriptions
ADD COLUMN original_text_compressed BYTEA;

-- Add comment for documentation
COMMENT ON COLUMN transcriptions.original_text_compressed IS 'Gzip-compressed binary data for original_text. Used to handle large text without SSL connection issues.';

-- Create index on compressed data for faster queries (optional)
-- CREATE INDEX idx_transcriptions_original_text_compressed ON transcriptions(original_text_compressed) WHERE original_text_compressed IS NOT NULL;
