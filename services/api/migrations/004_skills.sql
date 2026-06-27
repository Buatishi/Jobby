-- Migration 004: Create skills table with HNSW vector index.
-- Date: 2026-06-26

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE skills (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
name TEXT NOT NULL,
category TEXT, -- technical|soft|language|domain
level TEXT, -- beginner|intermediate|advanced|expert
in_cv BOOLEAN DEFAULT FALSE,
in_linkedin BOOLEAN DEFAULT FALSE,
confirmed BOOLEAN DEFAULT FALSE,
embedding vector(1536),
created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_skills_embedding ON skills
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
