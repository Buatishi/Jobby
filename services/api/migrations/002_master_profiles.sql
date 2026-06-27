-- Migration 002: Create master profiles table.
-- Date: 2026-06-26

CREATE TABLE master_profiles (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
headline TEXT,
summary TEXT,
target_role TEXT,
target_seniority TEXT, -- junior|mid|senior|staff|principal
work_modality TEXT, -- remote|hybrid|onsite
target_industry TEXT[],
linkedin_url TEXT,
completeness_pct SMALLINT DEFAULT 0,
inferred_soft_skills TEXT[] DEFAULT '{}',
soft_skills_computed_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW()
);
