-- Migration 009: Create rejected skills table.
-- Date: 2026-06-26

CREATE TABLE rejected_skills (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
name TEXT NOT NULL,
source TEXT, -- cv|linkedin|manual
reason TEXT,
created_at TIMESTAMPTZ DEFAULT NOW()
);
