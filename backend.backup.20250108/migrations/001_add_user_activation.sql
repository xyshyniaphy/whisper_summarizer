-- Migration 001: Add user activation and admin fields
-- Run this SQL to add user management fields to the users table

-- Add is_active column (account activation status)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT FALSE;

-- Add is_admin column (admin role flag)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Add activated_at timestamp (when account was activated)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP;

-- Add deleted_at timestamp (soft delete support)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users(deleted_at);

-- Verify the changes
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('is_active', 'is_admin', 'activated_at', 'deleted_at');
