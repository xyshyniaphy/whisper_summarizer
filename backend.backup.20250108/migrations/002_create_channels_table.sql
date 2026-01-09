-- Migration 002: Create channels table
-- Run this SQL to create the channels table for organizing content

-- Create channels table
CREATE TABLE IF NOT EXISTS channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for created_by foreign key
CREATE INDEX IF NOT EXISTS idx_channels_created_by ON channels(created_by);

-- Verify the changes
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'channels'
ORDER BY ordinal_position;
