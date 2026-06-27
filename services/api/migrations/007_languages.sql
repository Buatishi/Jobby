-- Migration 007: Create languages table.
-- Date: 2026-06-26

CREATE TABLE languages (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
name TEXT NOT NULL,
proficiency TEXT, -- basic|intermediate|advanced|native
created_at TIMESTAMPTZ DEFAULT NOW()
);
