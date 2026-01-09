-- Migration 003: Create junction tables for many-to-many relationships
-- Run this SQL to create channel_memberships and transcription_channels tables

-- Create channel_memberships table (users <-> channels)
CREATE TABLE IF NOT EXISTS channel_memberships (
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (channel_id, user_id)
);

-- Create transcription_channels table (transcriptions <-> channels)
CREATE TABLE IF NOT EXISTS transcription_channels (
    transcription_id UUID REFERENCES transcriptions(id) ON DELETE CASCADE,
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (transcription_id, channel_id)
);

-- Create indexes for foreign keys
CREATE INDEX IF NOT EXISTS idx_channel_memberships_user ON channel_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_channel_memberships_channel ON channel_memberships(channel_id);
CREATE INDEX IF NOT EXISTS idx_transcription_channels_transcription ON transcription_channels(transcription_id);
CREATE INDEX IF NOT EXISTS idx_transcription_channels_channel ON transcription_channels(channel_id);

-- Verify channel_memberships
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'channel_memberships'
ORDER BY ordinal_position;

-- Verify transcription_channels
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'transcription_channels'
ORDER BY ordinal_position;
