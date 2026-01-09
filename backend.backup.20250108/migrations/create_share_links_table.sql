-- Create share_links table for public sharing of transcriptions
CREATE TABLE IF NOT EXISTS share_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    share_token VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0 NOT NULL
);

-- Create unique index on share_token for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_share_links_share_token ON share_links(share_token);

-- Create index on transcription_id for finding all shares of a transcription
CREATE INDEX IF NOT EXISTS idx_share_links_transcription_id ON share_links(transcription_id);

-- Create index on expires_at for cleanup of expired links
CREATE INDEX IF NOT EXISTS idx_share_links_expires_at ON share_links(expires_at) WHERE expires_at IS NOT NULL;
