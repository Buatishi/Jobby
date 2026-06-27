-- Migration 010: Create job descriptions table with HNSW vector index.
-- Date: 2026-06-26

CREATE TABLE job_descriptions (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
source_url TEXT,
raw_text TEXT,
job_title TEXT,
company_name TEXT,
required_seniority TEXT,
required_modality TEXT,
industry TEXT,
tech_stack TEXT[],
required_skills JSONB,
soft_skills TEXT[],
required_education TEXT,
required_languages JSONB,
salary_min INTEGER,
salary_max INTEGER,
currency TEXT,
embedding vector(1536),
created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_job_embedding ON job_descriptions
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
