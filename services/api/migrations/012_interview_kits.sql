-- Migration 012: Create interview kits table.
-- Date: 2026-06-26

CREATE TABLE interview_kits (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
job_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
match_id UUID REFERENCES job_matches(id) ON DELETE SET NULL,
title TEXT,
questions JSONB,
prep_notes JSONB,
ai_model_used TEXT,
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW()
);
