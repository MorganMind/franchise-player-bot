-- Add stream_points column to users table
-- This tracks streaming points separately from total points
-- Run this in your Supabase SQL editor

ALTER TABLE users ADD COLUMN stream_points INTEGER DEFAULT 0;

-- Update existing users to have 0 stream points
UPDATE users SET stream_points = 0 WHERE stream_points IS NULL;

-- Add comment to document the column
COMMENT ON COLUMN users.stream_points IS 'Points earned specifically from streaming activities (max 8)';
