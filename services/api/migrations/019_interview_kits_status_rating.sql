-- Migration 019: Add status and rating fields to interview kits.
-- Date: 2026-06-28

ALTER TABLE interview_kits
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS error_msg TEXT,
ADD COLUMN IF NOT EXISTS user_rating SMALLINT;
