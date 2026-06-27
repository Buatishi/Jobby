-- Migration 011: Create job matches table.
-- Date: 2026-06-26

CREATE TABLE job_matches (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
job_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
match_score SMALLINT, -- 0-100
potential_score SMALLINT,
representation_score SMALLINT,
gap_origin TEXT, -- skills|seniority|both|none
score_breakdown JSONB,
recommendations JSONB,
user_rating SMALLINT, -- 1-5 (rating inline post-analisis)
ai_model_used TEXT, -- deepseek-chat | claude-sonnet-4-5
created_at TIMESTAMPTZ DEFAULT NOW()
);
